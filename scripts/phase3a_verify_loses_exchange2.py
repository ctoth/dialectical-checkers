"""Phase 3a — find a loses_exchange position (second pass).

Want: a Red CAPTURE move, non-terminal, where after Red's capture White is
forced into a multi-jump capturing MORE than Red took -> mover_swing < 0.

Construct: Red captures one White man; the landing square sets up a White man
to double-jump two Red men.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import KING_VALUE, MAN_VALUE, resolve


def _material(board: CheckersBoard, side: str) -> int:
    total = 0
    for cell in board.cells:
        if cell is None or cell[0] != side:
            continue
        total += KING_VALUE if cell[1] else MAN_VALUE
    return total


def _net(board: CheckersBoard, side: str) -> int:
    other = "w" if side == "r" else "r"
    return _material(board, side) - _material(board, other)


CANDIDATES: list[tuple[str, str]] = [
    # Red man 22 takes White 25 -> lands 29. White man 30 then takes Red...
    ("a", "B:W18,25,26:B14,21,22"),
    ("b", "B:W11,19,27:B6,15,16"),
    ("c", "B:W19,26,27:B15,22,23"),
    ("d", "B:W10,17,18:B6,13,14"),
    ("e", "B:W14,21,22:B9,17,18"),
    ("f", "B:W7,14,15:B2,10,11"),
]


def describe(name: str, fen: str) -> None:
    print(f"=== {name}  {fen} ===")
    board = CheckersBoard.from_fen(fen)
    mover = board.turn
    before = _net(board, mover)
    moves = board.legal_moves()
    print(f"  turn={mover}  legal_moves={len(moves)}")
    for move in moves:
        child = board.apply(move)
        immediate_gain = _net(child, mover) - before
        child_line = resolve(child)
        mover_swing = immediate_gain - child_line.material_swing
        flag = "  <-- LOSES EXCHANGE" if (
            move.is_jump and mover_swing < 0 and child_line.terminal is None
        ) else ""
        print(
            f"  move={move.pdn():<14} jump={move.is_jump!s:<5} "
            f"imm={immediate_gain:<5} child.swing={child_line.material_swing:<5} "
            f"mover_swing={mover_swing:<6} terminal={child_line.terminal}"
            f"{flag}"
        )


def main() -> None:
    for name, fen in CANDIDATES:
        try:
            describe(name, fen)
        except Exception as exc:  # noqa: BLE001 — probe script
            print(f"  ERROR for {name}: {exc!r}")
        print()


if __name__ == "__main__":
    main()
