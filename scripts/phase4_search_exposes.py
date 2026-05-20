"""Phase 4 — systematically search for an obj:exposes_man position.

obj:exposes_man fires iff: a move M, after which the opponent has a capture,
but opponent_shot(board,M) is None or non-FACT (loss not proven). Enumerate
small random-ish man positions and report the first few that fire it.
"""

from __future__ import annotations

import itertools

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.witnesses import probe_moves


def fires_exposes(fen: str) -> list[str]:
    board = CheckersBoard.from_fen(fen)
    hits = []
    for probe in probe_moves(board):
        if "obj:exposes_man" in probe.objections:
            hits.append(probe.pdn)
    return hits


def main() -> None:
    # Enumerate 2 Red men + 2 White men, Red to move, all men (no kings),
    # placed in the central rows so captures are possible. Limited search.
    central = list(range(6, 28))
    found = 0
    for combo in itertools.combinations(central, 4):
        r1, r2, w1, w2 = combo
        # assign two to Red, two to White — try one assignment
        fen = f"B:W{w1},{w2}:B{r1},{r2}"
        try:
            board = CheckersBoard.from_fen(fen)
        except ValueError:
            continue
        # skip if Red already has a capture (we want quiet positions too)
        hits = fires_exposes(fen)
        if hits:
            print(f"{fen}  -> exposes on {hits}")
            found += 1
            if found >= 8:
                break


if __name__ == "__main__":
    main()
