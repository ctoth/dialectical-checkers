"""Print resolve() output for the terminal-conflict test positions.

Run: ``uv run python scripts/print_terminal_conflict_resolve.py``

Pins the exact ResolvedLine fields the direct (non-differential) terminal-
conflict tests in tests/test_captures.py will assert. Each position was already
oracle-verified by scripts/verify_terminal_conflict.py and
scripts/search_minimising_conflict.py.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import resolve

POSITIONS = [
    ("maximising/root White terminal win", "W:W13,14,21:B1,9"),
    ("maximising/root Red terminal win", "B:W32,24:B20,19,12"),
    ("minimising/opponent White terminal win", "B:W15,K17,23,K24:B11,27"),
]


def main() -> None:
    for label, fen in POSITIONS:
        board = CheckersBoard.from_fen(fen)
        line = resolve(board)
        print(f"{label}")
        print(f"  fen={fen}")
        print(f"  material_swing={line.material_swing}")
        print(f"  forced={line.forced}")
        print(f"  truncated={line.truncated}")
        print(f"  terminal={line.terminal!r}")
        print(f"  tier={line.tier}")
        print(f"  principal_line={[m.pdn() for m in line.principal_line]}")
        print()


if __name__ == "__main__":
    main()
