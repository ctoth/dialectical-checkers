"""Phase 4 — targeted smoke for obj:exposes_man, bridge, echelon formations."""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import opponent_shot
from dialectical_checkers.evidence import to_argument_evidence
from dialectical_checkers.scheme import Tier
from dialectical_checkers.witnesses import probe_moves


def heuristic_labels(probe) -> list[str]:
    return [
        label
        for label in (*probe.reasons, *probe.objections,
                      *probe.reply_attacks, *probe.defenses)
        if to_argument_evidence(label).tier is Tier.HEURISTIC
    ]


def all_labels(probe) -> list[str]:
    return [*probe.reasons, *probe.objections,
            *probe.reply_attacks, *probe.defenses]


def dump(fen: str, note: str) -> None:
    board = CheckersBoard.from_fen(fen)
    print(f"--- {fen}  ({board.turn}) — {note}")
    move_by = {m.pdn(): m for m in board.legal_moves()}
    for probe in probe_moves(board):
        h = heuristic_labels(probe)
        m = move_by[probe.pdn]
        shot = opponent_shot(board, m)
        child = board.apply(m)
        opp_cap = any(x.is_jump for x in child.legal_moves())
        print(f"    {probe.pdn}: ALL={all_labels(probe)}  "
              f"opp_cap_after={opp_cap}  shot={shot}")
    print()


def main() -> None:
    # exposes_man: a quiet move leaving a Red man capturable but resolver
    # proves no fact shot (Red can recapture even).
    dump("B:W7,23:B2,18", "even-trade setup (2x11 even); check exposes")
    # Bridge: White to place a man on 29 or 31 with the other already there.
    dump("W:W31,18:B6", "White man to 29? needs both 29 & 31")
    dump("W:W29,18:B6", "White man to 31? wait 18 cannot reach 31")
    # echelon: three Red men on a diagonal after a move.
    dump("B:W30:B6,10,13", "Red diagonal run check")
    dump("B:W30:B1,10,15", "Red diagonal 1-10? not adjacent")


if __name__ == "__main__":
    main()
