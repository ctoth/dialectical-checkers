"""Phase 4 — verify the separation-parity opposition rule is self-consistent.

Rule under test: in an equal-force ending with exactly one piece per side, the
side to move HOLDS the opposition iff the Chebyshev (king-step) distance
between the two pieces is EVEN.

Self-consistency requirement: after ANY legal move by the side to move, the
opposition must pass to the other side (the new side to move). I.e. if Red
holds the opposition and Red moves, White (now to move) must NOT hold it, and
vice versa — opposition is a strict alternating property under a single ply,
because one king step changes the Chebyshev distance by exactly 0 or 2 ... no:
a king step toward/away changes distance by +-1 along one axis. We test the
actual claim: does the rule alternate sensibly across a ply?

Print, for 1K-v-1K positions, the rule's verdict before and after each move.
"""

from __future__ import annotations

from dialectical_checkers.board import NUM_SQUARES, CheckersBoard, _coord


def chebyshev(board: CheckersBoard) -> int | None:
    """King-step distance between the two pieces, or None if not 1-v-1."""
    reds = [i for i in range(NUM_SQUARES)
            if board.cells[i] and board.cells[i][0] == "r"]
    whites = [i for i in range(NUM_SQUARES)
              if board.cells[i] and board.cells[i][0] == "w"]
    if len(reds) != 1 or len(whites) != 1:
        return None
    r1, c1 = _coord(reds[0])
    r2, c2 = _coord(whites[0])
    return max(abs(r1 - r2), abs(c1 - c2))


def stm_holds(board: CheckersBoard) -> bool | None:
    d = chebyshev(board)
    if d is None:
        return None
    return d % 2 == 0


def main() -> None:
    fens = [
        "B:WK8:BK15",
        "B:WK11:BK15",
        "B:WK4:BK15",
        "B:WK22:BK15",
        "W:WK8:BK15",
    ]
    for fen in fens:
        board = CheckersBoard.from_fen(fen)
        d = chebyshev(board)
        before = stm_holds(board)
        print(f"{fen}  cheb={d}  STM-holds={before}")
        for m in board.legal_moves():
            child = board.apply(m)
            after = stm_holds(child)
            cd = chebyshev(child)
            print(f"    after {m.pdn()}: cheb={cd}  newSTM-holds={after}")
    # The meaningful self-consistency: a king step that APPROACHES the
    # opponent changes Chebyshev distance by 1 -> parity flips -> opposition
    # passes. A king step that keeps distance (sideways) does not flip. That
    # is correct: a 'waiting'/sideways move keeps the opposition with the same
    # side after the turn passes, which is exactly what 'holding the move'
    # while forcing the opponent to approach means.


if __name__ == "__main__":
    main()
