"""Phase 7 — verify the strength eval is reproducible: same seed, same result.

Runs the FULL reported strength evaluation — 48 games per matchup, seed 0,
MinimaxPlayer depths (1, 2, 4), loss mining included — twice, and asserts the
formatted reports are byte-identical (the Phase 7 reproducibility gate). This
covers exactly the run the strength report publishes, so the report's
"byte-identical results" claim is verified against the whole evaluation, not a
slice. No oneliners.
"""

from __future__ import annotations

from dialectical_checkers.cli.eval_cli import format_report
from dialectical_checkers.strength_eval import run_strength_eval


def main() -> None:
    a = run_strength_eval(games_per_matchup=48, seed=0, minimax_depths=(1, 2, 4))
    b = run_strength_eval(games_per_matchup=48, seed=0, minimax_depths=(1, 2, 4))
    ra = format_report(a, mine=True)
    rb = format_report(b, mine=True)
    print(f"two seed-0 runs byte-identical: {ra == rb}")
    if ra != rb:
        raise SystemExit("NOT reproducible")


if __name__ == "__main__":
    main()
