"""Phase 4 fix probe — non-capture opposition transitions in 1v1 endings.

For every 1-king-v-1-king position with the mover holding the opposition,
report the NON-CAPTURE legal moves and whether each flips the holder. Also
covers 1-man-v-1-man. The goal: confirm there exist quiet moves that surrender
a held opposition while the 1v1 equal-force structure survives — the genuine
obj:loses_opposition case (not a capture that wins the game outright).

Run: uv run python scripts/phase4fix_noncapture_opposition.py
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard, _coord


def holder(board: CheckersBoard) -> str | None:
    reds = [i + 1 for i, c in enumerate(board.cells) if c and c[0] == "r"]
    whites = [i + 1 for i, c in enumerate(board.cells) if c and c[0] == "w"]
    if len(reds) != 1 or len(whites) != 1:
        return None
    rk = board.cells[reds[0] - 1]
    wk = board.cells[whites[0] - 1]
    assert rk is not None and wk is not None
    if rk[1] != wk[1]:
        return None
    r_row, r_col = _coord(reds[0] - 1)
    w_row, w_col = _coord(whites[0] - 1)
    sep = max(abs(r_row - w_row), abs(r_col - w_col))
    opp = "w" if board.turn == "r" else "r"
    return opp if sep % 2 == 0 else board.turn


def scan(spec: str) -> None:
    """spec: 'kk' (king v king) or 'mm' (man v man)."""
    quiet_surrender = 0
    quiet_keep = 0
    examples: list[str] = []
    for turn in ("B", "W"):
        for rp in range(1, 33):
            for wp in range(1, 33):
                if rp == wp:
                    continue
                if spec == "kk":
                    fen = f"{turn}:WK{wp}:BK{rp}"
                else:
                    fen = f"{turn}:W{wp}:B{rp}"
                board = CheckersBoard.from_fen(fen)
                mover = board.turn
                hr = holder(board)
                if hr != mover:
                    continue
                for m in board.legal_moves():
                    if m.is_jump:
                        continue
                    child = board.apply(m)
                    hc = holder(child)
                    if hc is None:
                        continue  # crowned/structure-changed -> not 1v1 eq
                    if hc != mover:
                        quiet_surrender += 1
                        if len(examples) < 15:
                            examples.append(
                                f"{fen} move {m.pdn()} hR={hr} hS={hc}"
                            )
                    else:
                        quiet_keep += 1
    print(f"[{spec}] quiet moves that SURRENDER held opposition: "
          f"{quiet_surrender}")
    print(f"[{spec}] quiet moves that KEEP held opposition:      "
          f"{quiet_keep}")
    for e in examples:
        print("  " + e)


def main() -> None:
    scan("kk")
    scan("mm")


if __name__ == "__main__":
    main()
