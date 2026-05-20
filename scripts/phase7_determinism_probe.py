"""Phase 7 determinism probe — confirm the deterministic-matchup concern.

EnginePlayer and MinimaxPlayer have no RNG. Two engine-vs-minimax games from
the SAME start position must therefore be byte-identical — so N repeated games
of a deterministic matchup give zero extra signal. This script proves that, and
checks how many distinct legal opening plies the start position offers (the
basis for an opening-diversified game set). Measurement script, no oneliners.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.match import (
    EnginePlayer,
    MinimaxPlayer,
    play_game,
)


def main() -> None:
    g1 = play_game(EnginePlayer(), MinimaxPlayer(depth=3))
    g2 = play_game(EnginePlayer(), MinimaxPlayer(depth=3))
    identical = g1.moves == g2.moves and g1.outcome == g2.outcome
    print(f"two engine-vs-minimax3 games identical: {identical}")
    print(f"  game1: {g1.outcome}, {g1.ply_count} plies")
    print(f"  game2: {g2.outcome}, {g2.ply_count} plies")

    start = CheckersBoard.initial()
    opening = start.legal_moves()
    print(f"distinct opening plies from start: {len(opening)}")

    # Number of distinct positions after two plies (a varied opening pool).
    after_two: set[tuple] = set()
    for m1 in start.legal_moves():
        b1 = start.apply(m1)
        for m2 in b1.legal_moves():
            b2 = b1.apply(m2)
            after_two.add((b2.cells, b2.turn))
    print(f"distinct positions after 2 plies: {len(after_two)}")


if __name__ == "__main__":
    main()
