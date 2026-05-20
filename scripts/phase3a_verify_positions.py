"""Phase 3a — verify the curated witness positions before locking them in tests.

Standalone probe (no oneliners — every check is a file). For each candidate
position it prints, per legal move: the move PDN, whether it is a jump, the
child terminal status, the ``own_shot`` / ``opponent_shot`` results, the
``resolve`` of the child, and whether the move crowns a man. This lets the
expected FACT witnesses in tests/test_witnesses.py be hand-verified against the
real board and resolver rather than guessed.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard, RED_KING_ROW, WHITE_KING_ROW, _coord
from dialectical_checkers.captures import opponent_shot, own_shot, resolve

CANDIDATES: list[tuple[str, str]] = [
    ("free_winning_shot", "B:W18,26:B15"),
    ("win_material_two", "B:W16,24:B11"),
    ("crowning_simple_move", "B:W:BK6,7"),  # placeholder, refined below
    ("quiet_opening", "B:W21,22,23,24,25,26,27,28,29,30,31,32:"
                      "B1,2,3,4,5,6,7,8,9,10,11,12"),
]


def _crowns(board: CheckersBoard, move) -> bool:
    origin = move.origin - 1
    dest = move.destination - 1
    cell = board.cells[origin]
    if cell is None:
        return False
    _colour, is_king = cell
    if is_king:
        return False
    king_row = RED_KING_ROW if board.turn == "r" else WHITE_KING_ROW
    return _coord(dest)[0] == king_row


def describe(name: str, fen: str) -> None:
    print(f"=== {name}  {fen} ===")
    board = CheckersBoard.from_fen(fen)
    moves = board.legal_moves()
    print(f"  turn={board.turn}  legal_moves={len(moves)}")
    for move in moves:
        child = board.apply(move)
        child_terminal = child.is_terminal()
        child_winner = child.winner()
        own = own_shot(board, move)
        opp = opponent_shot(board, move)
        child_line = resolve(child)
        print(
            f"  move={move.pdn():<14} jump={move.is_jump!s:<5} "
            f"crowns={_crowns(board, move)!s:<5} "
            f"child_terminal={child_terminal!s:<5} winner={child_winner}"
        )
        print(
            f"      own_shot={own}  opponent_shot={opp}"
        )
        print(
            f"      resolve(child): swing={child_line.material_swing} "
            f"terminal={child_line.terminal} truncated={child_line.truncated} "
            f"tier={child_line.tier}"
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
