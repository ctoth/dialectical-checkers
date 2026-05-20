"""Phase 3a — third pass: an allows_shot position (material, NOT terminal).

Find a Red quiet move that lets White force a material gain while Red survives,
so opponent_shot returns terminal=None. Also probe a two-different-captures
position so a single-man-capture (pro:material:1) can sit beside another move.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import opponent_shot, own_shot, resolve

CANDIDATES: list[tuple[str, str]] = [
    # Red has extra material so a White forced capture nets White a man but
    # leaves Red with pieces (non-terminal shot).
    ("allows_material_shot_a", "B:W22,30:B6,9,13,14"),
    ("allows_material_shot_b", "B:W18,22:B9,13,25,29"),
    # Two distinct single captures available to Red (a 2-move capture set).
    ("two_single_captures", "B:W7,23:B2,18"),
]


def describe(name: str, fen: str) -> None:
    print(f"=== {name}  {fen} ===")
    board = CheckersBoard.from_fen(fen)
    moves = board.legal_moves()
    print(f"  turn={board.turn}  legal_moves={len(moves)}")
    for move in moves:
        child = board.apply(move)
        own = own_shot(board, move)
        opp = opponent_shot(board, move)
        child_line = resolve(child)
        print(
            f"  move={move.pdn():<14} jump={move.is_jump!s:<5} "
            f"child_terminal={child.is_terminal()!s:<5} winner={child.winner()}"
        )
        print(f"      own_shot={own}")
        print(f"      opponent_shot={opp}")
        print(
            f"      resolve(child): swing={child_line.material_swing} "
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
