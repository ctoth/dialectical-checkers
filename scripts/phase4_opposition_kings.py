"""Phase 4 — fix the opposition parity bit using same-diagonal king pairs.

Two kings on the SAME diagonal with d empty squares between them. Kings move
one diagonal step either way. With both confined toward that diagonal, the
side to move must either approach (closing d) or retreat. The classic 'direct
opposition': when two kings face on a diagonal with an ODD number of squares
between them, the side NOT to move holds the opposition (the mover must give
ground); with an EVEN gap it flips. This is the unambiguous geometric anchor.

We pick real diagonal-adjacent king pairs and print the system count parity
alongside the gap parity, to FIX the rule's single offset bit.

Diagonals: NE = row+1,col+1. Column-stepped squares on one long diagonal:
PDN 4(0,7) is a corner. Diagonal from 4: 4(0,7)-8(1,6)-11(2,5)-15(3,4)-
18(4,3)-22(5,2)-25(6,1)-29(7,0). That is the full single-corner diagonal.
"""

from __future__ import annotations

from dialectical_checkers.board import NUM_SQUARES, CheckersBoard, _coord

# The main diagonal 4-8-11-15-18-22-25-29 (each step row+1,col-1).
DIAG = [4, 8, 11, 15, 18, 22, 25, 29]


def count_parity(board: CheckersBoard, mod_eq: int) -> int:
    n = 0
    for idx in range(NUM_SQUARES):
        if board.cells[idx] is None:
            continue
        row, col = _coord(idx)
        if (row + col) % 4 == mod_eq:
            n += 1
    return n


def main() -> None:
    print("Two kings on diagonal 4-8-11-15-18-22-25-29:")
    print("position index along diagonal -> gap between them")
    for i in range(len(DIAG)):
        for j in range(i + 1, len(DIAG)):
            red_sq, white_sq = DIAG[i], DIAG[j]
            gap = j - i - 1  # empty diagonal squares between
            for turn in ("B", "W"):
                fen = f"{turn}:WK{white_sq}:BK{red_sq}"
                board = CheckersBoard.from_fen(fen)
                a = count_parity(board, 1)
                b = count_parity(board, 3)
                # geometric truth: with gap d, side-to-move must give ground
                # iff d is EVEN (direct opposition: opponent holds it).
                stm_holds = (gap % 2 == 1)
                if i == 0 and j <= 3:  # print a manageable sample
                    print(
                        f"  {fen}  gap={gap}  STM-holds={stm_holds}  "
                        f"sysA%2={a%2}  sysB%2={b%2}"
                    )
    # focused: same red square, vary white, fixed turn -> isolate the bit.
    print()
    print("Red king fixed on 15, White king varies along diagonal, Red to move:")
    for sq in DIAG:
        if sq == 15:
            continue
        fen = f"B:WK{sq}:BK15"
        board = CheckersBoard.from_fen(fen)
        a = count_parity(board, 1)
        b = count_parity(board, 3)
        ri = DIAG.index(15)
        wi = DIAG.index(sq)
        gap = abs(wi - ri) - 1
        stm_holds = (gap % 2 == 1)
        print(
            f"  {fen}  gap={gap}  STM-holds(truth)={stm_holds}  "
            f"sysA%2={a%2}  sysB%2={b%2}  total%2={(a+b)%2}"
        )


if __name__ == "__main__":
    main()
