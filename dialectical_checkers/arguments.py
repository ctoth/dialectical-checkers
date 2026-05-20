"""Crisp Dung layer over FACT-tier defeaters (design §6).

Phase 3b builds the **crisp** layer only — the plain Dung
``ArgumentationFramework`` of design ``notes/checkers-design.md`` §6, evaluated
with ``formal-argumentation``'s ``grounded_extension``. The graded Categoriser
layer over the survivors (design §7) is Phase 4 and is *not* built here; the
``ranking`` field of :class:`RootArgumentGraph` is left empty as a clean seam.

The crisp argument families (design §6), one Dung argument per row:

* ``move:{pdn}`` — one per legal move. The thing being attacked.
* ``obj:{pdn}:{label}`` — one per **FACT-tier** objection on a move. Defeats
  that move's ``move:`` argument.
* ``reply:{pdn}:{label}`` — one per **FACT-tier** reply attack on a move.
  Defeats that move's ``move:`` argument.
* ``defense:{pdn}:{label}`` — one per **FACT-tier** proven defense on a move.
  Defeats the objection / reply arguments on the *same* move.

There is **no ``doubt`` node** — soft reasoning lives in the graded layer
(§7), so the ``doubt`` node has no remaining job. There are **no duplicated /
copy arguments** — every argument id is distinct, weighting by duplication is
an anti-pattern the corpus rejects (design §0). HEURISTIC witnesses never
enter this layer; Phase 3a emits only FACT witnesses, but the construction
filters by ``evidence.to_argument_evidence(...).tier`` regardless, so a future
HEURISTIC witness still cannot leak in.

The argument id carries the move's PDN so that objection / reply / defense ids
are globally unique even when two moves carry an identically-labelled witness
(e.g. two different moves both ``obj:terminal_loss``) — distinct ids, never a
shared/duplicated argument.

A ``move:`` argument is in the grounded extension iff no undefeated FACT-tier
objection / reply attacks it — exactly "this move is not provably refuted"
(design §6). The **empty-survivor fallback**: if *no* ``move:`` argument is in
the grounded extension (every move carries an undefeated FACT objection), the
surviving set is *all* moves — the engine must still return a move, and the
selector (§7) then ranks by the magnitude of the unavoidable loss.

This module imports only ``dialectical_checkers``, the stdlib, and
``formal-argumentation``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from argumentation.dung import ArgumentationFramework, grounded_extension

from dialectical_checkers.evidence import to_argument_evidence
from dialectical_checkers.scheme import Tier


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
    """The crisp Dung argument graph output (design §6).

    ``arguments`` / ``defeats`` are the crisp Dung AF of FACT-tier defeaters
    (design §6); ``grounded_extension`` is its grounded extension;
    ``move_arguments`` maps each move's PDN to its ``move:`` argument id;
    ``survivors`` is the set of *move PDNs* that survive the crisp layer (the
    grounded ``move:`` arguments, or — under the empty-survivor fallback — all
    move PDNs).

    ``ranking`` is the seam for the Phase-4 graded Categoriser layer (design
    §7); Phase 3b leaves it empty.
    """

    arguments: frozenset[str] = frozenset()
    defeats: frozenset[tuple[str, str]] = frozenset()
    move_arguments: dict[str, str] = field(default_factory=dict)
    grounded_extension: frozenset[str] = frozenset()
    survivors: frozenset[str] = frozenset()
    ranking: dict[str, Any] = field(default_factory=dict)


def _move_arg(pdn: str) -> str:
    """The ``move:`` argument id for the move with PDN ``pdn``."""
    return f"move:{pdn}"


def _obj_arg(pdn: str, label: str) -> str:
    """The objection argument id for FACT objection ``label`` on move ``pdn``."""
    return f"obj:{pdn}:{label}"


def _reply_arg(pdn: str, label: str) -> str:
    """The reply-attack argument id for FACT reply ``label`` on move ``pdn``."""
    return f"reply:{pdn}:{label}"


def _defense_arg(pdn: str, label: str) -> str:
    """The defense argument id for FACT defense ``label`` on move ``pdn``."""
    return f"defense:{pdn}:{label}"


def _is_fact(label: str) -> bool:
    """True iff ``label`` is a FACT-tier witness (design §6 — only FACT enters).

    Parsed once through ``evidence.to_argument_evidence``: the single typed
    taxonomy. A label the parser rejects is not a known FACT witness and is
    excluded — the crisp layer never silently admits an untyped label.
    """
    try:
        return to_argument_evidence(label).tier is Tier.FACT
    except ValueError:
        return False


def build_root_argument_graph(probes: list[MoveProbe]) -> RootArgumentGraph:
    """Build the crisp Dung argument graph from move probes (design §6).

    For each probe (one per legal move):

    * a ``move:{pdn}`` argument;
    * for every **FACT-tier** objection on the probe, an ``obj:`` argument
      that defeats the move;
    * for every **FACT-tier** reply attack on the probe, a ``reply:``
      argument that defeats the move;
    * for every **FACT-tier** defense on the probe, a ``defense:`` argument
      that defeats *every* objection and reply argument on the *same* move
      (design §5/§6: a proven defense answers the objection/reply that the
      resolver showed is refuted).

    No ``doubt`` argument, no duplicated arguments — every id is distinct.
    HEURISTIC witnesses are filtered out. The grounded extension is computed
    with ``formal-argumentation``; the surviving move set is the moves whose
    ``move:`` argument is grounded, or — when none is (the empty-survivor
    fallback, design §6) — *all* moves.
    """
    arguments: set[str] = set()
    defeats: set[tuple[str, str]] = set()
    move_arguments: dict[str, str] = {}

    for probe in probes:
        move_id = _move_arg(probe.pdn)
        move_arguments[probe.pdn] = move_id
        arguments.add(move_id)

        # FACT-tier objections / reply attacks defeat this move's argument.
        fact_objections = [o for o in probe.objections if _is_fact(o)]
        fact_replies = [r for r in probe.reply_attacks if _is_fact(r)]
        attacker_ids: list[str] = []
        for label in fact_objections:
            arg_id = _obj_arg(probe.pdn, label)
            arguments.add(arg_id)
            defeats.add((arg_id, move_id))
            attacker_ids.append(arg_id)
        for label in fact_replies:
            arg_id = _reply_arg(probe.pdn, label)
            arguments.add(arg_id)
            defeats.add((arg_id, move_id))
            attacker_ids.append(arg_id)

        # FACT-tier defenses defeat the move's objection / reply arguments —
        # a proven defense refutes them, restoring the move (design §6).
        for label in probe.defenses:
            if not _is_fact(label):
                continue
            arg_id = _defense_arg(probe.pdn, label)
            arguments.add(arg_id)
            for attacked in attacker_ids:
                defeats.add((arg_id, attacked))

    framework = ArgumentationFramework(
        arguments=frozenset(arguments),
        defeats=frozenset(defeats),
    )
    grounded = grounded_extension(framework)

    grounded_moves = frozenset(
        pdn for pdn, arg_id in move_arguments.items() if arg_id in grounded
    )
    # Empty-survivor fallback (design §6): if no move: argument survived the
    # crisp layer, every move carries an undefeated FACT objection. The engine
    # must still play, so the surviving set is *all* moves; the selector then
    # ranks by the magnitude of the unavoidable FACT loss.
    if grounded_moves:
        survivors = grounded_moves
    else:
        survivors = frozenset(move_arguments)

    return RootArgumentGraph(
        arguments=frozenset(arguments),
        defeats=frozenset(defeats),
        move_arguments=move_arguments,
        grounded_extension=grounded,
        survivors=survivors,
        ranking={},
    )
