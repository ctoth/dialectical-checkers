"""Phase 7 loss-mining fixture probe — validate the constructed test positions.

The loss-mining tests rely on a few hand-built positions whose forced outcome
must be exactly known. This script prints the legal moves, the result of
playing the scripted line, and the captures.resolve / opponent_shot readings,
so the test fixtures are confirmed against runtime behaviour, not assumed.
Measurement script (port-plan §8, no oneliners).
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import opponent_shot, resolve


def _show(fen: str) -> None:
    board = CheckersBoard.from_fen(fen)
    print(f"--- {fen} (turn {board.turn}) ---")
    legal = board.legal_moves()
    print(f"  legal: {[m.pdn() for m in legal]}")
    for move in legal:
        shot = opponent_shot(board, move)
        after = board.apply(move)
        line = resolve(after)
        print(
            f"  {move.pdn():>8}: opponent_shot={shot} "
            f"after.turn={after.turn} resolve.swing={line.material_swing} "
            f"terminal={line.terminal}"
        )


def main() -> None:
    _show("B:W22:B18")
    _show("W:W15:B11")
    _show("B:W32:B1")

    # Play the scripted blunder line and report the final outcome.
    start = CheckersBoard.from_fen("B:W22:B18")
    b = start
    for pdn in ["18-23", "22x15"]:
        move = next(m for m in b.legal_moves() if m.pdn() == pdn)
        b = b.apply(move)
    print(f"after 18-23, 22x15: fen={b.to_fen()} turn={b.turn} "
          f"terminal={b.is_terminal()} winner={b.winner()}")


if __name__ == "__main__":
    main()
