"""Phase 5 — find curated quiet positions where the graded layer improves play.

A graded-improvement curated case (design §7 test directive) needs:

* a QUIET position — no FACT witness in play: every legal move has FACT key
  (0,0,0,0,0), so the Phase-3b FACT selector could only tiebreak by static eval
  / PDN;
* the Phase-5 ``argument`` mode picks a move that the Phase-3b-style FACT-only
  selector did NOT (it would have tiebroken to a different move);
* the Phase-5 move is heuristically CLEARLY better — it has strictly more
  accepted HEURISTIC pro-reasons, or a strictly higher Categoriser score
  (fewer / weaker HEURISTIC objections), or both, than the move the FACT-only
  selector picked.

This script scans the seeded sample, prints every qualifying position with the
two moves and their graded metrics, so the Coder can curate a handful into
``tests/test_phase5_graded_improvement.py``.
"""

from __future__ import annotations

import random

from dialectical_checkers.arguments import build_root_argument_graph
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.selection import (
    _accepted_heuristic_pro_count,
    _categoriser_score,
    _fact_pro_priority,
    _worst_fact_objection_magnitude,
    choose_move,
)
from dialectical_checkers.witnesses import probe_moves


def reachable(seed: int, plies: int) -> list[CheckersBoard]:
    rng = random.Random(seed)
    board = CheckersBoard.initial()
    out = [board]
    for _ in range(plies):
        moves = board.legal_moves()
        if not moves:
            break
        board = board.apply(rng.choice(moves))
        out.append(board)
        if board.is_draw():
            break
    return out


def fact_key(probe, graph):  # noqa: ANN001
    mag = _worst_fact_objection_magnitude(probe, graph)
    w, lg, cr, sm = _fact_pro_priority(probe)
    return (mag, -w, -lg, -cr, -sm)


def fact_only_choice(probes, graph, board):  # noqa: ANN001
    """The move a FACT-terms-only selector (Phase 3b) would pick.

    FACT key (terms 1-2), then static-eval / PDN tiebreak — exactly the
    pre-Phase-5 ``_selection_key`` with no graded terms.
    """
    from dialectical_checkers.search import static_evaluation

    def key(p):  # noqa: ANN001
        move = next(m for m in board.legal_moves() if m.pdn() == p.pdn)
        return (*fact_key(p, graph), static_evaluation(board.apply(move)), p.pdn)

    survivors = [p for p in probes if p.pdn in graph.survivors] or probes
    return min(survivors, key=key)


def main() -> None:
    seen: set[str] = set()
    found = 0
    for seed in range(400):
        for plies in (10, 18, 26, 34, 44):
            for board in reachable(seed, plies):
                fen = board.to_fen()
                if fen in seen or not board.legal_moves():
                    continue
                seen.add(fen)
                probes = list(probe_moves(board))
                graph = build_root_argument_graph(probes)
                # Quiet: every move's FACT key is the clean (0,0,0,0,0).
                if any(
                    fact_key(p, graph) != (0, 0, 0, 0, 0) for p in probes
                ):
                    continue
                if len(probes) < 2:
                    continue
                p5 = choose_move(probes, graph, board=board).pdn
                p3 = fact_only_choice(probes, graph, board).pdn
                if p5 == p3:
                    continue
                by = {p.pdn: p for p in probes}
                p5_cat = _categoriser_score(by[p5], graph)
                p3_cat = _categoriser_score(by[p3], graph)
                p5_pro = _accepted_heuristic_pro_count(by[p5])
                p3_pro = _accepted_heuristic_pro_count(by[p3])
                # Clearly better: strictly more heuristic pros OR strictly
                # higher Categoriser score, and never worse on the other.
                better = (
                    (p5_cat > p3_cat and p5_pro >= p3_pro)
                    or (p5_pro > p3_pro and p5_cat >= p3_cat)
                )
                if not better:
                    continue
                found += 1
                print(f"FEN: {fen}")
                print(
                    f"  Phase5 -> {p5}  (Cat={p5_cat:.4f} heuristic_pros={p5_pro})"
                )
                print(
                    f"  FACT-only -> {p3}  (Cat={p3_cat:.4f} heuristic_pros={p3_pro})"
                )
                print(f"  P5 move reasons: {by[p5].reasons}")
                print(f"  P5 move objections: {by[p5].objections}")
                print(f"  FACT-only move reasons: {by[p3].reasons}")
                print(f"  FACT-only move objections: {by[p3].objections}")
                print()
                if found >= 12:
                    print(f"total found: {found}")
                    return
    print(f"total found: {found}")


if __name__ == "__main__":
    main()
