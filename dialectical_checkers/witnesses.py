"""CQ-derived witness producers -> ``MoveProbe`` (design §5).

``probe_moves(board)`` produces one :class:`MoveProbe` per legal move, each
carrying the **FACT-tier** witnesses of design ``notes/checkers-design.md`` §5.
Phase 3a is the FACT-tier layer only; the HEURISTIC §5 rows
(``pro:opposition``, ``obj:back_rank_break``, …) are Phase 5 and are not
produced here.

A witness's tier is determined by what the forced-capture resolver
(``captures.py``) actually **proved** — never asserted. The resolver tags a
fully-resolved (in-budget) line ``Tier.FACT`` and a budget-truncated line
``Tier.HEURISTIC``; this module emits a witness only from a ``Tier.FACT``
resolver result, so a truncated line yields no FACT witness at all (design §5:
"never assert a tier the resolver did not earn").

FACT-tier witnesses produced, per legal move (``mover`` = the side to move):

AS1 pro-reasons (``MoveProbe.reasons``):

* ``pro:terminal_win`` — the move's child is terminal and ``mover`` wins.
* ``pro:material:{n}`` — the move is a capture; ``n`` is the weighted material
  the move's own capture immediately nets the mover.
* ``pro:crown`` — the move advances an uncrowned man onto its king-row.
* ``pro:shot_setup:{n}`` — ``captures.own_shot`` proves the move initiates a
  forced sequence netting the mover ``n`` (FACT only — not truncated).

CQ8_9 / CQ17 objections (``MoveProbe.objections``):

* ``obj:terminal_loss`` — ``captures.opponent_shot`` proves a forced line that
  ends the game with the **opponent** winning.
* ``obj:allows_shot:{n}`` — a **quiet** (non-capture) move that
  ``opponent_shot`` proves lets the opponent force a material gain of ``n``,
  the game not ending.
* ``obj:loses_exchange:{n}`` — a **capture** move whose forced continuation
  the resolver proves nets the mover a material loss of ``n`` (the capture's
  immediate gain minus the opponent's proven recapture).

CQ17 reply attacks (``MoveProbe.reply_attacks``):

* ``reply:terminal_loss`` / ``reply:material:{n}`` — the opponent's proven
  forcing reply after the move (the same ``opponent_shot`` fact, expressed in
  the reply channel; design §6 has both objections and reply attacks defeat a
  move in the crisp layer).

Proven defenses (``MoveProbe.defenses``):

* ``defense:holds_exchange`` — a capture move for which the opponent has a
  proven forcing recapture, but the resolver proves the mover's net swing
  across the whole line is even or favourable: the apparent reply is refuted.

The ``allows_shot`` / ``loses_exchange`` split — both FACT, both
resolver-sourced, with overlapping conditions in design §5 — is partitioned by
``move.is_jump``: a quiet move that walks into a combination is ``allows_shot``;
a capture that comes out behind in the trade is ``loses_exchange``. This is the
one design under-specification resolved in Phase 3a; see the phase report.

This module imports only from within ``dialectical_checkers`` and the stdlib.
pydraughts is a *test* dependency only (the non-oracle-strength stance).
"""

from __future__ import annotations

from dialectical_checkers.arguments import MoveProbe
from dialectical_checkers.board import (
    RED_KING_ROW,
    WHITE_KING_ROW,
    CheckersBoard,
    CheckersMove,
    _coord,
)
from dialectical_checkers.captures import (
    KING_VALUE,
    MAN_VALUE,
    Tier,
    opponent_shot,
    own_shot,
)

_KING_ROW = {"r": RED_KING_ROW, "w": WHITE_KING_ROW}


def _weighted_material(board: CheckersBoard, side: str) -> int:
    """Weighted material for ``side`` on ``board`` — man=100, king=150.

    The same weighting ``captures.py`` uses; counted here so ``witnesses.py``
    does not reach into ``captures``' private helpers.
    """
    total = 0
    for cell in board.cells:
        if cell is None or cell[0] != side:
            continue
        total += KING_VALUE if cell[1] else MAN_VALUE
    return total


def _net_material(board: CheckersBoard, side: str) -> int:
    """Weighted material balance on ``board`` from ``side``'s perspective."""
    other = "w" if side == "r" else "r"
    return _weighted_material(board, side) - _weighted_material(board, other)


def _crowns(board: CheckersBoard, move: CheckersMove) -> bool:
    """True iff ``move`` advances an uncrowned man onto its king-row.

    A move crowns when the moving piece is a *man* (not already a king) and its
    destination square lies on the mover's king-row — for a simple step or for
    a jump that lands on the king-row (which, per ``board.py``, ends the turn).
    """
    cell = board.cells[move.origin - 1]
    if cell is None or cell[1]:
        # Empty origin (should not happen for a legal move) or an already
        # crowned king — a king cannot be crowned again.
        return False
    return _coord(move.destination - 1)[0] == _KING_ROW[board.turn]


def _probe_move(board: CheckersBoard, move: CheckersMove) -> MoveProbe:
    """Build the FACT-tier :class:`MoveProbe` for one legal ``move``."""
    mover = board.turn
    child = board.apply(move)

    reasons: list[str] = []
    objections: list[str] = []
    reply_attacks: list[str] = []
    defenses: list[str] = []

    # --- pro:terminal_win — the move ends the game in the mover's favour ----
    child_terminal_win = child.is_terminal() and child.winner() == mover
    if child_terminal_win:
        reasons.append("pro:terminal_win")

    # --- pro:material — the weighted material the move itself captures ------
    # A capture move's own immediate net gain is the change in the mover's
    # material balance between the root and the child (the move's captures,
    # plus a +50 swing if the moving man crowns on this move).
    if move.is_jump:
        immediate_gain = _net_material(child, mover) - _net_material(board, mover)
        if immediate_gain > 0:
            reasons.append(f"pro:material:{immediate_gain}")
    else:
        immediate_gain = 0

    # --- pro:crown — a man reaches its king-row ----------------------------
    if _crowns(board, move):
        reasons.append("pro:crown")

    # --- pro:shot_setup — own_shot proves a forced winning sequence ---------
    # Only a FACT (non-truncated) own_shot earns a fact-tier reason.
    setup = own_shot(board, move)
    if setup is not None and setup.tier is Tier.FACT:
        reasons.append(f"pro:shot_setup:{setup.material_net}")

    # --- the opponent's forced reply: opponent_shot ------------------------
    # opponent_shot applies the move and resolves; a FACT result is a proven
    # forced sequence the opponent can play. Its material_net is measured from
    # the opponent's perspective after the move.
    shot = opponent_shot(board, move)
    if shot is not None and shot.tier is Tier.FACT:
        if shot.terminal is not None and shot.terminal != mover:
            # The forced reply ends the game with the opponent winning.
            objections.append("obj:terminal_loss")
            reply_attacks.append("reply:terminal_loss")
        elif shot.terminal is None:
            # A forced material gain for the opponent (the game does not end).
            reply_attacks.append(f"reply:material:{shot.material_net}")
            if move.is_jump:
                # A capture move: the mover's net swing across the whole line
                # is its own immediate capture minus the opponent's proven
                # recapture. Negative -> the exchange is genuinely lost;
                # even/favourable -> the apparent reply is refuted.
                mover_swing = immediate_gain - shot.material_net
                if mover_swing < 0:
                    objections.append(f"obj:loses_exchange:{-mover_swing}")
                else:
                    defenses.append("defense:holds_exchange")
            else:
                # A quiet move that walks into a forced combination.
                objections.append(f"obj:allows_shot:{shot.material_net}")

    return MoveProbe(
        pdn=move.pdn(),
        reasons=tuple(reasons),
        objections=tuple(objections),
        reply_attacks=tuple(reply_attacks),
        defenses=tuple(defenses),
    )


def probe_moves(board: CheckersBoard) -> tuple[MoveProbe, ...]:
    """Produce one FACT-tier :class:`MoveProbe` per legal move (design §5).

    The probes are returned in ``board.legal_moves()`` order — already sorted,
    so the result is deterministic. A terminal position (no legal move) yields
    an empty tuple.
    """
    return tuple(_probe_move(board, move) for move in board.legal_moves())
