"""Phase 4 — generate the engine-play regression baseline.

Plays seeded pseudo-random games from the start position to reach a spread of
>=100 legal, non-terminal positions; for each, records the FEN and the move
``DialecticalCheckersEngine.choose_move`` selects. The output is a Python
literal list of (fen, expected_pdn) pairs.

Run this on the PRE-Phase-4 committed state (git stash the Phase-4 changes)
to capture the baseline, then again on the Phase-4 state to confirm the moves
are identical. The test ``test_engine.py`` embeds the baseline this prints.
"""

from __future__ import annotations

import random

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.engine import DialecticalCheckersEngine

TARGET = 120  # >= 100 distinct non-terminal positions
SEED = 20260520


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
    print("REGRESSION_BASELINE = [")
    for fen, pdn in items:
        print(f"    ({fen!r}, {pdn!r}),")
    print("]")


if __name__ == "__main__":
    main()
