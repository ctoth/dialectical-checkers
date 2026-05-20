"""Selector modes + selection keys (design §7).

Phase 3b implements the **FACT-tier** terms of the design §7 selector key
only. The graded Categoriser term and the heuristic-pro term (design §7 key
terms 3-4) are Phase 4 — they are left as an explicit, documented seam below
(see ``_PHASE4_SEAM``) and are *not* implemented here.

The FACT-tier selector key, per surviving move, lexicographic — **smaller is
better** (the key is consumed by ``min``):

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
3. **deterministic tiebreak**: the Phase-3b static evaluation (``search.py``)
   of the position the move reaches, then the move's PDN string.

The Phase-4 terms (Categoriser score over heuristic objections; value-weighted
accepted-heuristic-pro count) slot in *between* term 2 and term 3 — see
``_PHASE4_SEAM``.

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

# --- Phase 4 seam -----------------------------------------------------------
#
# Design §7 selector key terms 3 and 4 — the graded layer — are deliberately
# NOT implemented in Phase 3b:
#
#   3. maximise Cat(move:A) — the Categoriser score over the move's HEURISTIC
#      objections (``arguments.py`` graded layer, Phase 4).
#   4. maximise the value-weighted accepted-HEURISTIC-pro count.
#
# When Phase 4 lands, those two terms slot into ``_selection_key`` *between*
# the FACT pro-value term and the static-eval tiebreak, keeping this module's
# lexicographic ordering otherwise intact. Until then the FACT-tier key below
# is the whole selector — sound, because a HEURISTIC term can only ever
# *rank* survivors and never resurrect a crisply-eliminated move (design §6).
_PHASE4_SEAM = "graded Categoriser + heuristic-pro terms — see design §7"


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


# --- the lexicographic selection key ----------------------------------------


def _selection_key(
    probe: MoveProbe,
    graph: RootArgumentGraph,
    board: CheckersBoard | None,
) -> tuple[int, int, int, int, int, int, str]:
    """The FACT-tier lexicographic selection key for ``probe`` (design §7).

    Smaller is better — the key is consumed by ``min``. The components, in
    order:

    1. the worst unavoidable FACT-objection magnitude (minimised) — 0 for any
       grounded crisp survivor, non-zero only in the §6 empty-survivor
       fallback (see :func:`_worst_fact_objection_magnitude`);
    2-5. the FACT pro-value priority tuple, negated so "more pro" sorts first
       (winning, large material, crown, small material);
    6. the static evaluation of the reached position, negated so a higher
       evaluation sorts first (deterministic tiebreak);
    7. the move's PDN string (final deterministic tiebreak).

    The Phase-4 graded terms (``_PHASE4_SEAM``) would slot in between
    components 5 and 6 when implemented.

    ``graph`` is the crisp Dung graph the probes were evaluated against — term
    1 reads its grounded extension to tell a grounded survivor (term 1 = 0)
    from an empty-survivor-fallback move.

    ``board`` is the position the moves are played from; it is needed to apply
    the move for the static-eval tiebreak. When it is ``None`` the static-eval
    component is 0 — the PDN tiebreak still makes the key total and
    deterministic.
    """
    objection_magnitude = _worst_fact_objection_magnitude(probe, graph)
    winning, large_material, crown, small_material = _fact_pro_priority(probe)

    if board is not None:
        move = _move_for_pdn(board, probe.pdn)
        # static_evaluation is side-to-move relative: after applying the move
        # it scores the *opponent*. Negate it so a higher value FOR THE MOVER
        # sorts first under ``min``.
        eval_for_mover = -static_evaluation(board.apply(move))
    else:
        eval_for_mover = 0

    return (
        objection_magnitude,
        -winning,
        -large_material,
        -crown,
        -small_material,
        -eval_for_mover,
        probe.pdn,
    )


def _move_for_pdn(board: CheckersBoard, pdn: str) -> CheckersMove:
    """Return the legal ``CheckersMove`` on ``board`` whose PDN is ``pdn``."""
    for move in board.legal_moves():
        if move.pdn() == pdn:
            return move
    raise ValueError(f"no legal move with PDN {pdn!r} on the given board")


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
    empty-survivor fallback), then picks the survivor minimising
    :func:`_selection_key` — the FACT-tier lexicographic key.

    ``selector_mode`` is accepted for the design §7 multi-mode surface; Phase
    3b implements one key, so every mode currently resolves to it. The mode
    set is validated by ``EngineSettings``; an unknown mode here is a caller
    error.

    ``board`` is the position the probed moves are played from — passing it
    enables the static-evaluation tiebreak (design §7 term 5). The engine
    always passes it; it is optional so the selector stays unit-testable
    without a board.

    Raises :class:`ValueError` if ``probes`` is empty — a terminal position
    has no move to choose and the engine handles that case before calling
    here.
    """
    if selector_mode not in SELECTOR_MODES:
        raise ValueError(f"unknown selector_mode: {selector_mode}")
    if not probes:
        raise ValueError("choose_move called with no probes (terminal position)")

    survivors = graph.survivors
    candidates = [p for p in probes if p.pdn in survivors] if survivors else list(
        probes
    )
    # ``survivors`` is empty only for a graph with no moves; with probes
    # present it always contains at least the empty-survivor-fallback set.
    if not candidates:
        candidates = list(probes)

    return min(candidates, key=lambda p: _selection_key(p, graph, board))
