"""Phase 4 fix — verify the S-based obj:loses_opposition mirror.

Proposed final rule (the exact dual of pro:opposition, which fires iff
holder(S) == mover):

    obj:loses_opposition fires on M iff holder(S) is defined (S is a 1v1
    equal-force man-v-man or king-v-king ending) AND holder(S) != mover.

This is the move-channel statement of a tempo deficit: the move LANDS the
game in a 1v1 equal-force ending whose opposition the opponent holds. It is
deterministic, reachable, and the precise dual of pro:opposition.

This script:
  1. confirms it fires on a quiet, non-terminal move (positive firing case);
  2. confirms it does NOT fire on the multi-piece silence position;
  3. confirms it does NOT fire when pro:opposition fires (they are exclusive
     on any move whose child is a 1v1 ending);
  4. prints a concrete positive firing position for the report.

Run: uv run python scripts/phase4fix_sbased_mirror.py
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard, _coord


def holder(board: CheckersBoard) -> str | None:
    reds = [i + 1 for i, c in enumerate(board.cells) if c and c[0] == "r"]
    whites = [i + 1 for i, c in enumerate(board.cells) if c and c[0] == "w"]
    if len(reds) != 1 or len(whites) != 1:
        return None
    rk = board.cells[reds[0] - 1]
    wk = board.cells[whites[0] - 1]
    assert rk is not None and wk is not None
    if rk[1] != wk[1]:
        return None
    r_row, r_col = _coord(reds[0] - 1)
    w_row, w_col = _coord(whites[0] - 1)
    s = max(abs(r_row - w_row), abs(r_col - w_col))
    opp = "w" if board.turn == "r" else "r"
    return opp if s % 2 == 0 else board.turn


def fires(board: CheckersBoard, move) -> bool:
    mover = board.turn
    child = board.apply(move)
    h = holder(child)
    return h is not None and h != mover


def report_pos(fen: str) -> None:
    board = CheckersBoard.from_fen(fen)
    mover = board.turn
    print(f"\n{fen} (mover={mover}):")
    for m in board.legal_moves():
        child = board.apply(m)
        h = holder(child)
        flag = "obj:loses_opposition" if fires(board, m) else ""
        proflag = "pro:opposition" if h == mover else ""
        print(f"  {m.pdn():9s} jump={m.is_jump!s:5s} "
              f"holder(S)={h!s:5s} {proflag} {flag}")


def main() -> None:
    # 1. positive — B:WK8:BK15: sep 2 even, holder=White; every Red move lands
    #    in a 1v1 kk ending White holds.
    pos = CheckersBoard.from_fen("B:WK8:BK15")
    moves = pos.legal_moves()
    quiet_pos = [m for m in moves
                 if not m.is_jump and fires(pos, m)
                 and not pos.apply(m).is_terminal()]
    print(f"B:WK8:BK15 quiet non-terminal firing moves: "
          f"{[m.pdn() for m in quiet_pos]}")

    # 2. silence on multi-piece position
    multi = CheckersBoard.from_fen("B:W22,30:B6,9,13,14")
    fired = [m.pdn() for m in multi.legal_moves() if fires(multi, m)]
    print(f"B:W22,30:B6,9,13,14 firing moves (expect none): {fired}")

    # 3. exclusivity with pro:opposition on B:WK4:BK15 (Red holds)
    held = CheckersBoard.from_fen("B:WK4:BK15")
    bad = []
    for m in held.legal_moves():
        child = held.apply(m)
        h = holder(child)
        if h == held.turn and fires(held, m):
            bad.append(m.pdn())
    print(f"B:WK4:BK15 moves with BOTH pro & obj (expect none): {bad}")

    report_pos("B:WK8:BK15")
    report_pos("B:WK4:BK15")


if __name__ == "__main__":
    main()
