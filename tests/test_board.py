"""Phase 1 — tests for ``dialectical_checkers.board``.

Three test families, mirroring the project markers:

* ``unit`` — one focused position per binding WCDF rule (port-plan §5.1,
  design §2.5).
* ``property`` — hypothesis metamorphic invariants: PDN-FEN round-trip,
  ``apply`` validity, the mandatory-capture invariant.
* ``differential`` — move-set equality and perft against the qualified oracle
  pydraughts 0.6.7 (English variant). pydraughts is imported ONLY here, never
  by ``dialectical_checkers`` itself (the non-oracle-strength stance).

Side mapping (scout report ``oracle-qualify-pydraughts.md``): pydraughts BLACK
== the engine's Red (squares 1-12, moves first); pydraughts WHITE == engine
White. PDN-FEN turn token ``B`` == Red.
"""

from __future__ import annotations

import random

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dialectical_checkers.board import (
    NO_PROGRESS_DRAW_PLIES,
    CheckersBoard,
    CheckersMove,
    perft,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def move_set(board: CheckersBoard) -> set[tuple[tuple[int, ...], tuple[int, ...]]]:
    """The engine's legal moves as a comparable set of (path, captured) tuples."""
    return {(m.path, m.captured) for m in board.legal_moves()}


def pdn_set(board: CheckersBoard) -> set[str]:
    """The engine's legal moves as a set of PDN move strings."""
    return {m.pdn() for m in board.legal_moves()}


def oracle_pdn_set(fen: str) -> set[str]:
    """pydraughts' legal moves for ``fen`` as a set of PDN move strings.

    The oracle helper lives in the test file only (directive 5). pydraughts'
    English variant uses the same square numbering and the same FEN form as the
    engine, so PDN strings are directly comparable.
    """
    from draughts import Board as OracleBoard

    oracle = OracleBoard(variant="english", fen=fen)
    result: set[str] = set()
    for move in oracle.legal_moves():
        steps = list(move.steps_move)
        sep = "x" if move.has_captures else "-"
        result.add(sep.join(str(s) for s in steps))
    return result


# Curated edge-case positions: one per binding rule (directive 7). Each is a
# PDN-FEN plus a human label; reused by both the unit tests and the
# differential edge-case test (directive 9).
EDGE_CASES: list[tuple[str, str]] = [
    ("start", CheckersBoard.initial().to_fen()),
    ("man_forward_only", "B:W:B15"),
    ("man_backward_jump_forbidden", "B:W11:B15"),
    ("man_forward_capture_forced", "B:W18:B15"),
    ("non_flying_king_quiet", "B:W:BK15"),
    ("non_flying_king_distant_man", "B:W14:BK5"),
    ("king_one_square_capture", "B:W19:BK15"),
    ("mandatory_capture", "B:W18,19:B15"),
    ("shorter_capture_allowed", "B:W15,16,23:B11"),
    ("captured_square_blocks_landing", "B:W18,11:B15"),
    ("crowning_ends_turn", "B:W25,26:B21"),
    ("no_move_is_a_loss", "B:W5,6,9,10:B1"),
    ("multi_jump_double", "B:W16,24:B11"),
    # King-specific differential cases (directive 3). A man cannot reach any of
    # these, so they exercise the king capture surface the analyst flagged as
    # uncovered. All three are oracle-confirmed against pydraughts English.
    ("king_backward_capture", "B:W18:BK22"),
    ("king_multi_jump", "B:W7,15,23,24:BK2"),
    ("king_loop_capture", "B:W17,18,25,26:BK14"),
]


# ---------------------------------------------------------------------------
# Unit tests — one per binding WCDF rule (directive 7)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_initial_position_has_seven_moves() -> None:
    """The WCDF start gives Red 7 forward simple moves (scout report §3.1)."""
    board = CheckersBoard.initial()
    assert pdn_set(board) == {
        "9-13",
        "9-14",
        "10-14",
        "10-15",
        "11-15",
        "11-16",
        "12-16",
    }


@pytest.mark.unit
def test_man_moves_forward_only() -> None:
    """A man steps diagonally forward only — never backward (WCDF 1.15)."""
    # Lone Red man on 15: forward (toward higher numbers) is 18, 19.
    board = CheckersBoard.from_fen("B:W:B15")
    assert pdn_set(board) == {"15-18", "15-19"}
    # Lone White man on 15: forward (toward lower numbers) is 10, 11.
    board = CheckersBoard.from_fen("W:W15:B")
    assert pdn_set(board) == {"15-10", "15-11"}


@pytest.mark.unit
def test_man_cannot_jump_backward() -> None:
    """A man may not capture backward (WCDF 1.18 — forward only).

    Red man on 15, White man on 11 which is diagonally *backward* of 15: the
    only legal moves are the two forward quiet steps; no backward jump 15x8.
    """
    board = CheckersBoard.from_fen("B:W11:B15")
    assert pdn_set(board) == {"15-18", "15-19"}
    assert all(not m.is_jump for m in board.legal_moves())


@pytest.mark.unit
def test_man_captures_forward() -> None:
    """A man's forward capture is generated and is mandatory (WCDF 1.18/1.20)."""
    board = CheckersBoard.from_fen("B:W18:B15")
    moves = board.legal_moves()
    assert len(moves) == 1
    assert moves[0].pdn() == "15x22"
    assert moves[0].captured == (18,)


@pytest.mark.unit
def test_non_flying_king_one_square() -> None:
    """A king moves exactly one square, any diagonal, non-flying (WCDF 1.17)."""
    board = CheckersBoard.from_fen("B:W:BK15")
    assert pdn_set(board) == {"15-10", "15-11", "15-18", "15-19"}


@pytest.mark.unit
def test_non_flying_king_cannot_reach_distant_man() -> None:
    """A king cannot capture a man that is not on an adjacent diagonal square."""
    board = CheckersBoard.from_fen("B:W14:BK5")
    # White man on 14 is not adjacent to the king on 5: only quiet moves.
    assert pdn_set(board) == {"5-1", "5-9"}
    assert all(not m.is_jump for m in board.legal_moves())


@pytest.mark.unit
def test_king_captures_one_square() -> None:
    """A king capture jumps exactly one square (non-flying, WCDF 1.21)."""
    board = CheckersBoard.from_fen("B:W19:BK15")
    moves = board.legal_moves()
    assert len(moves) == 1
    assert moves[0].pdn() == "15x24"
    assert moves[0].captured == (19,)


@pytest.mark.unit
def test_mandatory_capture() -> None:
    """When a capture exists, every legal move is a capture (WCDF 1.20)."""
    board = CheckersBoard.from_fen("B:W18,19:B15")
    moves = board.legal_moves()
    assert moves, "expected at least one move"
    assert all(m.is_jump for m in moves)


@pytest.mark.unit
def test_shorter_capture_allowed() -> None:
    """No maximum-capture rule: a shorter capture is a legal choice (WCDF 1.20).

    Red man on 11 can take only 16 (single, lands on 20) OR take 15 then 23
    (double, path 11->18->27). Both must be offered — the engine does not force
    the longer capture.
    """
    board = CheckersBoard.from_fen("B:W15,16,23:B11")
    pdns = pdn_set(board)
    assert "11x20" in pdns, "shorter single capture must be allowed"
    assert "11x18x27" in pdns, "longer double capture must be allowed"
    assert pdns == {"11x20", "11x18x27"}


@pytest.mark.unit
def test_captured_square_stays_occupied_during_chain() -> None:
    """A captured piece stays on the board, un-jumpable, until the chain ends.

    WCDF 1.19: captured pieces are removed only when the whole multi-jump
    sequence terminates. This is a REAL multi-jump continuation that proves it.

    Red king on 14 sits inside a closed ring of four White men 17,18,25,26.
    The full forced chain is ``14x23x30x21`` (jump 18->23, 25->30, 26->21).
    After the king lands on 21 it is again diagonally adjacent to White 18 with
    landing square 14 — but 18 was already captured earlier in this very
    sequence. Because the captured piece is still on square 18 (occupied, but
    flagged un-jumpable), the king CANNOT re-jump it and the chain ends at 21.

    If captured pieces were removed eagerly, square 18 would be empty and the
    king would (illegally) keep looping. The pydraughts oracle confirms the
    chain is exactly ``14x23x30x21`` — three captures, terminating at 21.
    """
    fen = "B:W18,25,26:BK14"
    board = CheckersBoard.from_fen(fen)
    moves = board.legal_moves()
    assert len(moves) == 1
    assert moves[0].pdn() == "14x23x30x21"
    # ``captured`` is in jump-sequence order: 18 jumped first (king lands 23),
    # then 26 (lands 30), then 25 (lands 21).
    assert moves[0].captured == (18, 26, 25)
    assert set(moves[0].captured) == {18, 25, 26}
    # No captured square is jumped twice — the un-jumpable flag held.
    assert len(set(moves[0].captured)) == len(moves[0].captured)
    # The oracle is the arbiter of the WCDF 1.19 end-of-sequence rule here.
    assert pdn_set(board) == oracle_pdn_set(fen)
    # After the move every captured man is gone and only the Red king remains.
    after = board.apply(moves[0])
    for cap in (18, 25, 26):
        assert after.cells[cap - 1] is None
    assert after.cells[21 - 1] == ("r", True)


@pytest.mark.unit
def test_circular_king_jump_lands_on_emptied_origin() -> None:
    """A king multi-jump may close a loop back onto its now-empty origin.

    WCDF 1.19/1.20: a started multi-jump continues until no capture remains.
    Red king on 14 inside the full ring of four White men 17,18,25,26: the
    king jumps all four and returns to its origin square 14, which is empty
    after the first hop. The captured pieces stay occupied during expansion
    (so they cannot be re-jumped), but the origin square does not.

    The engine must produce exactly the two four-capture loop sequences, each
    ending back on 14, matching the pydraughts oracle. Before this fix the
    engine read landing squares off the static original board, so square 14
    appeared occupied and the loop was truncated one capture early.
    """
    fen = "B:W17,18,25,26:BK14"
    board = CheckersBoard.from_fen(fen)
    pdns = pdn_set(board)
    assert pdns == {"14x21x30x23x14", "14x23x30x21x14"}
    assert pdns == oracle_pdn_set(fen)
    for m in board.legal_moves():
        # Every loop captures all four men exactly once and returns to 14.
        assert len(m.captured) == 4
        assert len(set(m.captured)) == 4
        assert m.origin == 14
        assert m.destination == 14
        # Applying the loop empties the four rings and re-seats the king on 14.
        after = board.apply(m)
        for cap in (17, 18, 25, 26):
            assert after.cells[cap - 1] is None
        assert after.cells[14 - 1] == ("r", True)


@pytest.mark.unit
def test_crowning_ends_turn() -> None:
    """A man jump landing on the king-row crowns and ends the turn (WCDF 1.16).

    Red man on 21 jumps White 25, landing on king-row square 30 and crowning.
    Even though a king on 30 could capture White 26, the sequence terminates —
    only the single jump 21x30 is legal.
    """
    board = CheckersBoard.from_fen("B:W25,26:B21")
    moves = board.legal_moves()
    assert len(moves) == 1
    assert moves[0].pdn() == "21x30"
    assert moves[0].captured == (25,)
    # After applying, the piece on 30 is a Red king and it is White's turn.
    after = board.apply(moves[0])
    assert after.cells[30 - 1] == ("r", True)
    assert after.turn == "w"


@pytest.mark.unit
def test_simple_man_move_crowns() -> None:
    """A man finishing a *simple* move on the king-row is crowned."""
    board = CheckersBoard.from_fen("B:W:B25")
    after = board.apply(CheckersMove(path=(25, 30), captured=()))
    assert after.cells[30 - 1] == ("r", True)


@pytest.mark.unit
def test_no_move_is_a_loss() -> None:
    """A side to move with no legal move loses — no stalemate draw (WCDF 1.30)."""
    board = CheckersBoard.from_fen("B:W5,6,9,10:B1")
    assert board.legal_moves() == ()
    assert board.is_loss_for("r") is True
    assert board.is_loss_for("w") is False
    assert board.is_terminal() is True
    assert board.winner() == "w"


@pytest.mark.unit
def test_multi_jump_double() -> None:
    """A double jump is generated as one fully-expanded move."""
    board = CheckersBoard.from_fen("B:W16,24:B11")
    moves = board.legal_moves()
    assert len(moves) == 1
    assert moves[0].path == (11, 20, 27)
    assert moves[0].captured == (16, 24)
    assert moves[0].pdn() == "11x20x27"


@pytest.mark.unit
def test_apply_removes_captured_pieces() -> None:
    """``apply`` removes every captured piece and moves the mover (design §2.5)."""
    board = CheckersBoard.from_fen("B:W16,24:B11")
    move = board.legal_moves()[0]
    after = board.apply(move)
    assert after.cells[16 - 1] is None
    assert after.cells[24 - 1] is None
    assert after.cells[11 - 1] is None
    assert after.cells[27 - 1] == ("r", False)
    assert after.turn == "w"


@pytest.mark.unit
def test_no_progress_counter() -> None:
    """The no-progress counter resets on man moves/captures, else increments."""
    # Two lone kings: a quiet king move increments the counter.
    board = CheckersBoard.from_fen("B:WK32:BK1")
    assert board.no_progress == 0
    after = board.apply(CheckersMove(path=(1, 5), captured=()))
    assert after.no_progress == 1
    after2 = after.apply(CheckersMove(path=(32, 27), captured=()))
    assert after2.no_progress == 2
    # A man move resets it to 0.
    board2 = CheckersBoard.from_fen("W:WK32:B9")
    moved = board2.apply(CheckersMove(path=(32, 27), captured=()))
    assert moved.no_progress == 1
    man_moved = moved.apply(CheckersMove(path=(9, 13), captured=()))
    assert man_moved.no_progress == 0


@pytest.mark.unit
def test_no_progress_draw_threshold() -> None:
    """``is_draw`` fires at the 80-ply (40-each) no-progress threshold."""
    cells = list(CheckersBoard.from_fen("B:WK32:BK1").cells)
    board = CheckersBoard(
        cells=tuple(cells),
        turn="r",
        no_progress=NO_PROGRESS_DRAW_PLIES,
        history=(),
    )
    assert board.is_draw() is True
    board_short = CheckersBoard(
        cells=tuple(cells),
        turn="r",
        no_progress=NO_PROGRESS_DRAW_PLIES - 1,
        history=(),
    )
    assert board_short.is_draw() is False


@pytest.mark.unit
def test_threefold_repetition_draw() -> None:
    """``is_draw`` fires when the position has occurred three times."""
    board = CheckersBoard.from_fen("B:WK32:BK1")
    # Shuffle the two kings back and forth to repeat positions.
    seq = [
        CheckersMove(path=(1, 5), captured=()),
        CheckersMove(path=(32, 27), captured=()),
        CheckersMove(path=(5, 1), captured=()),
        CheckersMove(path=(27, 32), captured=()),
    ]
    cur = board
    assert cur.is_draw() is False
    for _ in range(2):
        for mv in seq:
            cur = cur.apply(mv)
    # The start position (Red to move, kings on 1 and 32) has now occurred
    # three times: initial + two returns.
    assert cur.is_draw() is True


@pytest.mark.unit
def test_pdn_fen_start_round_trip() -> None:
    """The start position serializes to the pydraughts-form FEN and parses back."""
    board = CheckersBoard.initial()
    fen = board.to_fen()
    assert fen == (
        "B:W21,22,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,11,12"
    )
    parsed = CheckersBoard.from_fen(fen)
    assert parsed.cells == board.cells
    assert parsed.turn == board.turn


@pytest.mark.unit
def test_pdn_fen_kings_and_white_turn() -> None:
    """PDN-FEN handles king prefixes and the White-to-move token."""
    fen = "W:WK32:BK1"
    board = CheckersBoard.from_fen(fen)
    assert board.turn == "w"
    assert board.cells[32 - 1] == ("w", True)
    assert board.cells[1 - 1] == ("r", True)
    assert board.to_fen() == fen


# ---------------------------------------------------------------------------
# Property tests — hypothesis (directive 8)
# ---------------------------------------------------------------------------


def _reachable_boards(seed: int, max_plies: int) -> list[CheckersBoard]:
    """A deterministic random walk from the start; returns every visited board."""
    rng = random.Random(seed)
    board = CheckersBoard.initial()
    visited = [board]
    for _ in range(max_plies):
        moves = board.legal_moves()
        if not moves:
            break
        board = board.apply(rng.choice(moves))
        visited.append(board)
        if board.is_draw():
            break
    return visited


@pytest.mark.property
@given(seed=st.integers(min_value=0, max_value=10_000))
@settings(max_examples=60, deadline=None)
def test_property_pdn_fen_round_trip(seed: int) -> None:
    """parse∘serialize is identity on cells+turn for any reached position."""
    for board in _reachable_boards(seed, max_plies=40):
        parsed = CheckersBoard.from_fen(board.to_fen())
        assert parsed.cells == board.cells
        assert parsed.turn == board.turn
        # A second round-trip is stable.
        assert parsed.to_fen() == board.to_fen()


@pytest.mark.property
@given(seed=st.integers(min_value=0, max_value=10_000))
@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_property_apply_yields_valid_board(seed: int) -> None:
    """Every ``legal_moves`` entry, ``apply``-ed, yields a structurally valid board."""
    for board in _reachable_boards(seed, max_plies=40):
        for move in board.legal_moves():
            after = board.apply(move)
            # Length-32 cell tuple; turn flipped; every cell well-formed.
            assert len(after.cells) == 32
            assert after.turn != board.turn
            assert after.turn in ("r", "w")
            for cell in after.cells:
                if cell is not None:
                    colour, is_king = cell
                    assert colour in ("r", "w")
                    assert isinstance(is_king, bool)
            # The mover occupies its destination; it left its origin unless
            # the move is a circular king jump that lands back on its origin
            # square (a legal multi-jump — see the king-loop edge cases).
            assert after.cells[move.destination - 1] is not None
            if move.origin != move.destination:
                assert after.cells[move.origin - 1] is None
            # Captured squares are now empty. (For a circular jump the origin
            # is never a captured square, so this does not conflict above.)
            for cap in move.captured:
                assert after.cells[cap - 1] is None
            # Piece conservation: the captured side (the side to move on the
            # resulting board) loses exactly ``len(move.captured)`` pieces; the
            # moving side keeps all of its pieces.
            captured_side = after.turn
            moving_side = board.turn
            before_captured = sum(
                1 for c in board.cells if c is not None and c[0] == captured_side
            )
            after_captured = sum(
                1 for c in after.cells if c is not None and c[0] == captured_side
            )
            assert before_captured - after_captured == len(move.captured)
            before_moving = sum(
                1 for c in board.cells if c is not None and c[0] == moving_side
            )
            after_moving = sum(
                1 for c in after.cells if c is not None and c[0] == moving_side
            )
            assert before_moving == after_moving


@pytest.mark.property
@given(seed=st.integers(min_value=0, max_value=10_000))
@settings(max_examples=60, deadline=None)
def test_property_mandatory_capture_invariant(seed: int) -> None:
    """If any capture exists, every legal move is a capture (WCDF 1.20)."""
    for board in _reachable_boards(seed, max_plies=40):
        moves = board.legal_moves()
        if any(m.is_jump for m in moves):
            assert all(m.is_jump for m in moves)


# ---------------------------------------------------------------------------
# Differential tests vs pydraughts (directive 9 & 10)
# ---------------------------------------------------------------------------


@pytest.mark.differential
def test_perft_initial_position() -> None:
    """perft d=1..6 from the start equals the verified published values."""
    board = CheckersBoard.initial()
    expected = [7, 49, 302, 1469, 7361, 36768]
    produced = [perft(board, d) for d in range(1, 7)]
    assert produced == expected


@pytest.mark.differential
@pytest.mark.parametrize("label,fen", EDGE_CASES, ids=[c[0] for c in EDGE_CASES])
def test_differential_edge_cases(label: str, fen: str) -> None:
    """Each curated edge case has the same move set as pydraughts (directive 9)."""
    board = CheckersBoard.from_fen(fen)
    assert pdn_set(board) == oracle_pdn_set(fen), f"move-set mismatch on {label}"


@pytest.mark.differential
def test_differential_random_walk() -> None:
    """A 300+ position seeded random walk: engine move-set == pydraughts move-set.

    At each reached position the engine's set of legal moves (as PDN strings)
    must equal pydraughts' set. The walk follows the engine's own moves so the
    two stay on identical positions; the FEN is the shared comparison medium.
    """
    rng = random.Random(20260520)
    board = CheckersBoard.initial()
    positions_checked = 0
    walks = 0
    # Keep restarting fresh walks until at least 300 positions are compared.
    while positions_checked < 300:
        walks += 1
        board = CheckersBoard.initial()
        for _ in range(200):
            fen = board.to_fen()
            engine_moves = pdn_set(board)
            oracle_moves = oracle_pdn_set(fen)
            assert engine_moves == oracle_moves, (
                f"move-set mismatch at {fen}: "
                f"engine-only={engine_moves - oracle_moves}, "
                f"oracle-only={oracle_moves - engine_moves}"
            )
            positions_checked += 1
            moves = board.legal_moves()
            if not moves:
                break
            board = board.apply(rng.choice(moves))
            if board.is_draw():
                break
    assert positions_checked >= 300, positions_checked


@pytest.mark.differential
def test_differential_oracle_driven_walk() -> None:
    """A 300+ position seeded walk that steps along PYDRAUGHTS' chosen moves.

    The engine-following walk (``test_differential_random_walk``) has a blind
    spot the analyst named: it advances along the *engine's* generated moves,
    so if the engine omits a legal continuation that move is simply never
    taken and the omission stays invisible.

    This walk closes that blind spot. At every position it still asserts the
    engine's full legal-move set equals pydraughts' set, but it advances by
    picking the next move from *pydraughts'* legal moves and replaying that
    PDN string on the engine. The two stay synchronised because the move set
    is asserted equal first — but the path through the tree is now chosen by
    the oracle, so an engine-omitted branch can be entered and caught.

    Deterministically seeded; at least 300 positions are compared.
    """

    def engine_move_for_pdn(board: CheckersBoard, pdn: str) -> CheckersMove:
        """The engine move whose PDN string is ``pdn`` (they are equal sets)."""
        for move in board.legal_moves():
            if move.pdn() == pdn:
                return move
        raise AssertionError(
            f"oracle move {pdn!r} absent from engine legal set "
            f"{sorted(pdn_set(board))} at {board.to_fen()}"
        )

    rng = random.Random(20260521)
    positions_checked = 0
    walks = 0
    while positions_checked < 300:
        walks += 1
        board = CheckersBoard.initial()
        for _ in range(200):
            fen = board.to_fen()
            engine_moves = pdn_set(board)
            oracle_moves = oracle_pdn_set(fen)
            assert engine_moves == oracle_moves, (
                f"move-set mismatch at {fen}: "
                f"engine-only={engine_moves - oracle_moves}, "
                f"oracle-only={oracle_moves - engine_moves}"
            )
            positions_checked += 1
            if not oracle_moves:
                break
            # Advance along an ORACLE-chosen move, replayed on the engine.
            chosen_pdn = rng.choice(sorted(oracle_moves))
            board = board.apply(engine_move_for_pdn(board, chosen_pdn))
            if board.is_draw():
                break
    assert positions_checked >= 300, positions_checked


# ---------------------------------------------------------------------------
# Invalid PDN-FEN tests (directive 11)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_fen",
    [
        "B:W1,,2:B",  # doubled comma — empty middle token
        "B:W,1,2:B",  # leading comma — empty first token
        "B:W1,2,:B",  # trailing comma — empty last token
        "B:W:B1,,2",  # doubled comma in the Red field
        "B:W:B5,",  # trailing comma in the Red field
        "B:W,:B",  # a lone comma is a single empty token
    ],
)
def test_from_fen_rejects_empty_square_tokens(bad_fen: str) -> None:
    """``from_fen`` rejects empty list elements from doubled/edge commas.

    Previously these were silently dropped, so ``B:W1,,2:B`` parsed as
    ``B:W1,2:B`` (directive 11 / analyst MINOR). Malformed FEN must raise.
    """
    with pytest.raises(ValueError):
        CheckersBoard.from_fen(bad_fen)


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_fen",
    [
        "B:W1:B:extra",  # four colon-separated fields, not three
        "B:W1",  # only two fields
        "X:W1:B2",  # bad turn token
        "B:X1:B2",  # wrong colour tag on the first field
        "B:W1:X2",  # wrong colour tag on the second field
        "B:W33:B1",  # square out of range (> 32)
        "B:W0:B1",  # square out of range (< 1)
        "B:W1:B1",  # the same square claimed by both colours
        "B:W1,1:B2",  # the same square listed twice
        "B:Wx:B1",  # non-numeric square token
        "B:WK:B1",  # bare king prefix with no number
    ],
)
def test_from_fen_rejects_malformed_fen(bad_fen: str) -> None:
    """``from_fen`` rejects structurally malformed PDN-FEN of every shape."""
    with pytest.raises(ValueError):
        CheckersBoard.from_fen(bad_fen)
