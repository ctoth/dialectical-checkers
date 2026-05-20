"""Tests for the strength-evaluation harness (``dialectical_checkers.strength_eval``).

Phase 7 directives (``notes/checkers-port-plan.md`` §8): the eval harness plays
the dialectical engine against the Phase 6 baselines over N games per matchup,
the engine taking BOTH colours in equal share, deterministic under a seed. The
tests confirm: a small eval run is reproducible under a seed; the tabulated
win/draw/loss counts sum to the games played; and the engine plays both colours
in equal share.
"""

from __future__ import annotations

import pytest

from dialectical_checkers.match import MinimaxPlayer, RandomPlayer
from dialectical_checkers.strength_eval import (
    MatchupResult,
    StrengthReport,
    evaluate_matchup,
    opening_pool,
    run_strength_eval,
)

# --- opening pool -----------------------------------------------------------


@pytest.mark.unit
def test_opening_pool_is_deterministic_under_seed() -> None:
    """The opening pool is a deterministic function of (count, seed)."""
    a = opening_pool(count=12, seed=7)
    b = opening_pool(count=12, seed=7)
    assert [p.to_fen() for p in a] == [p.to_fen() for p in b]


@pytest.mark.unit
def test_opening_pool_seeds_diverge() -> None:
    """Different seeds select different opening sets (not a constant pool)."""
    a = opening_pool(count=12, seed=1)
    b = opening_pool(count=12, seed=2)
    assert [p.to_fen() for p in a] != [p.to_fen() for p in b]


@pytest.mark.unit
def test_opening_pool_entries_are_distinct() -> None:
    """Every opening in the pool is a distinct position — no duplicate games."""
    pool = opening_pool(count=20, seed=3)
    fens = [p.to_fen() for p in pool]
    assert len(fens) == len(set(fens))
    assert len(fens) == 20


@pytest.mark.unit
def test_opening_pool_count_too_large_raises() -> None:
    """Requesting more openings than the pool can supply is an error."""
    with pytest.raises(ValueError):
        opening_pool(count=10_000, seed=0)


# --- matchup ----------------------------------------------------------------


@pytest.mark.unit
def test_matchup_counts_sum_to_games_played() -> None:
    """W + D + L always equals the number of games played in the matchup."""
    result = evaluate_matchup(
        opponent_factory=lambda: RandomPlayer(seed=0),
        opponent_name="random",
        games=8,
        seed=5,
    )
    assert result.wins + result.draws + result.losses == result.games
    assert result.games == 8


@pytest.mark.unit
def test_matchup_engine_plays_both_colours_equally() -> None:
    """The engine takes Red in exactly half the games and White in the other."""
    result = evaluate_matchup(
        opponent_factory=lambda: RandomPlayer(seed=0),
        opponent_name="random",
        games=8,
        seed=5,
    )
    assert result.engine_red_games == result.engine_white_games == 4


@pytest.mark.unit
def test_matchup_odd_game_count_raises() -> None:
    """An odd game count cannot split the two colours equally — reject it."""
    with pytest.raises(ValueError):
        evaluate_matchup(
            opponent_factory=lambda: RandomPlayer(seed=0),
            opponent_name="random",
            games=7,
            seed=0,
        )


@pytest.mark.property
def test_matchup_is_reproducible_under_seed() -> None:
    """The same seed yields byte-identical matchup results (W/D/L and games)."""
    a = evaluate_matchup(
        opponent_factory=lambda: MinimaxPlayer(depth=2),
        opponent_name="minimax:2",
        games=6,
        seed=11,
    )
    b = evaluate_matchup(
        opponent_factory=lambda: MinimaxPlayer(depth=2),
        opponent_name="minimax:2",
        games=6,
        seed=11,
    )
    assert (a.wins, a.draws, a.losses) == (b.wins, b.draws, b.losses)
    assert a.win_rate == b.win_rate


@pytest.mark.property
def test_matchup_different_seed_can_change_games() -> None:
    """A different seed selects a different opening pool, so games differ.

    The per-game outcomes must not be a constant independent of the seed —
    otherwise the eval would not actually sample anything. The exact W/D/L need
    not differ, but the played games (their ply counts) must.
    """
    a = evaluate_matchup(
        opponent_factory=lambda: MinimaxPlayer(depth=2),
        opponent_name="minimax:2",
        games=6,
        seed=1,
    )
    b = evaluate_matchup(
        opponent_factory=lambda: MinimaxPlayer(depth=2),
        opponent_name="minimax:2",
        games=6,
        seed=2,
    )
    plies_a = [g.ply_count for g in a.games_played]
    plies_b = [g.ply_count for g in b.games_played]
    assert plies_a != plies_b


# --- full report ------------------------------------------------------------


@pytest.mark.unit
def test_run_strength_eval_produces_one_result_per_matchup() -> None:
    """A full eval over K opponents yields K matchup results, all consistent."""
    report = run_strength_eval(
        games_per_matchup=4,
        seed=0,
        minimax_depths=(1, 2),
    )
    assert isinstance(report, StrengthReport)
    # random + 2 minimax depths == 3 matchups.
    assert len(report.matchups) == 3
    for matchup in report.matchups:
        assert isinstance(matchup, MatchupResult)
        assert matchup.wins + matchup.draws + matchup.losses == matchup.games


@pytest.mark.property
def test_run_strength_eval_is_reproducible() -> None:
    """The whole eval is a deterministic function of its seed."""
    a = run_strength_eval(games_per_matchup=4, seed=42, minimax_depths=(1, 2))
    b = run_strength_eval(games_per_matchup=4, seed=42, minimax_depths=(1, 2))
    for ma, mb in zip(a.matchups, b.matchups, strict=True):
        assert (ma.wins, ma.draws, ma.losses) == (mb.wins, mb.draws, mb.losses)
        assert ma.opponent_name == mb.opponent_name
