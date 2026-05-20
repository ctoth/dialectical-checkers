"""Probe the terminal-vs-material conflict the analyst flagged (CRITICAL).

Run: ``uv run python scripts/probe_terminal_conflict.py``

For the oracle position ``W:W13,14,21:B1,9`` this:

* prints the current ``resolve()`` result;
* enumerates White's legal captures and, for each, the capture-only minimax
  end-balance + terminal status reached by a standalone reference walk;
* replays the candidate forced lines in pydraughts to confirm which one ends
  the game (Red out of pieces) and which merely nets material.

This pins the expected post-fix behaviour: the resolver must report the
terminal White win, not the +100 non-terminal material branch.
"""

from __future__ import annotations

from draughts import Board as OracleBoard

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import resolve

ORACLE_FEN = "W:W13,14,21:B1,9"

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


def walk(node: CheckersBoard, root: str) -> tuple[int, str | None, list[str]]:
    """Plain capture-only minimax — material only (mirrors the OLD rule)."""
    captures = [m for m in node.legal_moves() if m.is_jump]
    if not captures:
        moves = node.legal_moves()
        terminal = node.winner() if not moves else None
        return net(node, root), terminal, []
    node_side = node.turn
    scored: list[tuple[int, str | None, list[str], str]] = []
    for mv in captures:
        v, t, line = walk(node.apply(mv), root)
        scored.append((v, t, line, mv.pdn()))
    if node_side == root:
        chosen = max(scored, key=lambda r: (r[0], r[3]))
    else:
        chosen = min(scored, key=lambda r: (r[0], r[3]))
    return chosen[0], chosen[1], [chosen[3], *chosen[2]]


def main() -> None:
    board = CheckersBoard.from_fen(ORACLE_FEN)
    print(f"Position: {ORACLE_FEN}  (turn={board.turn})")
    line = resolve(board)
    print(f"Current resolve(): {line}")
    print()
    print("White's legal captures and their capture-only outcomes:")
    for mv in board.legal_moves():
        if not mv.is_jump:
            continue
        v, t, sub = walk(board.apply(mv), board.turn)
        start = net(board, board.turn)
        print(
            f"  {mv.pdn():12s} -> end_balance={v} swing={v - start} "
            f"terminal={t!r} continuation={sub}"
        )
    print()
    # Replay each first capture in pydraughts to confirm terminal status.
    for mv in board.legal_moves():
        if not mv.is_jump:
            continue
        after = board.apply(mv)
        oracle = OracleBoard(variant="english", fen=board.to_fen())
        pdns = {
            ("x" if m.has_captures else "-").join(
                str(s) for s in m.steps_move
            ): m
            for m in oracle.legal_moves()
        }
        legal = mv.pdn() in pdns
        print(
            f"  {mv.pdn():12s} legal-in-pydraughts={legal} "
            f"-> after FEN {after.to_fen()} terminal={after.is_terminal()}"
        )


if __name__ == "__main__":
    main()
