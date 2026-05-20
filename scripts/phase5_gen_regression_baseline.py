"""Phase 5 — regenerate the engine-play regression baseline.

Identical seeded sampling to ``phase4_gen_regression_baseline.py`` (SEED,
TARGET, walk shape) so the FEN sample is the SAME 120 positions — only the
recorded move differs, because the Phase-5 graded Categoriser layer changes
engine PLAY in quiet positions (design §7). The output is the Python literal
``REGRESSION_BASELINE`` list embedded by ``tests/test_phase5_regression.py``.

Run on the committed Phase-5 state; the test replays it and asserts the
engine reproduces each move (engine determinism + a frozen Phase-5 snapshot).
"""

from __future__ import annotations

import random

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.engine import DialecticalCheckersEngine

TARGET = 120  # >= 100 distinct non-terminal positions — same as Phase 4
SEED = 20260520  # same seed as Phase 4 -> the same FEN sample


def main() -> None:
    rng = random.Random(SEED)
    engine = DialecticalCheckersEngine()
    seen: dict[str, str] = {}
    games = 0
    while len(seen) < TARGET and games < 2000:
        games += 1
        board = CheckersBoard.initial()
        for _ply in range(60):
            if board.is_terminal() or board.is_draw():
                break
            fen = board.to_fen()
            if fen not in seen:
                decision = engine.choose_move(board)
                if decision.selected is None:
                    break
                seen[fen] = decision.move_pdn
            moves = board.legal_moves()
            board = board.apply(rng.choice(moves))
    items = sorted(seen.items())[:TARGET]
    print(f"# {len(items)} seeded positions (SEED={SEED})")
    print("REGRESSION_BASELINE: list[tuple[str, str]] = [")
    for fen, pdn in items:
        print(f"    ({fen!r}, {pdn!r}),")
    print("]")


if __name__ == "__main__":
    main()
