"""Tests for the ``dchk-match`` CLI (``dialectical_checkers.cli.match_cli``).

Phase 6 directive 4: the match CLI runs N games between two named players,
reports W/D/L, writes the games as PDN, and is deterministic under a seed.
"""

from __future__ import annotations

import pytest

from dialectical_checkers.cli.match_cli import build_player, main
from dialectical_checkers.match import EnginePlayer, MinimaxPlayer, RandomPlayer
from dialectical_checkers.pdn import parse_pdn


@pytest.mark.unit
def test_build_player_random() -> None:
    """``random`` builds a seeded RandomPlayer; roles use distinct seeds."""
    red = build_player("random", seed=5, role="red")
    white = build_player("random", seed=5, role="white")
    assert isinstance(red, RandomPlayer)
    assert isinstance(white, RandomPlayer)
    # Distinct names so the two are distinguishable in a PDN roster.
    assert red.name != white.name


@pytest.mark.unit
def test_build_player_minimax_with_depth() -> None:
    """``minimax:N`` builds a MinimaxPlayer of depth N."""
    player = build_player("minimax:4", seed=0, role="red")
    assert isinstance(player, MinimaxPlayer)
    assert player.depth == 4


@pytest.mark.unit
def test_build_player_engine() -> None:
    """``engine`` builds an EnginePlayer."""
    assert isinstance(build_player("engine", seed=0, role="red"), EnginePlayer)


@pytest.mark.unit
def test_build_player_unknown_raises() -> None:
    """An unknown player spec raises ``SystemExit``."""
    with pytest.raises(SystemExit):
        build_player("nonsense", seed=0, role="red")


@pytest.mark.unit
def test_cli_runs_random_match(capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI runs a random-vs-random match and prints a W/D/L summary."""
    code = main(
        ["--red", "random", "--white", "random", "-n", "2", "--seed", "1"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "over 2 game(s)" in out
    assert "game 1:" in out and "game 2:" in out


@pytest.mark.unit
def test_cli_is_deterministic_under_seed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The same ``--seed`` produces the same CLI output (deterministic)."""
    main(["--red", "random", "--white", "random", "-n", "2", "--seed", "3"])
    first = capsys.readouterr().out
    main(["--red", "random", "--white", "random", "-n", "2", "--seed", "3"])
    second = capsys.readouterr().out
    assert first == second


@pytest.mark.unit
def test_cli_writes_pdn_file(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--pdn`` writes the played games as parseable PDN."""
    pdn_path = tmp_path / "games.pdn"
    code = main(
        [
            "--red", "random", "--white", "random",
            "-n", "1", "--seed", "2", "--pdn", str(pdn_path),
        ]
    )
    assert code == 0
    assert pdn_path.exists()
    text = pdn_path.read_text(encoding="utf-8")
    game = parse_pdn(text)
    # The written game replays cleanly (every move legal).
    positions = game.positions()
    assert len(positions) == len(game.moves) + 1


@pytest.mark.unit
def test_cli_engine_vs_random(capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI runs an engine-vs-random game end to end."""
    code = main(["--red", "engine", "--white", "random", "-n", "1"])
    assert code == 0
    out = capsys.readouterr().out
    assert "game 1:" in out
