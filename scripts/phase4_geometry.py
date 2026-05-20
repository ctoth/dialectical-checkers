"""Phase 4 — print the board geometry to ground the HEURISTIC witness definitions.

Prints, for each PDN square 1-32: internal index, (row, col), and which
"system" parity it falls in for the opposition computation. Also prints which
squares are king-rows, which are the Single/Double corner squares, and a
candidate central-square set. No oracle, no engine logic — pure geometry print.
"""

from __future__ import annotations

from dialectical_checkers.board import (
    NUM_SQUARES,
    RED_KING_ROW,
    WHITE_KING_ROW,
    _coord,
)


def main() -> None:
    print("PDN idx (row,col)  red_fwd_parity")
    for pdn in range(1, NUM_SQUARES + 1):
        idx = pdn - 1
        row, col = _coord(idx)
        # Standard opposition "system": colour the 8x8 in two diagonal systems.
        # A common parity index used for the move/opposition in draughts is
        # (row + col) // 2 parity, or simply row parity counting toward a
        # king-row. Print several candidates.
        print(
            f"{pdn:2d}  {idx:2d}  ({row},{col})  "
            f"row%2={row % 2}  col%2={col % 2}  (r+c)%4={(row + col) % 4}"
        )
    print()
    print(f"RED_KING_ROW row = {RED_KING_ROW}  (squares 29-32)")
    print(f"WHITE_KING_ROW row = {WHITE_KING_ROW}  (squares 1-4)")
    # Single corner / double corner per port-plan 5.1: square 1-4 region and
    # 29-32. Port-plan: square 32 is the nearest double-corner square; the
    # near-left playing corner is the Single Corner.
    print()
    print("Rows top(0)..bottom(7); each row's PDN squares:")
    for row in range(8):
        pdns = [p for p in range(1, 33) if _coord(p - 1)[0] == row]
        cols = [_coord(p - 1)[1] for p in pdns]
        print(f"  row {row}: pdn={pdns} cols={cols}")


if __name__ == "__main__":
    main()
