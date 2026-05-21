"""Orchestration: probe -> graph -> choose, for dialectical checkers.

Copied in shape from ``dialectical_chess/engine.py`` and renamed for checkers
(design §1, port-plan §8). It is a thin orchestrator:
``probe_moves(board)`` -> ``build_root_argument_graph`` (the crisp Dung layer,
design §6) -> the FACT-tier selector (design §7) -> an :class:`EngineDecision`.

Phase 3b makes the engine PLAY: ``analyze`` / ``choose_move`` run end to end.
A position with **no legal move** is terminal — the game is over — and yields
a *null* decision (empty ``move_pdn``, ``selected`` is ``None``). The graded
Categoriser layer (design §7) is Phase 4; the engine wiring here does not
change when it lands — only ``build_root_argument_graph`` / ``choose_move`` do.
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
        """Probe, build the crisp argument graph, and choose a move.

        ``probe_moves`` yields one probe per legal move;
        ``build_root_argument_graph`` is the crisp Dung layer (design §6);
        ``choose_move`` applies the FACT-tier selector (design §7) over the
        crisp survivors. A terminal position (no legal move, hence no probe)
        yields a null :class:`EngineDecision` — the game is over.
        """
        probes = tuple(probe_moves(board))
        graph = build_root_argument_graph(list(probes), board=board)
        selected = (
            choose_move(
                list(probes),
                graph,
                selector_mode=self.settings.selector_mode,
                board=board,
            )
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
