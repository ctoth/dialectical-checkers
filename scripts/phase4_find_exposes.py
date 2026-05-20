"""Phase 4 — find positions that fire obj:exposes_man and pro:formation:bridge.

obj:exposes_man: a quiet move after which the opponent has a capture but
opponent_shot returns None / non-FACT (the loss is not proven).
bridge: the mover lands on a home-rank bridge square completing the pair.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.witnesses import probe_moves


def find(fen: str) -> None:
    board = CheckersBoard.from_fen(fen)
    for probe in probe_moves(board):
        labs = [*probe.reasons, *probe.objections]
        if "obj:exposes_man" in labs or any(
            x.startswith("pro:formation:bridge") for x in labs
        ):
            print(f"  {fen}  {board.turn}  {probe.pdn}: {labs}")


def main() -> None:
    # exposes_man: search a spread of simple positions.
    print("exposes_man / bridge search:")
    exposes_fens = [
        "B:W15:B11,7",        # Red man advancing next to a White man
        "B:W15,32:B11,7",
        "B:W19:B10,6",
        "B:W23:B14,18",
        "B:W18:B14,9",
        "B:W26,15:B10,6",
        "B:W14:B9,5",
        "B:W19,23:B15,10",
    ]
    for fen in exposes_fens:
        find(fen)
    print()
    print("bridge — White completing 29+31 or Red completing 2+4:")
    bridge_fens = [
        # White man on 31, another White man one step from 29 (man on 25).
        "W:W31,25:B6",
        # White man on 29, White man on 26 stepping to 31? 26->31 not a step.
        # 27 steps to 31 (SW? row6col5 -> row7col4). Try W man on 27 + 29.
        "W:W29,27:B6",
        # Red man on 2, Red man stepping to 4: from 8 -> 4? 8=(1,6) 4=(0,7).
        "B:W30:B2,8",
        # Red man on 4, Red man stepping to 2: from 6 -> 2? 6=(1,2) 2=(0,3).
        "B:W30:B4,6",
    ]
    for fen in bridge_fens:
        find(fen)


if __name__ == "__main__":
    main()
