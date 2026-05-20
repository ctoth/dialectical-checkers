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

from dialectical_checkers.arguments import MoveProbe, build_root_argument_graph
from dialectical_checkers.selection import (
    _fact_pro_priority,
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
