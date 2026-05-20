"""Selector modes + selection keys.

Phase 0 skeleton. The lexicographic selector key over crisp survivors and the
multi-mode ``choose_move`` surface (design §7) are built in Phase 4. The
mode set is declared here per design §7; the keys are not implemented yet.
"""

from __future__ import annotations

from dialectical_checkers.arguments import MoveProbe, RootArgumentGraph

SELECTOR_MODES = frozenset(
    {"argument", "score", "grounded", "support", "categoriser", "optimizer"}
)


def choose_move(
    probes: list[MoveProbe],
    graph: RootArgumentGraph,
    *,
    selector_mode: str = "argument",
) -> MoveProbe:
    """Select a move from the crisp survivors (design §7). Built in Phase 4."""
    raise NotImplementedError
