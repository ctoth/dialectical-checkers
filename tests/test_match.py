"""Tests for the self-play match harness (``dialectical_checkers.match``).

Phase 6 directives: a RandomPlayer-vs-RandomPlayer game runs to a genuine
terminal or draw result with every played move legal; the WCDF draw rules
(threefold repetition; the 80-ply no-progress rule) fire on constructed
positions; a short engine-vs-RandomPlayer match runs end to end; the same seed
reproduces the same games; and a runner-produced game replays legally in the
pydraughts oracle (differential).
"""

from __future__ import annotations

import pytest

from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.match import (
    DEFAULT_PLY_CAP,
    DRAW,
    RED_WIN,
    WHITE_WIN,
    EnginePlayer,
    GameResult,
    MinimaxPlayer,
    PlyCapExceeded,
    RandomPlayer,
    play_game,
    play_match,
)

# --- helpers ----------------------------------------------------------------


def _assert_every_move_was_legal(result: GameResult) -> None:
    """Re-derive each position and assert every played move was legal there.

    Independent of the runner's own legality check: replays from
    ``result.positions[0]`` and confirms each move is in ``legal_moves()`` and
    that ``apply`` reproduces the recorded next position.
    """
    board = result.positions[0]
    for ply, move in enumerate(result.moves, start=1):
        assert move in board.legal_moves(), (
            f"ply {ply}: {move.pdn()} not legal in {board.to_fen()}"
        )
        board = board.apply(move)
        assert board.cells == result.positions[ply].cells
        assert board.turn == result.positions[ply].turn


class _ScriptedPlayer:
    """A test player that always picks the same labelled move when available.

    Used to construct deterministic repetition / no-progress runs. ``picker``
    receives the board and returns a chosen :class:`CheckersMove`.
    """

    def __init__(self, name: str, picker) -> None:  # type: ignore[no-untyped-def]
        self.name = name
        self._picker = picker

    def choose(self, board: CheckersBoard) -> CheckersMove:
        return self._picker(board)


# --- RandomPlayer vs RandomPlayer -------------------------------------------


@pytest.mark.unit
def test_random_vs_random_reaches_a_terminal_or_draw() -> None:
    """A RandomPlayer-vs-RandomPlayer game ends in a real terminal/draw result."""
    result = play_game(RandomPlayer(seed=1), RandomPlayer(seed=2))
    assert result.outcome in (RED_WIN, WHITE_WIN, DRAW)
    assert result.reason in (
        "terminal", "threefold-repetition", "no-progress"
    )
    # The recorded final position is consistent with the recorded outcome.
    final = result.positions[-1]
    if result.reason == "terminal":
        winner = final.winner()
        assert winner is not None
        assert result.outcome == (RED_WIN if winner == "r" else WHITE_WIN)
    else:
        assert result.outcome == DRAW
        assert final.is_draw()


@pytest.mark.property
def test_random_vs_random_every_move_legal() -> None:
    """Every move played in a random-vs-random game was legal when played."""
    for seed in range(5):
        result = play_game(RandomPlayer(seed=seed), RandomPlayer(seed=seed + 100))
        _assert_every_move_was_legal(result)
        # positions has exactly one more entry than moves.
        assert len(result.positions) == len(result.moves) + 1


# --- Determinism ------------------------------------------------------------


@pytest.mark.property
def test_same_seed_same_game() -> None:
    """Two games with the same player seeds play the identical move sequence."""
    a = play_game(RandomPlayer(seed=7), RandomPlayer(seed=8))
    b = play_game(RandomPlayer(seed=7), RandomPlayer(seed=8))
    assert a.moves == b.moves
    assert a.outcome == b.outcome
    assert a.reason == b.reason


@pytest.mark.property
def test_different_seed_can_differ() -> None:
    """Different seeds produce a different game (sanity check on the RNG)."""
    a = play_game(RandomPlayer(seed=7), RandomPlayer(seed=8))
    b = play_game(RandomPlayer(seed=99), RandomPlayer(seed=123))
    # Not a guarantee for all seeds, but these chosen seeds diverge.
    assert a.moves != b.moves


# --- WCDF terminal rule -----------------------------------------------------


@pytest.mark.unit
def test_terminal_loss_for_side_with_no_move() -> None:
    """A game starting in a position where the side to move has no move ends.

    ``B:W5,6,9,10:B1`` — Red man on 1, to move, fully blocked: terminal, Red
    loses (WCDF 1.30, no stalemate draw).
    """
    start = CheckersBoard.from_fen("B:W5,6,9,10:B1")
    assert start.is_terminal()
    result = play_game(RandomPlayer(seed=0), RandomPlayer(seed=1), start=start)
    assert result.outcome == WHITE_WIN
    assert result.reason == "terminal"
    assert result.ply_count == 0


# --- WCDF draw rules --------------------------------------------------------


@pytest.mark.unit
def test_threefold_repetition_draw() -> None:
    """Two kings shuffling between the same squares draw by threefold repetition.

    Constructed: a lone Red king and a lone White king, each scripted to
    bounce between two squares. The position identity recurs and the runner
    must return a draw with reason ``threefold-repetition`` — and before the
    80-ply no-progress rule could fire.
    """
    # Red king on 14, White king on 19. Each shuffles between two squares.
    start = CheckersBoard.from_fen("B:WK19:BK14")

    def red_pick(board: CheckersBoard) -> CheckersMove:
        # Red king bounces 14<->10 (both quiet king moves, no capture).
        legal = {m.pdn(): m for m in board.legal_moves()}
        for pdn in ("14-10", "10-14"):
            if pdn in legal:
                return legal[pdn]
        return next(iter(board.legal_moves()))

    def white_pick(board: CheckersBoard) -> CheckersMove:
        legal = {m.pdn(): m for m in board.legal_moves()}
        for pdn in ("19-23", "23-19"):
            if pdn in legal:
                return legal[pdn]
        return next(iter(board.legal_moves()))

    red = _ScriptedPlayer("RedShuffle", red_pick)
    white = _ScriptedPlayer("WhiteShuffle", white_pick)
    result = play_game(red, white, start=start)
    assert result.outcome == DRAW
    assert result.reason == "threefold-repetition"
    # Repetition fires well before the 80-ply no-progress cap.
    assert result.ply_count < 80


@pytest.mark.unit
def test_no_progress_draw() -> None:
    """The WCDF 1.32.2 no-progress rule draws a game via the runner.

    Constructed to exercise the runner's *no-progress* draw branch
    specifically: a king-only position whose ``no_progress`` counter starts at
    78. Two quiet king moves (no man advance, no capture) push the counter to
    80 — the WCDF 1.32.2 threshold — and the runner returns a draw with reason
    ``no-progress``. The start board carries an empty ``history`` so threefold
    repetition cannot fire first across the two plies.
    """
    # Kings far enough apart that each side has a quiet, non-capturing move and
    # neither is blocked. no_progress pre-set to 78: two quiet plies reach 80.
    cells: list = [None] * 32
    cells[10] = ("r", True)   # Red king on PDN 11
    cells[19] = ("w", True)   # White king on PDN 20
    start = CheckersBoard(
        cells=tuple(cells), turn="r", no_progress=78, history=()
    )
    assert not start.is_terminal()
    result = play_game(RandomPlayer(seed=3), RandomPlayer(seed=4), start=start)
    assert result.outcome == DRAW
    assert result.reason == "no-progress"
    assert result.positions[-1].no_progress >= 80
    # Exactly the two quiet plies needed to cross the threshold.
    assert result.ply_count == 2


@pytest.mark.unit
def test_no_progress_counter_advances_only_on_quiet_moves() -> None:
    """The runner's no-progress draw fires only after enough quiet king plies.

    A counter pre-set to 79 with one quiet king ply each available: after the
    single Red ply the counter is 80 and the game draws by the no-progress
    rule — confirming the runner reads ``board.no_progress`` for the WCDF
    1.32.2 check rather than counting plies itself.
    """
    cells: list = [None] * 32
    cells[10] = ("r", True)   # Red king on PDN 11
    cells[19] = ("w", True)   # White king on PDN 20
    start = CheckersBoard(
        cells=tuple(cells), turn="r", no_progress=79, history=()
    )
    result = play_game(RandomPlayer(seed=3), RandomPlayer(seed=4), start=start)
    assert result.outcome == DRAW
    assert result.reason == "no-progress"
    assert result.ply_count == 1


# --- ply cap ----------------------------------------------------------------


@pytest.mark.unit
def test_ply_cap_raises_when_game_would_not_terminate() -> None:
    """A tiny ply cap surfaces a non-terminating game as ``PlyCapExceeded``.

    The cap is a safety net: with a cap of 4 a normal game cannot finish, so
    the runner raises rather than playing on. (A real game always ends well
    inside :data:`DEFAULT_PLY_CAP`.)
    """
    with pytest.raises(PlyCapExceeded):
        play_game(RandomPlayer(seed=1), RandomPlayer(seed=2), ply_cap=4)


@pytest.mark.unit
def test_default_ply_cap_is_generous() -> None:
    """The default ply cap is well above the 80-ply no-progress draw bound."""
    assert DEFAULT_PLY_CAP > 80


# --- illegal-move guard -----------------------------------------------------


@pytest.mark.unit
def test_illegal_player_move_raises() -> None:
    """A player returning an illegal move makes the runner raise ``ValueError``."""

    def bad_pick(board: CheckersBoard) -> CheckersMove:
        # A move that is never legal: jump nothing across non-adjacent squares.
        return CheckersMove(path=(1, 32), captured=())

    bad = _ScriptedPlayer("BadPlayer", bad_pick)
    with pytest.raises(ValueError):
        play_game(bad, RandomPlayer(seed=0))


# --- baseline opponents -----------------------------------------------------


@pytest.mark.unit
def test_minimax_player_is_deterministic() -> None:
    """Two MinimaxPlayer games of the same depth play identically."""
    a = play_game(MinimaxPlayer(depth=2), RandomPlayer(seed=5))
    b = play_game(MinimaxPlayer(depth=2), RandomPlayer(seed=5))
    assert a.moves == b.moves
    assert a.outcome == b.outcome


@pytest.mark.unit
def test_minimax_player_takes_a_free_capture() -> None:
    """MinimaxPlayer takes a free winning capture when one is available.

    ``B:W18:B15`` — Red man on 15 must capture 18 (capture is mandatory); the
    point is that MinimaxPlayer returns a legal move and the resulting position
    nets Red the piece.
    """
    start = CheckersBoard.from_fen("B:W18:B15")
    player = MinimaxPlayer(depth=2)
    move = player.choose(start)
    assert move in start.legal_moves()
    assert move.is_jump


@pytest.mark.unit
def test_minimax_beats_random_or_draws_more_often() -> None:
    """A short MinimaxPlayer-vs-RandomPlayer match completes end to end."""
    report = play_match(
        MinimaxPlayer(depth=2), RandomPlayer(seed=11), games=2
    )
    assert report.games == 2
    assert report.red_wins + report.white_wins + report.draws == 2


# --- engine as a player -----------------------------------------------------


@pytest.mark.unit
def test_engine_vs_random_runs_end_to_end() -> None:
    """A short engine-vs-RandomPlayer game runs to a real result."""
    result = play_game(EnginePlayer(), RandomPlayer(seed=42))
    assert result.outcome in (RED_WIN, WHITE_WIN, DRAW)
    _assert_every_move_was_legal(result)


@pytest.mark.unit
def test_engine_player_returns_legal_move() -> None:
    """EnginePlayer maps the engine's PDN decision back to a legal move."""
    board = CheckersBoard.initial()
    move = EnginePlayer().choose(board)
    assert move in board.legal_moves()


@pytest.mark.unit
def test_match_report_summary_counts_add_up() -> None:
    """A match report's W/D/L counts sum to the game count."""
    report = play_match(RandomPlayer(seed=1), RandomPlayer(seed=2), games=4)
    assert report.red_wins + report.white_wins + report.draws == report.games
    assert "over 4 game(s)" in report.summary()


# --- differential vs pydraughts ---------------------------------------------


def _oracle_replay_is_legal(result: GameResult) -> bool:
    """Replay a runner-produced game in pydraughts; every move must be legal.

    pydraughts is a test-only oracle (port-plan §6). Its English variant uses
    the same square numbering and PDN move strings as the engine, so a played
    move string can be matched against the oracle's legal-move set.
    """
    from draughts import Board as OracleBoard

    oracle = OracleBoard(variant="english", fen=result.positions[0].to_fen())
    for move in result.moves:
        legal_strings: set[str] = set()
        legal_objs = {}
        for omove in oracle.legal_moves():
            steps = list(omove.steps_move)
            sep = "x" if omove.has_captures else "-"
            key = sep.join(str(s) for s in steps)
            legal_strings.add(key)
            legal_objs[key] = omove
        if move.pdn() not in legal_strings:
            return False
        oracle.push(legal_objs[move.pdn()])
    return True


@pytest.mark.differential
def test_runner_game_replays_legally_in_oracle() -> None:
    """A runner-produced random-vs-random game replays legally in pydraughts."""
    result = play_game(RandomPlayer(seed=21), RandomPlayer(seed=22))
    assert _oracle_replay_is_legal(result)


@pytest.mark.differential
def test_runner_outcome_agrees_with_oracle_terminal() -> None:
    """When the runner reports a terminal win, the oracle agrees the game ended.

    Replays the full game in pydraughts; after the last move the oracle must
    also report no legal moves (a terminal position) for a runner-terminal
    game.
    """
    from draughts import Board as OracleBoard

    # Find a seed pair that ends in a terminal (not a draw) within the cap.
    result = None
    for seed in range(30):
        candidate = play_game(
            RandomPlayer(seed=seed), RandomPlayer(seed=seed + 50)
        )
        if candidate.reason == "terminal":
            result = candidate
            break
    assert result is not None, "no terminal game found in the seed range"

    oracle = OracleBoard(variant="english", fen=result.positions[0].to_fen())
    for move in result.moves:
        legal_objs = {}
        for omove in oracle.legal_moves():
            steps = list(omove.steps_move)
            sep = "x" if omove.has_captures else "-"
            legal_objs[sep.join(str(s) for s in steps)] = omove
        oracle.push(legal_objs[move.pdn()])
    # The oracle agrees the final position is terminal (no legal moves).
    assert len(oracle.legal_moves()) == 0
