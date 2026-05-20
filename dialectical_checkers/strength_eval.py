"""Strength-evaluation harness — the dialectical engine vs the Phase 6 baselines.

``notes/checkers-port-plan.md`` §8 Phase 7: play the dialectical engine against
the verified Phase 6 baselines (:class:`RandomPlayer`, :class:`MinimaxPlayer` at
several depths) over N games per matchup, the engine taking BOTH colours in
equal share, deterministic under a seed, and tabulate win/draw/loss counts and
rates. The output is consumed by the honest, measured strength report.

This module is **evaluation TOOLING**. It does not change the engine's move
selection or any verified Phase 0-6 module — it only *runs* :func:`play_game`
from :mod:`dialectical_checkers.match` and counts outcomes. It imports only
``dialectical_checkers`` + the stdlib.

## Why opening diversification

:class:`EnginePlayer` and :class:`MinimaxPlayer` are **fully deterministic** —
neither holds an RNG. Two engine-vs-minimax games from the *same* start
position are therefore byte-identical; replaying the same matchup N times from
the standard start would yield N copies of one game and zero statistical
signal. So the harness builds an **opening pool**: a deterministic, seed-derived
set of distinct positions reached a few plies into the game. Each game in a
matchup starts from a distinct opening, so deterministic matchups still produce
N genuinely different games. The seed fixes the pool, so the whole eval is
reproducible — the same seed yields the same results (the Phase 7 gate).
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.match import (
    DRAW,
    RED_WIN,
    WHITE_WIN,
    EnginePlayer,
    GameResult,
    MinimaxPlayer,
    Player,
    RandomPlayer,
    play_game,
)

# --- opening pool -----------------------------------------------------------

#: Plies played from the standard start to reach an opening-pool position. Two
#: plies (one move each side) already yields 49 distinct positions — a pool
#: large enough for the eval — while keeping every opening a legal, balanced,
#: near-symmetric position rather than an artificial construction.
_OPENING_PLIES = 2


def _enumerate_openings(plies: int) -> list[CheckersBoard]:
    """Every distinct position reachable from the start in exactly ``plies``.

    A breadth-first expansion of the legal-move tree. Positions are
    de-duplicated by their ``(cells, turn)`` identity, so transpositions are
    collapsed. The returned list is sorted by PDN-FEN for a deterministic order
    independent of dict/set iteration.
    """
    frontier: list[CheckersBoard] = [CheckersBoard.initial()]
    for _ in range(plies):
        nxt: dict[tuple, CheckersBoard] = {}
        for board in frontier:
            for move in board.legal_moves():
                child = board.apply(move)
                nxt[(child.cells, child.turn)] = child
        frontier = list(nxt.values())
    unique: dict[str, CheckersBoard] = {}
    for board in frontier:
        unique[board.to_fen()] = board
    return [unique[fen] for fen in sorted(unique)]


def opening_pool(*, count: int, seed: int) -> tuple[CheckersBoard, ...]:
    """Return ``count`` distinct opening positions, selected deterministically.

    The full set of positions ``_OPENING_PLIES`` deep is enumerated, then
    ``count`` of them are sampled with a seeded RNG. The selection is a
    deterministic function of ``(count, seed)``: the same arguments always
    return the same openings, in the same order. Different seeds select
    different sets. Raises :class:`ValueError` if ``count`` exceeds the number
    of distinct openings available.
    """
    if count < 1:
        raise ValueError("opening_pool count must be >= 1")
    all_openings = _enumerate_openings(_OPENING_PLIES)
    if count > len(all_openings):
        raise ValueError(
            f"requested {count} openings but only {len(all_openings)} "
            f"distinct positions exist {_OPENING_PLIES} plies deep"
        )
    rng = random.Random(seed)
    return tuple(rng.sample(all_openings, count))


# --- per-matchup result -----------------------------------------------------


@dataclass(frozen=True)
class MatchupResult:
    """The measured outcome of one engine-vs-baseline matchup.

    Counts are from the **engine's** point of view: ``wins`` + ``draws`` +
    ``losses`` == ``games``. ``engine_red_games`` / ``engine_white_games`` are
    how many games the engine played each colour (the harness splits them
    equally). ``games_played`` holds every :class:`GameResult` for inspection
    (e.g. by the loss-mining diagnostic). ``conditions`` records the exact eval
    parameters for the report.
    """

    opponent_name: str
    games: int
    wins: int
    draws: int
    losses: int
    engine_red_games: int
    engine_white_games: int
    games_played: tuple[GameResult, ...] = field(default_factory=tuple)
    conditions: str = ""

    @property
    def win_rate(self) -> float:
        """Engine wins as a fraction of games played."""
        return self.wins / self.games if self.games else 0.0

    @property
    def draw_rate(self) -> float:
        """Draws as a fraction of games played."""
        return self.draws / self.games if self.games else 0.0

    @property
    def loss_rate(self) -> float:
        """Engine losses as a fraction of games played."""
        return self.losses / self.games if self.games else 0.0

    @property
    def score(self) -> float:
        """The engine's match score: a win = 1, a draw = 0.5, a loss = 0."""
        return (self.wins + 0.5 * self.draws) / self.games if self.games else 0.0

    def summary(self) -> str:
        """A one-line W/D/L summary from the engine's point of view."""
        return (
            f"engine vs {self.opponent_name}: "
            f"{self.wins}W-{self.draws}D-{self.losses}L "
            f"over {self.games} games "
            f"(win rate {self.win_rate:.1%}, score {self.score:.1%})"
        )


def _engine_outcome(result: GameResult, engine_is_red: bool) -> str:
    """Map a :class:`GameResult` to ``"win"`` / ``"draw"`` / ``"loss"``.

    ``result.outcome`` is from Red's seat; this translates it to the engine's
    seat given which colour the engine played in that game.
    """
    if result.outcome == DRAW:
        return "draw"
    engine_won = (result.outcome == RED_WIN) == engine_is_red
    return "win" if engine_won else "loss"


def evaluate_matchup(
    *,
    opponent_factory: Callable[[], Player],
    opponent_name: str,
    games: int,
    seed: int,
) -> MatchupResult:
    """Play ``games`` games of the engine against a baseline and tabulate W/D/L.

    ``opponent_factory`` is called fresh for every game (a new opponent object
    per game — a seeded :class:`RandomPlayer` thus replays identically, which
    keeps the matchup reproducible). The engine plays Red in the first half of
    the games and White in the second half — an exact, equal colour split, so
    ``games`` must be even. Each game starts from a distinct opening drawn from
    the deterministic, seed-derived :func:`opening_pool`, so the deterministic
    engine-vs-minimax matchups still produce ``games`` genuinely different
    games. The whole matchup is a deterministic function of ``seed``.

    Returns a :class:`MatchupResult` with counts from the engine's perspective.
    """
    if games < 2 or games % 2 != 0:
        raise ValueError(
            f"games must be an even number >= 2 to split the colours "
            f"equally; got {games}"
        )
    openings = opening_pool(count=games, seed=seed)
    half = games // 2

    wins = draws = losses = 0
    played: list[GameResult] = []
    for index, opening in enumerate(openings):
        engine_is_red = index < half
        engine = EnginePlayer()
        opponent = opponent_factory()
        if engine_is_red:
            red: Player = engine
            white: Player = opponent
        else:
            red = opponent
            white = engine
        result = play_game(red, white, start=opening)
        played.append(result)
        outcome = _engine_outcome(result, engine_is_red)
        if outcome == "win":
            wins += 1
        elif outcome == "draw":
            draws += 1
        else:
            losses += 1

    conditions = (
        f"{games} games, seed {seed}, openings {_OPENING_PLIES} plies deep, "
        f"engine plays Red in {half} and White in {half}"
    )
    return MatchupResult(
        opponent_name=opponent_name,
        games=games,
        wins=wins,
        draws=draws,
        losses=losses,
        engine_red_games=half,
        engine_white_games=half,
        games_played=tuple(played),
        conditions=conditions,
    )


# --- full strength report ---------------------------------------------------


@dataclass(frozen=True)
class StrengthReport:
    """The aggregate of every matchup in a strength evaluation.

    ``matchups`` holds one :class:`MatchupResult` per baseline opponent.
    ``seed`` and ``games_per_matchup`` record the exact run conditions so the
    written report can state them and the run can be reproduced.
    """

    matchups: tuple[MatchupResult, ...]
    seed: int
    games_per_matchup: int

    def summary_lines(self) -> list[str]:
        """One summary line per matchup, for printing or report assembly."""
        return [m.summary() for m in self.matchups]


def run_strength_eval(
    *,
    games_per_matchup: int,
    seed: int,
    minimax_depths: tuple[int, ...] = (1, 2, 4),
) -> StrengthReport:
    """Run the full strength evaluation: the engine vs every Phase 6 baseline.

    Plays ``games_per_matchup`` games against :class:`RandomPlayer` and against
    a :class:`MinimaxPlayer` at each depth in ``minimax_depths`` (at least two
    depths, per Phase 7). Every matchup is seeded off ``seed`` — a distinct
    per-matchup seed derived from it — so the whole evaluation is reproducible.

    Returns a :class:`StrengthReport` aggregating all matchups.
    """
    if not minimax_depths or len(minimax_depths) < 2:
        raise ValueError("Phase 7 requires at least two MinimaxPlayer depths")

    matchups: list[MatchupResult] = []

    # RandomPlayer — the weakest baseline. Each game gets a fresh seeded
    # RandomPlayer so the matchup is reproducible; the per-game seed is derived
    # from the run seed and the game index inside ``evaluate_matchup``'s pool.
    matchups.append(
        evaluate_matchup(
            opponent_factory=lambda: RandomPlayer(seed=seed),
            opponent_name="RandomPlayer",
            games=games_per_matchup,
            seed=seed,
        )
    )

    # MinimaxPlayer at each requested depth. A distinct matchup seed per depth
    # keeps the opening pools independent across depths.
    for offset, depth in enumerate(minimax_depths, start=1):
        matchups.append(
            evaluate_matchup(
                opponent_factory=lambda d=depth: MinimaxPlayer(depth=d),
                opponent_name=f"MinimaxPlayer(depth={depth})",
                games=games_per_matchup,
                seed=seed + offset,
            )
        )

    return StrengthReport(
        matchups=tuple(matchups),
        seed=seed,
        games_per_matchup=games_per_matchup,
    )
