"""Phase 4 fix — verify all 4 MAJOR fixes against the analyst's positions.

Runs the actual probe_moves on each analyst-constructed position and asserts
the witness now behaves correctly.

Run: uv run python scripts/phase4fix_verify_all.py
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.witnesses import probe_moves


def labels(fen: str) -> dict[str, tuple[str, ...]]:
    out: dict[str, tuple[str, ...]] = {}
    for p in probe_moves(CheckersBoard.from_fen(fen)):
        out[p.pdn] = tuple(p.reasons) + tuple(p.objections)
    return out


def check(name: str, cond: bool, detail: str) -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}: {detail}")
    if not cond:
        raise SystemExit(1)


def main() -> None:
    # FIX 1 — opposition silent on man-vs-king (analyst: B:WK10:B15).
    f1 = labels("B:WK10:B15")
    op1 = any("pro:opposition" in v for v in f1.values())
    lo1 = any("obj:loses_opposition" in v for v in f1.values())
    check("FIX1 man-vs-king opposition silent",
          not op1 and not lo1,
          f"pro:opposition seen={op1} obj:loses_opposition seen={lo1}")

    # FIX 1 — equal force 1-king-v-1-king still fires (regression guard).
    f1b = labels("B:WK4:BK15")
    check("FIX1 king-v-king opposition still fires",
          all("pro:opposition" in v for v in f1b.values()),
          "pro:opposition on every move of B:WK4:BK15")

    # FIX 2 — back-rank: kings on home rank are NOT guards (analyst:
    # W:WK29,K32,18:B6).
    f2 = labels("W:WK29,K32,18:B6")
    check("FIX2 back_rank_hold not from kings",
          "pro:back_rank_hold" not in f2.get("18-14", ()),
          f"18-14 labels={f2.get('18-14')}")
    check("FIX2 back_rank_break not for a king leaving home rank",
          "obj:back_rank_break" not in f2.get("29-25", ()),
          f"29-25 labels={f2.get('29-25')}")

    # FIX 2 — men on home rank still count (regression guard:
    # W:W29,32,18:B6 — the existing curated test position).
    f2b = labels("W:W29,32,18:B6")
    check("FIX2 back_rank_hold still fires for men",
          "pro:back_rank_hold" in f2b.get("18-14", ()),
          f"18-14 labels={f2b.get('18-14')}")
    check("FIX2 back_rank_break still fires for a man",
          "obj:back_rank_break" in f2b.get("29-25", ()),
          f"29-25 labels={f2b.get('29-25')}")

    # FIX 3 — obj:exposes_man must NOT fire when the en-prise piece is a king
    # (analyst: B:WK18,19:B3,8,K13,K17,K20,K30, move 17-14).
    f3 = labels("B:WK18,19:B3,8,K13,K17,K20,K30")
    check("FIX3 exposes_man silent for an exposed king",
          "obj:exposes_man" not in f3.get("17-14", ()),
          f"17-14 labels={f3.get('17-14')}")

    # FIX 3 — obj:exposes_man still fires for an exposed man (regression
    # guard: B:W13,16:B8,9, move 8-12 — existing curated test).
    f3b = labels("B:W13,16:B8,9")
    check("FIX3 exposes_man still fires for an exposed man",
          "obj:exposes_man" in f3b.get("8-12", ()),
          f"8-12 labels={f3b.get('8-12')}")

    # FIX 4 — obj:loses_opposition now reachable (B:WK8:BK15, quiet move).
    f4 = labels("B:WK8:BK15")
    fired4 = [pdn for pdn, v in f4.items() if "obj:loses_opposition" in v]
    check("FIX4 obj:loses_opposition reachable",
          fired4 == sorted(f4),
          f"firing moves={fired4}")
    # the firing move 15-18 is quiet and non-terminal
    board = CheckersBoard.from_fen("B:WK8:BK15")
    mv = next(m for m in board.legal_moves() if m.pdn() == "15-18")
    nonterm = not board.apply(mv).is_terminal()
    check("FIX4 firing move 15-18 is quiet & non-terminal",
          not mv.is_jump and nonterm,
          f"jump={mv.is_jump} non_terminal={nonterm}")

    print("\nALL FIX VERIFICATIONS PASSED")


if __name__ == "__main__":
    main()
