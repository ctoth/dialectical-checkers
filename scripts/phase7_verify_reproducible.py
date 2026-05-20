"""Phase 7 — verify the strength eval is reproducible: same seed, same result.

Runs run_strength_eval twice with the same seed and asserts the formatted
reports are byte-identical (the Phase 7 reproducibility gate). No oneliners.
"""

from __future__ import annotations

from dialectical_checkers.cli.eval_cli import format_report
from dialectical_checkers.strength_eval import run_strength_eval


def main() -> None:
    a = run_strength_eval(games_per_matchup=12, seed=0, minimax_depths=(1, 2))
    b = run_strength_eval(games_per_matchup=12, seed=0, minimax_depths=(1, 2))
    ra = format_report(a, mine=True)
    rb = format_report(b, mine=True)
    print(f"two seed-0 runs byte-identical: {ra == rb}")
    if ra != rb:
        raise SystemExit("NOT reproducible")


if __name__ == "__main__":
    main()
