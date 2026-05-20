"""Phase 4 fix — examine the holder() definition's self-consistency.

The current witnesses.py rule:
    separation = Chebyshev distance between the two 1v1 pieces
    holder(pos) = side NOT to move  if separation even
                = side to move      if separation odd

Claimed: "when a side holds the opposition every legal move passes it to the
opponent" (witnesses.py docstring lines 52-54). The non-capture probe showed
the OPPOSITE: every quiet move keeps it for the mover. This script checks the
alternation property move-by-move on concrete king-king endings to determine
which statement is true.

For a held-opposition root: enumerate quiet moves; for each child print
holder(R), holder(child), and the turn of child. If holder is truly an
alternating "the move" property, after the mover plays, holder(child) should be
the OPPONENT (the move passed it on). If holder(child)==mover, the rule does
not have the claimed alternation -> the witness mirror is structurally dead.

Run: uv run python scripts/phase4fix_holder_semantics.py
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard, _coord


def sep(board: CheckersBoard) -> int | None:
    reds = [i + 1 for i, c in enumerate(board.cells) if c and c[0] == "r"]
    whites = [i + 1 for i, c in enumerate(board.cells) if c and c[0] == "w"]
    if len(reds) != 1 or len(whites) != 1:
        return None
    r_row, r_col = _coord(reds[0] - 1)
    w_row, w_col = _coord(whites[0] - 1)
    return max(abs(r_row - w_row), abs(r_col - w_col))


def holder(board: CheckersBoard) -> str | None:
    s = sep(board)
    if s is None:
        return None
    opp = "w" if board.turn == "r" else "r"
    return opp if s % 2 == 0 else board.turn


SAMPLE = ["B:WK6:BK1", "B:WK4:BK15", "W:WK18:BK10", "B:WK23:BK11"]

for fen in SAMPLE:
    board = CheckersBoard.from_fen(fen)
    mover = board.turn
    print(f"{fen}: sep={sep(board)} holder(R)={holder(board)} mover={mover}")
    for m in board.legal_moves():
        if m.is_jump:
            continue
        child = board.apply(m)
        print(f"  {m.pdn():9s} -> sep={sep(child)} "
              f"child.turn={child.turn} holder(child)={holder(child)}")
