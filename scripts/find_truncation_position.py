"""Find a position whose forced-capture MINIMAX TREE has many nodes.

Run: ``uv run python scripts/find_truncation_position.py``

The budget/truncation test needs a position whose capture tree is genuinely
multi-node — i.e. captures by both sides spread across several plies, so a tiny
``max_nodes`` budget actually truncates. A single multi-jump is one
``CheckersMove`` (board.py expands the whole chain), so a lone multi-jump
position has a one-node tree and never truncates.

This walks seeded games, counts the resolve-tree node count of every position
(by an independent capture-only recursion identical to the resolver's), and
prints the positions with the largest trees plus what a tiny budget yields.
"""

from __future__ import annotations

import random

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import resolve

MAN_VALUE = 100
KING_VALUE = 150


def material(board: CheckersBoard, side: str) -> int:
    return sum(
        (KING_VALUE if c[1] else MAN_VALUE)
        for c in board.cells
        if c is not None and c[0] == side
    )


def net(board: CheckersBoard, root: str) -> int:
    other = "w" if root == "r" else "r"
    return material(board, root) - material(board, other)


def tree_nodes(board: CheckersBoard) -> int:
    """Count nodes the capture-only minimax descends through from ``board``."""
    count = 0

    def walk(node: CheckersBoard) -> None:
        nonlocal count
        captures = [m for m in node.legal_moves() if m.is_jump]
        if not captures:
            return
        for mv in captures:
            count += 1
            walk(node.apply(mv))

    walk(board)
    return count


def main() -> None:
    best: list[tuple[int, str]] = []
    seen: set[str] = set()
    for seed in range(400):
        rng = random.Random(seed)
        board = CheckersBoard.initial()
        for _ in range(60):
            fen = board.to_fen()
            if fen not in seen:
                seen.add(fen)
                n = tree_nodes(board)
                if n >= 2:
                    best.append((n, fen))
            moves = board.legal_moves()
            if not moves:
                break
            board = board.apply(rng.choice(moves))
            if board.is_draw():
                break
    best.sort(reverse=True)
    print(f"positions scanned: {len(seen)}; with multi-node tree: {len(best)}")
    print("top 10 by tree-node count:")
    for n, fen in best[:10]:
        full = resolve(CheckersBoard.from_fen(fen))
        tiny = resolve(CheckersBoard.from_fen(fen), max_depth=1, max_nodes=1)
        print(
            f"  nodes={n:3d} fen={fen}\n"
            f"    full: swing={full.material_swing} truncated={full.truncated} "
            f"tier={full.tier.value}\n"
            f"    tiny budget: swing={tiny.material_swing} "
            f"truncated={tiny.truncated} tier={tiny.tier.value}"
        )


if __name__ == "__main__":
    main()
