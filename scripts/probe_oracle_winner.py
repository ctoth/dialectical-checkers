"""Probe pydraughts' ``winner`` value at a terminal position.

Run: ``uv run python scripts/probe_oracle_winner.py``

Replays the resolver's claimed line for ``W:W13,14,21:B1,9`` and prints
``oracle.winner`` so the cross-check can map it to the engine's "r"/"w".
pydraughts side mapping (per scout report): pydraughts WHITE == engine white,
pydraughts BLACK == engine red. Confirm what ``winner`` returns.
"""

from __future__ import annotations

from draughts import Board as OracleBoard

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import resolve


def replay_and_report(fen: str) -> None:
    board = CheckersBoard.from_fen(fen)
    line = resolve(board)
    oracle = OracleBoard(variant="english", fen=board.to_fen())
    for mv in line.principal_line:
        idx = {
            ("x" if m.has_captures else "-").join(
                str(s) for s in m.steps_move
            ): m
            for m in oracle.legal_moves()
        }
        oracle.push(idx[mv.pdn()])
    print(f"{fen}")
    print(f"  engine terminal={line.terminal!r}")
    print(f"  oracle.is_over()={oracle.is_over()}")
    print(f"  oracle.winner()={oracle.winner()!r}")
    print(f"  oracle final FEN={oracle.fen}")
    print()


def main() -> None:
    replay_and_report("W:W13,14,21:B1,9")
    # A Red terminal win for the symmetric case.
    replay_and_report("B:W18:B15")


if __name__ == "__main__":
    main()
