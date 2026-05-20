"""Phase 4 — debug why exposes_man / bridge are not firing."""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import opponent_shot
from dialectical_checkers.witnesses import probe_moves


def show(fen: str) -> None:
    board = CheckersBoard.from_fen(fen)
    print(f"=== {fen}  {board.turn} to move")
    move_by = {m.pdn(): m for m in board.legal_moves()}
    for probe in probe_moves(board):
        m = move_by[probe.pdn]
        child = board.apply(m)
        opp_caps = [x.pdn() for x in child.legal_moves() if x.is_jump]
        shot = opponent_shot(board, m)
        print(f"  {probe.pdn}: dest={m.destination} jump={m.is_jump}  "
              f"opp_caps_after={opp_caps}  shot={'None' if shot is None else shot.tier}  "
              f"objs={list(probe.objections)}  reasons={list(probe.reasons)}")
    print()


def main() -> None:
    # For exposes_man, need quiet move + opponent capture available after +
    # opponent_shot None. Try: Red man steps adjacent to a White man so White
    # CAN jump it, but Red can recapture (so opponent_shot None).
    show("B:W15:B11,7")   # Red 11->? next to White 15
    show("B:W19,32:B10,6")
    # White man to bridge square 31: from 27 (27=(6,5) SW->31=(7,4)).
    show("W:W29,27:B6")  # White 27->31 completes 29+31 bridge
    show("W:W31,25:B6")  # White 25->29 completes bridge


if __name__ == "__main__":
    main()
