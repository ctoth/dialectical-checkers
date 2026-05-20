"""Phase 4 — determine ground-truth opposition holder by exhaustive search.

For a man-only equal-force position, the side that HOLDS the opposition is the
one that can force the other into zugzwang. We cannot fully decide a 12v12
game, but for tiny man-only positions we can exhaustively search: a side
'holds the opposition' iff it can force the opponent to be the first to make a
losing concession (here we use: the side that, with best play, does NOT lose).

This is only to FIX the single parity bit of the system-count rule. We use a
position simple enough to brute-force: two men, mover must give ground.

system A square iff (row+col)%4==1.
"""

from __future__ import annotations

from functools import lru_cache

from dialectical_checkers.board import NUM_SQUARES, CheckersBoard, _coord


def count_system_a(board: CheckersBoard) -> int:
    n = 0
    for idx in range(NUM_SQUARES):
        if board.cells[idx] is None:
            continue
        row, col = _coord(idx)
        if (row + col) % 4 == 1:
            n += 1
    return n


@lru_cache(maxsize=None)
def loses(fen: str, depth: int) -> bool:
    """True iff the side to move loses with best play within `depth` plies."""
    board = CheckersBoard.from_fen(fen)
    moves = board.legal_moves()
    if not moves:
        return True  # no move => side to move loses (WCDF 1.30)
    if depth <= 0:
        return False  # undecided within horizon — treat as not-lost
    # side to move can avoid losing iff SOME move leads to opponent losing.
    for m in moves:
        child = board.apply(m)
        if loses(child.to_fen(), depth - 1):
            return False
    return True


def main() -> None:
    # A man-only ending where the side to move is squeezed. Use a position
    # where Red has one man, White has one man, blocked so whoever must move
    # eventually runs out of squares. Hard to construct trivially; instead
    # enumerate small symmetric man positions and report systemA parity vs who
    # loses-on-best-play within a deep horizon.
    test_fens = [
        # Red man on 14, White man on 19 — directly facing diagonally.
        "B:W19:B14",
        "W:W19:B14",
        # Red man 13, White man 22.
        "B:W22:B13",
        "W:W22:B13",
        # near king-row squeezes
        "B:W30:B27",
        "W:W30:B27",
    ]
    for fen in test_fens:
        board = CheckersBoard.from_fen(fen)
        ca = count_system_a(board)
        stm_loses = loses(fen, 30)
        print(
            f"{fen}  turn={board.turn}  systemA={ca}(%2={ca%2})  "
            f"STM-loses-best-play(d30)={stm_loses}"
        )


if __name__ == "__main__":
    main()
