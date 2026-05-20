"""Phase 5 — FACT-preservation property tests (design §6-7, the critical gate).

The Phase-5 graded Categoriser layer (design ``notes/checkers-design.md`` §7)
ranks among the crisp survivors. It must NEVER:

* resurrect a move the crisp layer (design §6) eliminated, or
* change the engine's choice on a position the FACT terms 1-2 of the selector
  key already decide.

Equivalently: the Phase-3b FACT-tier guarantees must STILL hold (a legal move
is always played; no avoidable forced loss; a free winning shot is always
taken — those are pinned in ``test_engine.py`` and re-run unchanged). This file
adds the two graded-specific property tests over >=200 seeded positions.

The seeded-position sampler is the same deterministic walk used by
``test_engine.py`` — re-implemented here so the two property files are
independent.
"""

from __future__ import annotations

import random

import pytest

from dialectical_checkers import DialecticalCheckersEngine
from dialectical_checkers.arguments import build_root_argument_graph
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.selection import (
    _fact_pro_priority,
    _selection_key,
    _worst_fact_objection_magnitude,
    choose_move,
)
from dialectical_checkers.witnesses import probe_moves


# ---------------------------------------------------------------------------
# seeded-position sampler (deterministic) — same walk shape as test_engine.py
# ---------------------------------------------------------------------------


def _reachable_boards(seed: int, max_plies: int) -> list[CheckersBoard]:
    """A deterministic random walk from the start; every visited board."""
    rng = random.Random(seed)
    board = CheckersBoard.initial()
    visited = [board]
    for _ in range(max_plies):
        moves = board.legal_moves()
        if not moves:
            break
        board = board.apply(rng.choice(moves))
        visited.append(board)
        if board.is_draw():
            break
    return visited


def _seeded_positions(target: int) -> list[CheckersBoard]:
    """At least ``target`` distinct non-terminal positions, deterministically."""
    seen: set[str] = set()
    out: list[CheckersBoard] = []
    seed = 0
    while len(out) < target:
        for depth in (8, 16, 24, 32, 44):
            for board in _reachable_boards(seed, depth):
                if not board.legal_moves():
                    continue
                fen = board.to_fen()
                if fen in seen:
                    continue
                seen.add(fen)
                out.append(board)
        seed += 1
        if seed > 5_000:  # safety — should never be hit
            break
    return out


def _fact_key(probe, graph) -> tuple[int, int, int, int, int]:  # noqa: ANN001
    """The FACT-only selector key (terms 1-2) for ``probe`` against ``graph``.

    The first five components of the full ``_selection_key`` — the worst
    unavoidable FACT-objection magnitude, then the negated FACT pro-value
    priority tuple. Two moves with an equal FACT key are *not distinguished by
    the FACT terms*; any difference in the engine's choice between them is a
    purely graded decision.
    """
    magnitude = _worst_fact_objection_magnitude(probe, graph)
    winning, large, crown, small = _fact_pro_priority(probe)
    return (magnitude, -winning, -large, -crown, -small)


# ---------------------------------------------------------------------------
# property — the graded layer never resurrects a crisply-eliminated move
# ---------------------------------------------------------------------------


@pytest.mark.property
def test_graded_layer_never_resurrects_an_eliminated_move() -> None:
    """For >=200 seeded positions the engine's move is always a crisp survivor.

    The graded layer ranks only ``graph.survivors`` (design §7). Across the
    seeded sample the engine's chosen move must therefore always be in
    ``graph.survivors`` — the graded layer can never resurrect a move the crisp
    Dung layer eliminated. The sample is also required to actually contain
    positions where the crisp layer eliminated at least one move, else the
    check is vacuous.
    """
    engine = DialecticalCheckersEngine()
    positions = _seeded_positions(200)
    assert len(positions) >= 200
    positions_with_elimination = 0
    for board in positions:
        probes = list(probe_moves(board))
        graph = build_root_argument_graph(probes)
        if len(graph.survivors) < len(probes):
            positions_with_elimination += 1
        chosen = engine.choose_move(board).move_pdn
        assert chosen in graph.survivors, (
            board.to_fen(),
            chosen,
            "engine played a move the crisp layer eliminated",
            sorted(graph.survivors),
        )
    # The crisp layer must genuinely eliminate moves somewhere in the sample,
    # else "never resurrects" is trivially satisfied.
    assert positions_with_elimination >= 1, positions_with_elimination


# ---------------------------------------------------------------------------
# property — the graded layer never overrides a FACT-decided position
# ---------------------------------------------------------------------------


@pytest.mark.property
def test_graded_layer_never_overrides_a_fact_decision() -> None:
    """For >=200 seeded positions the FACT terms still decide every FACT case.

    When the FACT terms 1-2 of the selector key already pick a unique move —
    i.e. exactly one crisp survivor has the strictly best FACT key — the
    engine's chosen move MUST be that move. The graded terms 3-4 come after the
    FACT terms in the lexicographic key, so a FACT decision is never overridden
    by a graded one (design §7 fact-as-highest-value).

    The sample must actually contain FACT-decided positions, else the check is
    vacuous.
    """
    engine = DialecticalCheckersEngine()
    positions = _seeded_positions(200)
    assert len(positions) >= 200
    fact_decided = 0
    for board in positions:
        probes = list(probe_moves(board))
        graph = build_root_argument_graph(probes)
        survivors = [p for p in probes if p.pdn in graph.survivors]
        if not survivors:
            continue
        fact_keys = {p.pdn: _fact_key(p, graph) for p in survivors}
        best_fact = min(fact_keys.values())
        winners = [pdn for pdn, k in fact_keys.items() if k == best_fact]
        if len(winners) != 1:
            # The FACT terms tie among >=2 survivors — the graded terms are
            # *meant* to break this; it is not a FACT-decided position.
            continue
        fact_decided += 1
        chosen = engine.choose_move(board).move_pdn
        assert chosen == winners[0], (
            board.to_fen(),
            chosen,
            "graded layer overrode a FACT decision; FACT winner was",
            winners[0],
        )
    assert fact_decided >= 1, fact_decided


# ---------------------------------------------------------------------------
# property — the graded layer only ever re-ranks within a FACT-key tier
# ---------------------------------------------------------------------------


@pytest.mark.property
def test_graded_choice_shares_the_best_fact_key() -> None:
    """For >=200 seeded positions the chosen move has the best FACT key.

    The strongest single statement of fact-preservation: whatever the graded
    layer does, the engine's chosen move always has the *minimum* FACT key
    (terms 1-2) among the crisp survivors. The graded terms 3-4 only ever
    re-rank moves *within* the best FACT-key tier — they can change which move
    in that tier is chosen, never promote a move out of a worse tier. This is
    the lexicographic-ordering guarantee, checked end to end against the
    engine.
    """
    engine = DialecticalCheckersEngine()
    positions = _seeded_positions(200)
    assert len(positions) >= 200
    for board in positions:
        probes = list(probe_moves(board))
        graph = build_root_argument_graph(probes)
        survivors = [p for p in probes if p.pdn in graph.survivors]
        if not survivors:
            continue
        best_fact = min(_fact_key(p, graph) for p in survivors)
        chosen_pdn = engine.choose_move(board).move_pdn
        chosen = next(p for p in probes if p.pdn == chosen_pdn)
        assert _fact_key(chosen, graph) == best_fact, (
            board.to_fen(),
            chosen_pdn,
            "chosen move is not in the best FACT-key tier",
        )


# ---------------------------------------------------------------------------
# property — the graded layer never changes a unanimous-FACT engine choice
# ---------------------------------------------------------------------------


@pytest.mark.property
def test_full_key_equals_grounded_key_when_fact_terms_decide() -> None:
    """When the FACT terms decide, ``argument`` and ``grounded`` modes agree.

    ``grounded`` mode ranks by the FACT terms 1-2 alone; ``argument`` mode adds
    the graded terms 3-4. On a position whose FACT terms pick a unique move the
    two modes MUST agree — the graded terms cannot move the choice. (On a
    FACT-tied position they are allowed to differ; that is the graded layer
    doing its job.) Across >=200 seeded positions every FACT-decided case
    agrees.
    """
    positions = _seeded_positions(200)
    assert len(positions) >= 200
    checked = 0
    for board in positions:
        probes = list(probe_moves(board))
        graph = build_root_argument_graph(probes)
        survivors = [p for p in probes if p.pdn in graph.survivors]
        if not survivors:
            continue
        fact_keys = {p.pdn: _fact_key(p, graph) for p in survivors}
        best_fact = min(fact_keys.values())
        if sum(1 for k in fact_keys.values() if k == best_fact) != 1:
            continue  # FACT-tied — the modes may legitimately differ.
        checked += 1
        argument_move = choose_move(
            probes, graph, selector_mode="argument", board=board
        ).pdn
        grounded_move = choose_move(
            probes, graph, selector_mode="grounded", board=board
        ).pdn
        assert argument_move == grounded_move, (
            board.to_fen(),
            argument_move,
            grounded_move,
            "graded terms changed a FACT-decided choice",
        )
    assert checked >= 1, checked
