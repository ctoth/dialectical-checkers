"""Phase 7 — run the actual strength evaluation and print timed results.

Runs the full strength evaluation at a chosen game count and seed, prints the
measured W/D/L per matchup, the loss-mining turning points, and the wall-clock
time of each matchup, so the strength report can quote real measured numbers
and honest timing. Measurement script (port-plan §8, no oneliners).
"""

from __future__ import annotations

import sys
import time

from dialectical_checkers.cli.eval_cli import format_report
from dialectical_checkers.strength_eval import evaluate_matchup, run_strength_eval
from dialectical_checkers.match import MinimaxPlayer, RandomPlayer


def main() -> None:
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    depths = (1, 2, 4)

    print(f"=== strength eval: {games} games/matchup, seed {seed}, "
          f"minimax depths {depths} ===")
    total_start = time.perf_counter()

    # Time each matchup individually for honest per-matchup timing.
    t0 = time.perf_counter()
    rnd = evaluate_matchup(
        opponent_factory=lambda: RandomPlayer(seed=seed),
        opponent_name="RandomPlayer", games=games, seed=seed)
    print(f"[{time.perf_counter()-t0:.2f}s] {rnd.summary()}")

    for off, d in enumerate(depths, start=1):
        t0 = time.perf_counter()
        mm = evaluate_matchup(
            opponent_factory=lambda d=d: MinimaxPlayer(depth=d),
            opponent_name=f"MinimaxPlayer(depth={d})",
            games=games, seed=seed + off)
        print(f"[{time.perf_counter()-t0:.2f}s] {mm.summary()}")

    total = time.perf_counter() - total_start
    print(f"=== total wall time: {total:.2f}s ===")

    # Full report via the run_strength_eval path (the reproducible one).
    report = run_strength_eval(
        games_per_matchup=games, seed=seed, minimax_depths=depths)
    print()
    print(format_report(report, mine=True))


if __name__ == "__main__":
    main()
