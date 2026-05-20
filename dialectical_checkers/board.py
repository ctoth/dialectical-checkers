"""``CheckersBoard``, ``CheckersMove``, move-gen, PDN-FEN, perft.

The English-draughts (American checkers, 8x8) board substrate — design §2 of
``notes/checkers-design.md`` and the verified WCDF rules of
``notes/checkers-port-plan.md §5.1``.

Squares use PDN/English-draughts numbering 1-32; the internal cell index is the
PDN square minus one (``idx = pdn - 1``). The numbering and the diagonal
geometry were verified square-by-square against pydraughts' English variant.

Move generation never does coordinate arithmetic: it walks two static
precomputed tables, ``STEP`` and ``JUMP`` (design §2.1), built once from the
8x8 dark-square geometry. This is the deliberate design choice that designs out
every dark-square parity bug.

No oracle is imported here. ``perft`` is pure. pydraughts is a *test* dependency
only (the non-oracle-strength stance, design §2.7).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

# --- Geometry ---------------------------------------------------------------
#
# 32 dark playable squares numbered 1-32; internal index 0..31 = pdn - 1.
# Standard English-draughts numbering: 8 rows of 4 dark squares, row 0 at the
# top. Square N -> (row, col) on the 8x8 grid:
#   row = (N-1)//4, idx_in_row = (N-1)%4,
#   col = 2*idx_in_row + (1 if row even else 0).
# Row increases downward; Red moves toward higher rows/numbers, White toward
# lower. Verified to reproduce pydraughts' adjacency for all 32 squares.

NUM_SQUARES = 32

# Direction codes. Rows increase "down the board" (toward Red's king-row).
NE = 0  # row+1, col+1
NW = 1  # row+1, col-1
SE = 2  # row-1, col+1
SW = 3  # row-1, col-1
_DIRS = (NE, NW, SE, SW)
_DELTA = {NE: (1, 1), NW: (1, -1), SE: (-1, 1), SW: (-1, -1)}

# Red ("r") is the side on squares 1-12 that moves first; it advances toward
# higher numbers (increasing row). "Forward" directions per colour:
_FORWARD = {"r": (NE, NW), "w": (SE, SW)}

RED_KING_ROW = 7  # squares 29-32 — Red crowns here
WHITE_KING_ROW = 0  # squares 1-4 — White crowns here


def _coord(idx: int) -> tuple[int, int]:
    """Return the ``(row, col)`` 8x8 grid coordinate of internal index ``idx``."""
    row = idx // 4
    in_row = idx % 4
    col = 2 * in_row + (1 if row % 2 == 0 else 0)
    return row, col


def _build_tables() -> tuple[
    tuple[tuple[int | None, ...], ...],
    tuple[tuple[tuple[int, int] | None, ...], ...],
]:
    """Precompute the ``STEP`` and ``JUMP`` neighbour tables (design §2.1)."""
    coord_to_idx: dict[tuple[int, int], int] = {}
    for idx in range(NUM_SQUARES):
        coord_to_idx[_coord(idx)] = idx

    step: list[tuple[int | None, ...]] = []
    jump: list[tuple[tuple[int, int] | None, ...]] = []
    for idx in range(NUM_SQUARES):
        row, col = _coord(idx)
        step_row: list[int | None] = []
        jump_row: list[tuple[int, int] | None] = []
        for d in _DIRS:
            dr, dc = _DELTA[d]
            over = coord_to_idx.get((row + dr, col + dc))
            land = coord_to_idx.get((row + 2 * dr, col + 2 * dc))
            step_row.append(over)
            if over is not None and land is not None:
                jump_row.append((over, land))
            else:
                jump_row.append(None)
        step.append(tuple(step_row))
        jump.append(tuple(jump_row))
    return tuple(step), tuple(jump)


# STEP[idx][dir]  -> neighbour index or None.
# JUMP[idx][dir]  -> (over_idx, land_idx) or None.
STEP, JUMP = _build_tables()


# --- Cells ------------------------------------------------------------------

#: A cell holding a piece: ``(colour, is_king)``; ``colour`` is "r" or "w".
Cell = tuple[str, bool]

#: A repeatable-position identity: ``(cells, turn)``. Used as-is for
#: threefold-repetition detection — a stable, deterministic, collision-free
#: value (never a process-randomized hash).
PositionId = tuple[tuple["Cell | None", ...], str]

_KING_ROW = {"r": RED_KING_ROW, "w": WHITE_KING_ROW}
_OPPONENT = {"r": "w", "w": "r"}

#: Plies of no-progress (per WCDF 1.32.2: 40 moves *each* side) that draw the
#: game — 40 Red + 40 White = 80 plies on the counter.
NO_PROGRESS_DRAW_PLIES = 80


# --- Move type --------------------------------------------------------------


@dataclass(frozen=True, order=True)
class CheckersMove:
    """A draughts move (design §2.3).

    ``path`` lists the visited squares as **PDN numbers** (1-32): length 2 for a
    simple move, length >= 2 for a jump chain. ``captured`` lists the captured
    squares as PDN numbers; it is empty for a simple move. Ordering is by
    ``(path, captured)`` for deterministic move ordering.
    """

    path: tuple[int, ...]
    captured: tuple[int, ...]

    @property
    def is_jump(self) -> bool:
        """True iff this move captures at least one piece."""
        return bool(self.captured)

    @property
    def origin(self) -> int:
        """The PDN square the moving piece started on."""
        return self.path[0]

    @property
    def destination(self) -> int:
        """The PDN square the moving piece finished on."""
        return self.path[-1]

    def pdn(self) -> str:
        """Render in PDN move notation: ``a-b`` simple, ``aXbX...`` jump."""
        sep = "x" if self.is_jump else "-"
        return sep.join(str(sq) for sq in self.path)


# --- Board ------------------------------------------------------------------


def _initial_cells() -> tuple[Cell | None, ...]:
    """The WCDF start: Red on 1-12, White on 21-32, 13-20 empty (port-plan §5.1)."""
    cells: list[Cell | None] = [None] * NUM_SQUARES
    for pdn in range(1, 13):
        cells[pdn - 1] = ("r", False)
    for pdn in range(21, 33):
        cells[pdn - 1] = ("w", False)
    return tuple(cells)


@dataclass(frozen=True)
class CheckersBoard:
    """Immutable English-draughts position (design §2.2).

    ``cells`` is a length-32 tuple indexed by internal index (PDN - 1); each
    entry is ``None`` or ``(colour, is_king)``. ``turn`` is ``"r"`` or ``"w"``
    (Red moves first). ``no_progress`` counts plies since the last man move or
    capture. ``history`` holds the position *identities* — the stable
    ``(cells, turn)`` tuples — for threefold-repetition detection.
    """

    cells: tuple[Cell | None, ...] = field(default_factory=_initial_cells)
    turn: str = "r"
    no_progress: int = 0
    history: tuple[PositionId, ...] = ()

    # -- construction --------------------------------------------------------

    @classmethod
    def initial(cls) -> CheckersBoard:
        """Return the standard WCDF starting position, Red to move."""
        board = cls(cells=_initial_cells(), turn="r", no_progress=0, history=())
        return replace(board, history=(board._position_id(),))

    # -- position identity ---------------------------------------------------

    def _position_id(self) -> PositionId:
        """The repeatable-position identity ``(cells, turn)`` (design §2.6).

        Stored verbatim in ``history`` — a stable, deterministic, collision-free
        tuple. It deliberately does NOT call ``hash``: Python's string hash is
        process-randomized, so a hash would make repetition detection
        collision-prone and persisted/debugged histories unstable across runs.
        ``cells`` and ``turn`` are themselves immutable and hashable, so the
        tuple works directly as a dict/set key and ``tuple.count`` comparand.
        """
        return (self.cells, self.turn)

    # -- move generation -----------------------------------------------------

    def legal_moves(self) -> tuple[CheckersMove, ...]:
        """Return the legal move set for the side to move (design §2.4).

        Mandatory capture (WCDF 1.20): if any jump exists, the jump set *is* the
        legal set; otherwise the simple moves are returned. Always sorted, for
        deterministic move ordering.
        """
        jumps = self._jump_moves()
        if jumps:
            return tuple(sorted(jumps))
        return tuple(sorted(self._simple_moves()))

    def _simple_moves(self) -> list[CheckersMove]:
        """Non-capturing moves: men step forward one square, kings any diagonal."""
        moves: list[CheckersMove] = []
        side = self.turn
        for idx in range(NUM_SQUARES):
            cell = self.cells[idx]
            if cell is None or cell[0] != side:
                continue
            is_king = cell[1]
            dirs = _DIRS if is_king else _FORWARD[side]
            for d in dirs:
                dest = STEP[idx][d]
                if dest is not None and self.cells[dest] is None:
                    moves.append(
                        CheckersMove(path=(idx + 1, dest + 1), captured=())
                    )
        return moves

    def _jump_moves(self) -> list[CheckersMove]:
        """All fully-expanded multi-jump sequences for the side to move."""
        moves: list[CheckersMove] = []
        side = self.turn
        for idx in range(NUM_SQUARES):
            cell = self.cells[idx]
            if cell is None or cell[0] != side:
                continue
            self._expand_jumps(
                cur=idx,
                is_king=cell[1],
                path=[idx],
                captured=[],
                out=moves,
            )
        return moves

    def _expand_jumps(
        self,
        cur: int,
        is_king: bool,
        path: list[int],
        captured: list[int],
        out: list[CheckersMove],
    ) -> None:
        """Depth-first multi-jump expansion from internal index ``cur``.

        Honours every subtlety of design §2.5 / port-plan §5.1:

        * a piece is jumped at most once (``captured`` membership);
        * captured pieces are removed only at sequence end, so their squares
          stay occupied during expansion — a landing square may be neither
          currently occupied nor an already-captured square;
        * men capture forward only; non-flying kings capture one square any
          diagonal;
        * crowning ends the turn — when a *man* lands on its king-row the
          sequence terminates here even if further jumps exist.
        """
        side = self.turn
        opponent = _OPPONENT[side]
        dirs = _DIRS if is_king else _FORWARD[side]
        extended = False
        for d in dirs:
            hop = JUMP[cur][d]
            if hop is None:
                continue
            over, land = hop
            if over in captured:
                # A piece may be jumped only once (WCDF 1.20).
                continue
            over_cell = self.cells[over]
            if over_cell is None or over_cell[0] != opponent:
                continue
            # The landing square must be vacant *in the mid-jump board state*,
            # which is NOT ``self.cells`` (the static original board):
            #
            #  * the moving piece's own origin square (``path[0]``) is empty
            #    after the first hop — the piece left it — even though
            #    ``self.cells`` still shows it occupied. A legal circular king
            #    jump may land back on that now-empty origin, so it must not be
            #    treated as blocked (WCDF 1.19/1.20).
            #  * captured pieces are removed only at sequence end (WCDF 1.19),
            #    so an already-captured square stays occupied and un-landable
            #    during expansion — tracked by ``captured``, not ``self.cells``.
            #  * every other square is read from ``self.cells`` as usual; the
            #    intermediate landing squares of ``path`` were empty to begin
            #    with and the piece has since vacated them.
            origin = path[0]
            land_occupied = self.cells[land] is not None and land != origin
            if land_occupied or land in captured:
                continue
            extended = True
            new_path = path + [land]
            new_captured = captured + [over]
            crowned = (not is_king) and _coord(land)[0] == _KING_ROW[side]
            if crowned:
                # Crowning ends the turn even mid-multi-jump (WCDF 1.16/1.19).
                out.append(
                    CheckersMove(
                        path=tuple(sq + 1 for sq in new_path),
                        captured=tuple(sq + 1 for sq in new_captured),
                    )
                )
            else:
                self._expand_jumps(
                    cur=land,
                    is_king=is_king,
                    path=new_path,
                    captured=new_captured,
                    out=out,
                )
        if not extended and captured:
            # No further jump from here: emit the completed sequence.
            out.append(
                CheckersMove(
                    path=tuple(sq + 1 for sq in path),
                    captured=tuple(sq + 1 for sq in captured),
                )
            )

    # -- applying a move -----------------------------------------------------

    def apply(self, move: CheckersMove) -> CheckersBoard:
        """Return a new board with ``move`` played (design §2.5).

        Moves the piece along ``path``, removes ``captured`` at the end, crowns
        a man that finished on its king-row, flips ``turn``, updates the
        no-progress counter (reset to 0 on any man move or any capture, else
        +1), and appends the new position identity to ``history``.
        """
        side = self.turn
        origin = move.origin - 1
        dest = move.destination - 1
        cell = self.cells[origin]
        if cell is None:
            raise ValueError(f"no piece on origin square {move.origin}")
        if cell[0] != side:
            raise ValueError(
                f"piece on square {move.origin} is not the side to move"
            )

        cells = list(self.cells)
        cells[origin] = None
        for cap in move.captured:
            cells[cap - 1] = None

        is_king = cell[1]
        crowned = (not is_king) and _coord(dest)[0] == _KING_ROW[side]
        cells[dest] = (side, is_king or crowned)

        man_move = not is_king
        if man_move or move.is_jump:
            no_progress = 0
        else:
            no_progress = self.no_progress + 1

        new_board = CheckersBoard(
            cells=tuple(cells),
            turn=_OPPONENT[side],
            no_progress=no_progress,
            history=self.history,
        )
        return replace(
            new_board, history=self.history + (new_board._position_id(),)
        )

    # -- terminal & draw -----------------------------------------------------

    def is_loss_for(self, side: str) -> bool:
        """True iff ``side`` is to move and has no legal move (design §2.6).

        A side to move with no legal move *loses* (WCDF 1.30) — there is no
        stalemate draw in draughts.
        """
        if side != self.turn:
            return False
        return not self.legal_moves()

    def is_terminal(self) -> bool:
        """True iff the game is over: the side to move has no legal move."""
        return not self.legal_moves()

    def winner(self) -> str | None:
        """Return the winning side, or ``None`` if the game is not (yet) over.

        The side to move with no legal move loses, so the *other* side wins.
        """
        if self.legal_moves():
            return None
        return _OPPONENT[self.turn]

    def is_draw(self) -> bool:
        """True iff the position is drawn (design §2.6).

        Threefold repetition (the current position appearing three times in
        ``history``), or the WCDF 1.32.2 no-progress rule — 40 moves each side
        with no man-advance and no capture (80 plies on the counter).
        """
        if self.no_progress >= NO_PROGRESS_DRAW_PLIES:
            return True
        if self.history:
            current = self.history[-1]
            if self.history.count(current) >= 3:
                return True
        return False

    # -- PDN-FEN I/O ---------------------------------------------------------

    def to_fen(self) -> str:
        """Serialize to the PDN FEN tag form ``<turn>:W...:B...`` (design §2.7).

        Turn token ``B`` = Red to move, ``W`` = White to move. Each square list
        is comma-separated PDN numbers; a king is prefixed ``K``. Matches the
        pydraughts English-variant FEN exactly: pydraughts BLACK is the engine's
        Red.
        """
        white: list[str] = []
        black: list[str] = []
        for idx in range(NUM_SQUARES):
            cell = self.cells[idx]
            if cell is None:
                continue
            colour, is_king = cell
            token = f"K{idx + 1}" if is_king else f"{idx + 1}"
            if colour == "w":
                white.append(token)
            else:
                black.append(token)
        turn_token = "B" if self.turn == "r" else "W"
        return f"{turn_token}:W{','.join(white)}:B{','.join(black)}"

    @classmethod
    def from_fen(cls, fen: str) -> CheckersBoard:
        """Parse a PDN FEN tag (design §2.7) into a fresh board.

        Accepts the form ``<turn>:W<squares>:B<squares>`` — turn token ``B``
        (Red) or ``W`` (White); each square list comma-separated PDN numbers
        with an optional ``K`` king prefix; empty lists permitted.
        """
        parts = fen.strip().split(":")
        if len(parts) != 3:
            raise ValueError(f"malformed PDN-FEN, expected 3 fields: {fen!r}")
        turn_token, first, second = parts
        if turn_token == "B":
            turn = "r"
        elif turn_token == "W":
            turn = "w"
        else:
            raise ValueError(f"bad turn token {turn_token!r} in PDN-FEN")

        cells: list[Cell | None] = [None] * NUM_SQUARES

        def place(field_text: str, colour: str) -> None:
            if not field_text:
                raise ValueError(f"PDN-FEN field missing colour tag: {fen!r}")
            tag, body = field_text[0], field_text[1:]
            if (colour == "w" and tag != "W") or (colour == "r" and tag != "B"):
                raise ValueError(f"PDN-FEN field {field_text!r} has wrong tag")
            if not body:
                return
            for raw_token in body.split(","):
                token = raw_token.strip()
                if not token:
                    # An empty list element — produced by a doubled comma
                    # (``W1,,2``), a leading comma (``W,1``) or a trailing
                    # comma (``W1,``) — is malformed PDN-FEN, not an empty
                    # list. Reject it rather than silently dropping it.
                    raise ValueError(
                        f"empty square token in PDN-FEN field {field_text!r}: "
                        f"{fen!r}"
                    )
                is_king = token.startswith("K")
                number_text = token[1:] if is_king else token
                try:
                    pdn = int(number_text)
                except ValueError:
                    raise ValueError(
                        f"non-numeric PDN square token {token!r} in {fen!r}"
                    ) from None
                if not 1 <= pdn <= NUM_SQUARES:
                    raise ValueError(f"PDN square {pdn} out of range in {fen!r}")
                if cells[pdn - 1] is not None:
                    raise ValueError(f"PDN square {pdn} listed twice in {fen!r}")
                cells[pdn - 1] = (colour, is_king)

        place(first, "w")
        place(second, "r")

        board = cls(cells=tuple(cells), turn=turn, no_progress=0, history=())
        return replace(board, history=(board._position_id(),))


# --- perft ------------------------------------------------------------------


def perft(board: CheckersBoard, depth: int) -> int:
    """Count leaf nodes of the move tree to ``depth`` (design §2.7).

    Pure: imports no oracle. ``perft(board, 0) == 1``; a terminal position
    (no legal moves) contributes 0 below the requested depth.
    """
    if depth < 0:
        raise ValueError("perft depth must be non-negative")
    if depth == 0:
        return 1
    moves = board.legal_moves()
    if not moves:
        return 0
    total = 0
    for move in moves:
        total += perft(board.apply(move), depth - 1)
    return total
