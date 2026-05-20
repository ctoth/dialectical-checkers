"""Reproduce the Phase 3b analyst findings before fixing them.

Run: ``uv run python scripts/phase3b_reproduce_findings.py``

Prints, for the analyst's key position ``B:W10,17,18:B6,13,14``:
  * every legal move with its probe witnesses;
  * the crisp graph survivors;
  * the selection key of each survivor;
  * the engine's chosen move.

This is a diagnostic, not a test — it documents the pre-fix behaviour the
analyst observed (MAJOR 1 selector inversion -> engine plays ``14x23``).
"""

from __future__ import annotations

from dialectical_checkers import DialecticalCheckersEngine
from dialectical_checkers.arguments import build_root_argument_graph
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.selection import _selection_key
from dialectical_checkers.witnesses import probe_moves

FEN = "B:W10,17,18:B6,13,14"


def main() -> None:
    board = CheckersBoard.from_fen(FEN)
    probes = list(probe_moves(board))
    graph = build_root_argument_graph(probes)

    print(f"position: {FEN}")
    print(f"legal moves: {[p.pdn for p in probes]}")
    print(f"crisp survivors: {sorted(graph.survivors)}")
    print()
    for probe in probes:
        print(f"  move {probe.pdn}")
        print(f"    reasons       : {probe.reasons}")
        print(f"    objections    : {probe.objections}")
        print(f"    reply_attacks : {probe.reply_attacks}")
        print(f"    defenses      : {probe.defenses}")
        try:
            key = _selection_key(probe, graph, board)
            print(f"    selection key : {key}")
        except Exception as exc:  # noqa: BLE001 — diagnostic only
            print(f"    selection key : <error: {exc!r}>")
    print()

    print("defeats:")
    for attacker, target in sorted(graph.defeats):
        print(f"  {attacker}  ->  {target}")
    print()

    engine = DialecticalCheckersEngine()
    decision = engine.choose_move(board)
    print(f"ENGINE CHOSE: {decision.move_pdn}")


if __name__ == "__main__":
    main()
