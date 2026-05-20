"""Phase 4 fix probe — find positions where obj:loses_opposition should fire.

For every 1-king-vs-1-king position (equal force, the case the opposition
witness is defined for), with each side to move, enumerate legal moves and
report, per move, the root holder, the child holder, whether the move captures,
and whether (under the CURRENT keeps_exist gate) obj:loses_opposition fires,
and whether (under the PROPOSED mirror rule — fires iff holder(R)==mover and
holder(child)!=mover) it would fire.

Run: uv run python scripts/phase4fix_loses_opposition_probe.py
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard, _coord


def holder(board: CheckersBoard) -> str | None:
    """The opposition holder for a 1-king-v-1-king board, mirror of witnesses."""
    reds = [i + 1 for i, c in enumerate(board.cells) if c and c[0] == "r"]
    whites = [i + 1 for i, c in enumerate(board.cells) if c and c[0] == "w"]
    if len(reds) != 1 or len(whites) != 1:
        return None
    rk = board.cells[reds[0] - 1]
    wk = board.cells[whites[0] - 1]
    assert rk is not None and wk is not None
    if rk[1] != wk[1]:
        # unequal force (man vs king) — not defined
        return None
    r_row, r_col = _coord(reds[0] - 1)
    w_row, w_col = _coord(whites[0] - 1)
    sep = max(abs(r_row - w_row), abs(r_col - w_col))
    opp = "w" if board.turn == "r" else "r"
    return opp if sep % 2 == 0 else board.turn


def main() -> None:
    proposed_fires = 0
    current_fires = 0
    examples_proposed: list[str] = []
    for turn in ("B", "W"):
        for rk in range(1, 33):
            for wk in range(1, 33):
                if rk == wk:
                    continue
                fen = f"{turn}:WK{wk}:BK{rk}"
                board = CheckersBoard.from_fen(fen)
                mover = board.turn
                hr = holder(board)
                if hr != mover:
                    continue
                moves = board.legal_moves()
                for m in moves:
                    child = board.apply(m)
                    hc = holder(child)
                    proposed = hr == mover and hc != mover
                    # current rule: also requires a sibling that keeps it
                    keeps = any(
                        holder(board.apply(s)) == mover
                        for s in moves
                        if s != m
                    )
                    current = proposed and keeps
                    if proposed:
                        proposed_fires += 1
                        if len(examples_proposed) < 12:
                            examples_proposed.append(
                                f"{fen} move {m.pdn()} "
                                f"holder(R)={hr} holder(S)={hc} "
                                f"jump={m.is_jump} sibling_keeps={keeps}"
                            )
                    if current:
                        current_fires += 1
    print(f"proposed-rule firings (kk 1v1): {proposed_fires}")
    print(f"current-rule firings  (kk 1v1): {current_fires}")
    print("examples (proposed rule):")
    for e in examples_proposed:
        print("  " + e)


if __name__ == "__main__":
    main()
