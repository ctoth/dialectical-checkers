"""Phase 7 — search for a clean one-move-blunder fixture for loss-mining tests.

Need a position where the side to move has NO mandatory capture, has at least
one quiet move that hands the opponent a forced capture (opponent_shot fires),
and ALSO has at least one quiet move that does not — so a non-losing move
existed and the blunder is a genuine turning point. Brute-force small positions.
Measurement script, no oneliners.
"""

from __future__ import annotations

from itertools import combinations

from dialectical_checkers.board import NUM_SQUARES, Cell, CheckersBoard
from dialectical_checkers.captures import opponent_shot


def _board(red_men: tuple[int, ...], white_men: tuple[int, ...], turn: str):
    cells: list[Cell | None] = [None] * NUM_SQUARES
    for sq in red_men:
        cells[sq - 1] = ("r", False)
    for sq in white_men:
        cells[sq - 1] = ("w", False)
    from dataclasses import replace

    board = CheckersBoard(cells=tuple(cells), turn=turn, no_progress=0,
                          history=())
    return replace(board, history=(board._position_id(),))


def main() -> None:
    found = 0
    # Red man somewhere in the middle rows, White man nearby. Small search.
    for red_sq in range(9, 25):
        for white_sq in range(9, 25):
            if red_sq == white_sq:
                continue
            board = _board((red_sq,), (white_sq,), "r")
            legal = board.legal_moves()
            if any(m.is_jump for m in legal):
                continue  # need a quiet position
            if len(legal) < 2:
                continue  # need a safe alternative to exist
            blunders = []
            safes = []
            for move in legal:
                if move_concedes(board, move):
                    blunders.append(move.pdn())
                else:
                    safes.append(move.pdn())
            if blunders and safes:
                found += 1
                print(
                    f"R{red_sq} W{white_sq} turn r: "
                    f"fen={board.to_fen()} blunder={blunders} safe={safes}"
                )
                if found >= 6:
                    return
    if not found:
        print("no two-piece blunder fixture found in the search range")


def move_concedes(board: CheckersBoard, move) -> bool:
    shot = opponent_shot(board, move)
    return shot is not None and (shot.material_net > 0 or shot.terminal
                                 == board.apply(move).turn)


if __name__ == "__main__":
    main()
