"""Phase 5 — classify which Phase-4-baseline positions changed move, and why.

The Phase-5 graded layer changes engine PLAY in QUIET positions (design §7).
The Phase-4 regression baseline pinned play as unchanged by the (then inert)
heuristic layer. This script replays every baseline row and, for each position
whose chosen move changed, confirms the change is GRADED-only — i.e. the
position is not decided by the FACT terms:

* it prints whether the OLD baseline move and the NEW move are BOTH crisp
  survivors (the graded layer only ranks survivors — a changed move must still
  be a survivor, never a resurrected eliminated move);
* it prints the FACT key (terms 1-2) of the old and new move — if those are
  EQUAL, the FACT terms did not decide and the change is purely graded; if they
  differ, the FACT terms changed, which would be a Phase-3b-guarantee
  regression and must be reported.
"""

from __future__ import annotations

from dialectical_checkers import DialecticalCheckersEngine
from dialectical_checkers.arguments import build_root_argument_graph
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.selection import (
    _fact_pro_priority,
    _worst_fact_objection_magnitude,
)
from dialectical_checkers.witnesses import probe_moves
from tests.test_phase4_regression import REGRESSION_BASELINE


def fact_key(probe, graph):  # noqa: ANN001
    """The FACT-only key (selector terms 1-2) for a probe."""
    mag = _worst_fact_objection_magnitude(probe, graph)
    winning, large, crown, small = _fact_pro_priority(probe)
    return (mag, -winning, -large, -crown, -small)


engine = DialecticalCheckersEngine()
changed = 0
fact_regressions = []
resurrections = []

for fen, old_pdn in REGRESSION_BASELINE:
    board = CheckersBoard.from_fen(fen)
    new_pdn = engine.choose_move(board).move_pdn
    if new_pdn == old_pdn:
        continue
    changed += 1
    probes = {p.pdn: p for p in probe_moves(board)}
    graph = build_root_argument_graph(list(probes.values()))
    old_survivor = old_pdn in graph.survivors
    new_survivor = new_pdn in graph.survivors
    old_fact = fact_key(probes[old_pdn], graph)
    new_fact = fact_key(probes[new_pdn], graph)
    if not new_survivor:
        resurrections.append((fen, old_pdn, new_pdn))
    if old_fact != new_fact:
        fact_regressions.append((fen, old_pdn, new_pdn, old_fact, new_fact))
    print(
        f"{fen}\n  old={old_pdn} (survivor={old_survivor} fact={old_fact})"
        f"  new={new_pdn} (survivor={new_survivor} fact={new_fact})"
    )

print()
print(f"changed moves: {changed} / {len(REGRESSION_BASELINE)}")
print(f"NEW move not a crisp survivor (resurrection): {len(resurrections)}")
for row in resurrections:
    print("  RESURRECTION:", row)
print(f"FACT key differs old vs new (FACT regression): {len(fact_regressions)}")
for row in fact_regressions:
    print("  FACT-REGRESSION:", row)
