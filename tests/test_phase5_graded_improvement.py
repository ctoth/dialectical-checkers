"""Phase 5 — graded-improvement curated positions (design §7 test directive).

Phase 5 wires the graded Categoriser layer into the engine. The directive asks
for curated QUIET positions — no FACT witness in play, so the Phase-3b FACT
selector could only tiebreak by static evaluation / PDN — where one survivor is
heuristically CLEARLY better, and to show that:

* the Phase-5 engine (``argument`` mode, the full §7 key) picks the
  heuristically better move; and
* the pre-Phase-5 engine (the FACT terms 1-2 only, then the static-eval / PDN
  tiebreak — exactly the Phase-3b ``_selection_key`` with no graded terms)
  did NOT — it tiebroke to a different move.

``_fact_only_choice`` below reconstructs the pre-Phase-5 selector exactly, so
each curated case demonstrates a genuine Phase-5 improvement, not an asserted
one. Every curated FEN was located by ``scripts/phase5_find_graded_improvement``
which confirmed the position is quiet (every move's FACT key is the clean
``(0,0,0,0,0)``) and the Phase-5 move is heuristically better — strictly more
accepted HEURISTIC pro-reasons, or a strictly higher Categoriser score (fewer /
weaker HEURISTIC objections), and never worse on the other metric.

Two flavours are curated:

* ``CAT_IMPROVEMENT`` — the pre-Phase-5 move carries a HEURISTIC objection
  (``obj:exposes_man``) that drops its Categoriser score to 0.5; the Phase-5
  move is clean (Categoriser 1.0). The graded layer steers the engine off a
  heuristically dubious move onto a sound one.
* ``PRO_IMPROVEMENT`` — both moves are clean (Categoriser 1.0), but the
  Phase-5 move carries strictly more accepted HEURISTIC pro-reasons; the
  graded term 4 (the heuristic-pro support proxy) picks it.
"""

from __future__ import annotations

import pytest

from dialectical_checkers import DialecticalCheckersEngine
from dialectical_checkers.arguments import build_root_argument_graph
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.selection import (
    _accepted_heuristic_pro_count,
    _categoriser_score,
    _fact_pro_priority,
    _worst_fact_objection_magnitude,
)
from dialectical_checkers.search import static_evaluation
from dialectical_checkers.witnesses import probe_moves

# Quiet positions where the pre-Phase-5 move carries ``obj:exposes_man``
# (Categoriser 0.5) and the Phase-5 move is clean (Categoriser 1.0). Each row
# is (FEN, the Phase-5 move, the pre-Phase-5 FACT-only move).
CAT_IMPROVEMENT: list[tuple[str, str, str]] = [
    ("B:W18,21,22,24,25,26,29,30,31,32:B1,2,3,4,5,6,7,8,9,11,28", "6-10", "11-15"),
    ("W:W18,21,22,24,25,26,29,30,31,32:B1,2,3,4,5,6,7,8,9,16,28", "21-17", "18-14"),
    ("W:W18,21,22,25,29,30,31,32:B1,2,3,4,5,6,7,9,19,28", "30-26", "18-14"),
    (
        "B:W17,20,22,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,9,10,11,12,16",
        "9-14",
        "10-14",
    ),
]

# Quiet positions where both moves are clean (Categoriser 1.0) but the Phase-5
# move carries strictly more accepted HEURISTIC pro-reasons. Each row is
# (FEN, the Phase-5 move, the pre-Phase-5 FACT-only move).
PRO_IMPROVEMENT: list[tuple[str, str, str]] = [
    (
        "W:W21,22,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,11,16",
        "22-18",
        "21-17",
    ),
    (
        "B:W18,21,22,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,11,16",
        "10-15",
        "10-14",
    ),
    (
        "W:W17,20,22,23,25,26,27,28,29,30,31,32:B1,2,3,5,6,7,8,9,10,11,12,16",
        "22-18",
        "17-13",
    ),
    ("B:W13,21,24,25,26,27,28,29,30,32:B1,2,3,4,5,7,8,12,20", "7-11", "1-6"),
]


def _fact_key(probe, graph) -> tuple[int, int, int, int, int]:  # noqa: ANN001
    """The FACT-only selector key (terms 1-2) for ``probe`` against ``graph``."""
    magnitude = _worst_fact_objection_magnitude(probe, graph)
    winning, large, crown, small = _fact_pro_priority(probe)
    return (magnitude, -winning, -large, -crown, -small)


def _fact_only_choice(board: CheckersBoard) -> str:
    """The move the PRE-Phase-5 engine would pick — the FACT terms only.

    Reconstructs the Phase-3b ``_selection_key`` exactly: the FACT terms 1-2,
    then the static-eval / PDN tiebreak, with NO graded terms 3-4. Restricted
    to the crisp survivors, as Phase 3b's ``choose_move`` was.
    """
    probes = list(probe_moves(board))
    graph = build_root_argument_graph(probes)
    survivors = [p for p in probes if p.pdn in graph.survivors] or probes

    def key(probe) -> tuple[int, int, int, int, int, int, str]:  # noqa: ANN001
        move = next(m for m in board.legal_moves() if m.pdn() == probe.pdn)
        return (
            *_fact_key(probe, graph),
            static_evaluation(board.apply(move)),
            probe.pdn,
        )

    return min(survivors, key=key).pdn


def _is_quiet(board: CheckersBoard) -> bool:
    """True iff no move on ``board`` carries a FACT witness — a quiet position.

    Every legal move's FACT key is the clean ``(0, 0, 0, 0, 0)``: no FACT
    objection, no FACT pro. The Phase-3b FACT selector could only tiebreak such
    a position by static eval / PDN — so any difference the Phase-5 engine makes
    here is purely the graded layer.
    """
    probes = list(probe_moves(board))
    graph = build_root_argument_graph(probes)
    return all(_fact_key(p, graph) == (0, 0, 0, 0, 0) for p in probes)


@pytest.mark.differential
@pytest.mark.parametrize(
    ("fen", "phase5_move", "fact_only_move"),
    CAT_IMPROVEMENT,
    ids=lambda v: str(v),
)
def test_graded_layer_steers_off_a_heuristically_objected_move(
    fen: str, phase5_move: str, fact_only_move: str
) -> None:
    """Phase 5 picks the clean move; the FACT-only selector picked the objected.

    A quiet position where the pre-Phase-5 FACT-only selector tiebreaks to a
    move carrying a HEURISTIC objection (Categoriser score 0.5), while a clean
    survivor (Categoriser 1.0) exists. The Phase-5 ``argument`` mode picks the
    clean move — the graded Categoriser term steered the engine off the
    heuristically dubious move. The pre-Phase-5 engine demonstrably did not.
    """
    board = CheckersBoard.from_fen(fen)
    assert _is_quiet(board), (fen, "curated position is not quiet")
    probes = {p.pdn: p for p in probe_moves(board)}
    graph = build_root_argument_graph(list(probes.values()))

    # The Phase-5 move is heuristically clean; the FACT-only move is objected.
    assert _categoriser_score(probes[phase5_move], graph) == 1.0
    assert _categoriser_score(probes[fact_only_move], graph) == pytest.approx(0.5)

    # The pre-Phase-5 engine picked the objected move...
    assert _fact_only_choice(board) == fact_only_move, fen
    # ...and the Phase-5 engine picks the clean one.
    chosen = DialecticalCheckersEngine().choose_move(board).move_pdn
    assert chosen == phase5_move, (fen, chosen, phase5_move)


@pytest.mark.differential
@pytest.mark.parametrize(
    ("fen", "phase5_move", "fact_only_move"),
    PRO_IMPROVEMENT,
    ids=lambda v: str(v),
)
def test_graded_layer_picks_the_better_supported_move(
    fen: str, phase5_move: str, fact_only_move: str
) -> None:
    """Phase 5 picks the move with more accepted HEURISTIC pro-reasons.

    A quiet position where both candidate moves are heuristically clean
    (Categoriser 1.0 — no HEURISTIC objection), but the Phase-5 move carries
    strictly more accepted HEURISTIC pro-reasons. The graded term 4 (the
    heuristic-pro support proxy) ranks the better-supported move first; the
    pre-Phase-5 FACT-only selector, blind to heuristic pros, tiebroke to the
    other move.
    """
    board = CheckersBoard.from_fen(fen)
    assert _is_quiet(board), (fen, "curated position is not quiet")
    probes = {p.pdn: p for p in probe_moves(board)}
    graph = build_root_argument_graph(list(probes.values()))

    # Both moves clean; the Phase-5 move has strictly more heuristic pros.
    assert _categoriser_score(probes[phase5_move], graph) == 1.0
    assert _categoriser_score(probes[fact_only_move], graph) == 1.0
    assert _accepted_heuristic_pro_count(
        probes[phase5_move]
    ) > _accepted_heuristic_pro_count(probes[fact_only_move])

    # The pre-Phase-5 engine picked the thinner move...
    assert _fact_only_choice(board) == fact_only_move, fen
    # ...and the Phase-5 engine picks the better-supported one.
    chosen = DialecticalCheckersEngine().choose_move(board).move_pdn
    assert chosen == phase5_move, (fen, chosen, phase5_move)


@pytest.mark.differential
def test_graded_improvement_corpus_is_non_trivial() -> None:
    """The curated graded-improvement corpus has enough positions to be real."""
    assert len(CAT_IMPROVEMENT) >= 3
    assert len(PRO_IMPROVEMENT) >= 3
