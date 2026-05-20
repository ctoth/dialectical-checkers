"""Phase 4 fix — find moves that capture down INTO a 1v1 with split holders.

The genuine reachable obj:loses_opposition: from a multi-piece root R, the
mover has a choice of moves; some reach a 1v1 equal-force ending the mover
holds the opposition of (pro:opposition fires), some reach a 1v1 ending the
mover does NOT hold (obj:loses_opposition should fire) -- the move surrendered
an opposition a sibling secured.

We need R to offer >=2 legal moves whose children are 1v1-equal-force endings
with DIFFERENT holders. Sweep small positions (2 white + 2 red, men+kings),
both turns. Report any root with split outcomes.

Run: uv run python scripts/phase4fix_capture_into_1v1.py
"""

from __future__ import annotations

import itertools

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
    s = max(abs(r_row - w_row), abs(r_col - w_col))
    opp = "w" if board.turn == "r" else "r"
    return opp if s % 2 == 0 else board.turn


def tok(p: int, k: bool) -> str:
    return ("K" if k else "") + str(p)


def main() -> None:
    splits = 0
    examples: list[str] = []
    squares = list(range(1, 33))
    for turn in ("B", "W"):
        for wsq in itertools.combinations(squares, 2):
            for rsq in itertools.combinations(squares, 2):
                if set(wsq) & set(rsq):
                    continue
                for wk in itertools.product((False, True), repeat=2):
                    for rk in itertools.product((False, True), repeat=2):
                        wt = ",".join(tok(p, k) for p, k in zip(wsq, wk))
                        rt = ",".join(tok(p, k) for p, k in zip(rsq, rk))
                        fen = f"{turn}:W{wt}:B{rt}"
                        try:
                            board = CheckersBoard.from_fen(fen)
                        except Exception:
                            continue
                        mover = board.turn
                        moves = board.legal_moves()
                        if len(moves) < 2:
                            continue
                        outcomes = {}
                        for m in moves:
                            outcomes[m] = holder(board.apply(m))
                        # only consider moves whose child is a real 1v1 ending
                        defined = {m: h for m, h in outcomes.items()
                                   if h is not None}
                        if len(defined) < 2:
                            continue
                        hs = set(defined.values())
                        if len(hs) < 2:
                            continue
                        # split: some children mover-held, some not
                        if mover in hs:
                            splits += 1
                            if len(examples) < 25:
                                secures = [m.pdn() for m, h in defined.items()
                                           if h == mover]
                                fails = [m.pdn() for m, h in defined.items()
                                         if h != mover]
                                examples.append(
                                    f"{fen} secures={secures} fails={fails}")
    print(f"roots with split 1v1-child holders: {splits}")
    for e in examples:
        print("  " + e)


if __name__ == "__main__":
    main()
