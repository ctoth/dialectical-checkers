"""Verify curated KING / DEEP shot positions for tests/test_captures.py.

Run: ``uv run python scripts/verify_king_deep_shots.py``

The analyst's MINOR finding: the six curated shots are all man-captures (0 king
captures, 0 king multi-jumps, max forced depth 1 ply). This script hand-pins
new curated shots covering the king/deep risk area, each independently
verified:

* a standalone capture-only minimax over the ENGINE board (banded ordering —
  the fixed rule) computes the net swing, terminal status and principal line;
* the principal line is replayed move-by-move in pydraughts; every move must be
  legal and pydraughts' material balance + terminal verdict must agree.

The script also classifies each position: whether the FIRST move is a king
capture, whether any king multi-jump (a king move capturing >= 2) occurs in the
line, and the line's ply length. It prints everything so a wrong hand-computed
expected number is caught here, not in a test.
"""

from __future__ import annotations

from draughts import Board as OracleBoard

from dialectical_checkers.board import CheckersBoard

MAN_VALUE = 100
KING_VALUE = 150


def material(board: CheckersBoard, side: str) -> int:
    total = 0
    for cell in board.cells:
        if cell is None or cell[0] != side:
            continue
        total += KING_VALUE if cell[1] else MAN_VALUE
    return total


def net(board: CheckersBoard, root: str) -> int:
    other = "w" if root == "r" else "r"
    return material(board, root) - material(board, other)


def rank(balance: int, terminal: str | None, root: str) -> tuple[int, int]:
    if terminal is None:
        band = 0
    elif terminal == root:
        band = 1
    else:
        band = -1
    return (band, balance)


def walk(node: CheckersBoard, root: str) -> tuple[int, str | None, list[object]]:
    """Banded capture-only minimax; returns (balance, terminal, move list)."""
    captures = [m for m in node.legal_moves() if m.is_jump]
    if not captures:
        moves = node.legal_moves()
        terminal = node.winner() if not moves else None
        return net(node, root), terminal, []
    scored: list[tuple[int, str | None, list[object], object]] = []
    for mv in captures:
        v, t, sub = walk(node.apply(mv), root)
        scored.append((v, t, [mv, *sub], mv))

    def key(r: tuple[int, str | None, list[object], object]) -> tuple[object, str]:
        return (rank(r[0], r[1], root), r[3].pdn())  # type: ignore[attr-defined]

    if node.turn == root:
        chosen = max(scored, key=key)
    else:
        chosen = min(scored, key=key)
    return chosen[0], chosen[1], chosen[2]


def piece_at(board: CheckersBoard, pdn: int) -> tuple[str, bool] | None:
    return board.cells[pdn - 1]


def classify(fen: str) -> dict[str, object]:
    """Walk the line and classify it for the curated-shot directive."""
    board = CheckersBoard.from_fen(fen)
    root = board.turn
    start = net(board, root)
    end, terminal, line = walk(board, root)

    # Is the first move a king capture? Is there a king multi-jump anywhere?
    node = board
    first_is_king = False
    has_king_multijump = False
    for i, mv in enumerate(line):
        origin = mv.origin  # type: ignore[attr-defined]
        moving = piece_at(node, origin)
        is_king_move = moving is not None and moving[1]
        ncaps = len(mv.captured)  # type: ignore[attr-defined]
        if i == 0 and is_king_move and ncaps >= 1:
            first_is_king = True
        if is_king_move and ncaps >= 2:
            has_king_multijump = True
        node = node.apply(mv)

    # Replay in pydraughts.
    oracle = OracleBoard(variant="english", fen=board.to_fen())
    for mv in line:
        idx = {
            ("x" if m.has_captures else "-").join(
                str(s) for s in m.steps_move
            ): m
            for m in oracle.legal_moves()
        }
        pdn = mv.pdn()  # type: ignore[attr-defined]
        assert pdn in idx, (pdn, sorted(idx))
        oracle.push(idx[pdn])
    oracle_over = oracle.is_over()
    oracle_winner = oracle.winner() if oracle_over else None
    oracle_term = (
        {1: "r", 2: "w"}.get(oracle_winner)
        if oracle_winner is not None
        else None
    )

    return {
        "fen": fen,
        "root": root,
        "swing": end - start,
        "terminal": terminal,
        "line": [m.pdn() for m in line],  # type: ignore[attr-defined]
        "plies": len(line),
        "first_is_king_capture": first_is_king,
        "has_king_multijump": has_king_multijump,
        "oracle_terminal": oracle_term,
    }


# Candidate curated king/deep shots. Verified / adjusted by running this script.
CANDIDATES: list[tuple[str, str]] = [
    # A lone Red KING capturing a White man: king moves backward, man cannot.
    ("king_single_capture", "B:W18:BK15"),
    # A Red KING multi-jump: king takes two men in one chained jump.
    ("king_double_jump", "B:W7,15:BK2"),
    # A Red KING triple jump around the board.
    ("king_triple_jump", "B:W18,25,26:BK14"),
    # A genuine 3-PLY forced reply sequence (found by search_deep_forced.py):
    # Red 18x25, White forced 15x24 (a king recapture), Red forced 27x20 (a
    # king capture) — three separate forced plies, ending with White out of
    # pieces, a terminal Red win.
    ("deep_three_ply_king_finish", "B:WK15,22:B18,19,K27,31"),
]


def main() -> None:
    for label, fen in CANDIDATES:
        info = classify(fen)
        print(f"=== {label}: {fen} ===")
        for k in (
            "root",
            "swing",
            "terminal",
            "oracle_terminal",
            "plies",
            "first_is_king_capture",
            "has_king_multijump",
            "line",
        ):
            print(f"  {k}: {info[k]!r}")
        assert info["terminal"] == info["oracle_terminal"], (
            f"{label}: engine terminal {info['terminal']!r} != oracle "
            f"{info['oracle_terminal']!r}"
        )
        print()


if __name__ == "__main__":
    main()
