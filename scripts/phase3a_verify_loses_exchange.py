"""Phase 3a — find a loses_exchange position.

A loses_exchange move is a CAPTURE (jump) the mover is forced/able to play that,
across the full resolved forced line, nets the mover a material LOSS.

mover_swing = (move's immediate capture gain, mover view)
              - resolve(child).material_swing   # child swing is opponent view

This script prints, per legal move, that computed mover_swing so a genuine
net-loss capture can be hand-picked for the test.
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
    # Red is forced to capture but the recapture sequence costs Red more.
    ("forced_bad_capture_a", "B:W14,22,23:B10,18"),
    ("forced_bad_capture_b", "B:W7,15,24:B11"),
    ("forced_bad_capture_c", "B:W6,14,22,30:B9"),
    ("forced_bad_capture_d", "B:W15,23,24,32:B19"),
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
        print(
            f"  move={move.pdn():<14} jump={move.is_jump!s:<5} "
            f"immediate_gain={immediate_gain:<5} "
            f"resolve(child).swing={child_line.material_swing:<5} "
            f"=> mover_swing={mover_swing} "
            f"terminal={child_line.terminal} truncated={child_line.truncated}"
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
