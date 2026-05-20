"""Selector modes + selection keys (design §7).

Phase 3b implements the **FACT-tier** terms of the design §7 selector key
only. The graded Categoriser term and the heuristic-pro term (design §7 key
terms 3-4) are Phase 4 — they are left as an explicit, documented seam below
(see ``_PHASE4_SEAM``) and are *not* implemented here.

The FACT-tier selector key, per surviving move, lexicographic — **smaller is
better** (the key is consumed by ``min``):

1. **minimise the worst unavoidable FACT-objection magnitude.** For a move
   that survived the crisp layer this is 0 (it carries no undefeated FACT
   objection — it is *clean*). It is non-zero only under the design §6
   empty-survivor fallback, where *every* move carries an undefeated FACT
   objection and the selector must still pick the least-bad: then this term is
   the magnitude of the move's worst FACT objection, with a forced
   ``obj:terminal_loss`` (losing the *game*) ranked above any finite material
   loss.
2. **maximise the FACT-tier pro value**, as the value-priority tuple
   ``winning > large material > crown > small material`` (design §7 term 2).
3. **deterministic tiebreak**: the Phase-3b static evaluation (``search.py``)
   of the position the move reaches, then the move's PDN string.

The Phase-4 terms (Categoriser score over heuristic objections; value-weighted
accepted-heuristic-pro count) slot in *between* term 2 and term 3 — see
``_PHASE4_SEAM``.

This module imports only ``dialectical_checkers`` and the stdlib.
"""

from __future__ import annotations

from dialectical_checkers.arguments import MoveProbe, RootArgumentGraph
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


def _worst_fact_objection_magnitude(probe: MoveProbe) -> int:
    """The worst unavoidable FACT-objection magnitude on ``probe`` (term 1).

    0 when the move carries no FACT objection — it is *clean*, the normal case
    for a move that survived the crisp layer. Otherwise the largest magnitude
    among the move's FACT objections and reply attacks, with a forced
    ``obj:terminal_loss`` / ``reply:terminal_loss`` (losing the game itself)
    ranked above any finite material loss via ``_TERMINAL_LOSS_MAGNITUDE``.

    Both ``objections`` and ``reply_attacks`` are consulted: design §6 has
    both channels defeat a move in the crisp layer, so both contribute to "the
    worst thing proven against this move".
    """
    worst = 0
    for label in (*probe.objections, *probe.reply_attacks):
        try:
            evidence = to_argument_evidence(label)
        except ValueError:
            continue
        if evidence.tier is not Tier.FACT:
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

_LARGE_MATERIAL_THRESHOLD = 100  # strictly more than one man is "large"


def _fact_pro_priority(probe: MoveProbe) -> tuple[int, int, int, int]:
    """The FACT pro-value priority tuple for ``probe`` (term 2).

    Returns ``(winning, large_material, crown, small_material)`` — every
    component "bigger is better":

    * ``winning`` — 1 if the move carries ``pro:terminal_win`` (realises the
      ``winning`` value — ends the game in the mover's favour), else 0.
    * ``large_material`` — the largest FACT material magnitude on the move
      (``pro:material`` / ``pro:shot_setup``) that exceeds one man, else 0.
    * ``crown`` — 1 if the move carries ``pro:crown``, else 0.
    * ``small_material`` — the largest FACT material magnitude on the move
      that is at most one man, else 0.

    Design §7 orders these strictly: winning beats large material beats crown
    beats small material.
    """
    winning = 0
    crown = 0
    large_material = 0
    small_material = 0
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
            if evidence.magnitude > _LARGE_MATERIAL_THRESHOLD:
                large_material = max(large_material, evidence.magnitude)
            else:
                small_material = max(small_material, evidence.magnitude)
    return (winning, large_material, crown, small_material)


# --- the lexicographic selection key ----------------------------------------


def _selection_key(
    probe: MoveProbe, board: CheckersBoard | None
) -> tuple[int, int, int, int, int, int, str]:
    """The FACT-tier lexicographic selection key for ``probe`` (design §7).

    Smaller is better — the key is consumed by ``min``. The components, in
    order:

    1. the worst unavoidable FACT-objection magnitude (minimised);
    2-5. the FACT pro-value priority tuple, negated so "more pro" sorts first
       (winning, large material, crown, small material);
    6. the static evaluation of the reached position, negated so a higher
       evaluation sorts first (deterministic tiebreak);
    7. the move's PDN string (final deterministic tiebreak).

    The Phase-4 graded terms (``_PHASE4_SEAM``) would slot in between
    components 5 and 6 when implemented.

    ``board`` is the position the moves are played from; it is needed to apply
    the move for the static-eval tiebreak. When it is ``None`` the static-eval
    component is 0 — the PDN tiebreak still makes the key total and
    deterministic.
    """
    objection_magnitude = _worst_fact_objection_magnitude(probe)
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

    return min(candidates, key=lambda p: _selection_key(p, board))
