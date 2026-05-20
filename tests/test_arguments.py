"""Phase 3b — tests for ``dialectical_checkers.arguments``.

The crisp Dung argument layer (design ``notes/checkers-design.md`` §6):
``build_root_argument_graph(probes)`` builds a plain Dung
``ArgumentationFramework`` of FACT-tier defeaters, evaluates its grounded
extension with ``formal-argumentation``, and reports the surviving move set.

The directive's crisp-layer assertions:

* a move with an undefeated FACT objection is NOT in the grounded extension;
* a clean move IS;
* a FACT defense that defeats an objection restores its move;
* the empty-survivor fallback returns all moves;
* there is NO ``doubt:`` argument and there are NO duplicated arguments.

Two test styles are mixed: ``unit`` tests over hand-built ``MoveProbe`` lists
that drive the graph construction directly (so the crisp semantics are tested
in isolation, independent of the witness layer), and ``unit`` tests over real
``probe_moves`` output on curated FENs (so the graph is tested on the genuine
FACT witnesses Phase 3a produces).
"""

from __future__ import annotations

import pytest

from dialectical_checkers.arguments import (
    MoveProbe,
    RootArgumentGraph,
    build_root_argument_graph,
)
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.witnesses import probe_moves


# ---------------------------------------------------------------------------
# unit — graph construction over hand-built probes (crisp semantics in isolation)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_clean_move_is_in_grounded_extension() -> None:
    """A move with no FACT objection survives the crisp layer.

    A single probe carrying only a pro-reason and no objection: its ``move:``
    argument has no attacker, so the grounded extension contains it and the
    move survives.
    """
    probes = [MoveProbe(pdn="11-15", reasons=("pro:crown",))]
    graph = build_root_argument_graph(probes)
    move_id = graph.move_arguments["11-15"]
    assert move_id in graph.grounded_extension
    assert "11-15" in graph.survivors


@pytest.mark.unit
def test_move_with_undefeated_fact_objection_is_eliminated() -> None:
    """A move with an undefeated FACT objection is NOT in the grounded extension.

    A probe carrying ``obj:allows_shot:100`` (a FACT objection): the objection
    argument has no attacker, so it is grounded and defeats the ``move:``
    argument — the move is eliminated. With another, clean move present the
    grounded survivor set is exactly that other move.
    """
    probes = [
        MoveProbe(pdn="13-17", objections=("obj:allows_shot:100",)),
        MoveProbe(pdn="6-10"),
    ]
    graph = build_root_argument_graph(probes)
    losing_id = graph.move_arguments["13-17"]
    clean_id = graph.move_arguments["6-10"]
    assert losing_id not in graph.grounded_extension
    assert clean_id in graph.grounded_extension
    assert graph.survivors == frozenset({"6-10"})


@pytest.mark.unit
def test_move_with_undefeated_reply_attack_is_eliminated() -> None:
    """A move defeated by a FACT reply attack is eliminated, like an objection.

    Design §6: both objection and reply-attack channels defeat a move in the
    crisp layer. A probe carrying only ``reply:terminal_loss`` is eliminated.
    """
    probes = [
        MoveProbe(pdn="13-17", reply_attacks=("reply:terminal_loss",)),
        MoveProbe(pdn="6-10"),
    ]
    graph = build_root_argument_graph(probes)
    assert graph.move_arguments["13-17"] not in graph.grounded_extension
    assert graph.survivors == frozenset({"6-10"})


@pytest.mark.unit
def test_fact_defense_restores_its_move() -> None:
    """A FACT defense that defeats an objection restores its move.

    A probe carries both a FACT reply attack (``reply:material:100``) and a
    FACT defense (``defense:holds_exchange``). The defense argument defeats the
    reply argument; the reply is then not grounded, the ``move:`` argument has
    no undefeated attacker, and the move is back in the grounded extension.
    """
    probes = [
        MoveProbe(
            pdn="2x11",
            reasons=("pro:material:100",),
            reply_attacks=("reply:material:100",),
            defenses=("defense:holds_exchange",),
        )
    ]
    graph = build_root_argument_graph(probes)
    move_id = graph.move_arguments["2x11"]
    assert move_id in graph.grounded_extension
    assert "2x11" in graph.survivors


@pytest.mark.unit
def test_empty_survivor_fallback_returns_all_moves() -> None:
    """When every move carries an undefeated FACT objection, all moves survive.

    Design §6 empty-survivor fallback: no ``move:`` argument is grounded, so
    the crisp layer cannot eliminate — the surviving set is *all* moves and
    the engine must still pick one.
    """
    probes = [
        MoveProbe(pdn="13-17", objections=("obj:allows_shot:100",)),
        MoveProbe(pdn="6-10", objections=("obj:allows_shot:50",)),
        MoveProbe(pdn="9-14", reply_attacks=("reply:terminal_loss",)),
    ]
    graph = build_root_argument_graph(probes)
    # No move argument grounded.
    grounded_moves = {
        pdn
        for pdn, arg_id in graph.move_arguments.items()
        if arg_id in graph.grounded_extension
    }
    assert grounded_moves == set()
    # ...so the fallback returns every move.
    assert graph.survivors == frozenset({"13-17", "6-10", "9-14"})


@pytest.mark.unit
def test_no_doubt_node_and_no_duplicate_arguments() -> None:
    """The crisp graph has NO ``doubt:`` argument and NO duplicated arguments.

    Design §0/§6: the ``doubt`` node and copy-counting are anti-patterns the
    corpus rejects. Every argument id is distinct (``arguments`` is a
    ``frozenset`` and the construction never reuses an id), and no id starts
    with ``doubt``.
    """
    probes = [
        MoveProbe(
            pdn="13-17",
            objections=("obj:allows_shot:100",),
            reply_attacks=("reply:material:100",),
        ),
        MoveProbe(pdn="6-10"),
        MoveProbe(pdn="9-14", objections=("obj:terminal_loss",)),
    ]
    graph = build_root_argument_graph(probes)
    assert not any(arg.startswith("doubt") for arg in graph.arguments)
    # Distinct count == set count: a frozenset cannot hold a duplicate, and
    # every move/objection/reply id embeds its move PDN so two probes never
    # collide. Confirm the expected total: 3 move + 2 objection + 1 reply = 6.
    assert len(graph.arguments) == 6


@pytest.mark.unit
def test_two_moves_with_same_objection_label_get_distinct_arguments() -> None:
    """Two moves carrying an identical objection label get distinct arg ids.

    ``obj:terminal_loss`` carries no magnitude, so two different moves can
    both have it. The argument id embeds the move PDN, so the two objection
    arguments are distinct — no shared/duplicated argument.
    """
    probes = [
        MoveProbe(pdn="13-17", objections=("obj:terminal_loss",)),
        MoveProbe(pdn="9-14", objections=("obj:terminal_loss",)),
    ]
    graph = build_root_argument_graph(probes)
    obj_args = {a for a in graph.arguments if a.startswith("obj:")}
    assert len(obj_args) == 2, obj_args
    assert obj_args == {
        "obj:13-17:obj:terminal_loss",
        "obj:9-14:obj:terminal_loss",
    }


@pytest.mark.unit
def test_empty_probes_yields_empty_graph() -> None:
    """An empty probe list (terminal position) yields an empty graph."""
    graph = build_root_argument_graph([])
    assert graph.arguments == frozenset()
    assert graph.defeats == frozenset()
    assert graph.survivors == frozenset()
    assert graph.move_arguments == {}


@pytest.mark.unit
def test_ranking_seam_left_empty_for_phase4() -> None:
    """Phase 3b leaves the graded-layer ``ranking`` seam empty (design §7)."""
    graph = build_root_argument_graph([MoveProbe(pdn="11-15")])
    assert graph.ranking == {}


# ---------------------------------------------------------------------------
# unit — the crisp graph over real probe_moves output on curated FENs
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_losing_move_eliminated_on_real_position() -> None:
    """On a real position the move that loses the game is crisply eliminated.

    ``B:W22,30:B9,13`` (Red) — ``13-17`` loses the game by force (Phase 3a
    ``obj:terminal_loss``); ``9-14`` is clean. The crisp layer must keep only
    ``9-14``.
    """
    board = CheckersBoard.from_fen("B:W22,30:B9,13")
    probes = list(probe_moves(board))
    graph = build_root_argument_graph(probes)
    assert graph.survivors == frozenset({"9-14"})
    assert graph.move_arguments["13-17"] not in graph.grounded_extension


@pytest.mark.unit
def test_clean_winning_shot_survives_on_real_position() -> None:
    """The single forced winning shot survives the crisp layer.

    ``B:W18,26:B15`` (Red) — the only move ``15x22x31`` wins the game and
    carries no objection: it must survive.
    """
    board = CheckersBoard.from_fen("B:W18,26:B15")
    probes = list(probe_moves(board))
    graph = build_root_argument_graph(probes)
    assert graph.survivors == frozenset({"15x22x31"})
    assert "15x22x31" in graph.survivors


@pytest.mark.unit
def test_all_losing_position_triggers_fallback_on_real_position() -> None:
    """A position where every move loses material triggers the §6 fallback.

    ``B:W23,30:B18,19,27`` (Red) — the only legal move ``19x26`` is a forced
    capture the resolver proves loses the exchange (``obj:loses_exchange:100``,
    with no defense). No ``move:`` argument is grounded, so the crisp layer
    cannot eliminate and the §6 empty-survivor fallback returns *all* moves.
    """
    board = CheckersBoard.from_fen("B:W23,30:B18,19,27")
    probes = list(probe_moves(board))
    graph = build_root_argument_graph(probes)
    grounded_moves = {
        pdn
        for pdn, arg_id in graph.move_arguments.items()
        if arg_id in graph.grounded_extension
    }
    assert grounded_moves == set()
    assert graph.survivors == frozenset(p.pdn for p in probes)
    assert len(graph.survivors) == len(probes)


@pytest.mark.unit
def test_no_heuristic_or_doubt_argument_on_real_positions() -> None:
    """No ``doubt:`` argument appears in the crisp graph for any curated FEN."""
    for fen in (
        "B:W18,26:B15",
        "B:W22,30:B9,13",
        "B:W10,17,18:B6,13,14",
        "B:W21:B27",
    ):
        board = CheckersBoard.from_fen(fen)
        graph = build_root_argument_graph(list(probe_moves(board)))
        assert not any(a.startswith("doubt") for a in graph.arguments), fen


@pytest.mark.unit
def test_graph_defeats_are_over_declared_arguments() -> None:
    """Every defeat pair is over arguments the graph declares (well-formed AF).

    ``ArgumentationFramework`` rejects a defeat over an undeclared argument, so
    a successful construction already implies this — the test makes the crisp
    AF's structural invariant explicit.
    """
    board = CheckersBoard.from_fen("B:W10,17,18:B6,13,14")
    graph: RootArgumentGraph = build_root_argument_graph(
        list(probe_moves(board))
    )
    for attacker, target in graph.defeats:
        assert attacker in graph.arguments
        assert target in graph.arguments
