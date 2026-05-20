"""Phase 4 — hand-verify the obj:exposes_man positions in detail.

For each curated exposes_man move: confirm (a) the move is quiet, (b) the
opponent has a legal capture after it, (c) opponent_shot returns None or
non-FACT (loss not proven), (d) no FACT objection on the move. Also walk what
the opponent's capture nets, to confirm the man is NOT provably lost.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import opponent_shot
from dialectical_checkers.evidence import to_argument_evidence
from dialectical_checkers.scheme import Tier
from dialectical_checkers.witnesses import probe_moves


def verify(fen: str, pdn: str) -> None:
    board = CheckersBoard.from_fen(fen)
    move_by = {m.pdn(): m for m in board.legal_moves()}
    m = move_by[pdn]
    child = board.apply(m)
    opp_caps = [x.pdn() for x in child.legal_moves() if x.is_jump]
    shot = opponent_shot(board, m)
    probe = {p.pdn: p for p in probe_moves(board)}[pdn]
    fact_objs = [
        o for o in probe.objections
        if to_argument_evidence(o).tier is Tier.FACT
    ]
    print(f"{fen}  move {pdn}:")
    print(f"  quiet={not m.is_jump}  opp_caps_after={opp_caps}")
    print(f"  opponent_shot={'None' if shot is None else shot.tier}")
    print(f"  FACT objections={fact_objs}")
    print(f"  emitted objections={list(probe.objections)}")
    # Walk one opponent capture to show net.
    if opp_caps:
        cap = next(x for x in child.legal_moves() if x.is_jump)
        after_cap = child.apply(cap)
        red_men = sum(1 for c in after_cap.cells if c and c[0] == "r")
        white_men = sum(1 for c in after_cap.cells if c and c[0] == "w")
        print(f"  after opp plays {cap.pdn()}: red={red_men} white={white_men} "
              f"(red can then recapture? "
              f"{any(x.is_jump for x in after_cap.legal_moves())})")
    print()


def main() -> None:
    verify("B:W13,16:B8,9", "8-12")
    verify("B:W14,18:B9,11", "11-15")
    verify("B:W15,18:B9,11", "9-14")


if __name__ == "__main__":
    main()
