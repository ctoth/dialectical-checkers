"""The ``dchk-match`` CLI — run N games between two named players (Phase 6).

A ``[project.scripts]`` entry point. Runs a self-play match between two named
players, reports the Red/White/draw tally, and optionally writes the games to a
PDN file. Deterministic under ``--seed``: the same seed reproduces the same
games (the only non-determinism the harness has is :class:`RandomPlayer`'s RNG,
which the seed fixes).

Player names (``--red`` / ``--white``):

* ``random`` — :class:`RandomPlayer`, seeded.
* ``minimax`` / ``minimax:N`` — :class:`MinimaxPlayer` of depth ``N`` (default 3).
* ``engine`` — :class:`EnginePlayer`, the dialectical engine.

This module imports only ``dialectical_checkers`` + the stdlib.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.match import (
    EnginePlayer,
    MinimaxPlayer,
    Player,
    RandomPlayer,
    play_match,
)
from dialectical_checkers.pdn import render_pdn

_DEFAULT_MINIMAX_DEPTH = 3


def build_player(spec: str, *, seed: int, role: str) -> Player:
    """Construct a :class:`Player` from a CLI player spec.

    ``spec`` is ``random``, ``minimax``/``minimax:N``, or ``engine``. ``role``
    (``"red"`` / ``"white"``) makes the two ``random`` players use distinct
    seeds, so a ``random vs random`` match is not mirror-symmetric.
    """
    spec = spec.strip().lower()
    if spec == "random":
        # Offset White's seed so the two RandomPlayers diverge yet the whole
        # match stays a deterministic function of ``--seed``.
        offset = 0 if role == "red" else 1
        return RandomPlayer(seed=seed + offset, name=f"random[{role}]")
    if spec == "minimax" or spec.startswith("minimax:"):
        depth = _DEFAULT_MINIMAX_DEPTH
        if ":" in spec:
            _, _, depth_text = spec.partition(":")
            try:
                depth = int(depth_text)
            except ValueError:
                raise SystemExit(
                    f"bad minimax depth in player spec {spec!r}"
                ) from None
        return MinimaxPlayer(depth=depth)
    if spec == "engine":
        return EnginePlayer()
    raise SystemExit(
        f"unknown player {spec!r}: expected random, minimax[:N], or engine"
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dchk-match",
        description="Run a self-play match between two checkers players.",
    )
    parser.add_argument(
        "--red", default="engine",
        help="Red player: random | minimax[:N] | engine (default: engine)",
    )
    parser.add_argument(
        "--white", default="random",
        help="White player: random | minimax[:N] | engine (default: random)",
    )
    parser.add_argument(
        "-n", "--games", type=int, default=1,
        help="number of games to play (default: 1)",
    )
    parser.add_argument(
        "--seed", type=int, default=0,
        help="RNG seed for RandomPlayer; same seed => same games (default: 0)",
    )
    parser.add_argument(
        "--start-fen", default=None,
        help="optional PDN-FEN start position (default: standard start)",
    )
    parser.add_argument(
        "--pdn", default=None,
        help="write the played games to this PDN file",
    )
    parser.add_argument(
        "--ply-cap", type=int, default=2000,
        help="hard ply safety cap per game (default: 2000)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``dchk-match`` console script.

    Returns a process exit code: ``0`` on a completed match.
    """
    args = _parse_args(argv)

    red = build_player(args.red, seed=args.seed, role="red")
    white = build_player(args.white, seed=args.seed, role="white")
    start = (
        CheckersBoard.from_fen(args.start_fen)
        if args.start_fen is not None
        else None
    )

    report = play_match(
        red, white,
        games=args.games,
        start=start,
        ply_cap=args.ply_cap,
    )

    print(report.summary(red.name, white.name))
    for index, result in enumerate(report.results, start=1):
        print(
            f"  game {index}: {result.outcome} "
            f"({result.reason}, {result.ply_count} plies)"
        )

    if args.pdn is not None:
        chunks: list[str] = []
        for result in report.results:
            game = result.to_pdn_game(
                setup_fen=args.start_fen,
            )
            chunks.append(render_pdn(game))
        with open(args.pdn, "w", encoding="utf-8") as handle:
            handle.write("\n".join(chunks))
        print(f"wrote {len(report.results)} game(s) to {args.pdn}")

    return 0


if __name__ == "__main__":  # pragma: no cover - module-as-script entry
    sys.exit(main())
