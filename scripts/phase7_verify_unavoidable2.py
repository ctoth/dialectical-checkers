"""Phase 7 — verify B:W11,20:B7 unavoidable Red loss line. No oneliners."""
from __future__ import annotations
from dialectical_checkers.board import CheckersBoard


def main() -> None:
    b = CheckersBoard.from_fen("B:W11,20:B7")
    print(f"start {b.to_fen()} legal={[m.pdn() for m in b.legal_moves()]}")
    # Red forced 7x16; then White's reply.
    for pdn in ["7x16"]:
        b = b.apply(next(m for m in b.legal_moves() if m.pdn() == pdn))
        print(f"  {pdn} -> {b.to_fen()} turn={b.turn} "
              f"legal={[m.pdn() for m in b.legal_moves()]}")
    # White to move now; pick its capture(s).
    for m in b.legal_moves():
        nb = b.apply(m)
        print(f"  White {m.pdn()} -> {nb.to_fen()} turn={nb.turn} "
              f"terminal={nb.is_terminal()} winner={nb.winner()}")


if __name__ == "__main__":
    main()
