"""v1.5 — graded-improvement curated positions (design V1.5-D1..D7).

The v1.5 graded layer replaces the attack-only Categoriser with doxa's
opinion-valued bipolar semantics. This file is the engine-level differential
proof that the new layer genuinely steers play: on curated QUIET positions —
no FACT witness in play, so the Phase-3b FACT selector could only tiebreak by
static evaluation / PDN — the v1.5 engine picks a heuristically better move
that the FACT-only selector did not.

Each curated case demonstrates a genuine v1.5 improvement, not an asserted one:

* the position is QUIET — every legal move's FACT key is the clean
  ``(0, 0, 0, 0, 0)``;
* the pre-Phase-5 FACT-only selector (``_fact_only_choice`` below, the
  Phase-3b ``_selection_key`` with no graded terms) tiebroke to ``fact_only_move``;
* the v1.5 ``argument``-mode engine instead picks ``v15_move``;
* and the v1.5 opinion-valued graded layer rates ``v15_move`` STRICTLY above
  ``fact_only_move`` — its ``Opinion.expectation()`` graded strength is higher,
  so the engine's choice is the layer's honest verdict, not a tiebreak.

The corpus was located by ``scripts/v15_find_graded_improvement.py`` against
the v1.5 opinion-valued layer (it supersedes the Phase-5
``phase5_find_graded_improvement.py``, which ran against the replaced
attack-only Categoriser). Every row was re-verified by
``scripts/v15_verify_improvement_corpus.py``.

The graded-layer unit tests — including the contested-move high-``u`` and
support-heavy-outranks-support-poor proofs — live in ``test_arguments.py``;
this file is the end-to-end engine differential.
"""

from __future__ import annotations

import pytest

from dialectical_checkers import DialecticalCheckersEngine
from dialectical_checkers.arguments import build_root_argument_graph
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.selection import (
    _fact_pro_priority,
    _graded_strength,
    _worst_fact_objection_magnitude,
)
from dialectical_checkers.search import static_evaluation
from dialectical_checkers.witnesses import probe_moves

# Curated quiet positions where the v1.5 opinion-valued graded layer steers the
# engine off the FACT-only tiebreak move onto a heuristically stronger move.
# Each row is (FEN, the v1.5 engine move, the pre-Phase-5 FACT-only move).
# Located by ``scripts/v15_find_graded_improvement.py``, verified by
# ``scripts/v15_verify_improvement_corpus.py``.
GRADED_IMPROVEMENT: list[tuple[str, str, str]] = [
    (
        "B:W21,22,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,11,12",
        "12-16",
        "10-14",
    ),
    (
        "B:W18,21,22,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,11,16",
        "8-12",
        "10-14",
    ),
    (
        "B:W18,21,22,24,25,26,29,30,31,32:B1,2,3,4,5,6,7,8,9,11,28",
        "6-10",
        "11-15",
    ),
    (
        "W:W18,21,22,24,25,26,29,30,31,32:B1,2,3,4,5,6,7,8,9,16,28",
        "21-17",
        "18-14",
    ),
    (
        "W:W18,21,22,25,29,30,31,32:B1,2,3,4,5,6,7,9,19,28",
        "30-26",
        "18-14",
    ),
    ("W:WK13,18,25,28,32:B8,16,20", "13-9", "13-17"),
    (
        "B:W17,20,22,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,9,10,11,12,16",
        "4-8",
        "10-14",
    ),
    (
        "B:W18,21,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,10,11,12,14",
        "5-9",
        "10-15",
    ),
    (
        "B:W18,21,23,24,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,12",
        "7-11",
        "10-14",
    ),
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
    a position by static eval / PDN — so any difference the v1.5 engine makes
    here is purely the opinion-valued graded layer.
    """
    probes = list(probe_moves(board))
    graph = build_root_argument_graph(probes)
    return all(_fact_key(p, graph) == (0, 0, 0, 0, 0) for p in probes)


@pytest.mark.differential
@pytest.mark.parametrize(
    ("fen", "v15_move", "fact_only_move"),
    GRADED_IMPROVEMENT,
    ids=lambda v: str(v),
)
def test_v15_graded_layer_steers_play_in_a_quiet_position(
    fen: str, v15_move: str, fact_only_move: str
) -> None:
    """v1.5 picks a move the FACT-only selector did not, with higher strength.

    A quiet position where the pre-Phase-5 FACT-only selector tiebreaks to
    ``fact_only_move``. The v1.5 ``argument``-mode engine instead picks
    ``v15_move`` — and the opinion-valued graded layer rates ``v15_move``
    strictly above ``fact_only_move`` (``Opinion.expectation()`` strength), so
    the engine's choice is the graded layer's honest verdict. The pre-Phase-5
    engine demonstrably picked the other move.
    """
    board = CheckersBoard.from_fen(fen)
    assert _is_quiet(board), (fen, "curated position is not quiet")
    probes = {p.pdn: p for p in probe_moves(board)}
    graph = build_root_argument_graph(list(probes.values()))

    # The opinion-valued graded layer rates the v1.5 move strictly higher.
    assert _graded_strength(probes[v15_move], graph) > _graded_strength(
        probes[fact_only_move], graph
    ), fen

    # The pre-Phase-5 engine picked the FACT-only tiebreak move...
    assert _fact_only_choice(board) == fact_only_move, fen
    # ...and the v1.5 engine picks the graded-layer-preferred move.
    chosen = DialecticalCheckersEngine().choose_move(board).move_pdn
    assert chosen == v15_move, (fen, chosen, v15_move)


@pytest.mark.differential
def test_graded_improvement_corpus_is_non_trivial() -> None:
    """The curated v1.5 graded-improvement corpus has enough positions to be real."""
    assert len(GRADED_IMPROVEMENT) >= 6
