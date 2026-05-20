"""PDN game I/O, loss-mining diagnostic.

Phase 0 skeleton. Portable Draughts Notation game read/write and the
loss-mining diagnostic (port-plan §6, design §1) are built in Phase 6.
Nothing here is implemented yet.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard


def load_pdn(text: str) -> tuple[CheckersBoard, ...]:
    """Parse a PDN game into a sequence of positions. Built in Phase 6."""
    raise NotImplementedError


def dump_pdn(positions: tuple[CheckersBoard, ...]) -> str:
    """Serialise a sequence of positions to PDN. Built in Phase 6."""
    raise NotImplementedError
