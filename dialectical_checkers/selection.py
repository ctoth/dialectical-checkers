"""Selector modes + selection keys (design §7).

The design §7 selector key, per surviving move, lexicographic — **smaller is
better** (the key is consumed by ``min``). The FACT terms (1-2, Phase 3b) come
first, the **graded** terms (3-4, Phase 5) next, the deterministic tiebreak
last:

1. **minimise the worst unavoidable FACT-objection magnitude.** For a move
   that is a **grounded crisp survivor** this is 0 — its ``move:`` argument is
   in the grounded extension, so every FACT objection / reply on it is
   *defeated* (by a keyed defense) and the move carries no unavoidable loss.
   This term is non-zero only under the design §6 empty-survivor fallback,
   where *no* ``move:`` argument is grounded and the selector must still pick
   the least-bad: then this term is the magnitude of the move's worst
   **undefeated** FACT objection / reply — an attacker still in the grounded
   extension — with a forced ``obj:terminal_loss`` (losing the *game*) ranked
   above any finite material loss. A FACT objection / reply that is defeated by
   a FACT defense never contributes to this term (design §7).
2. **maximise the FACT-tier pro value**, as the value-priority tuple
   ``winning > large material > crown > small material`` (design §7 term 2).
   The material component is the **net** material the move keeps — its
   immediate FACT capture minus any defended reply that recaptures part of it
   — so a defended even exchange scores 0 material, below a clean gain.
3. **maximise the move's Categoriser score** ``Cat(move:A)`` — the graded
   Categoriser layer (``arguments.build_graded_layer``, design §7). High when
   the move has few / weak HEURISTIC objections. Read from
   ``graph.ranking["move_scores"]``.
4. **maximise the value-weighted count of the move's accepted HEURISTIC
   pro-reasons** — the design §7 v1 support proxy. HEURISTIC pro-reasons cannot
   enter a Dung AF (it has only attacks), so v1 counts them as a selector-key
   term, value-weighted by the AS2 value each pro promotes.
5. **deterministic tiebreak**: the static evaluation (``search.py``) of the
   position the move reaches, then the move's PDN string.

The graded terms 3-4 come strictly **after** the FACT terms 1-2: a FACT
decision always dominates a graded one, so the graded layer can never override
a position the FACT terms already decide (design §7 — fact-as-highest-value).

The §7 multi-mode ``selector_mode`` surface (``argument`` default, plus
``categoriser`` / ``score`` / ``grounded`` / ``support`` / ``optimizer``)
mirrors the dialectical-chess ``choose_move`` surface. Every mode is a
deterministic selector over the crisp survivors — see :func:`choose_move`.

This module imports only ``dialectical_checkers`` and the stdlib.
"""

from __future__ import annotations

from dialectical_checkers.arguments import (
    MoveProbe,
    RootArgumentGraph,
    obj_arg_id,
    reply_arg_id,
)
from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.evidence import to_argument_evidence
from dialectical_checkers.scheme import Tier, Value
from dialectical_checkers.search import static_evaluation

SELECTOR_MODES = frozenset(
    {"argument", "score", "grounded", "support", "categoriser", "optimizer"}
)


# --- FACT-objection magnitude (selector key term 1) -------------------------
#
# A forced terminal game loss is qualitatively worse than any finite material
# loss; it is ranked above every magnitude with this sentinel.
_TERMINAL_LOSS_MAGNITUDE = 10**9


def _worst_fact_objection_magnitude(
    probe: MoveProbe, graph: RootArgumentGraph
) -> int:
    """The worst unavoidable FACT-objection magnitude on ``probe`` (term 1).

    **0 for any grounded crisp survivor** — a move whose ``move:`` argument is
    in the grounded extension carries no *undefeated* FACT objection (every
    objection / reply on it is defeated by a keyed FACT defense), so it has no
    unavoidable loss. This is the normal case (design §7: "0 if clean").

    Non-zero only under the design §6 empty-survivor fallback, where *no*
    ``move:`` argument is grounded. Then this is the largest magnitude among
    the move's **undefeated** FACT objections / reply attacks — an attacker is
    undefeated iff its argument is itself in the grounded extension — with a
    forced ``obj:terminal_loss`` / ``reply:terminal_loss`` (losing the game
    itself) ranked above any finite material loss via
    ``_TERMINAL_LOSS_MAGNITUDE``.

    A FACT objection / reply defeated by a keyed FACT defense (its argument not
    grounded) never contributes — design §7: defeated attackers on a grounded
    survivor are not unavoidable losses. Both the objection and reply channels
    are consulted: design §6 has both defeat a move in the crisp layer.
    """
    move_id = graph.move_arguments.get(probe.pdn)
    if move_id is not None and move_id in graph.grounded_extension:
        # A grounded crisp survivor — no undefeated FACT objection stands.
        return 0

    worst = 0
    attackers = [
        (label, obj_arg_id(probe.pdn, label)) for label in probe.objections
    ] + [
        (label, reply_arg_id(probe.pdn, label))
        for label in probe.reply_attacks
    ]
    for label, attacker_id in attackers:
        try:
            evidence = to_argument_evidence(label)
        except ValueError:
            continue
        if evidence.tier is not Tier.FACT:
            continue
        # Only an UNDEFEATED attacker — one whose argument is itself in the
        # grounded extension — is an unavoidable loss. A keyed defense that
        # defeated it removes it from the grounded extension, so it is skipped.
        if attacker_id not in graph.grounded_extension:
            continue
        if evidence.value is Value.WINNING:
            # obj:terminal_loss / reply:terminal_loss — a forced GAME loss.
            worst = max(worst, _TERMINAL_LOSS_MAGNITUDE)
        elif evidence.magnitude is not None:
            worst = max(worst, evidence.magnitude)
    return worst


# --- FACT pro value (selector key term 2) -----------------------------------
#
# The value-priority tuple of design §7: winning > large material > crown >
# small material. "Large" vs "small" material is split at one man (100): a
# capture/shot netting more than a man is "large". Each component is a count
# /magnitude so that, among moves at the same priority level, more is better.
# The key is consumed by ``min``, so the tuple is NEGATED to make "more pro"
# sort earlier.
#
# The pro material value is a **NET** quantity. A grounded crisp survivor can
# still carry a FACT ``reply:material`` attack that a keyed ``defense:`` only
# DEFEATS (it does not erase the giveback): the move captures material, then
# the opponent's defended forcing reply recaptures part of it. The move's pro
# VALUE is what it actually keeps — the immediate ``pro:material`` minus the
# material handed back by every defended reply. Using the gross immediate
# capture would tie a move that nets +200 with one that grabs 200 and gives
# 100 back, and a clean +100 with a held-even 0 — that is exactly the selector
# defect MAJOR 1's term-1 fix uncovered. Ranking on the net keeps design §7's
# "maximise FACT-tier pro value" honest: the value is the material kept.

_LARGE_MATERIAL_THRESHOLD = 100  # strictly more than one man is "large"


def _defended_reply_giveback(probe: MoveProbe) -> int:
    """The FACT material a move's keyed defenses concede back to the opponent.

    A ``defense:holds_exchange@{answered}`` on a grounded survivor proves the
    exchange is even or favourable, but the opponent's ``{answered}`` forcing
    reply still recaptures its ``reply:material:{n}`` worth of material. The
    move's net pro material is its immediate capture minus this giveback. Sums
    the magnitudes of every distinct defended FACT ``reply:material`` so a move
    with several defended replies concedes each one's material.
    """
    giveback = 0
    seen: set[str] = set()
    for label in probe.defenses:
        try:
            evidence = to_argument_evidence(label)
        except ValueError:
            continue
        if evidence.tier is not Tier.FACT or evidence.answered is None:
            continue
        answered = evidence.answered
        if answered in seen:
            continue
        seen.add(answered)
        try:
            answered_evidence = to_argument_evidence(answered)
        except ValueError:
            continue
        # Only a finite material reply concedes measurable material here; a
        # terminal-loss reply is not a "giveback", it is handled by term 1.
        if (
            answered_evidence.value is Value.MATERIAL
            and answered_evidence.magnitude is not None
        ):
            giveback += answered_evidence.magnitude
    return giveback


def _fact_pro_priority(probe: MoveProbe) -> tuple[int, int, int, int]:
    """The FACT pro-value priority tuple for ``probe`` (term 2).

    Returns ``(winning, large_material, crown, small_material)`` — every
    component "bigger is better":

    * ``winning`` — 1 if the move carries ``pro:terminal_win`` (realises the
      ``winning`` value — ends the game in the mover's favour), else 0.
    * ``large_material`` — the **net** FACT material the move keeps (the
      largest ``pro:material`` / ``pro:shot_setup`` magnitude minus the
      :func:`_defended_reply_giveback`) when that net exceeds one man, else 0.
    * ``crown`` — 1 if the move carries ``pro:crown``, else 0.
    * ``small_material`` — the net FACT material the move keeps when it is
      positive and at most one man, else 0.

    Design §7 orders these strictly: winning beats large material beats crown
    beats small material. The material the move *keeps* — net of any defended
    reply that recaptures part of it — is the honest pro value (see the module
    note above); a defended even exchange therefore scores 0 material, below a
    genuine clean material gain.
    """
    winning = 0
    crown = 0
    gross_material = 0
    for label in probe.reasons:
        try:
            evidence = to_argument_evidence(label)
        except ValueError:
            continue
        if evidence.tier is not Tier.FACT:
            continue
        if evidence.value is Value.WINNING:
            winning = 1
        elif evidence.value is Value.KING_COUNT:
            crown = 1
        elif evidence.value is Value.MATERIAL and evidence.magnitude is not None:
            gross_material = max(gross_material, evidence.magnitude)

    # Net the gross immediate material against any defended-reply giveback —
    # the move's pro value is the material it actually keeps (module note).
    net_material = gross_material - _defended_reply_giveback(probe)
    large_material = 0
    small_material = 0
    if net_material > _LARGE_MATERIAL_THRESHOLD:
        large_material = net_material
    elif net_material > 0:
        small_material = net_material
    return (winning, large_material, crown, small_material)


# --- graded Categoriser score (selector key term 3) -------------------------
#
# Design §7 term 3: maximise Cat(move:A), the move's Categoriser score from the
# graded layer (``arguments.build_graded_layer``). High when the move has few /
# weak HEURISTIC objections. The score is a float in (0, 1]; the lexicographic
# key is consumed by ``min`` over ints/strings, so the score is mapped to a
# negated integer at a fixed scale (more Cat -> smaller key). The scale
# ``_CAT_SCALE`` is large enough that the Categoriser fixpoint's float
# resolution is preserved as an int ordering.

_CAT_SCALE = 10**9


def _categoriser_score(probe: MoveProbe, graph: RootArgumentGraph) -> float:
    """The move's graded-layer Categoriser score (selector key term 3).

    Read from ``graph.ranking["move_scores"]`` — the per-move Categoriser score
    keyed by move PDN (``arguments.build_graded_layer``). A move absent from the
    graded AF (it was crisply eliminated, or the ranking is empty) scores the
    Categoriser default of an unattacked argument, ``1.0`` — a move the graded
    layer makes no claim about is not penalised by term 3.
    """
    move_scores = graph.ranking.get("move_scores")
    if not move_scores:
        return 1.0
    return float(move_scores.get(probe.pdn, 1.0))


# --- value-weighted accepted-heuristic-pro count (selector key term 4) ------
#
# Design §7 term 4: maximise a value-weighted count of the move's ACCEPTED
# HEURISTIC pro-reasons — the v1 support proxy. HEURISTIC pro-reasons cannot
# enter a Dung AF (it has only attacks), so design §7 v1 makes them a
# selector-key term, not a graded-AF node (the QBAF that would model them as
# first-class support is the deferred v1.5).
#
# "Accepted" here: a HEURISTIC pro-reason is a positional judgement that *fired*
# on the move (its precise firing condition held — see ``witnesses.py``). It is
# never a node in any argument framework, so "accepted" cannot mean
# grounded-extension membership; every HEURISTIC pro the witness layer emitted
# on a surviving move is an accepted pro-reason.
#
# "value-weighted": design §7 says "value-weighted" but names NO numeric weight
# for the HEURISTIC values (TEMPO / STRUCTURE / MOBILITY). The §4 ``Value`` enum
# carries no priority ordering among heuristics — only the FACT pro-value tuple
# (term 2) is explicitly ordered by design §7, and only ``Tier`` (FACT > all
# HEURISTIC) ranks across tiers. With no stated weight, the sole choice that
# introduces zero architectural discretion is a uniform weight of 1 per
# accepted HEURISTIC pro — i.e. the design §7 (line 329) literal "a ... count of
# accepted heuristic pro-reasons". This module therefore weights every accepted
# HEURISTIC pro equally; the Phase-5 report records this as the resolution of
# the one design under-specification. (A measured value ordering, or the v1.5
# QBAF, is the place to refine this — design §7 "observe first".)
_HEURISTIC_PRO_WEIGHT = 1


def _accepted_heuristic_pro_count(probe: MoveProbe) -> int:
    """The value-weighted accepted-HEURISTIC-pro count for ``probe`` (term 4).

    Counts every HEURISTIC-tier pro-reason the probe carries, each at the
    uniform ``_HEURISTIC_PRO_WEIGHT`` (see the module note above — design §7
    names no per-value weight, so a uniform weight is the only non-discretionary
    reading). A label the evidence parser rejects is not a known HEURISTIC pro
    and is skipped. FACT pro-reasons never contribute — they are term 2's
    business; only HEURISTIC pros are the graded support proxy.
    """
    total = 0
    for label in probe.reasons:
        try:
            evidence = to_argument_evidence(label)
        except ValueError:
            continue
        if evidence.tier is Tier.HEURISTIC:
            total += _HEURISTIC_PRO_WEIGHT
    return total


# --- the lexicographic selection key ----------------------------------------


def _selection_key(
    probe: MoveProbe,
    graph: RootArgumentGraph,
    board: CheckersBoard | None,
) -> tuple[int, int, int, int, int, int, int, int, str]:
    """The full lexicographic selection key for ``probe`` (design §7).

    Smaller is better — the key is consumed by ``min``. The components, in
    order — the FACT terms (1-2) first, the graded terms (3-4) next, the
    deterministic tiebreak (5) last:

    1. the worst unavoidable FACT-objection magnitude (minimised) — 0 for any
       grounded crisp survivor, non-zero only in the §6 empty-survivor
       fallback (see :func:`_worst_fact_objection_magnitude`);
    2. the FACT pro-value priority tuple, negated so "more pro" sorts first
       (winning, large material, crown, small material) — four components;
    3. the move's Categoriser score (graded layer), scaled to an int and
       negated so a *higher* Categoriser score sorts first
       (see :func:`_categoriser_score`);
    4. the value-weighted accepted-HEURISTIC-pro count, negated so *more*
       accepted heuristic support sorts first
       (see :func:`_accepted_heuristic_pro_count`);
    5. the static evaluation of the reached position, negated so a higher
       evaluation sorts first, then the move's PDN string (deterministic
       tiebreak — two components).

    The graded terms 3-4 come strictly **after** the FACT terms 1-2 in the
    lexicographic ordering: a FACT decision always dominates a graded one, so
    the graded layer can never override a position the FACT terms already
    decide (design §7 — fact-as-highest-value). The graded layer also ranks
    only crisp survivors and so can never resurrect a crisply-eliminated move.

    ``graph`` is the crisp + graded argument graph the probes were evaluated
    against — term 1 reads its grounded extension to tell a grounded survivor
    from an empty-survivor-fallback move, term 3 reads its graded ``ranking``.

    ``board`` is the position the moves are played from; it is needed to apply
    the move for the static-eval tiebreak. When it is ``None`` the static-eval
    component is 0 — the PDN tiebreak still makes the key total and
    deterministic.
    """
    objection_magnitude = _worst_fact_objection_magnitude(probe, graph)
    winning, large_material, crown, small_material = _fact_pro_priority(probe)

    # Graded term 3 — the Categoriser score, scaled to a negated int so a
    # higher Cat (fewer / weaker heuristic objections) sorts first under ``min``.
    cat_key = -round(_categoriser_score(probe, graph) * _CAT_SCALE)
    # Graded term 4 — the value-weighted accepted-heuristic-pro count, negated
    # so more accepted heuristic support sorts first.
    heuristic_pro_key = -_accepted_heuristic_pro_count(probe)
    # Term 5 — the static-eval tiebreak (smaller child evaluation = better for
    # the mover, see ``_static_eval_int``).
    eval_key = _static_eval_int(probe, board)

    return (
        objection_magnitude,
        -winning,
        -large_material,
        -crown,
        -small_material,
        cat_key,
        heuristic_pro_key,
        eval_key,
        probe.pdn,
    )


def _move_for_pdn(board: CheckersBoard, pdn: str) -> CheckersMove:
    """Return the legal ``CheckersMove`` on ``board`` whose PDN is ``pdn``."""
    for move in board.legal_moves():
        if move.pdn() == pdn:
            return move
    raise ValueError(f"no legal move with PDN {pdn!r} on the given board")


# --- the multi-mode selector surface (design §7) ----------------------------
#
# Design §7: "keep the dialectical-chess multi-mode ``choose_move`` surface
# (``grounded``, ``categoriser``, ``score``, ...) for differential testing,
# with the lexicographic key above as the default (``argument``) mode."
#
# Every mode below is a DETERMINISTIC selector over the CRISP SURVIVORS — the
# ``min`` candidate set is always ``graph.survivors`` (or, under the design §6
# empty-survivor fallback, all moves), so no mode can ever resurrect a
# crisply-eliminated move. The modes differ only in the key they minimise; each
# key ends in ``probe.pdn`` so the result is total and deterministic.


def _static_eval_int(probe: MoveProbe, board: CheckersBoard | None) -> int:
    """The static-eval tiebreak component for ``probe`` — smaller sorts first.

    ``static_evaluation`` is side-to-move relative; after applying the move it
    scores the *opponent*, so ``static_evaluation(board.apply(move))`` is the
    evaluation FOR THE OPPONENT. A *better* position for the mover is a *worse*
    one for the opponent, i.e. a smaller ``static_evaluation`` of the child —
    which already sorts first under ``min``, so the child evaluation is returned
    directly (no extra negation). ``board`` ``None`` (the selector is being
    unit-tested without a board) yields 0.
    """
    if board is None:
        return 0
    move = _move_for_pdn(board, probe.pdn)
    return static_evaluation(board.apply(move))


def _score_key(
    probe: MoveProbe, board: CheckersBoard | None
) -> tuple[int, str]:
    """``score`` mode key — minimise the negated static evaluation, then PDN."""
    return (_static_eval_int(probe, board), probe.pdn)


def _grounded_key(
    probe: MoveProbe, graph: RootArgumentGraph, board: CheckersBoard | None
) -> tuple[int, int, int, int, int, int, str]:
    """``grounded`` mode key — the FACT terms 1-2 only, then the tiebreak.

    The crisp-layer key: worst unavoidable FACT-objection magnitude, then the
    FACT pro-value priority tuple, then the static-eval / PDN tiebreak. The
    graded terms 3-4 are deliberately omitted — ``grounded`` ranks purely by
    the crisp Dung layer.
    """
    objection_magnitude = _worst_fact_objection_magnitude(probe, graph)
    winning, large_material, crown, small_material = _fact_pro_priority(probe)
    return (
        objection_magnitude,
        -winning,
        -large_material,
        -crown,
        -small_material,
        _static_eval_int(probe, board),
        probe.pdn,
    )


def _categoriser_key(
    probe: MoveProbe, graph: RootArgumentGraph, board: CheckersBoard | None
) -> tuple[int, int, int, str]:
    """``categoriser`` mode key — the graded layer alone, then the tiebreak.

    Minimises the negated Categoriser score (graded term 3), then the negated
    accepted-heuristic-pro count (graded term 4), then the static-eval / PDN
    tiebreak. The FACT terms 1-2 are omitted — ``categoriser`` ranks purely by
    the graded Categoriser layer (this is the mode the design §7 names for
    differential testing of the graded layer in isolation).
    """
    cat_key = -round(_categoriser_score(probe, graph) * _CAT_SCALE)
    heuristic_pro_key = -_accepted_heuristic_pro_count(probe)
    return (cat_key, heuristic_pro_key, _static_eval_int(probe, board), probe.pdn)


def _support_key(
    probe: MoveProbe, graph: RootArgumentGraph, board: CheckersBoard | None
) -> tuple[int, int, int, str]:
    """``support`` mode key — the heuristic-pro support proxy first.

    Minimises the negated accepted-heuristic-pro count (the design §7 v1
    support proxy) first, then the negated Categoriser score, then the
    static-eval / PDN tiebreak — the graded layer with the support term
    promoted ahead of the Categoriser term, for differential testing of the
    heuristic-pro contribution.
    """
    heuristic_pro_key = -_accepted_heuristic_pro_count(probe)
    cat_key = -round(_categoriser_score(probe, graph) * _CAT_SCALE)
    return (heuristic_pro_key, cat_key, _static_eval_int(probe, board), probe.pdn)


def _candidates(
    probes: list[MoveProbe], graph: RootArgumentGraph
) -> list[MoveProbe]:
    """The crisp survivors among ``probes`` — the candidate set every mode ranks.

    ``graph.survivors`` is the grounded ``move:`` set, or — under the design §6
    empty-survivor fallback — all moves. Restricting every mode to this set is
    the structural guarantee that no ``selector_mode`` can resurrect a
    crisply-eliminated move (design §7). ``survivors`` is empty only for a graph
    with no moves; with probes present it always contains at least the
    empty-survivor-fallback set, so the returned list is non-empty.
    """
    survivors = graph.survivors
    candidates = (
        [p for p in probes if p.pdn in survivors] if survivors else list(probes)
    )
    if not candidates:
        candidates = list(probes)
    return candidates


def choose_move(
    probes: list[MoveProbe],
    graph: RootArgumentGraph,
    *,
    selector_mode: str = "argument",
    board: CheckersBoard | None = None,
) -> MoveProbe:
    """Select a move from the crisp survivors (design §7).

    Restricts to the crisp-layer survivors (``graph.survivors`` — the moves
    whose ``move:`` argument is grounded, or *all* moves under the design §6
    empty-survivor fallback), then picks the survivor minimising the key for
    ``selector_mode``:

    * ``argument`` (default) — the full §7 lexicographic key: FACT terms 1-2,
      then graded terms 3-4, then the static-eval / PDN tiebreak
      (:func:`_selection_key`). This is the engine's playing mode.
    * ``categoriser`` — the graded layer alone (Categoriser score, then
      heuristic-pro count), then the tiebreak (:func:`_categoriser_key`).
    * ``score`` — the static evaluation alone, then the PDN tiebreak
      (:func:`_score_key`).
    * ``grounded`` — the crisp FACT terms 1-2 alone, then the tiebreak
      (:func:`_grounded_key`).
    * ``support`` — the heuristic-pro support proxy promoted ahead of the
      Categoriser score, then the tiebreak (:func:`_support_key`).
    * ``optimizer`` — the full §7 lexicographic key, identical to ``argument``.
      dialectical-chess routes ``optimizer`` to a separate optimisation module;
      checkers has no such module (design §1 names none), so this mode is the
      full key — a documented, deterministic alias kept for surface parity.

    Every mode ranks the **same** candidate set — the crisp survivors — so no
    mode can resurrect a crisply-eliminated move. Every key ends in
    ``probe.pdn``, so every mode is deterministic.

    ``board`` is the position the probed moves are played from — passing it
    enables the static-evaluation tiebreak (design §7 term 5). The engine
    always passes it; it is optional so the selector stays unit-testable
    without a board.

    Raises :class:`ValueError` if ``selector_mode`` is unknown or if ``probes``
    is empty — a terminal position has no move to choose and the engine handles
    that case before calling here.
    """
    if selector_mode not in SELECTOR_MODES:
        raise ValueError(f"unknown selector_mode: {selector_mode}")
    if not probes:
        raise ValueError("choose_move called with no probes (terminal position)")

    candidates = _candidates(probes, graph)

    if selector_mode == "score":
        return min(candidates, key=lambda p: _score_key(p, board))
    if selector_mode == "grounded":
        return min(candidates, key=lambda p: _grounded_key(p, graph, board))
    if selector_mode == "categoriser":
        return min(candidates, key=lambda p: _categoriser_key(p, graph, board))
    if selector_mode == "support":
        return min(candidates, key=lambda p: _support_key(p, graph, board))
    # ``argument`` (default) and ``optimizer`` — the full §7 lexicographic key.
    return min(candidates, key=lambda p: _selection_key(p, graph, board))
