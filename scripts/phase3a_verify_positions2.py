"""Phase 3a — second pass: refine crowning / allows_shot / terminal_loss FENs.

Same probe shape as phase3a_verify_positions.py. Used to hand-verify the
remaining curated witness positions: a non-terminal crowning move, a quiet move
that allows the opponent a forced shot, and a move that loses the game on the
spot by force.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard, RED_KING_ROW, WHITE_KING_ROW, _coord
from dialectical_checkers.captures import opponent_shot, own_shot, resolve

CANDIDATES: list[tuple[str, str]] = [
    # Red man on 27 with White man on 21 far away. Red 27-31 / 27-32 step onto
    # king-row (29-32) and crown. White still has a piece -> child not terminal.
    ("crowning_nonterminal", "B:W21:B27"),
    # Red to move, a quiet move that exposes a man to a White forced jump.
    # Red men on 9 and 14; White man on 22, White man on 30. If Red plays a
    # quiet move leaving a man jumpable by White.
    ("allows_shot_candidate_a", "W:W23:B18,27"),
    # Red to move with one quiet move that walks into a White capture.
    ("allows_shot_candidate_b", "B:W22,30:B9,13"),
    # terminal-loss candidate: Red forced/quiet move after which White has a
    # forced sequence ending the game.
    ("terminal_loss_candidate", "B:W22:B18,26"),
]


def _crowns(board: CheckersBoard, move) -> bool:
    origin = move.origin - 1
    dest = move.destination - 1
    cell = board.cells[origin]
    if cell is None or cell[1]:
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
        own = own_shot(board, move)
        opp = opponent_shot(board, move)
        child_line = resolve(child)
        print(
            f"  move={move.pdn():<14} jump={move.is_jump!s:<5} "
            f"crowns={_crowns(board, move)!s:<5} "
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
