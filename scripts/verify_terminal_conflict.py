"""Verify the direct terminal-vs-material conflict test positions.

Run: ``uv run python scripts/verify_terminal_conflict.py``

The analyst's CRITICAL finding: a material-only minimax can choose a
non-terminal material gain over a forced terminal game-win. The fixed resolver
ranks ANY terminal win above ANY material outcome (and ANY terminal loss below
any material outcome) from the ROOT side's perspective — at BOTH maximising
(root) and minimising (opponent) nodes.

This script confirms two non-differential test positions independently of the
in-file brute-force reference:

* ``W:W13,14,21:B1,9`` — the analyst's oracle. White to move (the ROOT side, a
  MAXIMISING node) has 13x6 (forced terminal White win, swing 0) vs 14x5
  (non-terminal, swing +100). A material-max would wrongly pick 14x5. The
  resolver must report the terminal White win.

* A MINIMISING-node case: the root side is forced into one capture; at the
  resulting opponent node the opponent chooses among its captures, one of which
  is a forced terminal win FOR THE OPPONENT and another only a material gain.
  A material-min (which minimises the root side's balance) would pick whichever
  yields the smaller number; the resolver must instead pick the opponent's
  terminal win because a root-loss is banded below every material outcome.

For each position this walks a standalone capture-only minimax (engine board
only) under TWO rules — material-only (the OLD buggy rule) and banded (the
FIXED rule) — and replays the banded principal line in pydraughts to confirm
the terminal verdict. It prints both so the difference is explicit and the
expected test values are pinned by an oracle, not by hand-waving.
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


def walk(
    node: CheckersBoard, root: str, banded: bool
) -> tuple[int, str | None, list[str]]:
    """Capture-only minimax. ``banded`` selects the fixed (banded) rule."""
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


def replay_terminal(fen: str, line: list[str]) -> str | None:
    """Replay ``line`` in pydraughts; return the engine-side winner or None."""
    board = CheckersBoard.from_fen(fen)
    oracle = OracleBoard(variant="english", fen=board.to_fen())
    for pdn in line:
        idx = {
            ("x" if m.has_captures else "-").join(
                str(s) for s in m.steps_move
            ): m
            for m in oracle.legal_moves()
        }
        assert pdn in idx, (pdn, sorted(idx))
        oracle.push(idx[pdn])
    if not oracle.is_over():
        return None
    code = oracle.winner()
    return {1: "r", 2: "w"}.get(code) if code is not None else None


def report(label: str, fen: str) -> None:
    board = CheckersBoard.from_fen(fen)
    root = board.turn
    start = net(board, root)
    mat_v, mat_t, mat_line = walk(board, root, banded=False)
    band_v, band_t, band_line = walk(board, root, banded=True)
    oracle_t = replay_terminal(fen, band_line)
    print(f"=== {label}: {fen}  (root={root}) ===")
    print(
        f"  material-only rule: swing={mat_v - start} terminal={mat_t!r} "
        f"line={mat_line}"
    )
    print(
        f"  BANDED (fixed)    : swing={band_v - start} terminal={band_t!r} "
        f"line={band_line}"
    )
    print(f"  pydraughts replay of banded line: terminal={oracle_t!r}")
    assert oracle_t == band_t, (
        f"{label}: oracle terminal {oracle_t!r} != banded {band_t!r}"
    )
    print()


def main() -> None:
    # CRITICAL oracle — maximising node (White is root).
    report("maximising/root terminal win", "W:W13,14,21:B1,9")
    # Mirror by colour: same shape, Red is the root and wins terminally.
    report("maximising/root terminal win (red mirror)", "B:W32,24:B20,19,12")
    # Minimising-node case (built + verified below).
    report("minimising/opponent terminal win", MINIMISING_FEN)


# The minimising-node position (found + oracle-verified by
# scripts/search_minimising_conflict.py). Red (root) is forced into the single
# capture 11x18; after it White — the opponent, a MINIMISING node — must choose
# among its captures. The material-only ``min`` picks 23x14 (terminal=None) and
# misses White's forced terminal win; the banded rule picks 24x31, which forces
# 18x27, 31x24 and leaves Red with no piece — a terminal White win. Because a
# root (Red) LOSS is banded below every material outcome, the minimising node
# correctly selects the terminal win for White.
MINIMISING_FEN = "B:W15,K17,23,K24:B11,27"


if __name__ == "__main__":
    main()
