"""Forced-capture resolver — the exact tactical spine (design §3).

Because captures are mandatory in English draughts (``board.legal_moves()``
returns the jump set whenever any jump exists, WCDF 1.20), a capture sequence
is a **bounded, exact** computation — the draughts analog of quiescence search,
but *complete within a chain* rather than heuristic.

``resolve(board)`` runs a minimax over **capture-only** moves of both sides
until a *quiet* position (the side to move has no capture) is reached, and
reports the net weighted-material swing from the perspective of the side to
move at the ROOT, whether the realised line was *forced*, whether the line was
*truncated* by the recursion budget, and the terminal status if the line ends
the game.

Two derived queries the witness layer (§5) consumes:

* ``opponent_shot(board, move)`` — apply ``move``, resolve; if the opponent has
  a forced sequence netting material or the game, return a ``ShotResult``. This
  is the provable, fact-tier ``obj:allows_shot`` defeater.
* ``own_shot(board, move)`` — does ``move`` itself initiate a forced winning
  sequence? The ``pro:shot_setup`` reason.

Budget: the recursion is bounded by a **depth cap** and a **node cap** (design
§3, mirroring the chess ``ReplyAnalysisCache``). A line that hits the budget is
marked ``truncated`` and carries ``Tier.HEURISTIC`` — honesty about what was
proven; a fully resolved line (budget not hit) carries ``Tier.FACT``
(``Bench-Capon_2003`` fact-as-highest-value, design §4).

This module imports only from within ``dialectical_checkers`` and the stdlib.
pydraughts is a *test* dependency only (the non-oracle-strength stance).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dialectical_checkers.board import CheckersBoard, CheckersMove

# --- Material weights -------------------------------------------------------
#
# Design §8 / port-plan §5.6: a man is worth 100, a king 150 (kings ~= 1.5
# men). The resolver's material swing is the change in this WEIGHTED balance,
# so a man that crowns inside a forced line contributes its +50 king bonus.

MAN_VALUE = 100
KING_VALUE = 150


# --- Budget -----------------------------------------------------------------
#
# A capture node strictly reduces the opponent's piece count, so any capture
# line is at most 24 plies deep (12 pieces a side) — but chained multi-jumps
# and king loops keep the realised tree very small in practice. The defaults
# are sized generously so every position reachable in normal play resolves
# fully (Tier.FACT); the budget exists to bound pathological trees, not to
# truncate ordinary tactics.

DEFAULT_MAX_DEPTH = 64
DEFAULT_MAX_NODES = 20_000


class Tier(Enum):
    """Evidence tier (design §4 — ``Bench-Capon_2003`` fact-as-highest-value).

    ``FACT`` — the line was resolved completely within the budget; the result
    is proven exactly. ``HEURISTIC`` — the budget was hit, the line is
    truncated, and the result is an estimate, never a proof.
    """

    FACT = "fact"
    HEURISTIC = "heuristic"


@dataclass(frozen=True)
class ResolvedLine:
    """The outcome of resolving a forced capture sequence (design §3).

    ``material_swing`` — the change in weighted material balance, from the
    perspective of the side to move at the ROOT board, between the root and the
    quiet position the mandatory-capture sequence resolves to. Positive means
    the root side gains.

    ``forced`` — True iff the realised principal line passed only through
    capture nodes (every node's move set was the mandatory jump set). A quiet
    root resolves to an empty line and ``forced`` is vacuously True.

    ``truncated`` — True iff the recursion budget was hit; the result is then
    an estimate, not a proof.

    ``terminal`` — the winning side (``"r"``/``"w"``) if the resolved quiet
    position ends the game, else ``None``.

    ``tier`` — ``Tier.FACT`` iff not truncated, else ``Tier.HEURISTIC``.

    ``principal_line`` — the exact sequence of capture moves the minimax
    selected, from the root to the quiet position it resolved to. Empty for a
    quiet root. This is the resolver's *claimed* line: a cross-check (e.g. the
    pydraughts replay in the test suite) can replay these moves and verify the
    claim independently, without re-running the resolver's selection.
    """

    material_swing: int
    forced: bool
    truncated: bool
    terminal: str | None
    tier: Tier
    principal_line: tuple[CheckersMove, ...] = ()


@dataclass(frozen=True)
class ShotResult:
    """A proven forced capture sequence netting material or the game (design §3).

    ``material_net`` is the net weighted-material gain for the side the shot
    favours (the *opponent* for ``opponent_shot``, the *mover* for
    ``own_shot``). ``forced``/``truncated``/``terminal``/``tier`` mirror
    ``ResolvedLine``.
    """

    material_net: int
    forced: bool
    truncated: bool
    terminal: str | None
    tier: Tier


# --- material ---------------------------------------------------------------


def _material(board: CheckersBoard, side: str) -> int:
    """Weighted material for ``side`` on ``board`` (man=100, king=150)."""
    total = 0
    for cell in board.cells:
        if cell is None or cell[0] != side:
            continue
        total += KING_VALUE if cell[1] else MAN_VALUE
    return total


def _net_material(board: CheckersBoard, root_side: str) -> int:
    """Material balance on ``board`` from ``root_side``'s perspective."""
    other = "w" if root_side == "r" else "r"
    return _material(board, root_side) - _material(board, other)


# --- the recursive capture-only minimax -------------------------------------


@dataclass
class _Budget:
    """Mutable recursion budget — node count consumed, depth cap, hit flag."""

    nodes_left: int
    max_depth: int
    hit: bool = False


def _outcome_rank(balance: int, terminal: str | None, root_side: str) -> tuple[int, int]:
    """Total-order key for a capture-line outcome, from ``root_side``'s view.

    The minimax must NOT rank outcomes on material alone (the analyst's
    CRITICAL finding): a forced terminal *game* win is worth more than any
    material gain, and a forced terminal *game* loss is worse than any material
    loss. So an outcome is ranked first by a three-valued **terminal band** and
    only then, within the non-terminal band, by weighted material:

    * band ``+1`` — the resolved quiet position is terminal and ``root_side``
      wins the GAME. Outranks every non-terminal and every losing outcome.
    * band ``0`` — non-terminal (including a budget-truncated line, which
      claims no terminal). Ranked among itself by ``balance``.
    * band ``-1`` — terminal and ``root_side`` loses the GAME. Outranked by
      every non-terminal and every winning outcome.

    The returned ``(band, balance)`` tuple is a total order: comparing it with
    ``>`` / ``<`` gives terminal-dominates-material at both kinds of node. A
    maximising (root-side) node takes the ``max`` of this key — it prefers any
    win and avoids any loss; a minimising (opponent) node takes the ``min`` —
    it prefers handing ``root_side`` a loss and avoids handing it a win. The
    defect is therefore fixed symmetrically by one shared ordering.
    """
    if terminal is None:
        band = 0
    elif terminal == root_side:
        band = 1
    else:
        band = -1
    return (band, balance)


def _resolve_balance(
    node: CheckersBoard,
    root_side: str,
    depth: int,
    budget: _Budget,
) -> tuple[int, str | None, tuple[CheckersMove, ...]]:
    """Best end-balance reachable from ``node`` by capture-only play.

    Returns ``(balance, terminal, line)`` — the weighted material balance from
    ``root_side``'s perspective at the quiet position the mandatory-capture
    minimax resolves to, the winning side if that position is terminal, and
    ``line``, the exact sequence of capture moves the minimax selected from
    ``node`` down to that quiet position.

    Minimax over the :func:`_outcome_rank` total order: at a node where the
    *root* side is to move it maximises that key; at an opponent node it
    minimises it. Because the key bands a terminal game-win above every
    material outcome and a terminal game-loss below every material outcome,
    a forced win is never discarded for a larger material swing and a forced
    loss is never preferred over a material loss — at BOTH node kinds. Only
    capture moves are followed — a node with no capture is *quiet* and the
    recursion stops there. The budget bounds both depth and node count; when it
    is hit ``budget.hit`` is set and the current node is treated as quiet (its
    static balance is returned, terminal ``None``, empty line), so the caller
    can mark the line truncated.

    Tie-breaking is deterministic: when two children share the same outcome
    rank the first in ``legal_moves()`` order (already sorted) is kept, so the
    reported ``line`` is reproducible.
    """
    moves = node.legal_moves()
    captures = [m for m in moves if m.is_jump]

    if not captures:
        # Quiet node — the capture sequence has resolved here. A node with no
        # legal move at all is terminal: the side to move loses.
        terminal = node.winner() if not moves else None
        return _net_material(node, root_side), terminal, ()

    if depth >= budget.max_depth or budget.nodes_left <= 0:
        # Budget exhausted: stop and report the static balance. Honest — the
        # line is truncated, the caller will mark it HEURISTIC.
        budget.hit = True
        return _net_material(node, root_side), None, ()

    node_side = node.turn
    best_balance: int | None = None
    best_terminal: str | None = None
    best_rank: tuple[int, int] | None = None
    best_line: tuple[CheckersMove, ...] = ()
    for move in captures:
        budget.nodes_left -= 1
        child = node.apply(move)
        balance, terminal, sub_line = _resolve_balance(
            child, root_side, depth + 1, budget
        )
        rank = _outcome_rank(balance, terminal, root_side)
        if best_rank is None:
            best_balance, best_terminal, best_rank = balance, terminal, rank
            best_line = (move, *sub_line)
        elif node_side == root_side:
            # Root side: prefer the highest-ranked outcome (any terminal win
            # over any material; any material over any terminal loss).
            if rank > best_rank:
                best_balance, best_terminal, best_rank = balance, terminal, rank
                best_line = (move, *sub_line)
        else:
            # Opponent: prefer the lowest-ranked outcome for the root side.
            if rank < best_rank:
                best_balance, best_terminal, best_rank = balance, terminal, rank
                best_line = (move, *sub_line)

    # ``captures`` is non-empty, so the best outcome was assigned.
    assert best_balance is not None
    return best_balance, best_terminal, best_line


def resolve(
    board: CheckersBoard,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> ResolvedLine:
    """Resolve all forced capture sequences from ``board`` (design §3).

    Runs a capture-only minimax of both sides down to a quiet position and
    returns a :class:`ResolvedLine`. ``max_depth`` / ``max_nodes`` bound the
    recursion; hitting either marks the result truncated / ``Tier.HEURISTIC``.

    A *quiet* root (the side to move has no capture) resolves immediately to a
    zero swing — ``forced`` is vacuously True; ``terminal`` is set only if the
    root itself is a no-move terminal position.
    """
    root_side = board.turn
    budget = _Budget(nodes_left=max_nodes, max_depth=max_depth)

    start_balance = _net_material(board, root_side)
    end_balance, terminal, line = _resolve_balance(board, root_side, 0, budget)

    truncated = budget.hit
    # Every node the minimax descends through is a capture node, and captures
    # are mandatory whenever they exist (WCDF 1.20) — so any line the resolver
    # realises consisted only of forced moves. A quiet root yields the empty
    # line, which is forced vacuously. Hence ``forced`` is always True for the
    # line ``resolve`` produces; it is kept as an explicit field because the
    # witness layer (§5) reads it and a future non-mandatory variant would set
    # it differently.
    return ResolvedLine(
        material_swing=end_balance - start_balance,
        forced=True,
        truncated=truncated,
        terminal=terminal,
        tier=Tier.HEURISTIC if truncated else Tier.FACT,
        principal_line=line,
    )


# --- derived shot queries ---------------------------------------------------


def opponent_shot(
    board: CheckersBoard,
    move: CheckersMove,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> ShotResult | None:
    """The provable ``obj:allows_shot`` defeater (design §3).

    Apply ``move`` on ``board`` and resolve the resulting position. After
    ``move`` the *opponent* is to move, so ``resolve`` reports the swing from
    the opponent's perspective. If that forced sequence nets the opponent
    material (or the game), return a :class:`ShotResult` describing it; if the
    move concedes nothing, return ``None``.

    A truncated resolution is still returned (it may have *under*-estimated the
    loss) but carries ``Tier.HEURISTIC`` — the witness layer will not treat it
    as a fact-tier defeater.
    """
    after = board.apply(move)
    line = resolve(after, max_depth=max_depth, max_nodes=max_nodes)
    # ``after.turn`` is the opponent; ``line.material_swing`` is already from
    # the opponent's perspective. A shot exists when the opponent gains
    # material or wins the game outright.
    opponent = after.turn
    wins_game = line.terminal == opponent
    if line.material_swing <= 0 and not wins_game:
        return None
    return ShotResult(
        material_net=line.material_swing,
        forced=line.forced,
        truncated=line.truncated,
        terminal=line.terminal,
        tier=line.tier,
    )


def own_shot(
    board: CheckersBoard,
    move: CheckersMove,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> ShotResult | None:
    """The ``pro:shot_setup`` reason (design §3).

    Does ``move`` *initiate* a forced winning sequence for the mover? ``move``
    must itself be a capture (a quiet move starts no forced sequence). The shot
    value is the swing of the whole line that **begins with** ``move`` — the
    material ``move`` itself captures plus whatever the forced continuation of
    both sides then nets — measured from the *mover's* perspective. If the mover
    comes out ahead in material (or wins the game), return a :class:`ShotResult`;
    otherwise ``None``.

    A truncated resolution is returned with ``Tier.HEURISTIC`` — an unproven
    setup is not a fact-tier reason.
    """
    if not move.is_jump:
        # A quiet move begins no forced capture sequence.
        return None
    mover = board.turn
    after = board.apply(move)
    budget = _Budget(nodes_left=max_nodes, max_depth=max_depth)
    # Resolve the rest of the mandatory-capture chain after ``move``, measuring
    # the balance from the MOVER's perspective so the swing spans ``move``
    # itself. ``before`` is the balance at the root position (before ``move``).
    before = _net_material(board, mover)
    end_balance, terminal, _line = _resolve_balance(after, mover, 0, budget)
    truncated = budget.hit
    mover_swing = end_balance - before
    wins_game = terminal == mover
    if mover_swing <= 0 and not wins_game:
        return None
    return ShotResult(
        material_net=mover_swing,
        forced=True,
        truncated=truncated,
        terminal=terminal,
        tier=Tier.HEURISTIC if truncated else Tier.FACT,
    )
