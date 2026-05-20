"""Phase 5 probe — sanity-check the graded Categoriser layer wiring.

Builds the root argument graph on a few hand-built and real positions and
prints the graded-layer ranking, so the Coder can verify the graded AF is
constructed and ``categoriser_scores`` is consumed before writing tests.
"""

from __future__ import annotations

from dialectical_checkers.arguments import MoveProbe, build_root_argument_graph
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.witnesses import probe_moves


def show(label: str, graph) -> None:  # noqa: ANN001
    print(f"--- {label} ---")
    print("  survivors:", sorted(graph.survivors))
    r = graph.ranking
    print("  ranking keys:", sorted(r.keys()))
    print("  graded args:", sorted(r.get("arguments", ())))
    print("  graded defeats:", sorted(r.get("defeats", ())))
    print("  move_scores:", r.get("move_scores"))
    print("  converged:", r.get("converged"), "iterations:", r.get("iterations"))
    print()


# Hand-built: one clean survivor with no heuristic objection.
clean = MoveProbe(pdn="11-15", reasons=("pro:material:100",))
show("single clean probe", build_root_argument_graph([clean]))

# Hand-built: a survivor with a heuristic objection vs one without.
objected = MoveProbe(
    pdn="9-14", reasons=("pro:opposition",), objections=("obj:loses_opposition",)
)
clean2 = MoveProbe(pdn="10-15", reasons=("pro:opposition",))
show("heuristic-objected vs clean", build_root_argument_graph([objected, clean2]))

# Real position from the start.
board = CheckersBoard.initial()
show("initial position", build_root_argument_graph(list(probe_moves(board))))

# Empty (terminal).
show("empty probes", build_root_argument_graph([]))
