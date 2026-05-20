"""CQ-derived witness producers -> ``MoveProbe``.

Phase 0 skeleton. ``probe_moves`` produces one ``MoveProbe`` per legal move,
each label typed by ``evidence.py`` with a ``Value`` and a ``Tier`` (design
§5). The FACT-tier producers are built in Phase 3, the HEURISTIC-tier
producers in Phase 5. Nothing here is implemented yet.
"""

from __future__ import annotations

from dialectical_checkers.arguments import MoveProbe
from dialectical_checkers.board import CheckersBoard


def probe_moves(board: CheckersBoard) -> tuple[MoveProbe, ...]:
    """Produce one ``MoveProbe`` per legal move (design §5). Built in Phase 3."""
    raise NotImplementedError
