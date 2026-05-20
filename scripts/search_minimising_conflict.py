"""Search for a minimising-node terminal-vs-material conflict position.

Run: ``uv run python scripts/search_minimising_conflict.py``

The analyst's CRITICAL finding is symmetric: at a MINIMISING (opponent) node the
resolver must rank a forced terminal win FOR THE OPPONENT (a root LOSS) below
every material outcome — a material-only ``min`` would miss it.

This brute-force searches small random positions for one where:

* the root side is forced into exactly one capture (a deterministic root move);
* after it, the opponent (a minimising node) has >= 2 captures;
* the material-only minimax and the banded (fixed) minimax DISAGREE — the
  banded one must report a terminal loss for the root side that the
  material-only one misses.

Every hit is replayed in pydraughts to confirm the terminal verdict, and the
position is printed so it can be lifted into tests/test_captures.py as a
hand-pinned, oracle-verified test case.
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


def walk(
    node: CheckersBoard, root: str, banded: bool
) -> tuple[int, str | None, list[str]]:
    captures = [m for m in node.legal_moves() if m.is_jump]
    if not captures:
        moves = node.legal_moves()
        terminal = node.winner() if not moves else None
        return net(node, root), terminal, []
    scored: list[tuple[int, str | None, list[str], str]] = []
    for mv in captures:
        v, t, sub = walk(node.apply(mv), root, banded)
        scored.append((v, t, [mv.pdn(), *sub], mv.pdn()))

    def key(r: tuple[int, str | None, list[str], str]) -> tuple[object, str]:
        primary: object = rank(r[0], r[1], root) if banded else r[0]
        return (primary, r[3])

    if node.turn == root:
        chosen = max(scored, key=key)
    else:
        chosen = min(scored, key=key)
    return chosen[0], chosen[1], chosen[2]


def replay_terminal(board: CheckersBoard, line: list[str]) -> str | None:
    oracle = OracleBoard(variant="english", fen=board.to_fen())
    for pdn in line:
        idx = {
            ("x" if m.has_captures else "-").join(
                str(s) for s in m.steps_move
            ): m
            for m in oracle.legal_moves()
        }
        if pdn not in idx:
            return "ILLEGAL"
        oracle.push(idx[pdn])
    if not oracle.is_over():
        return None
    code = oracle.winner()
    return {1: "r", 2: "w"}.get(code) if code is not None else None


def random_position(rng: random.Random) -> CheckersBoard | None:
    """A small random legal-ish position: Red to move, 2-5 pieces a side."""
    squares = list(range(1, 33))
    rng.shuffle(squares)
    cells: list[tuple[str, bool] | None] = [None] * 32
    nr = rng.randint(2, 5)
    nw = rng.randint(2, 5)
    pool = iter(squares)
    try:
        for _ in range(nr):
            cells[next(pool) - 1] = ("r", rng.random() < 0.3)
        for _ in range(nw):
            cells[next(pool) - 1] = ("w", rng.random() < 0.3)
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
    """Search for a position whose WHOLE-TREE banded result is a root loss
    that the material-only minimax misses BECAUSE of a minimising (opponent)
    node — the opponent is forced into a node where it must choose its terminal
    win over a larger material grab.

    The root side is forced into exactly one capture so the only place a
    selection rule can change the outcome is the depth-1 (and deeper) opponent
    nodes. A whole-tree disagreement under that constraint therefore isolates
    the minimising-node fix.
    """
    rng = random.Random(20260520)
    hits: list[str] = []
    for _ in range(2_000_000):
        board = random_position(rng)
        if board is None:
            continue
        root = board.turn
        root_caps = [m for m in board.legal_moves() if m.is_jump]
        if len(root_caps) != 1:
            continue  # deterministic root move — isolate the opponent node
        after = board.apply(root_caps[0])
        opp_caps = [m for m in after.legal_moves() if m.is_jump]
        if len(opp_caps) < 2:
            continue  # the opponent (minimising node) must have a CHOICE
        # Isolate the depth-1 opponent node: does the banded vs material rule
        # disagree THERE, with banded reporting a root loss?
        opp_mat = walk(after, root, banded=False)
        opp_band = walk(after, root, banded=True)
        if opp_band[1] != root and opp_band[1] is not None:
            if opp_mat[1] == opp_band[1]:
                continue  # material rule already gets it — not a conflict
        else:
            continue
        start = net(board, root)
        mat_v, mat_t, mat_line = walk(board, root, banded=False)
        band_v, band_t, band_line = walk(board, root, banded=True)
        if band_t == root or band_t is None or mat_t == band_t:
            continue
        oracle_t = replay_terminal(board, band_line)
        if oracle_t != band_t:
            continue
        fen = board.to_fen()
        print(f"HIT: {fen}  (root={root})")
        print(
            f"  opponent node {after.to_fen()}: "
            f"material-min terminal={opp_mat[1]!r} banded-min "
            f"terminal={opp_band[1]!r}"
        )
        print(
            f"  whole tree material-only: swing={mat_v - start} "
            f"terminal={mat_t!r} line={mat_line}"
        )
        print(
            f"  whole tree BANDED       : swing={band_v - start} "
            f"terminal={band_t!r} line={band_line}"
        )
        print(f"  pydraughts replay of banded line: {oracle_t!r}")
        print()
        hits.append(fen)
        if len(hits) >= 5:
            break
    if not hits:
        print("no minimising-node conflict found")
    else:
        print(f"{len(hits)} hits")


if __name__ == "__main__":
    main()
