"""Portable Draughts Notation (PDN) game I/O.

Phase 6 of ``notes/checkers-port-plan.md`` (the match-running harness). PDN is
the draughts analog of chess's PGN — there is no UCI for draughts (port-plan
§6). This module parses a PDN game (the seven-tag roster, the optional ``FEN``
tag for a non-standard start, the movetext, the result token) and serialises a
played game back to PDN.

Move notation follows what ``CheckersMove.pdn()`` already renders: ``a-b`` for
a simple move and ``aXbX...`` for a jump chain (board.py §2.3). PDN movetext
conventionally uses ``x`` for jumps; the parser accepts ``x`` or ``X`` and
serialisation emits lowercase ``x`` (the ``CheckersMove`` rendering).

This module imports only ``dialectical_checkers`` + the stdlib (port-plan §8 —
no oracle in the harness; pydraughts is a test dependency only).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from dialectical_checkers.board import CheckersBoard, CheckersMove

# --- Result tokens ----------------------------------------------------------
#
# PDN result tokens. Draughts uses the same three-token vocabulary as chess
# plus ``*`` for an unterminated game.
RESULT_RED_WIN = "1-0"
RESULT_WHITE_WIN = "0-1"
RESULT_DRAW = "1/2-1/2"
RESULT_UNTERMINATED = "*"
_RESULT_TOKENS = frozenset(
    {RESULT_RED_WIN, RESULT_WHITE_WIN, RESULT_DRAW, RESULT_UNTERMINATED}
)


@dataclass(frozen=True)
class PdnGame:
    """A parsed or assembled PDN game.

    ``tags`` is the tag-pair roster (``Event``, ``Result``, an optional ``FEN``
    for a non-standard start, …). ``moves`` is the played move sequence in
    order. ``result`` is the PDN result token. ``setup_fen`` is the ``FEN`` tag
    value when the game does not start from the standard position, else
    ``None`` — the start position is then ``CheckersBoard.initial()``.
    """

    moves: tuple[CheckersMove, ...] = ()
    result: str = RESULT_UNTERMINATED
    tags: dict[str, str] = field(default_factory=dict)
    setup_fen: str | None = None

    def initial_board(self) -> CheckersBoard:
        """Return the position the game starts from.

        ``CheckersBoard.from_fen(setup_fen)`` when a ``FEN`` tag is present,
        otherwise the standard WCDF start ``CheckersBoard.initial()``.
        """
        if self.setup_fen is not None:
            return CheckersBoard.from_fen(self.setup_fen)
        return CheckersBoard.initial()

    def positions(self) -> tuple[CheckersBoard, ...]:
        """Replay the game, returning every position from start to end.

        The returned tuple has ``len(moves) + 1`` entries — the start position
        followed by the position after each move. Each move is validated
        against ``board.legal_moves()``; an illegal move raises ``ValueError``.
        """
        board = self.initial_board()
        out: list[CheckersBoard] = [board]
        for ply, move in enumerate(self.moves, start=1):
            if move not in board.legal_moves():
                raise ValueError(
                    f"PDN move {move.pdn()!r} at ply {ply} is illegal in "
                    f"position {board.to_fen()!r}"
                )
            board = board.apply(move)
            out.append(board)
        return tuple(out)


# --- Move-token parsing -----------------------------------------------------

#: A single PDN move token: PDN squares joined by ``-`` (simple) or ``x``/``X``
#: (jump). The numbers-and-separators shape; semantic validation follows.
_MOVE_TOKEN_RE = re.compile(r"^\d+(?:[-xX]\d+)+$")

#: A move-number prefix in movetext, e.g. ``12.`` or ``12...``.
_MOVE_NUMBER_RE = re.compile(r"^\d+\.+$")

#: A ``[Tag "value"]`` pair. The value may contain escaped quotes.
_TAG_RE = re.compile(r'^\[\s*(\w+)\s*"((?:[^"\\]|\\.)*)"\s*\]\s*$')

#: A ``{ ... }`` comment span in movetext.
_COMMENT_RE = re.compile(r"\{[^}]*\}")

#: A ``( ... )`` recursive-variation span (one nesting level).
_VARIATION_RE = re.compile(r"\([^()]*\)")


def parse_move_token(token: str) -> CheckersMove:
    """Parse a single PDN move token into a :class:`CheckersMove`.

    ``a-b`` is a simple move; ``axb`` / ``aXbX...`` a jump chain. PDN movetext
    gives only the visited squares — it does not list the captured squares — so
    the captured set is *reconstructed* from the jump path geometry: a jump hop
    captures the square the geometry passes over (board.py ``JUMP`` table).

    A token must use a *consistent* separator family: either the simple
    separator ``-`` or the jump separators ``x``/``X`` — never both. A token
    that mixes them (e.g. ``10x17-26``) is malformed and raises ``ValueError``.

    Raises ``ValueError`` for a malformed token.
    """
    text = token.strip()
    if not _MOVE_TOKEN_RE.match(text):
        raise ValueError(f"malformed PDN move token: {token!r}")
    has_simple_sep = "-" in text
    has_jump_sep = "x" in text or "X" in text
    if has_simple_sep and has_jump_sep:
        raise ValueError(
            f"PDN move token mixes simple ('-') and jump ('x') "
            f"separators: {token!r}"
        )
    is_jump = has_jump_sep
    sep = "x" if is_jump else "-"
    raw_squares = re.split(r"[-xX]", text)
    try:
        squares = tuple(int(s) for s in raw_squares)
    except ValueError:  # pragma: no cover - regex already constrains digits
        raise ValueError(f"non-numeric square in PDN token {token!r}") from None
    for sq in squares:
        if not 1 <= sq <= 32:
            raise ValueError(f"PDN square {sq} out of range in {token!r}")
    if not is_jump:
        if len(squares) != 2:
            raise ValueError(
                f"a simple PDN move must have exactly two squares: {token!r}"
            )
        return CheckersMove(path=squares, captured=())
    captured = _captured_for_path(squares)
    return CheckersMove(path=squares, captured=captured)


def _captured_for_path(squares: tuple[int, ...]) -> tuple[int, ...]:
    """Reconstruct the captured squares of a jump path from board geometry.

    For each consecutive (from, to) hop, find the board ``JUMP`` entry whose
    landing square is ``to``; the captured square is the one jumped over. A hop
    that is not a legal jump shape raises ``ValueError``.
    """
    # Imported lazily to keep the geometry tables an internal board detail.
    from dialectical_checkers.board import JUMP

    captured: list[int] = []
    for frm, to in zip(squares, squares[1:]):
        over: int | None = None
        for hop in JUMP[frm - 1]:
            if hop is not None and hop[1] + 1 == to:
                over = hop[0] + 1
                break
        if over is None:
            raise ValueError(
                f"PDN jump hop {frm}x{to} is not a legal jump shape"
            )
        captured.append(over)
    return tuple(captured)


# --- Game parsing -----------------------------------------------------------


def parse_pdn(text: str) -> PdnGame:
    """Parse a single PDN game from ``text`` into a :class:`PdnGame`.

    Handles the tag-pair roster (including an optional ``FEN`` setup tag),
    ``{ }`` comments, ``( )`` variations (discarded — only the mainline is
    kept), move-number prefixes, and the trailing result token. The movetext
    move tokens are turned into :class:`CheckersMove` values; their captured
    sets are reconstructed from board geometry (:func:`parse_move_token`).

    Raises ``ValueError`` for malformed tags or move tokens.
    """
    tags: dict[str, str] = {}
    movetext_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("["):
            match = _TAG_RE.match(line)
            if match is None:
                raise ValueError(f"malformed PDN tag line: {raw_line!r}")
            key, value = match.group(1), match.group(2)
            tags[key] = value.replace('\\"', '"').replace("\\\\", "\\")
        else:
            movetext_lines.append(line)

    movetext = " ".join(movetext_lines)
    movetext = _COMMENT_RE.sub(" ", movetext)
    # Strip variations until none remain (handles nesting one level at a time).
    while True:
        stripped = _VARIATION_RE.sub(" ", movetext)
        if stripped == movetext:
            break
        movetext = stripped

    moves: list[CheckersMove] = []
    result = RESULT_UNTERMINATED
    result_seen = False
    for token in movetext.split():
        if token in _RESULT_TOKENS:
            result = token
            result_seen = True
            continue
        if _MOVE_NUMBER_RE.match(token):
            continue
        moves.append(parse_move_token(token))
    if not result_seen and "Result" in tags and tags["Result"] in _RESULT_TOKENS:
        result = tags["Result"]

    setup_fen = tags.get("FEN")
    return PdnGame(
        moves=tuple(moves),
        result=result,
        tags=tags,
        setup_fen=setup_fen,
    )


# --- Game serialisation -----------------------------------------------------

#: The conventional PDN seven-tag roster order; extra tags follow in insertion
#: order. ``FEN`` (and its companion ``SetUp``) come after the roster.
_ROSTER_ORDER = (
    "Event",
    "Site",
    "Date",
    "Round",
    "Red",
    "White",
    "Result",
)


def _escape_tag_value(value: str) -> str:
    """Escape a tag value for the ``[Key "value"]`` form."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def render_pdn(game: PdnGame, *, moves_per_line: int = 8) -> str:
    """Serialise a :class:`PdnGame` to PDN text.

    Emits the tag roster (roster order first, then any extra tags, then
    ``FEN``/``SetUp`` when a non-standard start is set), a blank line, then the
    numbered movetext with the result token. A move pair gets one move number;
    ``moves_per_line`` numbered pairs are written per line.
    """
    tags = dict(game.tags)
    tags.setdefault("Result", game.result)
    if game.setup_fen is not None:
        tags.setdefault("SetUp", "1")
        tags.setdefault("FEN", game.setup_fen)

    lines: list[str] = []
    written: set[str] = set()
    for key in _ROSTER_ORDER:
        value = tags.get(key, "?" if key != "Result" else game.result)
        lines.append(f'[{key} "{_escape_tag_value(value)}"]')
        written.add(key)
    for key, value in tags.items():
        if key in written:
            continue
        lines.append(f'[{key} "{_escape_tag_value(value)}"]')
        written.add(key)

    lines.append("")

    tokens: list[str] = []
    for i in range(0, len(game.moves), 2):
        number = i // 2 + 1
        tokens.append(f"{number}.")
        tokens.append(game.moves[i].pdn())
        if i + 1 < len(game.moves):
            tokens.append(game.moves[i + 1].pdn())
    tokens.append(game.result)

    # Wrap the movetext: ``moves_per_line`` numbered pairs per line. Each pair
    # is up to three tokens (number, red move, white move); the result token
    # tails the final line.
    move_lines: list[str] = []
    current: list[str] = []
    pairs_on_line = 0
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        current.append(token)
        if _MOVE_NUMBER_RE.match(token):
            pairs_on_line += 1
        idx += 1
        if pairs_on_line >= moves_per_line and (
            idx >= len(tokens) or _MOVE_NUMBER_RE.match(tokens[idx])
        ):
            move_lines.append(" ".join(current))
            current = []
            pairs_on_line = 0
    if current:
        move_lines.append(" ".join(current))

    lines.extend(move_lines)
    return "\n".join(lines) + "\n"
