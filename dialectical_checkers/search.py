"""Negamax skeleton + checkers static eval (design §8).

Phase 3b implements the **static evaluation** only — the material-first
``static_evaluation`` of design §8 (man = 100, king = 150), needed as the
deterministic tiebreak of the FACT-tier selector (``selection.py``, design
§7 key term 5). Deeper search is not required for Phase 3b: the decision is
the argument layers, search is only a witness source / tiebreak.

The negamax recursion skeleton (design §8 — copied from dialectical-chess,
with the no-stalemate terminal change) is deferred to a later phase and still
raises ``NotImplementedError`` here; nothing in the Phase 3b engine path calls
it. ``static_evaluation`` is wired and exercised.

This module imports only ``dialectical_checkers`` and the stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass

from dialectical_checkers.board import CheckersBoard

MAN_VALUE = 100
KING_VALUE = 150


@dataclass(frozen=True)
class ReplyAnalysisSettings:
    """Budget for the bounded reply analysis (design §3, §8)."""

    max_depth: int = 0
    max_nodes: int = 0


def static_evaluation(board: CheckersBoard) -> int:
    """Material-first static evaluation, side-to-move relative (design §8).

    The weighted-material balance (man = 100, king = 150) from the perspective
    of the side to move on ``board``: positive means the side to move is
    ahead. Phase 3b uses this only as the deterministic selector tiebreak
    (design §7) — positional terms (back-rank men, advancement, trapped kings)
    are added in a later phase once the material baseline plays correctly.

    A terminal position (the side to move has no legal move) is a *loss* for
    the side to move (design §2.6 / §8 — checkers has no stalemate draw), so
    it scores a large negative sentinel rather than the raw material count.
    """
    if board.is_terminal():
        # No legal move => the side to move has lost (design §2.6/§8). Score it
        # below any reachable material balance (max 12 kings = 1800) so a
        # terminal loss is never preferred to a surviving position.
        return -100_000
    side = board.turn
    other = "w" if side == "r" else "r"
    own = 0
    opp = 0
    for cell in board.cells:
        if cell is None:
            continue
        colour, is_king = cell
        weight = KING_VALUE if is_king else MAN_VALUE
        if colour == side:
            own += weight
        elif colour == other:
            opp += weight
    return own - opp


def negamax(board: CheckersBoard, depth: int) -> int:
    """Negamax/alphabeta search; no-moves is a loss, never 0 (design §8).

    Deferred past Phase 3b — the decision is the argument layers, not search.
    """
    raise NotImplementedError
