"""``CheckersBoard``, ``CheckersMove``, move-gen, PDN-FEN, perft.

Phase 0 skeleton. The real board substrate (precomputed STEP/JUMP neighbour
tables, mandatory-capture move generation, multi-jump expansion, crowning,
terminal/draw detection, PDN-FEN I/O, perft) is design §2 and is built in
Phase 1. Nothing here is implemented yet.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckersMove:
    """A draughts move: a path of visited squares and the squares captured.

    Phase 1 (design §2.3) gives this real behaviour. ``path`` has length 2 for
    a simple move and length >= 2 for a jump chain; ``captured`` is empty for a
    simple move.
    """

    path: tuple[int, ...]
    captured: tuple[int, ...]


@dataclass(frozen=True)
class CheckersBoard:
    """Immutable English-draughts position (design §2.2).

    Phase 0 skeleton: fields and method signatures only. Move generation,
    ``apply``, terminal/draw detection and PDN-FEN I/O are Phase 1.
    """

    cells: tuple[tuple[str, bool] | None, ...]
    turn: str
    no_progress: int
    history: tuple[int, ...]

    def legal_moves(self) -> tuple[CheckersMove, ...]:
        """Return the legal move set for the side to move (design §2.4)."""
        raise NotImplementedError

    def apply(self, move: CheckersMove) -> CheckersBoard:
        """Return a new board with ``move`` played (design §2.5)."""
        raise NotImplementedError

    def is_loss_for(self, side: str) -> bool:
        """``side`` to move with no legal move loses (design §2.6)."""
        raise NotImplementedError

    def is_draw(self) -> bool:
        """Threefold repetition or the 40-move no-progress draw (design §2.6)."""
        raise NotImplementedError


def perft(board: CheckersBoard, depth: int) -> int:
    """Count leaf nodes to ``depth`` (design §2.7). Built in Phase 1."""
    raise NotImplementedError
