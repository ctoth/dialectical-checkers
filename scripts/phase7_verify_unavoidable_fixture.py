"""Phase 7 — verify the unavoidable-loss fixture B:W14,23:B9.

Confirms Red has exactly one forced move and the scripted line ends in a Red
loss, so test_mine_turning_point_unavoidable_is_flagged rests on runtime fact.
Measurement script, no oneliners.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard


def main() -> None:
    b = CheckersBoard.from_fen("B:W14,23:B9")
    print(f"start {b.to_fen()} legal={[m.pdn() for m in b.legal_moves()]}")
    for pdn in ["9x18", "23x16"]:
        legal = {m.pdn(): m for m in b.legal_moves()}
        if pdn not in legal:
            print(f"  {pdn} NOT LEGAL; legal={sorted(legal)}")
            return
        b = b.apply(legal[pdn])
        print(f"  {pdn} -> {b.to_fen()} turn={b.turn} "
              f"terminal={b.is_terminal()} winner={b.winner()}")


if __name__ == "__main__":
    main()
