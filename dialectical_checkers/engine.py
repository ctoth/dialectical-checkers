"""Orchestration: probe -> graph -> choose, for dialectical checkers.

Phase 0 shell. Copied in shape from ``dialectical_chess/engine.py`` and
renamed for checkers (design §1, port-plan §8). It is a thin orchestrator:
it probes the legal moves, builds the root argument graph, and selects a
move. The probe and selection callees are Phase-0 skeletons that raise
``NotImplementedError``; the real witness/graph/selection logic lands in
Phases 3-4. Constructing the engine and importing it is fully supported now.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dialectical_checkers.arguments import (
    MoveProbe,
    RootArgumentGraph,
    build_root_argument_graph,
)
from dialectical_checkers.selection import SELECTOR_MODES, choose_move
from dialectical_checkers.witnesses import probe_moves


@dataclass(frozen=True)
class EngineSettings:
    """Configuration for a ``DialecticalCheckersEngine``."""

    dialectic_depth: int = 1
    search_depth: int = 0
    search_backend: str = "negamax"
    selector_mode: str = "argument"
    positional_reasons: bool = True

    def __post_init__(self) -> None:
        if self.selector_mode not in SELECTOR_MODES:
            raise ValueError(f"unknown selector_mode: {self.selector_mode}")


@dataclass(frozen=True)
class EngineDecision:
    """The engine's chosen move and the probe it came from."""

    move_pdn: str
    selected: MoveProbe | None

    @property
    def score(self) -> int | None:
        return None if self.selected is None else self.selected.score


@dataclass(frozen=True)
class EngineAnalysis:
    """The full per-position analysis: probes, graph, decision."""

    probes: tuple[MoveProbe, ...]
    graph: RootArgumentGraph
    decision: EngineDecision


class DialecticalCheckersEngine:
    """Reusable engine surface used by harnesses, benchmarks, and PDN adapters."""

    def __init__(self, settings: EngineSettings | None = None) -> None:
        self.settings = settings or EngineSettings()

    def analyze(self, board: Any) -> EngineAnalysis:
        probes = tuple(probe_moves(board))
        graph = build_root_argument_graph(list(probes))
        selected = (
            choose_move(list(probes), graph, selector_mode=self.settings.selector_mode)
            if probes
            else None
        )
        decision = EngineDecision(
            move_pdn="" if selected is None else selected.pdn,
            selected=selected,
        )
        return EngineAnalysis(probes=probes, graph=graph, decision=decision)

    def choose_move(self, board: Any) -> EngineDecision:
        return self.analyze(board).decision
