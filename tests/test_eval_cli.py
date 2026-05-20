"""Tests for the ``dchk-eval`` CLI (``dialectical_checkers.cli.eval_cli``).

Phase 7 directive: the eval CLI runs the strength evaluation against the
Phase 6 baselines, reports W/D/L, is deterministic under a seed, and can
report loss-mining turning points. The tests confirm a small run completes,
the printed report names every matchup, and the same seed reproduces the same
output.
"""

from __future__ import annotations

import pytest

from dialectical_checkers.cli.eval_cli import format_report, main
from dialectical_checkers.strength_eval import run_strength_eval


@pytest.mark.unit
def test_main_runs_and_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """A small eval run completes and prints a report naming every matchup."""
    code = main(["-n", "4", "--seed", "0", "--minimax-depths", "1,2"])
    assert code == 0
    out = capsys.readouterr().out
    assert "strength evaluation" in out
    assert "RandomPlayer" in out
    assert "MinimaxPlayer(depth=1)" in out
    assert "MinimaxPlayer(depth=2)" in out


@pytest.mark.unit
def test_main_rejects_single_minimax_depth() -> None:
    """Phase 7 requires at least two minimax depths — one depth is rejected."""
    with pytest.raises(SystemExit):
        main(["-n", "4", "--minimax-depths", "2"])


@pytest.mark.property
def test_report_is_reproducible_under_seed() -> None:
    """The formatted report is a deterministic function of the seed."""
    a = run_strength_eval(games_per_matchup=4, seed=9, minimax_depths=(1, 2))
    b = run_strength_eval(games_per_matchup=4, seed=9, minimax_depths=(1, 2))
    assert format_report(a, mine=True) == format_report(b, mine=True)


@pytest.mark.unit
def test_mine_losses_flag_adds_loss_mining_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--mine-losses`` adds the loss-mining section to the printed report."""
    code = main(
        ["-n", "4", "--seed", "0", "--minimax-depths", "1,2", "--mine-losses"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Loss mining" in out
