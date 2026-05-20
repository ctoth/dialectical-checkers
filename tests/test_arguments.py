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
    """A FACT defense keyed to an objection restores its move.

    A probe carries both a FACT reply attack (``reply:material:100``) and a
    FACT defense keyed to it (``defense:holds_exchange@reply:material:100``).
    The defense argument defeats *that* reply argument; the reply is then not
    grounded, the ``move:`` argument has no undefeated attacker, and the move
    is back in the grounded extension.
    """
    probes = [
        MoveProbe(
            pdn="2x11",
            reasons=("pro:material:100",),
            reply_attacks=("reply:material:100",),
            defenses=("defense:holds_exchange@reply:material:100",),
        )
    ]
    graph = build_root_argument_graph(probes)
    move_id = graph.move_arguments["2x11"]
    assert move_id in graph.grounded_extension
    assert "2x11" in graph.survivors


@pytest.mark.unit
def test_keyed_defense_defeats_only_its_answered_attack() -> None:
    """A keyed defense defeats ONLY the objection / reply it answers (§6).

    Phase 3b analyst MAJOR-2 regression: a probe with two *independent* FACT
    attacks — ``reply:material:100`` and ``reply:material:200`` — and one
    defense keyed to the smaller (``defense:holds_exchange@reply:material:100``).
    The defense argument must defeat ONLY the ``reply:material:100`` argument;
    the ``reply:material:200`` attack is unanswered and still defeats the move,
    which therefore stays NON-grounded. The pre-fix construction wired the
    defense to *every* attacker and wrongly restored the move.

    A second, clean move is present so the §6 empty-survivor fallback does not
    fire — that way ``survivors`` reflects genuine grounding, not the
    every-move fallback.
    """
    probe = MoveProbe(
        pdn="7x14",
        reasons=("pro:material:100",),
        reply_attacks=("reply:material:100", "reply:material:200"),
        defenses=("defense:holds_exchange@reply:material:100",),
    )
    clean = MoveProbe(pdn="6-10", reasons=("pro:crown",))
    graph = build_root_argument_graph([probe, clean])
    move_id = graph.move_arguments["7x14"]
    defense_id = "defense:7x14:defense:holds_exchange@reply:material:100"
    answered_id = "reply:7x14:reply:material:100"
    unanswered_id = "reply:7x14:reply:material:200"
    # The defense defeats ONLY the reply it is keyed to.
    assert (defense_id, answered_id) in graph.defeats
    assert (defense_id, unanswered_id) not in graph.defeats
    # The answered reply is defeated; the unanswered reply still stands.
    assert answered_id not in graph.grounded_extension
    assert unanswered_id in graph.grounded_extension
    # ...so the move is NOT restored — it stays out of the grounded extension
    # and out of the survivor set (the clean move keeps the fallback dormant).
    assert move_id not in graph.grounded_extension
    assert "7x14" not in graph.survivors
    assert graph.survivors == frozenset({"6-10"})


@pytest.mark.unit
def test_keyed_defense_with_objection_and_reply_defeats_only_keyed_one() -> None:
    """A defense keyed to one of an objection + a reply restores nothing alone.

    The probe carries an independent FACT objection (``obj:allows_shot:100``)
    and a FACT reply (``reply:material:200``); the defense is keyed only to the
    reply. The objection is unanswered, so the move stays non-grounded — design
    §6's "and only that one" holds across the objection and reply channels.
    """
    probe = MoveProbe(
        pdn="9-14",
        objections=("obj:allows_shot:100",),
        reply_attacks=("reply:material:200",),
        defenses=("defense:holds_exchange@reply:material:200",),
    )
    clean = MoveProbe(pdn="6-10", reasons=("pro:crown",))
    graph = build_root_argument_graph([probe, clean])
    defense_id = "defense:9-14:defense:holds_exchange@reply:material:200"
    obj_id = "obj:9-14:obj:allows_shot:100"
    reply_id = "reply:9-14:reply:material:200"
    # The defense defeats the keyed reply only — never the objection.
    assert (defense_id, reply_id) in graph.defeats
    assert (defense_id, obj_id) not in graph.defeats
    # The unanswered objection still stands; the move is not restored.
    assert obj_id in graph.grounded_extension
    assert graph.move_arguments["9-14"] not in graph.grounded_extension
    assert "9-14" not in graph.survivors
    assert graph.survivors == frozenset({"6-10"})


@pytest.mark.unit
def test_keyed_defense_for_absent_attack_restores_nothing() -> None:
    """A defense keyed to an attack the probe never raised defeats nothing.

    The probe carries one undefeated FACT reply (``reply:material:100``) and a
    defense keyed to a *different*, absent label (``reply:material:999``). The
    defense argument exists but, having no matching attacker, defeats nothing —
    it cannot restore the move against the attack actually made.
    """
    probe = MoveProbe(
        pdn="13-17",
        reply_attacks=("reply:material:100",),
        defenses=("defense:holds_exchange@reply:material:999",),
    )
    clean = MoveProbe(pdn="6-10", reasons=("pro:crown",))
    graph = build_root_argument_graph([probe, clean])
    defense_id = "defense:13-17:defense:holds_exchange@reply:material:999"
    # The defense argument is declared but defeats nothing.
    assert defense_id in graph.arguments
    assert not any(src == defense_id for src, _ in graph.defeats)
    # The genuine reply is undefeated; the move stays non-grounded and out of
    # the survivor set (the clean move keeps the §6 fallback dormant).
    assert graph.move_arguments["13-17"] not in graph.grounded_extension
    assert "13-17" not in graph.survivors
    assert graph.survivors == frozenset({"6-10"})


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
def test_ranking_carries_the_graded_categoriser_layer() -> None:
    """Phase 5 fills the ``ranking`` field with the graded Categoriser layer.

    Phase 3b left ``ranking`` empty as a seam; Phase 5 (design §7) builds the
    graded layer into it. For a single clean probe — a move with no HEURISTIC
    objection — the graded AF has the one ``move:`` node, no defeats, and the
    move's Categoriser score is the unattacked-argument default of ``1.0``.
    """
    graph = build_root_argument_graph([MoveProbe(pdn="11-15")])
    assert graph.ranking != {}
    assert graph.ranking["move_scores"] == {"11-15": 1.0}
    assert graph.ranking["arguments"] == frozenset({"move:11-15"})
    assert graph.ranking["defeats"] == frozenset()
    assert graph.ranking["converged"] is True


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


# ---------------------------------------------------------------------------
# unit — the graded Categoriser layer (design §7, Phase 5)
# ---------------------------------------------------------------------------
#
# ``build_graded_layer`` builds a SECOND plain Dung AF over the crisp survivors
# — nodes = surviving ``move:`` + their HEURISTIC ``obj:`` nodes, edges
# heuristic ``obj -> move`` — and runs ``categoriser_scores`` on it. These
# tests drive it directly over hand-built probes so the graded semantics are
# tested in isolation.


@pytest.mark.unit
def test_graded_layer_clean_move_scores_one() -> None:
    """A surviving move with no HEURISTIC objection scores the Cat default 1.0.

    An unattacked argument's Categoriser score is 1.0 (Bonzon 2016 Def. 9). A
    clean move's ``move:`` node has no attacker in the graded AF, so its
    per-move Categoriser score is 1.0.
    """
    graph = build_root_argument_graph(
        [MoveProbe(pdn="11-15", reasons=("pro:opposition",))]
    )
    assert graph.ranking["move_scores"]["11-15"] == 1.0


@pytest.mark.unit
def test_graded_layer_heuristic_objection_lowers_score() -> None:
    """A HEURISTIC objection adds a graded-AF defeat and lowers the Cat score.

    A move carrying one HEURISTIC objection has an ``obj:`` node defeating its
    ``move:`` node in the graded AF; ``Cat(move) = 1/(1 + Cat(obj)) = 1/2``. A
    clean sibling stays at 1.0 — so the graded layer ranks the clean move above
    the objected one.
    """
    objected = MoveProbe(
        pdn="9-14",
        reasons=("pro:opposition",),
        objections=("obj:loses_opposition",),
    )
    clean = MoveProbe(pdn="10-15", reasons=("pro:opposition",))
    graph = build_root_argument_graph([objected, clean])
    assert graph.ranking["move_scores"]["9-14"] == pytest.approx(0.5)
    assert graph.ranking["move_scores"]["10-15"] == 1.0
    # The graded AF carries exactly the one heuristic obj -> move defeat.
    assert graph.ranking["defeats"] == frozenset(
        {("obj:9-14:obj:loses_opposition", "move:9-14")}
    )


@pytest.mark.unit
def test_graded_layer_more_objections_lower_score_monotonically() -> None:
    """More independent HEURISTIC objections lower the Cat score (Cardinality).

    ``Bonzon_2016`` proves the Categoriser satisfies Cardinality Precedence: N
    independent objections lower the score monotonically, with no copy-counting
    (design §7). Two heuristic objections score the move below one, one below
    none.
    """
    none = MoveProbe(pdn="10-15", reasons=("pro:opposition",))
    one = MoveProbe(
        pdn="9-14",
        reasons=("pro:opposition",),
        objections=("obj:loses_opposition",),
    )
    two = MoveProbe(
        pdn="11-16",
        reasons=("pro:opposition",),
        objections=("obj:loses_opposition", "obj:single_corner_drift"),
    )
    graph = build_root_argument_graph([none, one, two])
    scores = graph.ranking["move_scores"]
    assert scores["10-15"] > scores["9-14"] > scores["11-16"]


@pytest.mark.unit
def test_graded_layer_excludes_fact_objections() -> None:
    """Only HEURISTIC objections enter the graded AF — FACT ones do not.

    A FACT objection lives in the crisp layer (design §6); the graded layer
    (design §7) is built only from the HEURISTIC ``obj:`` nodes. A move
    carrying a FACT objection but no HEURISTIC one therefore has no graded-AF
    defeat — but note a move with an undefeated FACT objection is also
    crisply eliminated, so the case is tested in the empty-survivor fallback
    below. Here the move's FACT objection is defeated by a keyed FACT defense
    so the move survives, and the graded AF still carries no defeat for it.
    """
    probe = MoveProbe(
        pdn="2x11",
        reasons=("pro:material:100",),
        reply_attacks=("reply:material:100",),
        defenses=("defense:holds_exchange@reply:material:100",),
    )
    graph = build_root_argument_graph([probe])
    # The move survived the crisp layer.
    assert "2x11" in graph.survivors
    # ...and the graded AF carries no defeat — the FACT reply did not enter it.
    assert graph.ranking["defeats"] == frozenset()
    assert graph.ranking["move_scores"]["2x11"] == 1.0


@pytest.mark.unit
def test_graded_layer_only_ranks_crisp_survivors() -> None:
    """The graded AF's ``move:`` nodes are exactly the crisp survivors.

    A move crisply eliminated by an undefeated FACT objection is NOT a node in
    the graded AF — the graded layer can never resurrect it (design §7). Here
    one move is clean (survives) and one carries an undefeated FACT objection
    (eliminated): only the survivor appears in the graded layer.
    """
    survivor = MoveProbe(pdn="11-15", reasons=("pro:material:100",))
    eliminated = MoveProbe(
        pdn="9-14", objections=("obj:allows_shot:200",)
    )
    graph = build_root_argument_graph([survivor, eliminated])
    # The crisp layer eliminated 9-14 and kept 11-15.
    assert graph.survivors == frozenset({"11-15"})
    # The graded AF has only the survivor's move: node — 9-14 is absent.
    assert graph.ranking["arguments"] == frozenset({"move:11-15"})
    assert set(graph.ranking["move_scores"]) == {"11-15"}


@pytest.mark.unit
def test_graded_layer_empty_for_terminal_position() -> None:
    """An empty probe list yields an empty graded layer (no nodes, no scores)."""
    graph = build_root_argument_graph([])
    assert graph.ranking["arguments"] == frozenset()
    assert graph.ranking["move_scores"] == {}
