"""Phase 4 fix — exhaustive search for a QUIET move surrendering the opposition.

Rule under test (no sibling gate): obj:loses_opposition fires on M iff
holder(R) == mover and holder(M_child) != mover and M is not a capture.

Sweep ALL positions with 1..2 pieces per side, every man/king combination,
both turns. Report every quiet firing with a category: 'crown' (a man reached
its king-row), 'count-change' (piece count changed without a capture -- should
be impossible), or 'parity' (still 1v1 equal force but holder flipped).

This determines empirically whether a meaningful quiet obj:loses_opposition
exists at all.

Run: uv run python scripts/phase4fix_quiet_surrender_exhaustive.py
"""

from __future__ import annotations

import itertools

from dialectical_checkers.board import (
    CheckersBoard,
    RED_KING_ROW,
    WHITE_KING_ROW,
    _coord,
)


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
    s = max(abs(r_row - w_row), abs(r_col - w_col))
    opp = "w" if board.turn == "r" else "r"
    return opp if s % 2 == 0 else board.turn


def piece_token(p: int, k: bool) -> str:
    return ("K" if k else "") + str(p)


def main() -> None:
    crown = 0
    parity = 0
    other = 0
    examples: list[str] = []
    squares = list(range(1, 33))
    for turn in ("B", "W"):
        for wn in (1, 2):
            for rn in (1, 2):
                for wsq in itertools.combinations(squares, wn):
                    for rsq in itertools.combinations(squares, rn):
                        if set(wsq) & set(rsq):
                            continue
                        for wkings in itertools.product((False, True),
                                                        repeat=wn):
                            for rkings in itertools.product((False, True),
                                                            repeat=rn):
                                wtok = ",".join(
                                    piece_token(p, k)
                                    for p, k in zip(wsq, wkings))
                                rtok = ",".join(
                                    piece_token(p, k)
                                    for p, k in zip(rsq, rkings))
                                fen = f"{turn}:W{wtok}:B{rtok}"
                                try:
                                    board = CheckersBoard.from_fen(fen)
                                except Exception:
                                    continue
                                mover = board.turn
                                if holder(board) != mover:
                                    continue
                                for m in board.legal_moves():
                                    if m.is_jump:
                                        continue
                                    child = board.apply(m)
                                    if holder(child) == mover:
                                        continue
                                    # quiet move, surrendered opposition
                                    oc = board.cells[m.origin - 1]
                                    dr = _coord(m.destination - 1)[0]
                                    krow = (RED_KING_ROW if mover == "r"
                                            else WHITE_KING_ROW)
                                    crowned = (oc is not None
                                               and not oc[1]
                                               and dr == krow)
                                    if crowned:
                                        crown += 1
                                        cat = "crown"
                                    elif holder(child) is None:
                                        other += 1
                                        cat = "other"
                                    else:
                                        parity += 1
                                        cat = "parity"
                                    if len(examples) < 20:
                                        examples.append(
                                            f"[{cat}] {fen} M={m.pdn()}")
    print(f"quiet surrender via crown:  {crown}")
    print(f"quiet surrender via parity: {parity}")
    print(f"quiet surrender via other:  {other}")
    for e in examples:
        print("  " + e)


if __name__ == "__main__":
    main()
