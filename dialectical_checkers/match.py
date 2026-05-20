"""Self-play match runner and baseline opponents (Phase 6 harness).

``notes/checkers-port-plan.md`` §8 Phase 6: a self-play match runner over the
**verified** ``board.py`` substrate. ``play_game`` plays one full game from the
start position (or a given PDN-FEN), alternating two pluggable players, and
enforces every WCDF terminal / draw rule via ``board.py`` — terminal detection
(no legal move = loss, WCDF 1.30), threefold repetition (WCDF 1.32.1) and the
40-move/80-ply no-progress rule (WCDF 1.32.2).

This module is TOOLING — it does not change the engine's move selection or any
verified Phase 0-5 module. It imports only ``dialectical_checkers`` + the
stdlib (port-plan §8 — pydraughts is a test dependency only).

A player is anything with ``choose(board) -> CheckersMove`` returning a legal
move for the side to move. Three baselines ship here: :class:`RandomPlayer`
(seeded, deterministic), :class:`MinimaxPlayer` (fixed-depth material minimax
over ``search.static_evaluation``) and :class:`EnginePlayer` (the dialectical
engine itself as a player).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.engine import DialecticalCheckersEngine, EngineSettings
from dialectical_checkers.pdn import (
    RESULT_DRAW,
    RESULT_RED_WIN,
    RESULT_UNTERMINATED,
    RESULT_WHITE_WIN,
    PdnGame,
)
from dialectical_checkers.search import static_evaluation

# --- Outcomes ---------------------------------------------------------------

#: Match outcome from Red's point of view.
RED_WIN = "red"
WHITE_WIN = "white"
DRAW = "draw"

#: A safety-net ply cap. A game that neither terminates nor draws within this
#: many plies is a *bug* in the rule enforcement (the WCDF draw rules must fire
#: long before this) — the runner surfaces it rather than hanging. The WCDF
#: no-progress rule already caps any progress-free run at 80 plies; this cap is
#: generously above any plausible legitimate game length.
DEFAULT_PLY_CAP = 2000


class PlyCapExceeded(RuntimeError):
    """Raised when a game runs past the hard ply cap without terminating.

    A game reaching this is a bug: every WCDF rule path (terminal, threefold
    repetition, the 80-ply no-progress draw) is supposed to end the game far
    sooner. The runner raises rather than hanging so the bug is surfaced.
    """


# --- Player protocol --------------------------------------------------------


@runtime_checkable
class Player(Protocol):
    """A match participant.

    The single method ``choose`` is given the current :class:`CheckersBoard`
    (the side to move is ``board.turn``) and must return a *legal* move — one
    of ``board.legal_moves()``. ``play_game`` validates the returned move and
    raises if it is illegal, so a buggy player cannot corrupt a game record.
    """

    name: str

    def choose(self, board: CheckersBoard) -> CheckersMove: ...


# --- Baseline opponents -----------------------------------------------------


class RandomPlayer:
    """Picks a uniformly random legal move from a seeded RNG.

    Deterministic given the seed: two ``RandomPlayer(seed=s)`` instances make
    identical choices in identical positions. The legal-move set is sorted
    (``board.legal_moves()`` returns it sorted) before sampling so the choice
    depends only on the seed, never on set iteration order.
    """

    def __init__(self, seed: int = 0, name: str = "RandomPlayer") -> None:
        self.name = name
        self._seed = seed
        self._rng = random.Random(seed)

    def choose(self, board: CheckersBoard) -> CheckersMove:
        moves = board.legal_moves()
        if not moves:
            raise ValueError("RandomPlayer asked to move in a terminal position")
        return self._rng.choice(list(moves))


class MinimaxPlayer:
    """A fixed-depth material minimax over ``search.static_evaluation``.

    A plain negamax of fixed ``depth`` on the verified ``board.py`` substrate,
    scoring leaves with ``search.static_evaluation`` (material: man = 100,
    king = 150). A terminal position is a loss for the side to move (WCDF 1.30,
    no stalemate draw) — ``static_evaluation`` already returns the large
    negative sentinel for it. Ties are broken deterministically by PDN string,
    so the player is fully deterministic.

    This is a *baseline opponent* for measuring the dialectical engine; it does
    not use the argument layers. ``search.negamax`` is not yet implemented, so
    the recursion is self-contained here.
    """

    def __init__(self, depth: int = 3, name: str | None = None) -> None:
        if depth < 1:
            raise ValueError("MinimaxPlayer depth must be >= 1")
        self.depth = depth
        self.name = name or f"MinimaxPlayer(d={depth})"

    def choose(self, board: CheckersBoard) -> CheckersMove:
        moves = board.legal_moves()
        if not moves:
            raise ValueError("MinimaxPlayer asked to move in a terminal position")
        best_move: CheckersMove | None = None
        best_score = -_INF
        # Sorted move order (legal_moves is already sorted) keeps the choice
        # deterministic: the first move achieving the best score wins the tie.
        for move in moves:
            score = -self._negamax(board.apply(move), self.depth - 1)
            if score > best_score:
                best_score = score
                best_move = move
        assert best_move is not None
        return best_move

    def _negamax(self, board: CheckersBoard, depth: int) -> int:
        """Negamax value of ``board`` for the side to move on it.

        A no-moves position is terminal and a loss for the side to move
        (``static_evaluation`` returns the loss sentinel for it). At depth 0 a
        non-terminal position is scored statically.
        """
        if depth <= 0 or board.is_terminal():
            return static_evaluation(board)
        best = -_INF
        for move in board.legal_moves():
            best = max(best, -self._negamax(board.apply(move), depth - 1))
        return best


_INF = 10**9


class EnginePlayer:
    """The dialectical engine itself, wrapped as a :class:`Player`.

    Wraps :class:`DialecticalCheckersEngine` — ``choose`` runs the engine's
    ``probe -> argument graph -> select`` pipeline and maps the engine's chosen
    PDN string back to the matching legal :class:`CheckersMove`. The engine's
    move selection is unchanged: this wrapper only adapts its decision to the
    :class:`Player` interface.
    """

    def __init__(
        self,
        engine: DialecticalCheckersEngine | None = None,
        settings: EngineSettings | None = None,
        name: str = "DialecticalEngine",
    ) -> None:
        if engine is not None and settings is not None:
            raise ValueError("pass either engine or settings, not both")
        self.name = name
        self.engine = engine or DialecticalCheckersEngine(settings)

    def choose(self, board: CheckersBoard) -> CheckersMove:
        moves = board.legal_moves()
        if not moves:
            raise ValueError("EnginePlayer asked to move in a terminal position")
        decision = self.engine.choose_move(board)
        for move in moves:
            if move.pdn() == decision.move_pdn:
                return move
        raise ValueError(
            f"engine chose {decision.move_pdn!r}, which is not a legal move "
            f"in {board.to_fen()!r}"
        )


# --- Game result ------------------------------------------------------------


@dataclass(frozen=True)
class GameResult:
    """The outcome of one :func:`play_game`.

    ``outcome`` is :data:`RED_WIN` / :data:`WHITE_WIN` / :data:`DRAW`.
    ``moves`` is the move sequence played. ``positions`` is every board from
    the start to the terminal/draw position (``len(moves) + 1`` entries).
    ``reason`` names *why* the game ended ("terminal", "threefold-repetition",
    "no-progress"). ``pdn_result`` is the matching PDN result token.
    """

    outcome: str
    moves: tuple[CheckersMove, ...]
    positions: tuple[CheckersBoard, ...]
    reason: str
    red_name: str = "Red"
    white_name: str = "White"

    @property
    def ply_count(self) -> int:
        """The number of plies (half-moves) played."""
        return len(self.moves)

    @property
    def pdn_result(self) -> str:
        """The PDN result token for this outcome."""
        if self.outcome == RED_WIN:
            return RESULT_RED_WIN
        if self.outcome == WHITE_WIN:
            return RESULT_WHITE_WIN
        return RESULT_DRAW

    def to_pdn_game(
        self, tags: dict[str, str] | None = None, setup_fen: str | None = None
    ) -> PdnGame:
        """Build a :class:`PdnGame` record of this game for PDN serialisation."""
        roster: dict[str, str] = {
            "Red": self.red_name,
            "White": self.white_name,
            "Result": self.pdn_result,
        }
        if tags:
            roster.update(tags)
        return PdnGame(
            moves=self.moves,
            result=self.pdn_result,
            tags=roster,
            setup_fen=setup_fen,
        )


def play_game(
    red_player: Player,
    white_player: Player,
    *,
    start: CheckersBoard | None = None,
    ply_cap: int = DEFAULT_PLY_CAP,
) -> GameResult:
    """Play one full game between ``red_player`` and ``white_player``.

    Starts from ``start`` (default ``CheckersBoard.initial()``), alternating
    the two players — Red moves first (WCDF 1.13). Every WCDF rule is enforced
    via the verified ``board.py``:

    * **Terminal (WCDF 1.30).** Before each player moves, ``board.is_terminal()``
      is checked: a side to move with no legal move *loses* (there is no
      stalemate draw). The other side is the winner.
    * **Draw (WCDF 1.32).** ``board.is_draw()`` is checked after each move —
      threefold repetition (the position's identity appearing three times in
      ``board.history``) or the no-progress rule (``board.no_progress`` reaching
      80 plies). The draw check runs *after* terminal, so a game that both ends
      and would draw is scored as the win it actually is.
    * **Legality.** Each player's returned move is checked against
      ``board.legal_moves()``; an illegal move raises ``ValueError`` — a buggy
      player cannot produce a corrupt game record.
    * **Ply cap.** ``ply_cap`` is a hard safety net: a game that neither
      terminates nor draws within it raises :class:`PlyCapExceeded`. Reaching
      the cap is a bug in the rule enforcement, surfaced rather than hung on.

    Returns a :class:`GameResult` with the outcome, the move sequence and every
    intermediate position.
    """
    board = start if start is not None else CheckersBoard.initial()
    moves: list[CheckersMove] = []
    positions: list[CheckersBoard] = [board]
    players = {"r": red_player, "w": white_player}

    while True:
        # Terminal first: a side to move with no legal move has lost (WCDF
        # 1.30). The draw check below never overrides a real terminal.
        if board.is_terminal():
            winner = board.winner()
            assert winner is not None
            outcome = RED_WIN if winner == "r" else WHITE_WIN
            return _result(outcome, "terminal", moves, positions,
                           red_player, white_player)
        # A draw reached *before* anyone is to move with no move: threefold
        # repetition or the 80-ply no-progress rule (WCDF 1.32).
        if board.is_draw():
            return _result(DRAW, _draw_reason(board), moves, positions,
                           red_player, white_player)
        if len(moves) >= ply_cap:
            raise PlyCapExceeded(
                f"game exceeded the {ply_cap}-ply safety cap without a "
                f"terminal or draw result — a rule-enforcement bug; last "
                f"position {board.to_fen()!r}"
            )

        player = players[board.turn]
        move = player.choose(board)
        legal = board.legal_moves()
        if move not in legal:
            raise ValueError(
                f"{player.name} returned illegal move {move.pdn()!r} in "
                f"position {board.to_fen()!r}"
            )
        board = board.apply(move)
        moves.append(move)
        positions.append(board)


def _draw_reason(board: CheckersBoard) -> str:
    """Name which WCDF draw rule applies to a drawn ``board``."""
    from dialectical_checkers.board import NO_PROGRESS_DRAW_PLIES

    if board.no_progress >= NO_PROGRESS_DRAW_PLIES:
        return "no-progress"
    return "threefold-repetition"


def _result(
    outcome: str,
    reason: str,
    moves: list[CheckersMove],
    positions: list[CheckersBoard],
    red_player: Player,
    white_player: Player,
) -> GameResult:
    """Assemble a :class:`GameResult` from the runner's accumulated state."""
    return GameResult(
        outcome=outcome,
        moves=tuple(moves),
        positions=tuple(positions),
        reason=reason,
        red_name=red_player.name,
        white_name=white_player.name,
    )


# --- Match (N games) --------------------------------------------------------


@dataclass(frozen=True)
class MatchReport:
    """The aggregate result of an N-game match.

    Counts are from Red's seat: ``red_wins`` + ``white_wins`` + ``draws`` ==
    ``games``. ``results`` holds every :class:`GameResult` in play order.
    """

    games: int
    red_wins: int
    white_wins: int
    draws: int
    results: tuple[GameResult, ...] = field(default_factory=tuple)

    def summary(self, red_name: str = "Red", white_name: str = "White") -> str:
        """A one-line W/D/L summary string from Red's point of view."""
        return (
            f"{red_name} vs {white_name}: "
            f"{self.red_wins}W-{self.draws}D-{self.white_wins}L "
            f"over {self.games} game(s)"
        )


def play_match(
    red_player: Player,
    white_player: Player,
    *,
    games: int = 1,
    start: CheckersBoard | None = None,
    ply_cap: int = DEFAULT_PLY_CAP,
) -> MatchReport:
    """Play ``games`` games between the two players and aggregate the results.

    Each game is an independent :func:`play_game`; the same player objects are
    reused across games, so a seeded :class:`RandomPlayer` continues its RNG
    stream (the whole match is deterministic given the seeds). Returns a
    :class:`MatchReport` with the Red/White/draw tally and every game.
    """
    if games < 1:
        raise ValueError("a match must have at least one game")
    results: list[GameResult] = []
    red_wins = white_wins = draws = 0
    for _ in range(games):
        result = play_game(
            red_player, white_player, start=start, ply_cap=ply_cap
        )
        results.append(result)
        if result.outcome == RED_WIN:
            red_wins += 1
        elif result.outcome == WHITE_WIN:
            white_wins += 1
        else:
            draws += 1
    return MatchReport(
        games=games,
        red_wins=red_wins,
        white_wins=white_wins,
        draws=draws,
        results=tuple(results),
    )
