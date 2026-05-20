"""Phase 4 — smoke-test the HEURISTIC witnesses on hand-picked positions.

Prints, per probe, the HEURISTIC labels emitted, so each witness's firing can
be hand-verified against its precise definition before the formal test file is
written.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.evidence import to_argument_evidence
from dialectical_checkers.scheme import Tier
from dialectical_checkers.witnesses import probe_moves


def heuristic_labels(probe) -> list[str]:
    out = []
    for label in (*probe.reasons, *probe.objections,
                   *probe.reply_attacks, *probe.defenses):
        if to_argument_evidence(label).tier is Tier.HEURISTIC:
            out.append(label)
    return out


def dump(fen: str, note: str) -> None:
    board = CheckersBoard.from_fen(fen)
    print(f"--- {fen}  ({board.turn} to move) — {note}")
    for probe in probe_moves(board):
        h = heuristic_labels(probe)
        if h:
            print(f"    {probe.pdn}:  {h}")
    print()


def main() -> None:
    # Opposition: 1K vs 1K, equal force, one piece each.
    dump("B:WK4:BK15", "1K-1K: Red holds opposition (cheb 3 odd)")
    dump("B:WK8:BK15", "1K-1K: White holds opposition (cheb 2 even)")
    # Initial position — many pieces, opposition silent.
    dump("B:W22,30:B6,9,13,14", "midgame quiet — mobility/center/etc")
    # Back rank: White with 2 men on home rank (29-32).
    dump("W:W29,32,18:B6", "White has 2 home-rank men")
    # Single corner drift: a Red man moving toward square 4/8.
    dump("B:W21:B3", "Red man on 3, can drift to single corner")
    # Center: a move into the center.
    dump("B:W30:B10", "Red man can move toward center")
    # exposes_man: a man left capturable, loss not proven.
    dump("B:W18,30:B14,9", "Red man may become en prise")
    # echelon / formation
    dump("B:W30:B6,9,13", "Red men possibly on a diagonal")


if __name__ == "__main__":
    main()
