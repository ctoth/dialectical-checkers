"""Phase 7 — verify the full scripted blunder lines for loss-mining tests.

Plays the chosen blunder fixtures move by move and prints each position so the
test assertions (turning-point ply, final outcome) are confirmed against
runtime, not assumed. Measurement script, no oneliners.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import opponent_shot


def _play(fen: str, script: list[str]) -> None:
    print(f"=== start {fen} ===")
    board = CheckersBoard.from_fen(fen)
    for i, pdn in enumerate(script, start=1):
        legal = {m.pdn(): m for m in board.legal_moves()}
        if pdn not in legal:
            print(f"  ply {i}: {pdn} NOT LEGAL; legal={sorted(legal)}")
            return
        board = board.apply(legal[pdn])
        print(f"  ply {i}: {pdn} -> {board.to_fen()} turn={board.turn} "
              f"terminal={board.is_terminal()} winner={board.winner()}")


def main() -> None:
    # Red-seat blunder: Red 9 vs White 17. Red 9-14 blunders into 17x10.
    b = CheckersBoard.from_fen("B:W17:B9")
    bl = next(m for m in b.legal_moves() if m.pdn() == "9-14")
    print(f"opponent_shot(9-14) = {opponent_shot(b, bl)}")
    _play("B:W17:B9", ["9-14", "17x10"])
    # White-seat symmetric: White man, Red man. Need a White blunder.
    # Mirror of 9 vs 17: White 24 vs Red 16? probe geometry instead.
    _play("W:W17:B9", ["17-14", "9x18"])


if __name__ == "__main__":
    main()
