"""Tests for PDN game I/O (``dialectical_checkers.pdn``) — Phase 6 harness.

Per the Phase 6 directives: a PDN round-trip is stable (parse o render o parse
yields the same game), parsing a game with a ``FEN`` setup tag works, and
move-token parsing reconstructs jump capture squares from board geometry.
"""

from __future__ import annotations

import pytest

from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.pdn import (
    RESULT_DRAW,
    RESULT_RED_WIN,
    RESULT_WHITE_WIN,
    PdnGame,
    parse_move_token,
    parse_pdn,
    render_pdn,
)

# --- Move-token parsing -----------------------------------------------------


@pytest.mark.unit
def test_parse_simple_move_token() -> None:
    """A simple ``a-b`` token parses to a non-jump move with no captures."""
    move = parse_move_token("11-15")
    assert move == CheckersMove(path=(11, 15), captured=())
    assert not move.is_jump


@pytest.mark.unit
def test_parse_jump_token_reconstructs_captured_square() -> None:
    """A jump token reconstructs the captured square from board geometry.

    PDN movetext gives only visited squares; the captured square between a
    legal jump hop is implied by the board ``JUMP`` table. For ``15x22`` the
    jumped square is 18.
    """
    move = parse_move_token("15x22")
    assert move.path == (15, 22)
    assert move.captured == (18,)
    assert move.is_jump


@pytest.mark.unit
def test_parse_multi_jump_token() -> None:
    """A multi-hop jump token reconstructs every captured square in order."""
    # Red man 11 jumps 16 (landing 20), then 24 (landing 27).
    move = parse_move_token("11x20x27")
    assert move.path == (11, 20, 27)
    assert move.captured == (16, 24)


@pytest.mark.unit
def test_parse_jump_accepts_uppercase_x() -> None:
    """An uppercase ``X`` jump separator is accepted (PDN renders both)."""
    assert parse_move_token("15X22") == parse_move_token("15x22")


@pytest.mark.unit
def test_parse_move_token_rejects_malformed() -> None:
    """A malformed move token raises ``ValueError``."""
    for bad in ("", "11", "11-", "-15", "11--15", "abc", "11-15-19"):
        with pytest.raises(ValueError):
            parse_move_token(bad)


@pytest.mark.unit
def test_parse_move_token_rejects_mixed_separators() -> None:
    """A token mixing ``-`` and ``x``/``X`` separators raises ``ValueError``.

    A PDN move token must use a consistent separator family: either the simple
    separator ``-`` or the jump separators ``x``/``X``. A mixed token such as
    ``10x17-26`` or ``10-17x26`` must be rejected, not silently normalised into
    a jump chain.
    """
    for bad in ("10x17-26", "10-17x26", "10X17-26", "10-17X26"):
        with pytest.raises(ValueError):
            parse_move_token(bad)


@pytest.mark.unit
def test_parse_move_token_accepts_consistent_separators() -> None:
    """Valid single-family tokens still parse after the mixed-separator check."""
    simple = parse_move_token("11-15")
    assert simple == CheckersMove(path=(11, 15), captured=())
    assert not simple.is_jump
    jump = parse_move_token("11x20x27")
    assert jump.path == (11, 20, 27)
    assert jump.is_jump


@pytest.mark.unit
def test_parse_move_token_rejects_out_of_range_square() -> None:
    """A move token with a square outside 1-32 raises ``ValueError``."""
    with pytest.raises(ValueError):
        parse_move_token("11-99")


@pytest.mark.unit
def test_parse_move_token_rejects_illegal_jump_shape() -> None:
    """A jump hop that is not a legal jump shape raises ``ValueError``."""
    with pytest.raises(ValueError):
        parse_move_token("11x12")  # adjacent squares, not a jump


# --- Game parsing -----------------------------------------------------------


@pytest.mark.unit
def test_parse_pdn_basic_game() -> None:
    """A small PDN game parses its tags, moves and result token."""
    text = (
        '[Event "Test"]\n'
        '[Red "Alice"]\n'
        '[White "Bob"]\n'
        '[Result "1-0"]\n'
        "\n"
        "1. 11-15 23-19 2. 8-11 22-17 1-0\n"
    )
    game = parse_pdn(text)
    assert game.tags["Event"] == "Test"
    assert game.tags["Red"] == "Alice"
    assert game.result == RESULT_RED_WIN
    assert [m.pdn() for m in game.moves] == ["11-15", "23-19", "8-11", "22-17"]
    assert game.setup_fen is None


@pytest.mark.unit
def test_parse_pdn_with_fen_setup_tag() -> None:
    """A game with a ``FEN`` tag parses the non-standard start position."""
    fen = "B:W18:B15"
    text = f'[Event "FEN game"]\n[SetUp "1"]\n[FEN "{fen}"]\n\n1. 15x22 *\n'
    game = parse_pdn(text)
    assert game.setup_fen == fen
    start = game.initial_board()
    assert start.to_fen() == fen
    # The single move is legal from that setup and replays cleanly.
    positions = game.positions()
    assert len(positions) == 2
    assert positions[0].to_fen() == fen


@pytest.mark.unit
def test_parse_pdn_discards_comments_and_variations() -> None:
    """``{ }`` comments and ``( )`` variations are ignored; mainline kept."""
    text = (
        '[Result "*"]\n\n'
        "1. 11-15 {a comment} 23-19 (2. 9-13 21-17) 2. 8-11 *\n"
    )
    game = parse_pdn(text)
    assert [m.pdn() for m in game.moves] == ["11-15", "23-19", "8-11"]


@pytest.mark.unit
def test_parse_pdn_malformed_tag_raises() -> None:
    """A malformed tag line raises ``ValueError``."""
    with pytest.raises(ValueError):
        parse_pdn('[Event "unterminated\n\n1. 11-15 *\n')


@pytest.mark.unit
def test_positions_rejects_illegal_move() -> None:
    """Replaying a game whose movetext contains an illegal move raises."""
    # 11-16 is not a legal Red opening move (11's forward squares are 15, 16 —
    # 16 IS legal; use a genuinely illegal move instead: 1-6 (1 has no NW)).
    game = PdnGame(moves=(CheckersMove(path=(1, 5), captured=()),))
    with pytest.raises(ValueError):
        game.positions()


# --- Round-trip -------------------------------------------------------------


def _played_game() -> PdnGame:
    """A short legal game built by replaying the standard opening."""
    board = CheckersBoard.initial()
    moves: list[CheckersMove] = []
    # Play the first eight legal moves of a deterministic walk.
    import random

    rng = random.Random(12345)
    for _ in range(8):
        legal = board.legal_moves()
        if not legal:
            break
        move = rng.choice(list(legal))
        moves.append(move)
        board = board.apply(move)
    return PdnGame(
        moves=tuple(moves),
        result=RESULT_DRAW,
        tags={"Event": "Round-trip", "Red": "R", "White": "W"},
    )


@pytest.mark.property
def test_pdn_round_trip_is_stable() -> None:
    """parse(render(game)) yields the same moves and result — stable round-trip."""
    game = _played_game()
    text = render_pdn(game)
    reparsed = parse_pdn(text)
    assert reparsed.moves == game.moves
    assert reparsed.result == game.result
    # A second round-trip is a fixpoint.
    again = parse_pdn(render_pdn(reparsed))
    assert again.moves == reparsed.moves
    assert again.result == reparsed.result


@pytest.mark.property
def test_pdn_round_trip_preserves_fen_setup() -> None:
    """A round-trip preserves a non-standard ``FEN`` start position."""
    fen = "B:W18,19:B15"
    game = PdnGame(
        moves=(CheckersMove(path=(15, 22), captured=(18,)),),
        result=RESULT_WHITE_WIN,
        tags={"Event": "FEN round-trip"},
        setup_fen=fen,
    )
    reparsed = parse_pdn(render_pdn(game))
    assert reparsed.setup_fen == fen
    assert reparsed.moves == game.moves
    assert reparsed.initial_board().to_fen() == fen


@pytest.mark.unit
def test_render_pdn_emits_roster_and_result() -> None:
    """Rendered PDN carries the seven-tag roster and the result token."""
    game = _played_game()
    text = render_pdn(game)
    assert '[Event "Round-trip"]' in text
    assert '[Result "1/2-1/2"]' in text
    assert text.rstrip().endswith(RESULT_DRAW)
