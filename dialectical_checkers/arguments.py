"""Crisp Dung layer + graded Categoriser layer (design §6-7).

This module builds **two** layers, exactly as design ``notes/checkers-design.md``
§6-7 specifies:

* the **crisp** layer — the plain Dung ``ArgumentationFramework`` of design §6,
  evaluated with ``formal-argumentation``'s ``grounded_extension``. It admits
  **only FACT-tier** witnesses; a ``move:`` argument is grounded iff no
  undefeated FACT objection / reply attacks it ("not provably refuted"). The
  surviving move set is its grounded ``move:`` arguments (or — the
  empty-survivor fallback — all moves). The crisp layer is **unchanged** from
  Phase 3b: the graded layer below is purely additive.

* the **opinion-valued graded** layer (design v1.5, ``notes/checkers-v1.5-
  design.md`` decisions V1.5-D1..D7) — the v1.5 upgrade. Over the crisp
  survivors *only*, a ``doxa.BipolarOpinionGraph`` whose nodes are the surviving
  ``move:`` arguments plus one leaf node per **HEURISTIC** witness on those
  survivors. ``doxa.evaluate`` resolves it bottom-up to a per-argument Jøsang
  ``Opinion``: each move's resolved opinion accrues its HEURISTIC supporters
  (pro-reasons) and attackers (objections) under doxa's CCF operator. The
  per-move ``Opinion`` and its ``expectation()`` strength are exposed on
  :attr:`RootArgumentGraph.ranking`.

  This **replaces** the attack-only Categoriser of Phase 5. The decisive reason
  (design V1.5-D1): CCF accrual is the only operator where balanced
  disagreement raises uncertainty ``u`` — a *contested* move (strong HEURISTIC
  pro AND strong HEURISTIC objection) stays distinguishable from a *bland* one,
  which the attack-only scalar Categoriser structurally could not do. HEURISTIC
  **pro**-reasons are now first-class graph nodes (``supports`` edges) — they
  no longer need a separate selector-key proxy.

  The graded layer **only ranks** — it can never resurrect a crisply-eliminated
  move (its move-node set is a subset of the crisp survivors) and never
  overrides a FACT decision (the selector's graded key term comes strictly
  after the FACT terms — see ``selection.py``).

The crisp argument families (design §6), one Dung argument per row:

* ``move:{pdn}`` — one per legal move. The thing being attacked.
* ``obj:{pdn}:{label}`` — one per **FACT-tier** objection on a move. Defeats
  that move's ``move:`` argument.
* ``reply:{pdn}:{label}`` — one per **FACT-tier** reply attack on a move.
  Defeats that move's ``move:`` argument.
* ``defense:{pdn}:{label}`` — one per **FACT-tier** proven defense on a move.
  Defeats *only* the one objection / reply argument it is keyed to answer
  (design §6 — "and only that one"). A defense label is keyed
  ``defense:holds_exchange@{answered}``; the ``@{answered}`` part names the
  exact objection / reply label the defense answers, and the defense argument
  defeats only that attacker on the same move.

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
from typing import TYPE_CHECKING, Any

from argumentation.dung import ArgumentationFramework, grounded_extension
from doxa import BipolarOpinionGraph, Opinion, evaluate

from dialectical_checkers.evidence import to_argument_evidence
from dialectical_checkers.graded_tuning import (
    _EDGE_TRUST_BASE_RATE,
    _WITNESS_BASE_RATE,
    _WITNESS_UNCERTAINTY,
    move_base_rate,
    witness_belief,
)
from dialectical_checkers.scheme import Tier

if TYPE_CHECKING:
    from dialectical_checkers.board import CheckersBoard


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
    """The crisp + graded argument graph output (design §6-7).

    ``arguments`` / ``defeats`` are the **crisp** Dung AF of FACT-tier defeaters
    (design §6); ``grounded_extension`` is its grounded extension;
    ``move_arguments`` maps each move's PDN to its ``move:`` argument id;
    ``survivors`` is the set of *move PDNs* that survive the crisp layer (the
    grounded ``move:`` arguments, or — under the empty-survivor fallback — all
    move PDNs).

    ``ranking`` carries the **opinion-valued graded** layer (design v1.5),
    built by :func:`build_graded_layer` over the crisp survivors. Its keys:

    * ``"move_opinions"`` — ``dict[str, Opinion]``: each surviving move's
      resolved Jøsang ``Opinion`` from ``doxa.evaluate``, keyed by **move
      PDN**. The full opinion — the uncertainty channel ``u`` survives here for
      selection / explanation (design V1.5-D2).
    * ``"move_scores"`` — ``dict[str, float]``: each surviving move's scalar
      strength ``Opinion.expectation()`` (``b + a*u``), keyed by **move PDN** —
      the selector's term-3 lookup. A move PDN absent from the graded graph (a
      crisply-eliminated move) is absent here.
    * ``"opinions"`` — ``dict[str, Opinion]``: the resolved ``Opinion`` of
      *every* node of the graded graph (move nodes and HEURISTIC witness leaf
      nodes), for inspection / tests.
    * ``"arguments"`` / ``"supports"`` / ``"attacks"`` — the graded graph's
      node and edge sets, for inspection / tests.

    ``ranking`` is ``{}`` only for an empty graph (a terminal position, no
    probes); for any non-empty graph it carries the graded layer.
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


def obj_arg_id(pdn: str, label: str) -> str:
    """The objection argument id for FACT objection ``label`` on move ``pdn``.

    Public so the selector (``selection.py``) can reconstruct the same
    objection argument id and ask whether that attacker is in the grounded
    extension — i.e. still *undefeated* (design §7 selector key term 1).
    """
    return f"obj:{pdn}:{label}"


def reply_arg_id(pdn: str, label: str) -> str:
    """The reply-attack argument id for FACT reply ``label`` on move ``pdn``.

    Public for the same reason as :func:`obj_arg_id` — the selector needs to
    identify a reply attacker's argument to test whether it is undefeated.
    """
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


def _witness_arg_id(pdn: str, label: str) -> str:
    """The graded-graph leaf-node id for HEURISTIC witness ``label`` on ``pdn``.

    A ``wit:`` prefix (distinct from the crisp layer's ``obj:`` / ``reply:`` /
    ``defense:`` families) so a graded witness node can never collide with a
    crisp argument id. The PDN is embedded so the same HEURISTIC label on two
    different moves gets two distinct leaf nodes.
    """
    return f"wit:{pdn}:{label}"


def _witness_opinion(magnitude: int | None) -> Opinion:
    """The intrinsic ``Opinion`` of a HEURISTIC witness leaf node (design D5).

    Belief from :func:`graded_tuning.witness_belief` (the witness's firing
    strength, scaled by magnitude); the fixed soft-judgement uncertainty
    ``_WITNESS_UNCERTAINTY``; the residual disbelief; a neutral base rate. The
    same opinion shape encodes a pro-reason and an objection — the graph's
    ``supports`` vs ``attacks`` edge decides the sign (``doxa.evaluate`` negates
    a discounted attacker), so a witness opinion is always a positive belief in
    *the witness's own claim*.
    """
    belief = witness_belief(magnitude)
    disbelief = 1.0 - belief - _WITNESS_UNCERTAINTY
    return Opinion(belief, disbelief, _WITNESS_UNCERTAINTY, _WITNESS_BASE_RATE)


def build_graded_layer(
    probes: list[MoveProbe],
    survivors: frozenset[str],
    board: CheckersBoard | None,
) -> dict[str, Any]:
    """Build the opinion-valued graded layer over the crisp survivors (v1.5).

    Replaces the attack-only Categoriser (design v1.5, decisions V1.5-D1..D7).
    Builds a ``doxa.BipolarOpinionGraph`` over the crisp survivors *only* and
    resolves it with ``doxa.evaluate``:

    * **move nodes** — one ``move:{pdn}`` per move PDN in ``survivors``, with
      ``intrinsic = Opinion.vacuous(a)``: a vacuous opinion whose base rate
      ``a`` is the move's synthesized prior (design V1.5-D4 —
      :func:`graded_tuning.move_base_rate` of ``static_evaluation`` of the
      position the move reaches). A move with no HEURISTIC witness resolves to
      ``expectation() == a`` exactly.
    * **witness leaf nodes** — one ``wit:{pdn}:{label}`` per HEURISTIC witness
      (pro-reason or objection) on a surviving move, with a non-vacuous
      ``intrinsic`` Opinion encoding that witness (design V1.5-D5,
      :func:`_witness_opinion`). FACT witnesses do NOT enter — they are the
      crisp layer's business (design V1.5-D6).
    * **``supports``** — a ``(witness, move)`` edge per HEURISTIC pro-reason.
      **``attacks``** — a ``(witness, move)`` edge per HEURISTIC objection.
    * **``edge_opinions``** — full trust (``Opinion.dogmatic_true``) on every
      edge; per-edge witness reliability is a later tuning knob, not v1
      (design V1.5-D3).

    ``doxa.evaluate`` resolves each move's ``Opinion`` bottom-up: HEURISTIC
    supporters and (negated) attackers are accrued under doxa's CCF operator,
    so a *contested* move with a strong pro AND a strong objection resolves to
    high uncertainty ``u`` — the channel an attack-only scalar layer collapsed
    (design V1.5-D1). The returned dict is :attr:`RootArgumentGraph.ranking` —
    see that class's docstring for the key contract.

    ``board`` is the position the probed moves are played from — needed to
    apply each move for the base-rate synthesis (design V1.5-D4, the one
    signature change). When it is ``None`` (the graded layer is unit-tested
    without a board) every move base rate falls back to the neutral ``0.5``, so
    an unargued move resolves to ``expectation() == 0.5``.

    The graded graph can never resurrect a crisply-eliminated move: its move-
    node set is exactly ``survivors``. An empty ``survivors`` (no probes) yields
    an empty graded layer.
    """
    survivor_probes = [p for p in probes if p.pdn in survivors]
    if not survivor_probes:
        # A terminal position / empty survivor set — the trivial empty layer.
        return {
            "move_opinions": {},
            "move_scores": {},
            "opinions": {},
            "arguments": frozenset(),
            "supports": frozenset(),
            "attacks": frozenset(),
        }

    # The position the move reaches, per surviving move PDN — needed for the
    # base-rate synthesis. With no board the synthesis falls back to neutral.
    child_eval_by_pdn = _child_evaluations(board, survivor_probes)

    arguments: set[str] = set()
    intrinsic: dict[str, Opinion] = {}
    supports: set[tuple[str, str]] = set()
    attacks: set[tuple[str, str]] = set()
    edge_opinions: dict[tuple[str, str], Opinion] = {}
    move_node_by_pdn: dict[str, str] = {}

    for probe in survivor_probes:
        move_id = _move_arg(probe.pdn)
        move_node_by_pdn[probe.pdn] = move_id
        arguments.add(move_id)
        # The move node carries no own evidence — a vacuous opinion whose base
        # rate is the move's synthesized prior (design V1.5-D4).
        intrinsic[move_id] = Opinion.vacuous(
            move_base_rate(child_eval_by_pdn[probe.pdn])
        )

        # HEURISTIC pro-reasons -> support edges from a witness leaf.
        for label in probe.reasons:
            evidence = _heuristic_evidence(label)
            if evidence is None:
                continue
            wit_id = _witness_arg_id(probe.pdn, label)
            arguments.add(wit_id)
            intrinsic[wit_id] = _witness_opinion(evidence.magnitude)
            edge = (wit_id, move_id)
            supports.add(edge)
            edge_opinions[edge] = Opinion.dogmatic_true(_EDGE_TRUST_BASE_RATE)

        # HEURISTIC objections -> attack edges from a witness leaf. FACT
        # objections live in the crisp layer and are not re-litigated here.
        for label in probe.objections:
            evidence = _heuristic_evidence(label)
            if evidence is None:
                continue
            wit_id = _witness_arg_id(probe.pdn, label)
            arguments.add(wit_id)
            intrinsic[wit_id] = _witness_opinion(evidence.magnitude)
            edge = (wit_id, move_id)
            attacks.add(edge)
            edge_opinions[edge] = Opinion.dogmatic_true(_EDGE_TRUST_BASE_RATE)

    graph = BipolarOpinionGraph(
        arguments=frozenset(arguments),
        intrinsic=intrinsic,
        supports=frozenset(supports),
        attacks=frozenset(attacks),
        edge_opinions=edge_opinions,
    )
    # The graph is a DAG by construction — witness leaves point only at move
    # nodes, move nodes have no out-edges — so ``evaluate`` never raises
    # ``CyclicGraphError``.
    opinions = evaluate(graph)

    move_opinions = {
        pdn: opinions[node] for pdn, node in move_node_by_pdn.items()
    }
    # The per-move scalar strength — the selector's term-3 lookup. A move with
    # no HEURISTIC witness has a vacuous resolved opinion, so its expectation
    # falls back to exactly its synthesized base rate ``a`` (design V1.5-D4).
    move_scores = {
        pdn: opinion.expectation() for pdn, opinion in move_opinions.items()
    }

    return {
        "move_opinions": move_opinions,
        "move_scores": move_scores,
        "opinions": dict(opinions),
        "arguments": frozenset(arguments),
        "supports": frozenset(supports),
        "attacks": frozenset(attacks),
    }


def _heuristic_evidence(label: str):  # noqa: ANN202 — ArgumentEvidence | None
    """The parsed evidence for ``label`` iff it is a HEURISTIC witness, else None.

    A label the evidence parser rejects, or one that types FACT, is not a
    graded-layer witness and yields ``None`` — the graded layer never silently
    admits an untyped or FACT label, exactly as the crisp layer never does.
    """
    try:
        evidence = to_argument_evidence(label)
    except ValueError:
        return None
    if evidence.tier is not Tier.HEURISTIC:
        return None
    return evidence


def _child_evaluations(
    board: CheckersBoard | None, survivor_probes: list[MoveProbe]
) -> dict[str, int]:
    """Map each surviving move's PDN to ``static_evaluation`` of its child.

    The base-rate synthesis (design V1.5-D4) needs the static evaluation of the
    position each move reaches. With ``board`` ``None`` (the graded layer is
    unit-tested without a board) every child evaluation is 0 — so every move
    base rate falls back to the neutral ``0.5`` and an unargued move resolves to
    ``expectation() == 0.5``.
    """
    if board is None:
        return {p.pdn: 0 for p in survivor_probes}
    # Imported lazily — ``search`` and ``board`` are only needed when a real
    # board is threaded through, and importing them at module load would widen
    # the crisp layer's import surface for no reason on the board-free path.
    from dialectical_checkers.search import static_evaluation

    pdn_to_child: dict[str, int] = {}
    survivor_pdns = {p.pdn for p in survivor_probes}
    for move in board.legal_moves():
        pdn = move.pdn()
        if pdn in survivor_pdns:
            pdn_to_child[pdn] = static_evaluation(board.apply(move))
    # A survivor whose PDN is not a legal move on ``board`` (a mismatched
    # board / probe pairing) falls back to the neutral evaluation rather than
    # raising — the graded layer only ranks, it never gates legality.
    for pdn in survivor_pdns:
        pdn_to_child.setdefault(pdn, 0)
    return pdn_to_child


def build_root_argument_graph(
    probes: list[MoveProbe], board: CheckersBoard | None = None
) -> RootArgumentGraph:
    """Build the crisp Dung argument graph + opinion-valued graded layer.

    For each probe (one per legal move):

    * a ``move:{pdn}`` argument;
    * for every **FACT-tier** objection on the probe, an ``obj:`` argument
      that defeats the move;
    * for every **FACT-tier** reply attack on the probe, a ``reply:``
      argument that defeats the move;
    * for every **FACT-tier** defense on the probe, a ``defense:`` argument
      that defeats *only* the one objection / reply argument it is keyed to
      answer (design §6: a proven defense answers "the objection/reply ``x`` it
      answers, and only that one"). The defense label is keyed
      ``defense:holds_exchange@{answered}``; the defense argument defeats the
      attacker built from ``{answered}`` on the same move and nothing else. A
      keyed defense whose answered label is not present among the move's FACT
      attackers defeats nothing — it cannot restore a move on an attack the
      probe never raised.

    No ``doubt`` argument, no duplicated arguments — every id is distinct.
    HEURISTIC witnesses are filtered out of the **crisp** layer. The grounded
    extension is computed with ``formal-argumentation``; the surviving move set
    is the moves whose ``move:`` argument is grounded, or — when none is (the
    empty-survivor fallback, design §6) — *all* moves.

    The **opinion-valued graded** layer (design v1.5) is then built by
    :func:`build_graded_layer` over those crisp survivors and stored on
    :attr:`RootArgumentGraph.ranking`. The graded layer is purely additive: the
    crisp ``arguments`` / ``defeats`` / ``grounded_extension`` / ``survivors``
    are exactly Phase 3b's, and the graded layer's move-node set is a *subset*
    of ``survivors`` — it can never resurrect a crisply-eliminated move.

    ``board`` is the position the probed moves are played from — threaded to
    :func:`build_graded_layer` for the move base-rate synthesis (design
    V1.5-D4). It is optional: with no board the graded base rates fall back to
    the neutral ``0.5`` and the graded ranking is driven purely by the
    HEURISTIC-witness accrual.
    """
    arguments: set[str] = set()
    defeats: set[tuple[str, str]] = set()
    move_arguments: dict[str, str] = {}

    for probe in probes:
        move_id = _move_arg(probe.pdn)
        move_arguments[probe.pdn] = move_id
        arguments.add(move_id)

        # FACT-tier objections / reply attacks defeat this move's argument.
        # ``attacker_by_label`` maps the *witness label* of each FACT attacker
        # to its argument id, so a keyed defense can locate the one attacker it
        # answers (design §6 — "and only that one").
        fact_objections = [o for o in probe.objections if _is_fact(o)]
        fact_replies = [r for r in probe.reply_attacks if _is_fact(r)]
        attacker_by_label: dict[str, str] = {}
        for label in fact_objections:
            arg_id = obj_arg_id(probe.pdn, label)
            arguments.add(arg_id)
            defeats.add((arg_id, move_id))
            attacker_by_label[label] = arg_id
        for label in fact_replies:
            arg_id = reply_arg_id(probe.pdn, label)
            arguments.add(arg_id)
            defeats.add((arg_id, move_id))
            attacker_by_label[label] = arg_id

        # FACT-tier defenses defeat ONLY the one objection / reply they are
        # keyed to answer — a proven defense refutes exactly that attacker,
        # restoring the move only if no *other* attacker still stands (§6).
        for label in probe.defenses:
            if not _is_fact(label):
                continue
            answered = to_argument_evidence(label).answered
            arg_id = _defense_arg(probe.pdn, label)
            arguments.add(arg_id)
            # A keyed defense defeats only its answered attacker on this move.
            # If the answered label is absent (the probe never raised it) the
            # defense argument exists but defeats nothing — it cannot restore a
            # move against an attack that was never made.
            if answered is not None and answered in attacker_by_label:
                defeats.add((arg_id, attacker_by_label[answered]))

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

    # The opinion-valued graded layer (design v1.5) — built over the crisp
    # survivors only, so it can never resurrect a crisply-eliminated move. For
    # an empty graph (no probes / terminal position) ``survivors`` is empty and
    # the graded layer is the trivial empty result.
    ranking = build_graded_layer(probes, survivors, board)

    return RootArgumentGraph(
        arguments=frozenset(arguments),
        defeats=frozenset(defeats),
        move_arguments=move_arguments,
        grounded_extension=grounded,
        survivors=survivors,
        ranking=ranking,
    )
