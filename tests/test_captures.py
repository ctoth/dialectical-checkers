"""Phase 2 — tests for ``dialectical_checkers.captures``.

The forced-capture resolver (design ``notes/checkers-design.md`` §3) is the
exact tactical spine: because captures are mandatory, a capture sequence is a
*bounded, exact* minimax over capture-only moves down to a quiet position.

Three test families, mirroring the project markers:

* ``unit`` — focused contract tests, curated hand-built shot positions, and
  the budget/truncation behaviour.
* ``property`` — the differential test: a seeded set of >=200 reachable
  positions, every non-truncated resolver result checked against an
  INDEPENDENT brute-force reference defined in this file.
* ``differential`` — the pydraughts cross-check: the resolver's claimed forced
  sequence is replayed move-by-move in pydraughts and the material outcome
  confirmed.

The brute-force reference (`brute_force_resolve`) is deliberately naive — a
plain recursive capture-only minimax with no budget and no optimisation — so it
cannot share a bug with the real resolver. pydraughts is imported ONLY in this
file, never by ``dialectical_checkers`` itself (the non-oracle-strength stance).
"""

from __future__ import annotations

import random

import pytest

from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.captures import (
    KING_VALUE,
    MAN_VALUE,
    ResolvedLine,
    ShotResult,
    Tier,
    opponent_shot,
    own_shot,
    resolve,
)

# ---------------------------------------------------------------------------
# Independent brute-force reference (TDD directive)
# ---------------------------------------------------------------------------
#
# A deliberately naive, obviously-correct recursive capture-only minimax. It
# computes the exact forced material outcome of a position from the perspective
# of the side to move at the ROOT. No budget, no optimisation, no caching — so
# it cannot share an implementation bug with the real resolver in captures.py.
#
# Because captures are mandatory (board.legal_moves() returns the jump set when
# any jump exists), the capture tree is small and this recursion always
# terminates: every capture strictly reduces the opponent's piece count, so the
# depth of any capture line is bounded by the total number of pieces.


def _material(board: CheckersBoard, side: str) -> int:
    """Weighted material for ``side`` on ``board`` — man=100, king=150."""
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


def brute_force_resolve(board: CheckersBoard) -> tuple[int, bool, str | None]:
    """Exact forced material outcome of ``board`` — the reference oracle.

    Returns ``(net_swing, forced, terminal)`` where:

    * ``net_swing`` is the change in material balance, from the perspective of
      the side to move at the ROOT, between ``board`` and the quiet (no-capture)
      position the mandatory-capture sequence resolves to.
    * ``forced`` is True iff the realised principal line passed only through
      capture nodes — vacuously True for a quiet root.
    * ``terminal`` is the winning side ("r"/"w") if the resolved line ends a
      game, else None.

    Naive recursion: at a node with captures the side to move picks the capture
    that is best *for it* (minimax — the opponent minimises the root side's
    balance); at a node with no captures the line is quiet and stops.
    """
    root_side = board.turn
    start_balance = _net_material(board, root_side)

    def best_balance(node: CheckersBoard) -> tuple[int, bool, str | None]:
        """Best reachable end-balance (root perspective) by capture-only play."""
        moves = node.legal_moves()
        captures = [m for m in moves if m.is_jump]
        if not captures:
            # Quiet node — the capture sequence has resolved here.
            terminal = node.winner() if not moves else None
            return _net_material(node, root_side), True, terminal
        node_side = node.turn
        results: list[tuple[int, bool, str | None]] = []
        for mv in captures:
            results.append(best_balance(node.apply(mv)))
        if node_side == root_side:
            # Root side moves: maximise the root-perspective balance.
            chosen = max(results, key=lambda r: r[0])
        else:
            # Opponent moves: minimise the root-perspective balance.
            chosen = min(results, key=lambda r: r[0])
        # forced stays True: every node visited here had only captures.
        return chosen[0], True, chosen[2]

    end_balance, forced, terminal = best_balance(board)
    return end_balance - start_balance, forced, terminal


# ---------------------------------------------------------------------------
# Position generation for the differential test
# ---------------------------------------------------------------------------


def _reachable_boards(seed: int, max_plies: int) -> list[CheckersBoard]:
    """A deterministic random walk from the start; every visited board."""
    rng = random.Random(seed)
    board = CheckersBoard.initial()
    visited = [board]
    for _ in range(max_plies):
        moves = board.legal_moves()
        if not moves:
            break
        board = board.apply(rng.choice(moves))
        visited.append(board)
        if board.is_draw():
            break
    return visited


def differential_positions(target: int) -> list[CheckersBoard]:
    """At least ``target`` distinct positions from varied seeded walks.

    Walks start from the standard opening with many different seeds and varied
    depths, so the sample spans openings, midgames reached after exchanges, and
    capture-rich tactical positions.
    """
    seen: set[str] = set()
    out: list[CheckersBoard] = []
    seed = 0
    while len(out) < target:
        for depth in (8, 16, 24, 32, 44):
            for board in _reachable_boards(seed, depth):
                fen = board.to_fen()
                if fen in seen:
                    continue
                seen.add(fen)
                out.append(board)
        seed += 1
        if seed > 5_000:  # safety — should never be hit
            break
    return out


# ---------------------------------------------------------------------------
# pydraughts cross-check helpers (test-only — directive)
# ---------------------------------------------------------------------------


def _oracle_material(fen: str, side: str) -> int:
    """Weighted material for ``side`` from a PDN-FEN, via pydraughts' parse.

    Recomputed from the FEN that pydraughts produced after replaying a move —
    this confirms the engine's resolved sequence yields the same board the
    oracle reaches.
    """
    parts = fen.strip().split(":")
    field_for = {"W": "w", "B": "r"}
    total = 0
    for field_text in parts[1:]:
        tag, body = field_text[0], field_text[1:]
        colour = field_for[tag]
        if colour != side or not body:
            continue
        for token in body.split(","):
            token = token.strip()
            if not token:
                continue
            total += KING_VALUE if token.startswith("K") else MAN_VALUE
    return total


def _oracle_net(fen: str, root_side: str) -> int:
    """Material balance from a PDN-FEN, from ``root_side``'s perspective."""
    other = "w" if root_side == "r" else "r"
    return _oracle_material(fen, root_side) - _oracle_material(fen, other)


def _replay_principal_line_in_oracle(board: CheckersBoard) -> tuple[str, int]:
    """Replay the resolver's forced principal line move-by-move in pydraughts.

    Walks the engine's own capture minimax (same selection rule the resolver
    uses), and at every step asserts the chosen move is legal in pydraughts.
    Returns ``(final_fen, net_swing)`` — the oracle's FEN at the quiet position
    and the material swing it implies, from the root side's perspective.
    """
    from draughts import Board as OracleBoard

    root_side = board.turn
    start_fen = board.to_fen()
    start_balance = _oracle_net(start_fen, root_side)

    oracle = OracleBoard(variant="english", fen=start_fen)
    node = board
    while True:
        captures = [m for m in node.legal_moves() if m.is_jump]
        if not captures:
            break
        node_side = node.turn

        def line_value(mv: CheckersMove) -> int:
            child = resolve(node.apply(mv))
            # resolve returns swing from the child's root side; re-express as
            # this node's swing by negating when the child root differs.
            sign = 1 if node.apply(mv).turn == root_side else -1
            return sign * child.material_swing

        # Pick the move the resolver's minimax would pick at this node.
        if node_side == root_side:
            chosen = max(captures, key=lambda m: (line_value(m), m.pdn()))
        else:
            chosen = min(captures, key=lambda m: (line_value(m), m.pdn()))

        oracle_pdns = {
            ("x" if m.has_captures else "-").join(
                str(s) for s in m.steps_move
            ): m
            for m in oracle.legal_moves()
        }
        assert chosen.pdn() in oracle_pdns, (
            f"resolver's forced move {chosen.pdn()} not legal in pydraughts "
            f"at {node.to_fen()} (oracle moves {sorted(oracle_pdns)})"
        )
        oracle.push(oracle_pdns[chosen.pdn()])
        node = node.apply(chosen)

    final_fen = oracle.fen
    return final_fen, _oracle_net(final_fen, root_side) - start_balance


# ---------------------------------------------------------------------------
# unit — core contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_quiet_root_resolves_to_zero_swing() -> None:
    """A position with no captures resolves to zero swing, forced, FACT tier."""
    board = CheckersBoard.initial()
    line = resolve(board)
    assert isinstance(line, ResolvedLine)
    assert line.material_swing == 0
    assert line.forced is True
    assert line.truncated is False
    assert line.terminal is None
    assert line.tier is Tier.FACT


@pytest.mark.unit
def test_single_capture_nets_one_man() -> None:
    """A forced single capture nets the root side exactly one man (100)."""
    # Red man on 15, lone White man on 18: forced 15x22, White then has no
    # piece and no move -> terminal loss for White.
    board = CheckersBoard.from_fen("B:W18:B15")
    line = resolve(board)
    assert line.material_swing == MAN_VALUE
    assert line.forced is True
    assert line.truncated is False
    assert line.terminal == "r"
    assert line.tier is Tier.FACT


@pytest.mark.unit
def test_double_jump_nets_two_men() -> None:
    """A forced double jump nets the root side two men (200)."""
    board = CheckersBoard.from_fen("B:W16,24:B11")
    line = resolve(board)
    assert line.material_swing == 2 * MAN_VALUE
    assert line.forced is True
    assert line.truncated is False


@pytest.mark.unit
def test_resolve_matches_reference_on_quiet_and_capture() -> None:
    """The resolver agrees with the brute-force reference on simple cases."""
    for fen in ("B:W18:B15", "B:W16,24:B11", "B:W25,26:B21"):
        board = CheckersBoard.from_fen(fen)
        swing, forced, terminal = brute_force_resolve(board)
        line = resolve(board)
        assert line.material_swing == swing, fen
        assert line.forced == forced, fen
        assert line.terminal == terminal, fen


# ---------------------------------------------------------------------------
# unit — curated hand-built shot positions (directive: >=4)
# ---------------------------------------------------------------------------
#
# Each entry: (label, FEN, expected net swing from root side's perspective).
# All are verified against the brute-force reference AND pydraughts below.

CURATED_SHOTS: list[tuple[str, str, int]] = [
    # All expected swings are from the ROOT side's perspective and were
    # independently confirmed by scripts/verify_curated_shots.py — a standalone
    # capture-only minimax whose principal line is replayed in pydraughts. The
    # swing is the change in WEIGHTED material (man=100, king=150), so a man
    # that crowns inside the forced line contributes its +50 king bonus.
    #
    # 1. Plain single capture: Red 15 takes White 18 (15x22). White has no
    #    piece left -> terminal loss for White. Nets one man.
    ("single_man_capture", "B:W18:B15", MAN_VALUE),
    # 2. Double jump: Red 11 takes White 16 then 24 (11x20x27). Nets two men.
    ("double_jump", "B:W16,24:B11", 2 * MAN_VALUE),
    # 3. Two-for-zero crowning shot: Red 15 is forced into 15x22, which
    #    continues 22x31 capturing White 26 as well, and 31 is Red's king-row
    #    so the man crowns. Net = two men captured (200) + the crown bonus
    #    (50) = 250.
    ("double_capture_with_crown", "B:W18,26:B15", 2 * MAN_VALUE + 50),
    # 4. A genuine 2-for-1: Red has men on 14 and 15, White a lone man on 18.
    #    Red 15 is forced to take 18 (15x22). After 15x22 White has no piece
    #    -> terminal. Red kept the man on 14 and gained one -> net +100.
    ("two_men_one_capture", "B:W18:B14,15", MAN_VALUE),
    # 5. White-to-move forced double: White man on 22 must take Red 18
    #    (22x15), then continues 15x8 capturing Red 11. White nets two Red
    #    men (200) and Red is left with no piece -> terminal win for White.
    ("white_double_capture", "W:W22:B11,18", 2 * MAN_VALUE),
    # 6. Crowning shot: Red man on 21 takes White 25, landing on king-row 30
    #    and crowning; the crown ends the turn. Net = one man captured (100) +
    #    the crown bonus (50) = 150.
    ("crowning_capture", "B:W25:B21", MAN_VALUE + 50),
]


@pytest.mark.unit
@pytest.mark.parametrize(
    "label,fen,expected",
    CURATED_SHOTS,
    ids=[c[0] for c in CURATED_SHOTS],
)
def test_curated_shot_outcomes(label: str, fen: str, expected: int) -> None:
    """Each curated shot resolves to its hand-computed forced net outcome."""
    board = CheckersBoard.from_fen(fen)
    line = resolve(board)
    assert line.truncated is False, f"{label} should resolve within budget"
    assert line.material_swing == expected, label
    # The brute-force reference must agree — independent confirmation.
    ref_swing, ref_forced, ref_terminal = brute_force_resolve(board)
    assert ref_swing == expected, f"reference disagrees on {label}"
    assert line.forced == ref_forced, label
    assert line.terminal == ref_terminal, label


# ---------------------------------------------------------------------------
# differential — pydraughts cross-check of the principal line (directive)
# ---------------------------------------------------------------------------


@pytest.mark.differential
@pytest.mark.parametrize(
    "label,fen,expected",
    CURATED_SHOTS,
    ids=[c[0] for c in CURATED_SHOTS],
)
def test_curated_shots_match_pydraughts(label: str, fen: str, expected: int) -> None:
    """Replay the resolver's forced line in pydraughts; outcome must match.

    Every move the resolver's minimax would play is asserted legal in
    pydraughts, and the final material swing pydraughts reaches equals the
    resolver's ``material_swing``.
    """
    board = CheckersBoard.from_fen(fen)
    line = resolve(board)
    final_fen, oracle_swing = _replay_principal_line_in_oracle(board)
    assert oracle_swing == expected, f"{label}: oracle swing {oracle_swing}"
    assert oracle_swing == line.material_swing, (
        f"{label}: resolver {line.material_swing} != oracle {oracle_swing} "
        f"(final {final_fen})"
    )


@pytest.mark.differential
def test_multi_capture_positions_match_pydraughts() -> None:
    """Resolver's forced line is legal & outcome-correct in pydraughts.

    A set of capture-rich positions: the resolver's principal line is replayed
    move-by-move in pydraughts; each step must be legal and the final material
    swing must equal the resolver's claim.
    """
    multi_capture_fens = [
        "B:W16,24:B11",  # double jump
        "B:W18,26:B15",  # even exchange chain
        "B:W7,15,23,24:BK2",  # king multi-jump
        "B:W18,25,26:BK14",  # king triple jump
        "B:W17,18,25,26:BK14",  # king loop capture
        "B:W22:B11,18",  # white-to-move forced exchange
    ]
    for fen in multi_capture_fens:
        board = CheckersBoard.from_fen(fen)
        line = resolve(board)
        if line.truncated:
            continue  # truncated lines make no exact claim
        final_fen, oracle_swing = _replay_principal_line_in_oracle(board)
        assert oracle_swing == line.material_swing, (
            f"{fen}: resolver {line.material_swing} != oracle {oracle_swing} "
            f"(final {final_fen})"
        )


# ---------------------------------------------------------------------------
# property — the brute-force differential over >=200 positions (directive)
# ---------------------------------------------------------------------------


@pytest.mark.property
def test_differential_resolve_vs_brute_force() -> None:
    """Every non-truncated resolver result equals the brute-force reference.

    On a deterministic seeded set of >=200 reachable positions, the resolver's
    ``(material_swing, forced, terminal)`` must equal the independent
    brute-force capture-only minimax for every position whose result is not
    truncated (a truncated result makes no exact claim — design §3/§4).
    """
    positions = differential_positions(target=260)
    assert len(positions) >= 200, len(positions)
    checked = 0
    truncated = 0
    for board in positions:
        line = resolve(board)
        if line.truncated:
            truncated += 1
            continue
        ref_swing, ref_forced, ref_terminal = brute_force_resolve(board)
        fen = board.to_fen()
        assert line.material_swing == ref_swing, (
            f"swing mismatch at {fen}: resolver {line.material_swing} "
            f"!= reference {ref_swing}"
        )
        assert line.forced == ref_forced, f"forced mismatch at {fen}"
        assert line.terminal == ref_terminal, f"terminal mismatch at {fen}"
        assert line.tier is Tier.FACT, f"non-truncated must be FACT at {fen}"
        checked += 1
    # The vast majority of reachable positions resolve fully within budget.
    assert checked >= 200, f"only {checked} non-truncated positions checked"


@pytest.mark.property
def test_capture_positions_are_exercised() -> None:
    """The differential sample actually contains capture positions.

    A differential test over only quiet positions would be vacuous. Confirm the
    seeded sample includes positions where the side to move has a forced
    capture, so the resolver's recursion is genuinely exercised.
    """
    positions = differential_positions(target=260)
    with_captures = sum(
        1
        for b in positions
        if any(m.is_jump for m in b.legal_moves())
    )
    assert with_captures >= 20, with_captures


# ---------------------------------------------------------------------------
# unit — budget / truncation (directive)
# ---------------------------------------------------------------------------


# A position with a genuinely multi-PLY capture tree: captures by both sides
# spread across several plies, so the resolver's minimax descends through many
# nodes (48 — see scripts/find_truncation_position.py). A lone multi-jump is a
# single CheckersMove (board.py expands the whole chain) and would give a
# one-node tree that no budget could truncate; this position does not.
TRUNCATION_FEN = "W:W18,22,23,24,26,27,28,30,32:B1,3,4,5,7,11,12,14,19"


@pytest.mark.unit
def test_budget_truncation_yields_heuristic_tier() -> None:
    """A position exceeding the node budget yields a truncated HEURISTIC line.

    Passing a deliberately tiny budget forces truncation on a position whose
    capture tree is larger than the budget. A truncated line must be marked
    ``truncated`` and ``Tier.HEURISTIC`` — never a confident FACT-tier claim.
    """
    board = CheckersBoard.from_fen(TRUNCATION_FEN)
    line = resolve(board, max_depth=1, max_nodes=1)
    assert line.truncated is True
    assert line.tier is Tier.HEURISTIC


@pytest.mark.unit
def test_truncated_result_is_not_a_false_fact() -> None:
    """A truncated result never claims FACT tier even when its swing is wrong.

    With a tiny budget the resolver computes an incomplete swing. The contract
    is: it must NOT label that incomplete result FACT. For this position the
    truncated swing (200) genuinely differs from the true forced swing (100) —
    so a FACT label would be an outright false claim; the resolver marks it
    HEURISTIC instead. The full (un-budgeted) resolve is exact and equals the
    brute-force reference.
    """
    board = CheckersBoard.from_fen(TRUNCATION_FEN)
    truncated = resolve(board, max_depth=1, max_nodes=1)
    full = resolve(board)
    ref_swing, _, _ = brute_force_resolve(board)
    # The full resolve is exact and matches the reference.
    assert full.truncated is False
    assert full.tier is Tier.FACT
    assert full.material_swing == ref_swing
    # The truncated resolve disagrees with the truth here — and is honestly
    # marked HEURISTIC, never FACT, precisely because of that.
    assert truncated.truncated is True
    assert truncated.tier is Tier.HEURISTIC
    assert truncated.material_swing != full.material_swing


@pytest.mark.unit
def test_generous_budget_does_not_truncate_normal_positions() -> None:
    """Reachable positions resolve fully under the default budget."""
    for board in _reachable_boards(seed=7, max_plies=40):
        line = resolve(board)
        # Default budget is sized so ordinary capture trees fully resolve.
        assert line.truncated is False, board.to_fen()


# ---------------------------------------------------------------------------
# unit — opponent_shot / own_shot (design §3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_opponent_shot_detects_forced_loss() -> None:
    """``opponent_shot`` flags a move that hands the opponent a forced capture.

    Red king on 23, Red also has a man on 7; White man on 18. If Red plays the
    quiet king move 23-18? not possible (18 occupied). Construct directly: Red
    to move plays a quiet move that exposes a man to a forced White capture.

    Position: Red men on 9 and 14, White man on 22. Red plays 9-13 (quiet).
    After 9-13 it is White's move; White man 22 has no capture. So instead use:
    Red man on 15, White man on 24. Red plays 15-19; now White 24x15 captures
    -> opponent_shot must report a forced material gain for White.
    """
    board = CheckersBoard.from_fen("B:W24:B15")
    # Red's quiet move 15-19 places the Red man where White 24 can jump it.
    move = CheckersMove(path=(15, 19), captured=())
    assert move in board.legal_moves()
    shot = opponent_shot(board, move)
    assert shot is not None
    assert isinstance(shot, ShotResult)
    # White nets one Red man: from White's perspective +100.
    assert shot.material_net == MAN_VALUE
    assert shot.forced is True


@pytest.mark.unit
def test_opponent_shot_returns_none_for_safe_move() -> None:
    """``opponent_shot`` returns None when the move concedes nothing."""
    board = CheckersBoard.from_fen("B:W24:B15")
    # Red's other quiet move 15-18 does not expose the man to White 24.
    move = CheckersMove(path=(15, 18), captured=())
    assert move in board.legal_moves()
    assert opponent_shot(board, move) is None


@pytest.mark.unit
def test_own_shot_detects_initiating_a_winning_capture() -> None:
    """``own_shot`` flags a move that itself initiates a forced winning gain.

    Red man on 11 to move: the only legal move is the forced double jump
    11x20x27 (captures White 16 and 24). That move IS a forced winning
    sequence — ``own_shot`` must report a net gain of two men.
    """
    board = CheckersBoard.from_fen("B:W16,24:B11")
    move = board.legal_moves()[0]
    assert move.is_jump
    shot = own_shot(board, move)
    assert shot is not None
    assert shot.material_net == 2 * MAN_VALUE
    assert shot.forced is True


@pytest.mark.unit
def test_own_shot_returns_none_for_even_or_losing_move() -> None:
    """``own_shot`` returns None when the move wins no material.

    A quiet move from a quiet position initiates no forced gain.
    """
    board = CheckersBoard.initial()
    move = board.legal_moves()[0]
    assert not move.is_jump
    assert own_shot(board, move) is None
