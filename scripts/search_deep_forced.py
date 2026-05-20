"""Search for a 3+ ply forced-reply capture sequence for the curated suite.

Run: ``uv run python scripts/search_deep_forced.py``

The analyst's MINOR finding wants a curated shot with a 3+ ply forced reply
sequence — capture, forced opponent recapture, capture, ... across SEPARATE
plies (not one chained multi-jump, which board.py collapses into a single
move). This brute-force searches small random positions for one whose banded
capture-only principal line is >= 3 plies long, then replays it in pydraughts
to confirm legality and the terminal/material verdict.
"""

from __future__ import annotations

import random

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


def replay(board: CheckersBoard, line: list[object]) -> tuple[bool, str | None]:
    oracle = OracleBoard(variant="english", fen=board.to_fen())
    for mv in line:
        idx = {
            ("x" if m.has_captures else "-").join(
                str(s) for s in m.steps_move
            ): m
            for m in oracle.legal_moves()
        }
        pdn = mv.pdn()  # type: ignore[attr-defined]
        if pdn not in idx:
            return False, None
        oracle.push(idx[pdn])
    if not oracle.is_over():
        return True, None
    code = oracle.winner()
    return True, ({1: "r", 2: "w"}.get(code) if code is not None else None)


def random_position(rng: random.Random) -> CheckersBoard | None:
    squares = list(range(1, 33))
    rng.shuffle(squares)
    cells: list[tuple[str, bool] | None] = [None] * 32
    nr = rng.randint(2, 4)
    nw = rng.randint(2, 4)
    pool = iter(squares)
    try:
        for _ in range(nr):
            cells[next(pool) - 1] = ("r", rng.random() < 0.25)
        for _ in range(nw):
            cells[next(pool) - 1] = ("w", rng.random() < 0.25)
    except StopIteration:
        return None
    fen_w = ",".join(
        ("K" if c[1] else "") + str(i + 1)
        for i, c in enumerate(cells)
        if c is not None and c[0] == "w"
    )
    fen_b = ",".join(
        ("K" if c[1] else "") + str(i + 1)
        for i, c in enumerate(cells)
        if c is not None and c[0] == "r"
    )
    try:
        return CheckersBoard.from_fen(f"B:W{fen_w}:B{fen_b}")
    except ValueError:
        return None


def main() -> None:
    rng = random.Random(70705020)
    hits = 0
    for _ in range(1_000_000):
        board = random_position(rng)
        if board is None:
            continue
        root = board.turn
        if not any(m.is_jump for m in board.legal_moves()):
            continue
        end, terminal, line = walk(board, root)
        if len(line) < 3:
            continue
        # Confirm each ply is a separate forced capture (mandatory: the side to
        # move had only jumps), i.e. a genuine forced reply chain.
        node = board
        forced_chain = True
        for mv in line:
            caps = [m for m in node.legal_moves() if m.is_jump]
            if not caps:
                forced_chain = False
                break
            node = node.apply(mv)
        if not forced_chain:
            continue
        ok, oracle_term = replay(board, line)
        if not ok or oracle_term != terminal:
            continue
        start = net(board, root)
        print(f"HIT: {board.to_fen()}  (root={root})")
        print(
            f"  plies={len(line)} swing={end - start} terminal={terminal!r} "
            f"oracle_terminal={oracle_term!r}"
        )
        print(f"  line={[m.pdn() for m in line]}")  # type: ignore[attr-defined]
        print()
        hits += 1
        if hits >= 8:
            break
    print(f"{hits} hits")


if __name__ == "__main__":
    main()
