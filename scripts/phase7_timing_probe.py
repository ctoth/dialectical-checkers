"""Phase 7 timing probe — measure per-game wall time for each matchup.

Runs ONE game of each engine-vs-baseline matchup and prints the wall-clock
time and ply count, so the strength-eval game counts can be chosen to fit the
runtime budget. Not a test; a measurement script (port-plan §8, no oneliners).
"""

from __future__ import annotations

import time

from dialectical_checkers.match import (
    EnginePlayer,
    MinimaxPlayer,
    RandomPlayer,
    play_game,
)


def _time_game(red, white, label: str) -> None:
    start = time.perf_counter()
    result = play_game(red, white)
    elapsed = time.perf_counter() - start
    print(
        f"{label}: {result.outcome} ({result.reason}, "
        f"{result.ply_count} plies) in {elapsed:.2f}s"
    )


def main() -> None:
    _time_game(EnginePlayer(), RandomPlayer(seed=1), "engine(R) vs random(W)")
    _time_game(RandomPlayer(seed=1), EnginePlayer(), "random(R) vs engine(W)")
    _time_game(
        EnginePlayer(), MinimaxPlayer(depth=2), "engine(R) vs minimax2(W)"
    )
    _time_game(
        EnginePlayer(), MinimaxPlayer(depth=4), "engine(R) vs minimax4(W)"
    )


if __name__ == "__main__":
    main()
