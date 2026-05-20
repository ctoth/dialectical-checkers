"""Crisp Dung layer + graded Categoriser layer.

Phase 0 shell. Per port-plan §8, Phase 0 ports the typed ``MoveProbe`` /
``RootArgumentGraph`` dataclasses and an *empty* ``build_root_argument_graph``.
The real two-layer construction — crisp Dung AF of fact-tier defeaters
(design §6) plus the graded Categoriser layer over the survivors (design §7) —
is Phase 3 and Phase 4. No real graph construction happens here yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MoveProbe:
    """One AS1 argument for a legal move (design §5).

    Keeps the dialectical-chess probe shape (``uci`` -> ``pdn``) with
    ``reasons`` (AS1 pro-labels), ``objections`` (CQ-derived con-labels) and
    ``reply_attacks`` (CQ17 opponent replies). Every label is typed by
    ``evidence.py`` with a ``Value`` and a ``Tier`` once the witness layer is
    built (Phases 3, 5).
    """

    pdn: str
    score: int = 0
    reasons: tuple[str, ...] = ()
    objections: tuple[str, ...] = ()
    reply_attacks: tuple[str, ...] = ()
    defenses: tuple[str, ...] = ()
    search_score: int | None = None
    search_line: tuple[str, ...] = ()


@dataclass(frozen=True)
class RootArgumentGraph:
    """The two-layer argument graph output (design §6-7).

    ``arguments`` / ``defeats`` are the crisp Dung AF of fact-tier defeaters
    (design §6); ``grounded_extension`` is its grounded extension; ``ranking``
    holds the graded Categoriser scores over the crisp survivors (design §7).
    ``move_arguments`` maps each move's PDN to its ``move:`` argument id.
    """

    arguments: frozenset[str] = frozenset()
    defeats: frozenset[tuple[str, str]] = frozenset()
    move_arguments: dict[str, str] = field(default_factory=dict)
    grounded_extension: frozenset[str] = frozenset()
    ranking: dict[str, Any] = field(default_factory=dict)


def build_root_argument_graph(probes: list[MoveProbe]) -> RootArgumentGraph:
    """Build the root argument graph from move probes.

    Phase 0 shell: returns a trivial empty ``RootArgumentGraph``. The crisp
    Dung layer (design §6) and the graded Categoriser layer (design §7) are
    wired in Phase 3 and Phase 4. ``probes`` is accepted now so the engine
    orchestration shell is callable end to end.
    """
    return RootArgumentGraph()
