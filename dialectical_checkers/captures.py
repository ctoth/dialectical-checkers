"""Forced-capture resolver — the exact tactical spine.

Phase 0 skeleton. The bounded, exact capture-sequence resolver (design §3) is
built in Phase 2: ``resolve`` recurses through mandatory captures of both
sides to a quiet position, and the derived ``opponent_shot`` / ``own_shot``
queries feed the witness layer. Nothing here is implemented yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from dialectical_checkers.board import CheckersBoard, CheckersMove


@dataclass(frozen=True)
class ResolvedLine:
    """The outcome of resolving a forced capture sequence (design §3)."""

    material_swing: int
    forced: bool
    truncated: bool
    terminal: str | None


@dataclass(frozen=True)
class ShotResult:
    """A proven forced capture sequence netting material or the game (design §3)."""

    material_net: int
    forced: bool
    truncated: bool
    terminal: str | None


def resolve(board: CheckersBoard) -> ResolvedLine:
    """Resolve all forced capture sequences from ``board`` (design §3)."""
    raise NotImplementedError


def opponent_shot(board: CheckersBoard, move: CheckersMove) -> ShotResult | None:
    """The provable ``obj:allows_shot`` defeater (design §3)."""
    raise NotImplementedError


def own_shot(board: CheckersBoard, move: CheckersMove) -> ShotResult | None:
    """The ``pro:shot_setup`` reason (design §3)."""
    raise NotImplementedError
