"""Phase 4 fix — find genuine obj:loses_opposition firings as the mirror.

Mirror definition under test:
    pro:opposition fires on M iff holder(S) == mover.
    obj:loses_opposition fires on M iff:
        - SOME sibling move N reaches holder(N_child) == mover  (opposition
          was AVAILABLE to the mover this turn), AND
        - M itself reaches holder(S) != mover (M failed to secure it).

This is the strict mirror: a move that throws away an opposition the mover
could have taken. holder() is defined only for the 1v1 equal-force case
(man-man or king-king); a child that is not such an ending has holder None.

Scan positions with up to 2 pieces per side (so a capture-down to 1v1 is
reachable). Report firing examples, split by whether M is a capture.

Run: uv run python scripts/phase4fix_loses_opp_mirror.py
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


def fen_of(turn: str, whites: list[tuple[int, bool]],
           reds: list[tuple[int, bool]]) -> str:
    w = ",".join(("K" if k else "") + str(p) for p, k in sorted(whites))
    r = ",".join(("K" if k else "") + str(p) for p, k in sorted(reds))
    return f"{turn}:W{w}:B{r}"


def main() -> None:
    quiet_fires = 0
    capture_fires = 0
    quiet_ex: list[str] = []
    cap_ex: list[str] = []
    squares = range(1, 33)
    # 1 or 2 white pieces, 1 or 2 red pieces, men or kings.
    for turn in ("B", "W"):
        for wn in (1, 2):
            for rn in (1, 2):
                for wsq in itertools.combinations(squares, wn):
                    for rsq in itertools.combinations(squares, rn):
                        if set(wsq) & set(rsq):
                            continue
                        # men only here to keep the sweep finite and the
                        # man-v-man path covered; kings handled by a king pass.
                        whites = [(p, False) for p in wsq]
                        reds = [(p, False) for p in rsq]
                        fen = fen_of(turn, whites, reds)
                        try:
                            board = CheckersBoard.from_fen(fen)
                        except Exception:
                            continue
                        mover = board.turn
                        moves = board.legal_moves()
                        if len(moves) < 2:
                            continue
                        outc = {}
                        for m in moves:
                            outc[m] = holder(board.apply(m))
                        secures = [m for m in moves if outc[m] == mover]
                        fails = [m for m in moves if outc[m] != mover]
                        if not secures or not fails:
                            continue
                        for m in fails:
                            if m.is_jump:
                                capture_fires += 1
                                if len(cap_ex) < 6:
                                    cap_ex.append(
                                        f"{fen} M={m.pdn()} "
                                        f"hS={outc[m]} keeper="
                                        f"{secures[0].pdn()}")
                            else:
                                quiet_fires += 1
                                if len(quiet_ex) < 12:
                                    quiet_ex.append(
                                        f"{fen} M={m.pdn()} "
                                        f"hS={outc[m]} keeper="
                                        f"{secures[0].pdn()}")
    print(f"quiet obj:loses_opposition firings (men only):   {quiet_fires}")
    for e in quiet_ex:
        print("  Q " + e)
    print(f"capture obj:loses_opposition firings (men only): {capture_fires}")
    for e in cap_ex:
        print("  C " + e)


if __name__ == "__main__":
    main()
