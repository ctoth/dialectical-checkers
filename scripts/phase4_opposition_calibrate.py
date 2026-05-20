"""Phase 4 — calibrate the deterministic opposition (parity) rule.

The opposition / 'the move' is, per Pask (Lesson 21), a pairing-off parity. For
a single facing pair of kings on a column with d empty rows between them, the
side to move must approach first; the OTHER side holds the opposition. d even =>
side-not-to-move holds it.

This prints, for facing-king positions, several candidate parity values so the
system-count formula's constant offset is FIXED by matching geometry, not
invented.
"""

from __future__ import annotations

from dialectical_checkers.board import NUM_SQUARES, CheckersBoard, _coord


def system_a_count(board: CheckersBoard) -> int:
    n = 0
    for idx in range(NUM_SQUARES):
        if board.cells[idx] is None:
            continue
        row, col = _coord(idx)
        if (row + col) % 4 == 1:
            n += 1
    return n


def total_count(board: CheckersBoard) -> int:
    return sum(1 for c in board.cells if c is not None)


def rank_sum(board: CheckersBoard) -> int:
    return sum(_coord(i)[0] for i in range(NUM_SQUARES) if board.cells[i])


def main() -> None:
    # FEN form: <turn>:W<squares>:B<squares>; a king is K-prefixed inside a
    # field. "WK23" inside the W field = White KING on 23.
    # Column-4 squares: 7(1,4),15(3,4),23(5,4),31(7,4).
    cases = [
        # (red_king_sq, white_king_sq, d=empty rows between)
        (7, 23, 3),    # rows 1,5
        (7, 31, 5),    # rows 1,7
        (15, 23, 1),   # rows 3,5
        (15, 31, 3),   # rows 3,7
        (23, 31, 1),   # rows 5,7
    ]
    print("facing-king positions on column 4, Red (B) to move:")
    for red_sq, white_sq, d in cases:
        fen = f"B:WK{white_sq}:BK{red_sq}"
        board = CheckersBoard.from_fen(fen)
        ca = system_a_count(board)
        tc = total_count(board)
        rs = rank_sum(board)
        # Geometric truth: d even => side-not-to-move (White) holds opposition;
        # d odd => side-to-move (Red) holds opposition.
        truth_stm_holds = (d % 2 == 1)
        print(
            f"  {fen}  d={d}  STM-holds(truth)={truth_stm_holds}  "
            f"sysA={ca}(%2={ca%2})  tot={tc}(%2={tc%2})  "
            f"ranksum={rs}(%2={rs%2})"
        )


if __name__ == "__main__":
    main()
