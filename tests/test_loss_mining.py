"""Tests for the loss-mining diagnostic (``dialectical_checkers.loss_mining``).

Phase 7 directive: the loss-mining diagnostic analyses the engine's LOST games
for the *turning point* — the ply at which a non-losing move became a losing
one — classifying it with the verified ``captures.resolve()`` / the board. The
tests build a game whose losing turning point is known and confirm it is
identified correctly, and confirm a clean (won) game yields no turning point.

The constructed fixtures were validated against runtime behaviour
(``scripts/phase7_verify_blunder_line.py``): in ``B:W17:B9`` Red's quiet move
``9-14`` walks the man next to White's 17 so ``17x10`` captures it for free and
Red, left with no piece, loses — while ``9-13`` is a safe alternative, so the
blunder is a genuine turning point.
"""

from __future__ import annotations

import pytest

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.loss_mining import (
    LossTurningPoint,
    mine_turning_point,
    move_allows_shot,
)
from dialectical_checkers.match import RED_WIN, WHITE_WIN, play_game

# --- move_allows_shot -------------------------------------------------------


@pytest.mark.unit
def test_move_allows_shot_detects_a_blunder() -> None:
    """A quiet move handing the opponent a free capture is flagged.

    In ``B:W17:B9`` Red's quiet move ``9-14`` walks next to White's man on 17,
    so White's ``17x10`` wins the man — a proven one-move blunder.
    """
    board = CheckersBoard.from_fen("B:W17:B9")
    legal = {m.pdn(): m for m in board.legal_moves()}
    assert "9-14" in legal, f"expected 9-14 legal; got {sorted(legal)}"
    blunder = legal["9-14"]
    shot = move_allows_shot(board, blunder)
    assert shot is not None
    assert shot.material_net > 0


@pytest.mark.unit
def test_move_allows_shot_safe_move_returns_none() -> None:
    """The safe alternative concedes no forced capture — returns ``None``."""
    board = CheckersBoard.from_fen("B:W17:B9")
    legal = {m.pdn(): m for m in board.legal_moves()}
    assert "9-13" in legal, f"expected 9-13 legal; got {sorted(legal)}"
    assert move_allows_shot(board, legal["9-13"]) is None


# --- mine_turning_point -----------------------------------------------------


def _scripted(moves_pdn: list[str]):
    """A player that plays a fixed PDN script, in order."""

    class _Scripted:
        name = "scripted"

        def __init__(self) -> None:
            self._i = 0

        def choose(self, board: CheckersBoard):
            want = moves_pdn[self._i]
            self._i += 1
            for move in board.legal_moves():
                if move.pdn() == want:
                    return move
            raise AssertionError(
                f"scripted move {want} not legal in {board.to_fen()}"
            )

    return _Scripted()


@pytest.mark.unit
def test_mine_turning_point_finds_the_blunder_ply() -> None:
    """On a constructed lost game the turning-point ply is identified exactly.

    From ``B:W17:B9`` Red (the engine seat) plays the blunder ``9-14``; White
    replies ``17x10`` winning the man, and Red — left with no piece — is to
    move with no move and loses. The turning point is ply 1, Red's ``9-14``.
    """
    start = CheckersBoard.from_fen("B:W17:B9")
    red = _scripted(["9-14"])
    white = _scripted(["17x10"])
    result = play_game(red, white, start=start)
    assert result.outcome == WHITE_WIN

    point = mine_turning_point(result, engine_is_red=True)
    assert point is not None
    assert isinstance(point, LossTurningPoint)
    assert point.ply == 1
    assert point.played_move == "9-14"
    assert point.side == "r"
    assert point.fen_before == start.to_fen()
    # 9-13 was a safe alternative, so the blunder was avoidable.
    assert point.was_avoidable is True
    assert "9-13" in point.safe_alternatives


@pytest.mark.unit
def test_mine_turning_point_none_when_engine_did_not_lose() -> None:
    """A game the engine won (or drew) yields no turning point."""
    start = CheckersBoard.from_fen("B:W17:B9")
    red = _scripted(["9-14"])
    white = _scripted(["17x10"])
    result = play_game(red, white, start=start)
    # Here the engine is White, which WON — no losing turning point for it.
    point = mine_turning_point(result, engine_is_red=False)
    assert point is None


@pytest.mark.unit
def test_mine_turning_point_unavoidable_is_flagged() -> None:
    """A loss whose only conceding ply was a forced move is flagged unavoidable.

    In ``B:W11,20:B7`` Red has exactly one legal move — the forced capture
    ``7x16`` — after which White replies ``20x11`` winning Red's last man and
    Red, to move with no piece, loses. Red had no choice at ply 1, so the
    turning point there is ``was_avoidable=False``: the loss was already locked
    in (validated by ``scripts/phase7_verify_unavoidable2.py``).
    """
    start = CheckersBoard.from_fen("B:W11,20:B7")
    legal = {m.pdn() for m in start.legal_moves()}
    assert legal == {"7x16"}, f"expected only 7x16 forced; got {sorted(legal)}"
    red = _scripted(["7x16"])
    white = _scripted(["20x11"])
    result = play_game(red, white, start=start)
    assert result.outcome == WHITE_WIN

    point = mine_turning_point(result, engine_is_red=True)
    assert point is not None
    assert point.ply == 1
    assert point.played_move == "7x16"
    # Every legal move at ply 1 was the one forced capture — unavoidable.
    assert point.was_avoidable is False
    assert point.safe_alternatives == ()


@pytest.mark.differential
def test_mine_turning_point_engine_white_seat() -> None:
    """The diagnostic works from the engine's White seat too.

    From ``W:W17:B9`` White (the engine seat) plays the blunder ``17-14``; Red
    replies ``9x18`` winning the man and White, left with no piece, loses. The
    engine is White; the turning point is the White ply ``17-14``.
    """
    start = CheckersBoard.from_fen("W:W17:B9")
    legal = {m.pdn() for m in start.legal_moves()}
    assert "17-14" in legal, f"expected 17-14 legal; got {sorted(legal)}"
    white = _scripted(["17-14"])
    red = _scripted(["9x18"])
    result = play_game(red, white, start=start)
    assert result.outcome == RED_WIN

    point = mine_turning_point(result, engine_is_red=False)
    assert point is not None
    assert point.side == "w"
    assert point.played_move == "17-14"
    assert point.ply == 1
