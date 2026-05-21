"""Phase 3b — direct tests for the FACT-tier selector contract (design §7).

The directive's MINOR finding: the suite checked curated engine outcomes but had
no direct tests of the Phase-3b selector key contract. These tests drive
``selection._selection_key`` / ``selection.choose_move`` over hand-built
``MoveProbe`` lists and the crisp graph they build, proving:

* the first key term (worst unavoidable FACT-objection magnitude) is **0 for a
  grounded crisp survivor** and **non-zero only in the §6 empty-survivor
  fallback** — where it ranks by the worst *undefeated* FACT objection / reply;
* a FACT reply / objection **defeated by a keyed FACT defense** on a grounded
  survivor does NOT count as an unavoidable loss (term 1 stays 0);
* the clean FACT pro-value ordering is
  ``winning > large material > crown > small material`` (design §7 term 2);
* the pro-material component is the **net** material the move keeps — a
  defended even exchange scores 0 material, below a clean material gain.

All probes here are hand-built so the selector semantics are tested in
isolation, independent of the witness and board layers.
"""

from __future__ import annotations

import pytest

from dialectical_checkers.arguments import (
    MoveProbe,
    RootArgumentGraph,
    build_root_argument_graph,
)
from dialectical_checkers.selection import (
    SELECTOR_MODES,
    _accepted_heuristic_pro_count,
    _fact_pro_priority,
    _graded_strength,
    _selection_key,
    _worst_fact_objection_magnitude,
    choose_move,
)

# The terminal-loss sentinel mirrored from ``selection._TERMINAL_LOSS_MAGNITUDE``
# — a forced GAME loss outranks every finite material loss in key term 1.
_TERMINAL_LOSS = 10**9


# ---------------------------------------------------------------------------
# term 1 — worst unavoidable FACT-objection magnitude
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_term1_is_zero_for_clean_grounded_survivor() -> None:
    """A clean move (no objection at all) is a grounded survivor with term 1 = 0."""
    probes = [MoveProbe(pdn="11-15", reasons=("pro:material:100",))]
    graph = build_root_argument_graph(probes)
    assert _worst_fact_objection_magnitude(probes[0], graph) == 0
    assert _selection_key(probes[0], graph, None)[0] == 0


@pytest.mark.unit
def test_term1_is_zero_for_defended_grounded_survivor() -> None:
    """A grounded survivor whose only FACT reply is DEFEATED has term 1 = 0.

    The probe carries a FACT ``reply:material:100`` and a keyed
    ``defense:holds_exchange@reply:material:100`` that defeats it. The move's
    ``move:`` argument is therefore grounded — and term 1, the worst
    *unavoidable* FACT loss, must be 0: a defeated reply is not unavoidable.
    """
    probe = MoveProbe(
        pdn="2x11",
        reasons=("pro:material:100",),
        reply_attacks=("reply:material:100",),
        defenses=("defense:holds_exchange@reply:material:100",),
    )
    graph = build_root_argument_graph([probe])
    # The move survived the crisp layer — its argument is grounded.
    assert graph.move_arguments["2x11"] in graph.grounded_extension
    # ...so term 1 is 0 even though the probe carries a FACT reply label.
    assert _worst_fact_objection_magnitude(probe, graph) == 0
    assert _selection_key(probe, graph, None)[0] == 0


@pytest.mark.unit
def test_term1_nonzero_only_in_empty_survivor_fallback() -> None:
    """Term 1 is non-zero ONLY when no move is a grounded survivor.

    Two moves, each with an undefeated FACT objection: no ``move:`` argument is
    grounded, the §6 empty-survivor fallback fires, and term 1 of each move is
    the magnitude of its worst undefeated FACT objection.
    """
    probes = [
        MoveProbe(pdn="13-17", objections=("obj:allows_shot:100",)),
        MoveProbe(pdn="6-10", objections=("obj:allows_shot:50",)),
    ]
    graph = build_root_argument_graph(probes)
    # No move grounded — the fallback returns all moves.
    grounded_moves = {
        pdn
        for pdn, arg in graph.move_arguments.items()
        if arg in graph.grounded_extension
    }
    assert grounded_moves == set()
    assert _worst_fact_objection_magnitude(probes[0], graph) == 100
    assert _worst_fact_objection_magnitude(probes[1], graph) == 50


@pytest.mark.unit
def test_term1_terminal_loss_outranks_finite_material_loss() -> None:
    """In the fallback a forced terminal GAME loss outranks any material loss.

    Both moves are undefeated losers (fallback); the one losing the game itself
    carries the ``_TERMINAL_LOSS`` sentinel, far above the finite-material one.
    """
    probes = [
        MoveProbe(pdn="9-14", reply_attacks=("reply:terminal_loss",)),
        MoveProbe(pdn="6-10", objections=("obj:allows_shot:300",)),
    ]
    graph = build_root_argument_graph(probes)
    assert _worst_fact_objection_magnitude(probes[0], graph) == _TERMINAL_LOSS
    assert _worst_fact_objection_magnitude(probes[1], graph) == 300


@pytest.mark.unit
def test_term1_undefeated_attacker_counts_defeated_one_does_not() -> None:
    """In the fallback only an UNDEFEATED FACT attacker contributes to term 1.

    The move carries two FACT replies; a keyed defense answers only the
    smaller one. The move is still NOT grounded (the larger reply stands), so
    the fallback fires — and term 1 is the magnitude of the *undefeated* reply
    (200), not the defeated one (100).
    """
    probe = MoveProbe(
        pdn="7x14",
        reply_attacks=("reply:material:100", "reply:material:200"),
        defenses=("defense:holds_exchange@reply:material:100",),
    )
    graph = build_root_argument_graph([probe])
    assert graph.move_arguments["7x14"] not in graph.grounded_extension
    assert _worst_fact_objection_magnitude(probe, graph) == 200


# ---------------------------------------------------------------------------
# term 2 — FACT pro-value priority ordering
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_clean_pro_ordering_winning_beats_large_material() -> None:
    """``winning`` outranks ``large material`` in the FACT pro-value tuple."""
    winning = MoveProbe(pdn="1-5", reasons=("pro:terminal_win",))
    large = MoveProbe(pdn="2-6", reasons=("pro:material:300",))
    graph = build_root_argument_graph([winning, large])
    # Smaller key sorts first under ``min``; the winning move must sort first.
    assert _selection_key(winning, graph, None) < _selection_key(
        large, graph, None
    )


@pytest.mark.unit
def test_clean_pro_ordering_large_material_beats_crown() -> None:
    """``large material`` outranks ``crown`` in the FACT pro-value tuple."""
    large = MoveProbe(pdn="2-6", reasons=("pro:material:300",))
    crown = MoveProbe(pdn="3-7", reasons=("pro:crown",))
    graph = build_root_argument_graph([large, crown])
    assert _selection_key(large, graph, None) < _selection_key(
        crown, graph, None
    )


@pytest.mark.unit
def test_clean_pro_ordering_crown_beats_small_material() -> None:
    """``crown`` outranks ``small material`` in the FACT pro-value tuple."""
    crown = MoveProbe(pdn="3-7", reasons=("pro:crown",))
    small = MoveProbe(pdn="4-8", reasons=("pro:material:100",))
    graph = build_root_argument_graph([crown, small])
    assert _selection_key(crown, graph, None) < _selection_key(
        small, graph, None
    )


@pytest.mark.unit
def test_clean_pro_ordering_full_chain() -> None:
    """The full clean FACT pro ordering: winning > large > crown > small.

    ``choose_move`` over the four clean probes must pick the ``winning`` one,
    and removing it in turn exposes the next priority level.
    """
    winning = MoveProbe(pdn="1-5", reasons=("pro:terminal_win",))
    large = MoveProbe(pdn="2-6", reasons=("pro:material:300",))
    crown = MoveProbe(pdn="3-7", reasons=("pro:crown",))
    small = MoveProbe(pdn="4-8", reasons=("pro:material:100",))
    chain = [winning, large, crown, small]
    for i in range(len(chain)):
        probes = chain[i:]
        graph = build_root_argument_graph(probes)
        assert choose_move(probes, graph).pdn == probes[0].pdn


@pytest.mark.unit
def test_pro_material_component_is_net_of_defended_giveback() -> None:
    """The pro-material component is NET — a defended even exchange scores 0.

    ``clean`` is a clean ``pro:material:100``. ``held_even`` captures 100 but
    its defended reply recaptures 100 — net 0. The selector must rank the clean
    gain above the held-even exchange (its small_material is 0).
    """
    clean = MoveProbe(pdn="4-8", reasons=("pro:material:100",))
    held_even = MoveProbe(
        pdn="2x11",
        reasons=("pro:material:100",),
        reply_attacks=("reply:material:100",),
        defenses=("defense:holds_exchange@reply:material:100",),
    )
    graph = build_root_argument_graph([clean, held_even])
    # Both are grounded survivors with term 1 = 0.
    assert _worst_fact_objection_magnitude(clean, graph) == 0
    assert _worst_fact_objection_magnitude(held_even, graph) == 0
    # Net pro material: clean keeps 100 (small_material), held_even keeps 0.
    assert _fact_pro_priority(clean) == (0, 0, 0, 100)
    assert _fact_pro_priority(held_even) == (0, 0, 0, 0)
    # ...so the selector ranks the clean gain first.
    assert _selection_key(clean, graph, None) < _selection_key(
        held_even, graph, None
    )
    assert choose_move([clean, held_even], graph).pdn == "4-8"


@pytest.mark.unit
def test_net_material_demotes_large_capture_with_big_giveback() -> None:
    """A 300-capture that gives 250 back nets 50 — below a clean 100 gain.

    The defended-reply giveback can demote a move from the ``large material``
    band into the ``small material`` band: a move capturing 300 but conceding
    250 keeps only 50, ranked below a clean ``pro:material:100``.
    """
    big_giveback = MoveProbe(
        pdn="6x15x22",
        reasons=("pro:material:300",),
        reply_attacks=("reply:material:250",),
        defenses=("defense:holds_exchange@reply:material:250",),
    )
    clean_small = MoveProbe(pdn="4-8", reasons=("pro:material:100",))
    graph = build_root_argument_graph([big_giveback, clean_small])
    # big_giveback nets 50 -> small_material; clean_small nets 100 -> small.
    assert _fact_pro_priority(big_giveback) == (0, 0, 0, 50)
    assert _fact_pro_priority(clean_small) == (0, 0, 0, 100)
    assert choose_move([big_giveback, clean_small], graph).pdn == "4-8"


# ---------------------------------------------------------------------------
# term 3 — opinion-valued graded strength (design V1.5-D7)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_term3_graded_strength_clean_move_is_above_neutral() -> None:
    """A surviving move with a HEURISTIC pro resolves above the neutral 0.5.

    Term 3 reads the move's opinion-valued graded strength
    (``Opinion.expectation()``). A move with a HEURISTIC pro-reason and no
    objection accrues that supporter, so its strength rises strictly above the
    neutral 0.5 a witnessless / board-free move would resolve to.
    """
    probe = MoveProbe(pdn="11-15", reasons=("pro:opposition",))
    graph = build_root_argument_graph([probe])
    assert _graded_strength(probe, graph) > 0.5


@pytest.mark.unit
def test_term3_graded_strength_drops_under_heuristic_objection() -> None:
    """A HEURISTIC objection drops the move's term-3 graded strength.

    Two clean-FACT survivors (both term 1 = 0, no FACT pro): one carries a
    HEURISTIC objection, one does not. The objected move's opinion-valued
    strength is strictly lower, so graded term 3 ranks the clean move first —
    and ``choose_move`` in the default ``argument`` mode picks it. The
    pre-Phase-5 selector (FACT terms only) would have tied them and fallen to
    the PDN tiebreak, picking ``10-15`` only by string order — this test pins
    that the graded layer, not the tiebreak, makes the choice.
    """
    objected = MoveProbe(
        pdn="10-15",
        reasons=("pro:opposition",),
        objections=("obj:loses_opposition",),
    )
    clean = MoveProbe(pdn="11-16", reasons=("pro:opposition",))
    graph = build_root_argument_graph([objected, clean])
    assert _graded_strength(objected, graph) < _graded_strength(clean, graph)
    # Graded term 3 ranks the clean move first under the full key.
    assert _selection_key(clean, graph, None) < _selection_key(
        objected, graph, None
    )
    assert choose_move([objected, clean], graph).pdn == "11-16"


@pytest.mark.unit
def test_term3_comes_after_fact_terms() -> None:
    """A FACT pro always outranks a better graded strength (term 2 > term 3).

    ``fact_move`` carries a FACT ``pro:material:100`` but also a HEURISTIC
    objection (lower graded strength); ``graded_move`` is heuristically clean
    (higher graded strength) but has no FACT pro. The FACT pro-value term (2)
    dominates the graded strength term (3), so the selector picks the FACT move
    despite its lower graded strength — a FACT decision is never overridden by
    a graded one (design V1.5-D6).
    """
    fact_move = MoveProbe(
        pdn="2-6",
        reasons=("pro:material:100",),
        objections=("obj:loses_opposition",),
    )
    graded_move = MoveProbe(pdn="3-7", reasons=("pro:opposition",))
    graph = build_root_argument_graph([fact_move, graded_move])
    # The graded layer rates the clean move higher than the FACT move...
    assert _graded_strength(graded_move, graph) > _graded_strength(
        fact_move, graph
    )
    # ...but the FACT pro term decides: ``2-6`` wins despite the lower strength.
    assert choose_move([fact_move, graded_move], graph).pdn == "2-6"


# ---------------------------------------------------------------------------
# term 4 — value-weighted accepted-heuristic-pro count (design §7, Phase 5)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_term4_counts_heuristic_pros_not_fact_pros() -> None:
    """Term 4 counts HEURISTIC pro-reasons only — FACT pros never contribute.

    A probe carrying two HEURISTIC pros and one FACT pro has an
    accepted-heuristic-pro count of 2 — the FACT ``pro:material`` is term 2's
    business, not term 4's.
    """
    probe = MoveProbe(
        pdn="11-15",
        reasons=("pro:opposition", "pro:back_rank_hold", "pro:material:100"),
    )
    assert _accepted_heuristic_pro_count(probe) == 2


@pytest.mark.unit
def test_term4_breaks_a_graded_strength_tie() -> None:
    """Term 4 ranks more accepted heuristic pros first when term 3 ties.

    Two clean survivors, neither with a HEURISTIC objection. ``rich`` carries
    two no-magnitude HEURISTIC pros, ``thin`` carries one — and because the two
    no-magnitude witnesses carry an identical intrinsic ``Opinion``, doxa's CCF
    accrual is idempotent on them, so ``rich`` and ``thin`` resolve to an equal
    opinion-valued graded strength (term 3 ties). Term 4, the value-weighted
    accepted-heuristic-pro count, then breaks the tie in ``rich``'s favour —
    exactly the redundant-but-retained role design V1.5-D7 documents.
    """
    rich = MoveProbe(
        pdn="11-16", reasons=("pro:opposition", "pro:back_rank_hold")
    )
    thin = MoveProbe(pdn="10-15", reasons=("pro:opposition",))
    graph = build_root_argument_graph([rich, thin])
    # The two no-magnitude pros accrue idempotently — term 3 genuinely ties.
    assert _graded_strength(rich, graph) == pytest.approx(
        _graded_strength(thin, graph)
    )
    assert _accepted_heuristic_pro_count(rich) == 2
    assert _accepted_heuristic_pro_count(thin) == 1
    assert _selection_key(rich, graph, None) < _selection_key(
        thin, graph, None
    )
    assert choose_move([rich, thin], graph).pdn == "11-16"


# ---------------------------------------------------------------------------
# differential — selector-mode consistency and determinism (design §7)
# ---------------------------------------------------------------------------


def _mode_probes() -> tuple[list[MoveProbe], RootArgumentGraph]:
    """A hand-built probe set + its graph exercising every selector key term.

    Five surviving moves spanning FACT pros, HEURISTIC objections and
    HEURISTIC pros, so the different selector modes can genuinely diverge.
    """
    probes = [
        MoveProbe(pdn="1-5", reasons=("pro:terminal_win",)),
        MoveProbe(pdn="2-6", reasons=("pro:material:100",)),
        MoveProbe(
            pdn="3-7",
            reasons=("pro:opposition", "pro:back_rank_hold"),
        ),
        MoveProbe(
            pdn="4-8",
            reasons=("pro:opposition",),
            objections=("obj:loses_opposition",),
        ),
        MoveProbe(pdn="9-13", reasons=("pro:opposition",)),
    ]
    return probes, build_root_argument_graph(probes)


@pytest.mark.differential
@pytest.mark.parametrize("mode", sorted(SELECTOR_MODES))
def test_every_selector_mode_is_deterministic(mode: str) -> None:
    """Each ``selector_mode`` returns the same move on repeated calls.

    Every mode's key ends in ``probe.pdn`` (a total, deterministic tiebreak),
    so repeated ``choose_move`` calls in any mode must agree.
    """
    probes, graph = _mode_probes()
    first = choose_move(probes, graph, selector_mode=mode).pdn
    for _ in range(5):
        assert choose_move(probes, graph, selector_mode=mode).pdn == first


@pytest.mark.differential
@pytest.mark.parametrize("mode", sorted(SELECTOR_MODES))
def test_every_selector_mode_picks_a_crisp_survivor(mode: str) -> None:
    """Each ``selector_mode`` returns one of the crisp survivors.

    Every mode restricts its candidate set to ``graph.survivors`` — no mode can
    ever resurrect a crisply-eliminated move (design §7). Here a move carrying
    an undefeated FACT objection is crisply eliminated; no mode may pick it.
    """
    survivor = MoveProbe(pdn="11-15", reasons=("pro:opposition",))
    eliminated = MoveProbe(pdn="9-14", objections=("obj:allows_shot:200",))
    probes = [survivor, eliminated]
    graph = build_root_argument_graph(probes)
    assert graph.survivors == frozenset({"11-15"})
    chosen = choose_move(probes, graph, selector_mode=mode).pdn
    assert chosen in graph.survivors, (mode, chosen)
    assert chosen != "9-14", mode


@pytest.mark.differential
def test_argument_is_the_default_selector_mode() -> None:
    """``choose_move`` with no ``selector_mode`` is the ``argument`` mode."""
    probes, graph = _mode_probes()
    assert (
        choose_move(probes, graph).pdn
        == choose_move(probes, graph, selector_mode="argument").pdn
    )


@pytest.mark.differential
def test_optimizer_mode_aliases_argument_mode() -> None:
    """``optimizer`` mode is the full §7 key — identical to ``argument``.

    checkers has no separate optimisation module (design §1 names none), so
    ``optimizer`` is a documented deterministic alias of the full lexicographic
    key, kept for surface parity with dialectical-chess.
    """
    probes, graph = _mode_probes()
    assert (
        choose_move(probes, graph, selector_mode="optimizer").pdn
        == choose_move(probes, graph, selector_mode="argument").pdn
    )


@pytest.mark.differential
def test_selector_modes_can_diverge() -> None:
    """The selector modes are genuinely distinct — they do not all agree.

    If every mode returned the same move the multi-mode surface would be
    vacuous. Over the hand-built spread of probes, ``score`` (static eval) and
    ``categoriser`` (graded layer) reach a different move from ``argument``
    (full key) on at least one position — confirming the modes are real.
    """
    probes, graph = _mode_probes()
    by_mode = {
        mode: choose_move(probes, graph, selector_mode=mode).pdn
        for mode in sorted(SELECTOR_MODES)
    }
    # ``argument`` leads with the FACT terms -> the terminal-win move 1-5.
    assert by_mode["argument"] == "1-5"
    # ``categoriser`` ignores FACT terms; it ranks by the graded layer, where
    # 4-8 (the only move with a heuristic objection) is NOT chosen and a clean
    # move with more heuristic pros leads.
    assert by_mode["categoriser"] != "4-8"
    # Not every mode agrees — the surface is non-vacuous.
    assert len(set(by_mode.values())) >= 2, by_mode


@pytest.mark.unit
def test_unknown_selector_mode_rejected() -> None:
    """``choose_move`` raises on an unknown ``selector_mode``."""
    probes, graph = _mode_probes()
    with pytest.raises(ValueError, match="unknown selector_mode"):
        choose_move(probes, graph, selector_mode="nonsense")
