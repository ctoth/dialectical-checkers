"""Negamax skeleton + checkers static eval.

Phase 0 skeleton. The negamax/alphabeta recursion skeleton is copied from
dialectical-chess in Phase 5/8 with the one required change (design §8): no
stalemate draw — "no legal moves" is always a loss for the side to move.
``static_evaluation`` starts material-only (man = 100, king = 150). Search is
a witness source, not the decision maker. Nothing here is implemented yet.
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
    """Material-first static evaluation (design §8). Built in Phase 5/8."""
    raise NotImplementedError


def negamax(board: CheckersBoard, depth: int) -> int:
    """Negamax/alphabeta search; no-moves is a loss, never 0 (design §8)."""
    raise NotImplementedError
