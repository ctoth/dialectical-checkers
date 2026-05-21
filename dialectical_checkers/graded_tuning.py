"""Central tuning table for the v1.5 opinion-valued graded layer (design V1.5).

The v1.5 graded layer (``arguments.build_graded_layer``) replaces the
attack-only Categoriser with ``doxa``'s opinion-valued bipolar semantics
(design ``notes/checkers-v1.5-design.md`` decisions V1.5-D1..D7). Two families
of numbers drive it:

* the **move base-rate synthesis** (D4) — a checkers move has no ``probe.score``
  (always 0), so the move node's base rate ``a`` is synthesized from the static
  evaluation of the position the move reaches, squashed into the open interval
  ``(0, 1)`` that ``doxa.Opinion`` requires;
* the **witness -> Opinion mapping** (D5) — each HEURISTIC witness becomes a
  leaf node carrying a non-vacuous ``Opinion`` whose belief encodes how strongly
  the witness fires and whose uncertainty encodes that it is a *soft* positional
  judgement.

Design V1.5-D4 / D5 are explicit that the exact numbers are *tuning knobs* the
coder picks at defensible starting values; the Verifier's measured-strength gate
validates them. They are gathered HERE — one table with provenance — rather than
scattered as literals through ``arguments.py``, exactly as the coder directive
(point 6) requires.

This module is pure: it imports only the stdlib.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Move base-rate synthesis (design V1.5-D4)
# ---------------------------------------------------------------------------
#
# ``a`` is the move node's base rate — its prior strength before any HEURISTIC
# witness is heard. ``doxa.Opinion`` requires ``0 < a < 1`` strictly, and an
# unargued move resolves to ``expectation() == a`` (verified — a vacuous-
# intrinsic leaf with no edges). So ``a`` must be the move's own prior on a
# 0..1 scale where larger is better for the mover.
#
# The only checkers prior available is ``search.static_evaluation`` of the
# position the move reaches. ``static_evaluation`` is side-to-move relative;
# the position the move reaches has the OPPONENT to move, so a SMALLER child
# evaluation is a BETTER move for the mover (selection.py documents this exact
# sign). The synthesis therefore squashes the NEGATED child evaluation through a
# logistic so a better move (smaller child eval) maps to a larger ``a``.
#
# ``_BASE_RATE_SCALE`` sets how many weighted-material centipawns move ``a`` one
# logistic "unit". A man is 100; 400 (four men) is a decisive material swing,
# so a four-man advantage maps ``a`` to ~0.73 and a four-man deficit to ~0.27 —
# a meaningful but not saturating prior. The clamp keeps ``a`` strictly inside
# ``(0, 1)`` (the logistic only reaches the open bounds asymptotically, but a
# terminal-loss sentinel of -100_000 would otherwise round to exactly 0/1).

#: Centipawns of weighted material per logistic unit of the base-rate squash.
_BASE_RATE_SCALE: float = 400.0

#: The base rate is clamped into ``[_BASE_RATE_MIN, _BASE_RATE_MAX]`` so it
#: stays strictly inside the open ``(0, 1)`` ``doxa.Opinion`` requires even for
#: a terminal-loss / terminal-win child evaluation sentinel.
_BASE_RATE_MIN: float = 0.02
_BASE_RATE_MAX: float = 0.98


def move_base_rate(child_evaluation: int) -> float:
    """Synthesize a move node's base rate ``a`` from its child evaluation (D4).

    ``child_evaluation`` is ``search.static_evaluation(board.apply(move))`` —
    the static evaluation of the position the move reaches, which is
    OPPONENT-relative (the opponent is to move there). A smaller child
    evaluation is a better move for the mover, so the negated child evaluation
    is squashed through a logistic: ``a = 1 / (1 + exp(child_eval / scale))``.
    The result is clamped into the open interval ``(0, 1)`` ``doxa.Opinion``
    requires (a terminal sentinel would otherwise saturate to 0 or 1).

    A move reaching an even position (child evaluation 0) gets ``a == 0.5``.
    """
    # Logistic of the negated child evaluation: smaller child eval -> larger a.
    raw = 1.0 / (1.0 + math.exp(child_evaluation / _BASE_RATE_SCALE))
    return min(_BASE_RATE_MAX, max(_BASE_RATE_MIN, raw))


# ---------------------------------------------------------------------------
# Witness -> Opinion mapping (design V1.5-D5)
# ---------------------------------------------------------------------------
#
# Each HEURISTIC witness is a leaf node carrying a non-vacuous intrinsic
# ``Opinion(b, d, u, a)``:
#
# * ``b`` (belief) — how strongly the witness fires. A HEURISTIC witness with no
#   magnitude (``pro:opposition``, ``obj:back_rank_break``, ...) fires at a
#   fixed strength ``_WITNESS_BELIEF_BASE``. A magnitude-carrying witness
#   (``pro:center:{n}``, ``pro:mobility:{n}``) fires more strongly as ``n``
#   grows: belief interpolates linearly from ``_WITNESS_BELIEF_BASE`` toward
#   ``_WITNESS_BELIEF_MAX`` as the magnitude rises to ``_WITNESS_MAGNITUDE_SAT``,
#   and saturates there (a HEURISTIC count is noisy — past a few units more
#   does not raise confidence).
# * ``u`` (uncertainty) — fixed at ``_WITNESS_UNCERTAINTY``. EVERY graded-layer
#   witness is a *soft* positional judgement, never a proof (a proof would be a
#   FACT witness in the crisp layer). A meaningful, non-zero ``u`` is what makes
#   the uncertainty channel live: a contested move with a strong pro AND a
#   strong obj witness then correctly resolves to high ``u`` under doxa's CCF
#   accrual (design V1.5-D1 — the decisive reason for the opinion-valued layer).
# * ``d`` (disbelief) — the residual ``1 - b - u``; never set directly.
# * ``a`` (base rate) — ``_WITNESS_BASE_RATE``, a neutral 0.5. The witness node
#   is never itself ranked (only ``move:`` nodes are read by the selector), and
#   ``evaluate`` re-stamps every node's ``a`` with its own intrinsic ``a``, so a
#   witness leaf resolves with ``a = 0.5``; the value is immaterial to ranking
#   but must be a valid base rate.
#
# The belief band is bounded above by ``1 - _WITNESS_UNCERTAINTY`` so the
# residual disbelief ``d`` is never negative; ``_WITNESS_BELIEF_MAX`` is set at
# that bound. These numbers are the defensible starting values design V1.5-D5
# calls for; the Verifier's measured-strength gate is where they are tuned.

#: Fixed uncertainty of every HEURISTIC witness opinion — a positional
#: judgement is always a soft one, never a proof.
_WITNESS_UNCERTAINTY: float = 0.30

#: Belief of a HEURISTIC witness that carries no magnitude (it simply fired).
_WITNESS_BELIEF_BASE: float = 0.55

#: Belief of a fully-saturated magnitude-carrying HEURISTIC witness. Capped at
#: ``1 - _WITNESS_UNCERTAINTY`` so the residual disbelief stays non-negative.
_WITNESS_BELIEF_MAX: float = 1.0 - _WITNESS_UNCERTAINTY  # 0.70

#: The magnitude at which a magnitude-carrying witness reaches full belief. A
#: HEURISTIC ``:{n}`` count (central-square occupation, mobility gain) is noisy;
#: past a handful of units more does not add confidence.
_WITNESS_MAGNITUDE_SAT: int = 5

#: Neutral base rate for a witness leaf node — the witness is never ranked, so
#: this is immaterial to the move scores, but must be a valid ``(0, 1)`` value.
_WITNESS_BASE_RATE: float = 0.5

#: Full trust for every witness -> move edge (design V1.5-D3: per-edge witness
#: reliability is a later tuning knob, not v1). ``Opinion.dogmatic_true(0.5)``
#: passes the discounted child opinion through unchanged.
_EDGE_TRUST_BASE_RATE: float = 0.5


def witness_belief(magnitude: int | None) -> float:
    """The belief ``b`` of a HEURISTIC witness opinion (design V1.5-D5).

    A witness with no magnitude fires at the fixed ``_WITNESS_BELIEF_BASE``. A
    magnitude-carrying witness fires more strongly as ``magnitude`` grows:
    belief interpolates linearly from ``_WITNESS_BELIEF_BASE`` toward
    ``_WITNESS_BELIEF_MAX`` as the magnitude rises to ``_WITNESS_MAGNITUDE_SAT``
    and saturates there. The result is always in
    ``[_WITNESS_BELIEF_BASE, _WITNESS_BELIEF_MAX]``.
    """
    if magnitude is None:
        return _WITNESS_BELIEF_BASE
    # A witness magnitude is a strictly positive count (evidence.py guarantees
    # it); clamp into [0, sat] so belief interpolates and then saturates.
    capped = max(0, min(magnitude, _WITNESS_MAGNITUDE_SAT))
    fraction = capped / _WITNESS_MAGNITUDE_SAT
    span = _WITNESS_BELIEF_MAX - _WITNESS_BELIEF_BASE
    return _WITNESS_BELIEF_BASE + span * fraction
