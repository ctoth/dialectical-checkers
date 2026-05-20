"""The ``dchk-eval`` CLI — measure the dialectical engine's strength (Phase 7).

A ``[project.scripts]`` entry point. Runs the strength evaluation — the
dialectical engine against the verified Phase 6 baselines (:class:`RandomPlayer`
and :class:`MinimaxPlayer` at several depths) over N games per matchup, the
engine taking both colours in equal share — tabulates win/draw/loss counts and
rates, and (with ``--mine-losses``) reports the loss-mining turning points of
the games the engine lost.

Deterministic under ``--seed``: the same seed reproduces the same evaluation
(the Phase 7 reproducibility gate). This module imports only
``dialectical_checkers`` + the stdlib.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from dialectical_checkers.loss_mining import mine_losses
from dialectical_checkers.strength_eval import (
    MatchupResult,
    StrengthReport,
    run_strength_eval,
)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dchk-eval",
        description=(
            "Measure the dialectical checkers engine's strength against the "
            "Phase 6 baselines."
        ),
    )
    parser.add_argument(
        "-n", "--games", type=int, default=24,
        help="games per matchup; must be even (default: 24)",
    )
    parser.add_argument(
        "--seed", type=int, default=0,
        help="evaluation seed; same seed => same results (default: 0)",
    )
    parser.add_argument(
        "--minimax-depths", default="1,2,4",
        help="comma-separated MinimaxPlayer depths, >=2 of them (default: 1,2,4)",
    )
    parser.add_argument(
        "--mine-losses", action="store_true",
        help="report loss-mining turning points for the engine's lost games",
    )
    return parser.parse_args(argv)


def _matchup_lines(matchup: MatchupResult) -> list[str]:
    """Render one matchup's measured result as report lines."""
    return [
        matchup.summary(),
        f"    conditions: {matchup.conditions}",
        f"    win {matchup.win_rate:.1%} / draw {matchup.draw_rate:.1%} / "
        f"loss {matchup.loss_rate:.1%}",
    ]


def _loss_mining_lines(report: StrengthReport) -> list[str]:
    """Render the loss-mining turning points across every matchup."""
    lines: list[str] = ["", "Loss mining (turning points of lost games):"]
    any_loss = False
    for matchup in report.matchups:
        half = matchup.engine_red_games
        pairs = [
            (game, index < half)
            for index, game in enumerate(matchup.games_played)
        ]
        points = mine_losses(pairs)
        lost = matchup.losses
        if lost == 0:
            lines.append(f"  vs {matchup.opponent_name}: no losses")
            continue
        any_loss = True
        lines.append(
            f"  vs {matchup.opponent_name}: {lost} loss(es), "
            f"{len(points)} with a resolvable turning point"
        )
        for point in points:
            lines.append(f"    {point.describe()}")
        if len(points) < lost:
            lines.append(
                f"    ({lost - len(points)} loss(es) had no capture-resolvable "
                f"turning point — attrition, not a single blunder)"
            )
    if not any_loss:
        lines.append("  the engine lost no games in this evaluation")
    return lines


def format_report(report: StrengthReport, *, mine: bool) -> str:
    """Assemble the full textual strength report from a :class:`StrengthReport`."""
    lines: list[str] = [
        "Dialectical checkers — strength evaluation",
        f"seed {report.seed}, {report.games_per_matchup} games per matchup",
        "",
    ]
    for matchup in report.matchups:
        lines.extend(_matchup_lines(matchup))
    if mine:
        lines.extend(_loss_mining_lines(report))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``dchk-eval`` console script.

    Returns a process exit code: ``0`` on a completed evaluation.
    """
    args = _parse_args(argv)
    try:
        depths = tuple(
            int(tok) for tok in args.minimax_depths.split(",") if tok.strip()
        )
    except ValueError:
        raise SystemExit(
            f"bad --minimax-depths {args.minimax_depths!r}: expected integers"
        ) from None
    if len(depths) < 2:
        raise SystemExit("--minimax-depths needs at least two depths")

    report = run_strength_eval(
        games_per_matchup=args.games,
        seed=args.seed,
        minimax_depths=depths,
    )
    print(format_report(report, mine=args.mine_losses))
    return 0


if __name__ == "__main__":  # pragma: no cover - module-as-script entry
    sys.exit(main())
