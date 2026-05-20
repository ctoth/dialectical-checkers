"""Phase 4 — verify pro:formation:bridge fires for a maintained bridge."""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.witnesses import probe_moves


def show(fen: str) -> None:
    board = CheckersBoard.from_fen(fen)
    print(f"=== {fen}  {board.turn}")
    for probe in probe_moves(board):
        bridge = [r for r in probe.reasons if r == "pro:formation:bridge"]
        print(f"  {probe.pdn}: bridge={bool(bridge)}  reasons={list(probe.reasons)}")
    print()


def main() -> None:
    # White men on 29 and 31 (both bridge squares) + a third White man to move.
    show("W:W29,31,18:B6")
    # Red men on 2 and 4 (Red bridge) + a third Red man to move.
    show("B:W30:B2,4,10")
    # Bridge broken: White man on 29 only.
    show("W:W29,18:B6")


if __name__ == "__main__":
    main()
