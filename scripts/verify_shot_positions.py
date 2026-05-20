"""Verify the opponent_shot / own_shot test positions for test_captures.py.

Run: ``uv run python scripts/verify_shot_positions.py``

Confirms, using the engine board only, that:

* in ``B:W24:B15`` Red's quiet move 15-19 exposes the Red man to a forced
  White capture, while 15-18 does not;
* the capture-only minimax outcome after each move (net for the side then to
  move) is what the opponent_shot / own_shot tests assert.

Pins the hand-reasoning before the resolver is implemented.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard, CheckersMove

MAN_VALUE = 100
KING_VALUE = 150


def material(board: CheckersBoard, side: str) -> int:
    return sum(
        (KING_VALUE if c[1] else MAN_VALUE)
        for c in board.cells
        if c is not None and c[0] == side
    )


def net(board: CheckersBoard, root: str) -> int:
    other = "w" if root == "r" else "r"
    return material(board, root) - material(board, other)


def resolve_ref(board: CheckersBoard) -> tuple[int, str | None]:
    root = board.turn
    start = net(board, root)

    def best(node: CheckersBoard) -> tuple[int, str | None]:
        captures = [m for m in node.legal_moves() if m.is_jump]
        if not captures:
            moves = node.legal_moves()
            return net(node, root), (node.winner() if not moves else None)
        side = node.turn
        scored = [best(node.apply(m)) for m in captures]
        return (max if side == root else min)(scored, key=lambda r: r[0])

    end, terminal = best(board)
    return end - start, terminal


def main() -> None:
    board = CheckersBoard.from_fen("B:W24:B15")
    print(f"root legal moves: {[m.pdn() for m in board.legal_moves()]}")
    for pdn, mv in (
        ("15-19", CheckersMove(path=(15, 19), captured=())),
        ("15-18", CheckersMove(path=(15, 18), captured=())),
    ):
        legal = mv in board.legal_moves()
        after = board.apply(mv)
        swing, terminal = resolve_ref(after)
        # after.turn is White; swing is from White's perspective.
        print(
            f"  move {pdn}: legal={legal} after.turn={after.turn} "
            f"resolve-after swing(for {after.turn})={swing} terminal={terminal}"
        )

    print()
    own = CheckersBoard.from_fen("B:W16,24:B11")
    mv = own.legal_moves()[0]
    print(f"own_shot pos B:W16,24:B11 only move = {mv.pdn()} is_jump={mv.is_jump}")
    swing, terminal = resolve_ref(own)
    print(f"  resolve swing(for r) = {swing} terminal={terminal}")


if __name__ == "__main__":
    main()
