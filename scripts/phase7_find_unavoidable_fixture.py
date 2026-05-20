"""Phase 7 — search for an unavoidable one-ply Red loss fixture.

Need: Red to move has exactly one legal move, it is a capture, and after it
White has a forced reply that wins Red's last piece (or the game). That is a
position where Red's loss is locked in with no choice — the unavoidable case
for the loss-mining test. Brute-force 3-piece positions. No oneliners.
"""

from __future__ import annotations

from dataclasses import replace
from itertools import permutations

from dialectical_checkers.board import NUM_SQUARES, Cell, CheckersBoard
from dialectical_checkers.captures import opponent_shot


def _board(red: tuple[int, ...], white: tuple[int, ...], turn: str):
    cells: list[Cell | None] = [None] * NUM_SQUARES
    for sq in red:
        cells[sq - 1] = ("r", False)
    for sq in white:
        cells[sq - 1] = ("w", False)
    b = CheckersBoard(cells=tuple(cells), turn=turn, no_progress=0, history=())
    return replace(b, history=(b._position_id(),))


def main() -> None:
    found = 0
    squares = list(range(6, 28))
    for r in squares:
        for w1, w2 in permutations(squares, 2):
            if len({r, w1, w2}) != 3:
                continue
            b = _board((r,), (w1, w2), "r")
            legal = b.legal_moves()
            if len(legal) != 1:
                continue
            only = legal[0]
            if not only.is_jump:
                continue
            after = b.apply(only)
            # Red must be losing after the forced move: White (now to move)
            # has a reply that wins, OR Red is already terminal-lost.
            if after.is_terminal():
                if after.winner() == "w":
                    print(f"R{r} W{w1},{w2} turn r: fen={b.to_fen()} "
                          f"forced={only.pdn()} -> immediate White win")
                    found += 1
                continue
            # White to move: does White have a shot that wins Red's last man?
            white_shot = False
            for wm in after.legal_moves():
                shot = opponent_shot(after, wm)
                # opponent here = Red; we want White to gain, so check the
                # other direction: after White's move Red has no shot and
                # White won material. Simpler: just play White's best capture.
                if wm.is_jump:
                    white_shot = True
            if white_shot:
                # White has a capture reply — likely wins Red's man.
                after2 = after.apply(
                    next(m for m in after.legal_moves() if m.is_jump))
                if after2.winner() == "w" or not any(
                        c and c[0] == "r" for c in after2.cells):
                    print(f"R{r} W{w1},{w2} turn r: fen={b.to_fen()} "
                          f"forced={only.pdn()} then White wins")
                    found += 1
            if found >= 5:
                return
    if not found:
        print("no unavoidable 3-piece fixture found")


if __name__ == "__main__":
    main()
