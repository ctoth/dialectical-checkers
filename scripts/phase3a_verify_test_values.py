"""Phase 3a — confirm the exact expected values asserted in test_witnesses.py.

Prints opponent_shot / own_shot / child-opponent-captures for the specific
moves the curated tests assert on, so the asserted magnitudes are verified
against the real resolver rather than guessed.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import opponent_shot, own_shot

CHECKS: list[tuple[str, str, str]] = [
    ("loses_exchange 13x22", "B:W10,17,18:B6,13,14", "13x22"),
    ("even trade 2x11", "B:W7,23:B2,18", "2x11"),
    ("terminal loss 13-17", "B:W22,30:B9,13", "13-17"),
    ("allows shot 13-17", "B:W22,30:B6,9,13,14", "13-17"),
]


def main() -> None:
    for name, fen, pdn in CHECKS:
        board = CheckersBoard.from_fen(fen)
        move = next(m for m in board.legal_moves() if m.pdn() == pdn)
        child = board.apply(move)
        child_opp_captures = any(m.is_jump for m in child.legal_moves())
        print(f"=== {name}  ({fen}  move {pdn}) ===")
        print(f"  own_shot      = {own_shot(board, move)}")
        print(f"  opponent_shot = {opponent_shot(board, move)}")
        print(f"  child has opponent captures = {child_opp_captures}")
        print()


if __name__ == "__main__":
    main()
