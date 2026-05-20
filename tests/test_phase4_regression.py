"""Phase 4 — regression: the engine's PLAY is unchanged by the HEURISTIC layer.

Phase 4 is ADDITIVE (design ``notes/checkers-design.md`` §5, port-plan §8):
``witnesses.py`` now emits the HEURISTIC-tier §5 witnesses alongside the
FACT-tier ones, but

* the crisp Dung argument layer (``arguments.build_root_argument_graph``)
  admits **only FACT-tier** witnesses — it filters every objection / reply /
  defense through ``evidence.to_argument_evidence``'s tier;
* the FACT-tier selector (``selection.py``) reads only FACT-tier witnesses —
  the graded Categoriser term over HEURISTIC witnesses is a later phase.

So the engine's chosen move must be **identical** to its pre-Phase-4 choice on
every position. This file pins that:

* ``REGRESSION_BASELINE`` — 120 deterministic-seeded positions (a seeded
  pseudo-random walk from the start position, ``SEED=20260520``) paired with
  the move ``DialecticalCheckersEngine.choose_move`` selected on each. The
  baseline was captured by ``scripts/phase4_gen_regression_baseline.py`` run
  against the **pre-Phase-4** committed source (the Phase-4 witness changes
  ``git stash``-ed away); the same script run against the Phase-4 source
  produced an identical list. The test below replays it and asserts the engine
  still chooses each baseline move.
* the crisp-layer tests assert ``build_root_argument_graph`` admits no
  HEURISTIC-derived argument, across the same 120 positions — the structural
  reason the play cannot change.

If a future change moves a HEURISTIC witness into the engine's decision path,
these tests fail — exactly the guard Phase 4 needs.
"""

from __future__ import annotations

import pytest

from dialectical_checkers import DialecticalCheckersEngine
from dialectical_checkers.arguments import build_root_argument_graph
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.evidence import to_argument_evidence
from dialectical_checkers.scheme import Tier
from dialectical_checkers.witnesses import probe_moves

# 120 seeded positions (SEED=20260520) — see the module docstring. Each pair is
# (PDN-FEN, the move the pre-Phase-4 engine chose). Regenerate with
# ``scripts/phase4_gen_regression_baseline.py``.
REGRESSION_BASELINE: list[tuple[str, str]] = [
    ("B:W10,28,29,32:B2,4,8,16,20,23,K30", "16-19"),
    ("B:W13,14,20,22,25,28,29,30:B3,4,11,16,21", "16-19"),
    ("B:W13,21,23,28,29,32:B2,4,5,8,10,16,20,26", "26-30"),
    ("B:W13,21,27,28,29,32:B2,4,5,8,10,12,20,26", "26-30"),
    ("B:W14,17,20,22,25,28,29,30:B3,4,11,12,21", "11-15"),
    ("B:W14,17,20,25,26,28,29,30:B3,4,7,12,21", "3-8"),
    ("B:W14,17,21,27,28,29,32:B2,3,4,5,6,8,12,20,26", "26-30"),
    ("B:W14,19,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,7,8,9,10,12,16,21", "10x17"),
    ("B:W14,19,25,26,27,28,29,30,31,32:B1,2,3,4,5,7,8,10,12,16,21", "10x17"),
    ("B:W14,20,22,25,26,28,29,30:B3,4,7,8,21", "7-10"),
    ("B:W14,21,22,27,28,29,32:B2,3,4,5,6,8,12,16,26", "26-30"),
    ("B:W14,K19:BK26,27,K32", "27-31"),
    ("B:W15,18,21,23,26,27,28,29,32:B2,3,4,5,6,8,10,12,16", "10x19"),
    ("B:W15,20,22,23,25,26,28,29,30,32:B3,4,7,8,11,14,21", "11x18x27"),
    ("B:W17,19,20,21,22,23,25,26,29,32:B2,3,6,8,10,11,12,13,14,16", "14-18"),
    ("B:W17,19,20,21,22,23,25,28,29,31,32:B2,3,6,8,9,10,11,12,14,15,16", "15x24"),
    ("B:W17,19,20,21,22,23,25,29,31,32:B2,3,6,8,9,10,11,12,14,16", "2-7"),
    ("B:W17,19,21,22,23,24,25,28,29,31,32:B1,2,3,8,9,10,11,12,14,15,16", "1-5"),
    ("B:W17,19,21,23,24,25,26,28,29,31,32:B1,2,3,7,8,9,10,12,14,15,16", "1-5"),
    ("B:W17,19,21,23,25,26,27,28,29,31,32:B1,2,3,7,8,9,10,11,12,14,16", "1-5"),
    ("B:W17,20,22,23,24,25,28,29,30,31,32:B2,3,4,5,6,7,8,10,11,12,14,21", "11-15"),
    ("B:W17,20,22,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,7,8,9,10,11,12,14", "14x21"),
    ("B:W17,20,23,24,25,26,28,29,30,31,32:B2,3,4,5,6,7,8,9,10,11,12,21", "10-15"),
    ("B:W17,20,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,7,8,9,10,11,12,21", "1-6"),
    ("B:W17,22,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,11,12,14", "14x21"),
    ("B:W17,28,29,32:B2,4,8,10,16,20,23,K30", "10-15"),
    ("B:W17,K19:B27,K30,K32", "27-31"),
    ("B:W18,19,21,23,26,27,28,29,32:B2,3,4,5,6,7,8,12,16", "16-20"),
    ("B:W18,19,21,23,27,28,29,31,32:B1,2,3,4,5,7,8,12,16", "1-6"),
    ("B:W18,19,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,12,16,21", "16-20"),
    ("B:W18,19,23,27,28,29,30,31,32:B1,2,3,4,5,7,8,12,16,21", "1-6"),
    ("B:W18,21,22,23,27,28,29,32:B2,3,4,5,6,8,12,16,19", "19x26"),
    ("B:W18,21,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,12,16", "10-14"),
    ("B:W18,21,28,29,32:B2,4,8,10,14,16,20,K30", "14x23"),
    ("B:W18,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,11,12,21", "11-15"),
    ("B:W19,21,22,23,25,26,27,28,29,31,32:B1,2,3,6,7,8,10,11,12,14,16", "1-5"),
    ("B:W19,23,25,27,28,29,30,31,32:B1,2,3,4,5,7,8,12,16,17,21", "1-6"),
    ("B:W20,21,22,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,10,11,12,14", "10-15"),
    ("B:W20,22,23,25,26,28,29,30:B3,4,7,8,14,21", "7-10"),
    ("B:W21,22,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,11,12", "10-14"),
    ("B:W21,22,23,24,25,26,27,28,29,31,32:B1,2,3,4,6,7,10,11,12,14,16", "1-5"),
    ("B:W21,22,23,24,25,27,28,29,30,31,32:B1,2,3,4,6,7,8,10,12,14,16", "1-5"),
    ("B:W6,14,18,20,25,28,29,30:B8,11,12,16,21", "16-19"),
    ("B:W7,17,21,27,28,29,32:B2,3,4,5,8,12,20,26", "2x11"),
    ("B:W9,14,18,20,25,28,29,30:B4,11,12,16,21", "16-19"),
    ("B:W9,14,20,22,25,28,29,30:B4,8,11,16,21", "16-19"),
    ("B:W9,21,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,10,12,16", "5x14"),
    ("B:W9,21,23,28,29,32:B2,4,5,8,10,16,20,K30", "5x14"),
    ("B:WK1,10,20,21,22,23,25,26,29,32:B3,7,8,11,12,13,16", "7x14"),
    ("B:WK1,17,20,21,22,23,25,26,29,32:B2,3,8,11,12,13,14,16", "2-7"),
    ("B:WK1,20,22,23,24,25,28,29,30,31,32:B2,3,4,5,7,8,11,12,15,21", "11-16"),
    ("B:WK12,17:B18,K30,K32", "18-22"),
    ("B:WK12,21:B14,K30,K32", "14-18"),
    ("B:WK16,17:B23,K30,K32", "23-26"),
    ("B:WK16,20,22,23,24,25,26,28,29,30,32:B3,4,7,8,11,12,14,21", "12x19"),
    ("B:WK19,20,22,23,24,25,26,28,29,30,32:B3,4,7,8,9,11,12,21", "11-15"),
    ("B:WK19,20,22,23,24,25,28,29,30,31,32:B3,4,5,7,8,11,12,21", "11-15"),
    ("B:WK3,10,25:B4,7,K30,K32", "30x21"),
    ("B:WK3,10,27,29:B4,7,23,K30", "23x32"),
    ("B:WK3,10,29,32:B2,4,23,K30", "2-7"),
    ("B:WK3,21:B4,14,K30,K32", "14-18"),
    ("B:WK4,21,K22,29:B13,14,27", "27-31"),
    ("B:WK4,21,K25,29:B10,13,19", "10-14"),
    ("B:WK4,21,K25,29:B10,13,27", "27-31"),
    ("B:WK4,6,14,15,18,29,30:B21", "21-25"),
    ("B:WK4,6,14,18,24,29,30:B16,21", "16-20"),
    ("B:WK4,6,14,18,25,28,29,30:B12,15,21", "15x22"),
    ("B:WK4,6,14,18,28,29,30:B12,21", "12-16"),
    ("B:WK4,K13,21,29:B14,27", "27-31"),
    ("B:WK4,K17,21,29:B18,27", "27-31"),
    ("B:WK4,K5,16,21,25,29:B10,12,13,14,K17", "12x19"),
    ("B:WK4,K5,19,21,22,25,29:B10,12,13,14,K26", "26x17"),
    ("B:WK4,K5,21,22,23,25,29:B10,12,13,14,K30", "10-15"),
    ("B:WK4,K5,21,22,29:B10,13,14,K17,19", "17x26"),
    ("B:WK4,K9,21,29:B10,13,14,19,K26", "14-18"),
    ("B:WK5,19,20,21,22,25,26,29,32:B7,8,11,12,13,14,16", "16x23x30"),
    ("B:WK5,20,21,22,23,25,26,29,32:B3,8,11,12,13,14,16", "3-7"),
    ("B:WK5,20,21,22,23,25,29:B8,10,11,12,13,14,K30", "10-15"),
    ("B:WK5,20,21,22,25,27,29:B7,8,11,12,13,14,K30", "11-15"),
    ("B:WK8,21,K25,29:B10,13,24", "10-14"),
    ("B:WK8,K17,21,29:B23,27", "27-31"),
    ("W:W10,28,29,32:B2,4,8,16,23,24,K30", "28x19x12x3"),
    ("W:W13,14,20,22,25,28,29,30:B4,8,11,16,21", "13-9"),
    ("W:W13,21,23,28,29,32:B2,4,5,8,10,16,20,K30", "21-17"),
    ("W:W13,21,27,28,29,32:B2,4,5,8,10,16,20,26", "21-17"),
    ("W:W14,17,20,22,25,28,29,30:B3,4,11,16,21", "14-10"),
    ("W:W14,17,20,25,26,28,29,30:B3,4,11,12,21", "14-10"),
    ("W:W14,17,21,27,28,29,32:B2,3,4,5,8,10,12,20,26", "14x7"),
    ("W:W14,20,22,25,26,28,29,30:B3,4,7,12,21", "14-9"),
    ("W:W14,21,22,27,28,29,32:B2,3,4,5,6,8,12,20,26", "21-17"),
    ("W:W14,K19:BK26,K31,K32", "14-10"),
    ("W:W17,19,20,21,22,23,25,26,29,32:B2,3,6,8,11,12,13,14,15,16", "19x10x1"),
    ("W:W17,19,20,21,22,23,25,29,31,32:B2,3,6,8,10,11,12,13,14,16", "19-15"),
    ("W:W17,19,21,22,23,24,25,28,29,31,32:B2,3,6,8,9,10,11,12,14,15,16", "17-13"),
    ("W:W17,19,21,23,24,25,26,28,29,31,32:B1,2,3,8,9,10,11,12,14,15,16", "17-13"),
    ("W:W17,19,21,23,25,26,27,28,29,31,32:B1,2,3,7,8,9,10,12,14,15,16", "17-13"),
    ("W:W17,20,21,22,23,25,28,29,31,32:B2,3,6,8,9,10,11,12,14,16,24", "28x19"),
    ("W:W17,20,22,23,24,25,28,29,30,31,32:B2,3,4,5,6,7,8,11,12,14,15,21", "17x10x1"),
    ("W:W17,20,23,24,25,26,28,29,30,31,32:B2,3,4,5,6,7,8,10,11,12,14,21", "17-13"),
    ("W:W17,20,23,25,26,27,28,29,30,31,32:B2,3,4,5,6,7,8,9,10,11,12,21", "17-13"),
    ("W:W17,21,27,28,29,32:B2,4,5,8,10,12,20,26", "17-13"),
    ("W:W17,28,29,32:B2,4,8,14,16,20,23,K30", "17x10"),
    ("W:W17,K19:BK26,27,K32", "17-13"),
    ("W:W18,19,21,23,26,27,28,29,32:B2,3,4,5,6,8,10,12,16", "18-14"),
    ("W:W18,19,21,23,27,28,29,31,32:B2,3,4,5,6,7,8,12,16", "18-14"),
    ("W:W18,19,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,7,8,9,10,12,16,21", "18-15"),
    ("W:W18,19,23,27,28,29,30,31,32:B1,2,3,4,5,7,8,12,16,25", "29x22"),
    ("W:W18,21,22,27,28,29,32:B2,3,4,5,6,8,12,16,26", "18-14"),
    ("W:W18,21,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,10,12,14,16", "18x9"),
    ("W:W18,21,23,26,27,28,29,32:B2,3,4,5,6,8,12,16,19", "18-14"),
    ("W:W18,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,12,16,21", "18-14"),
    ("W:W19,21,22,23,25,26,27,28,29,31,32:B1,2,3,7,8,9,10,11,12,14,16", "22-17"),
    ("W:W19,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,7,8,10,12,16,18,21", "23x14"),
    ("W:W19,23,25,27,28,29,30,31,32:B1,2,3,4,5,7,8,12,16,21,22", "25x18"),
    ("W:W19,25,26,27,28,29,30,31,32:B1,2,3,4,5,7,8,12,16,17,21", "19-15"),
    ("W:W20,21,22,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,7,8,9,10,11,12,14", "22-17"),
    ("W:W20,22,23,24,25,26,28,29,30,32:B3,4,7,8,11,14,19,21", "23x16"),
    ("W:W20,22,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,7,8,9,10,11,12,21", "22-17"),
    ("W:W20,22,23,25,26,28,29,30:B3,4,7,8,18,21", "22x15"),
    ("W:W20,22,25,26,28,29,30,32:B3,4,7,8,14,21,27", "32x23"),
]


def test_regression_baseline_has_at_least_100_positions() -> None:
    """The directive requires the regression sample to be >= 100 positions."""
    assert len(REGRESSION_BASELINE) >= 100


@pytest.mark.differential
@pytest.mark.parametrize(
    "fen,expected_pdn", REGRESSION_BASELINE, ids=lambda v: str(v)
)
def test_engine_play_unchanged_by_heuristic_layer(
    fen: str, expected_pdn: str
) -> None:
    """The engine still chooses the pre-Phase-4 move on every seeded position.

    Phase 4 only *adds* HEURISTIC witnesses; the crisp layer and the FACT-tier
    selector ignore them, so ``choose_move`` must return the exact same move it
    returned before this phase — the move frozen in ``REGRESSION_BASELINE``.
    """
    engine = DialecticalCheckersEngine()
    board = CheckersBoard.from_fen(fen)
    decision = engine.choose_move(board)
    assert decision.move_pdn == expected_pdn, (fen, decision.move_pdn)


@pytest.mark.differential
@pytest.mark.parametrize(
    "fen", [row[0] for row in REGRESSION_BASELINE], ids=lambda v: str(v)
)
def test_crisp_layer_admits_only_fact_witnesses(fen: str) -> None:
    """The crisp Dung argument graph contains no HEURISTIC-derived argument.

    ``build_root_argument_graph`` builds an ``obj:`` / ``reply:`` / ``defense:``
    argument only for a FACT-tier witness (it filters by
    ``evidence.to_argument_evidence`` tier). This walks every non-``move:``
    argument id of the graph across the regression sample and confirms the
    witness label embedded in it parses to ``Tier.FACT`` — no HEURISTIC witness
    has leaked into the crisp layer. This is the *structural* reason the engine
    play (above) cannot change.
    """
    board = CheckersBoard.from_fen(fen)
    probes = list(probe_moves(board))
    graph = build_root_argument_graph(probes)
    move_ids = set(graph.move_arguments.values())
    for arg_id in graph.arguments:
        if arg_id in move_ids:
            continue
        # A non-move argument id is ``<family>:<pdn>:<witness-label>`` — the
        # witness label is everything after the first two ``:``-segments.
        family, _, rest = arg_id.partition(":")
        assert family in ("obj", "reply", "defense"), arg_id
        _pdn, _, witness_label = rest.partition(":")
        assert witness_label, arg_id
        assert to_argument_evidence(witness_label).tier is Tier.FACT, (
            fen,
            arg_id,
            witness_label,
        )
