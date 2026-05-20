"""Verify the witness labels probe_moves() emits for king/deep positions.

Run: ``uv run python scripts/phase3a_verify_king_witness_labels.py``

The analyst's MINOR finding 3: the witness suite has no king-capture or 3+ ply
forced-line coverage. This script drives the king/deep positions confirmed by
``scripts/verify_king_deep_shots.py`` through ``probe_moves()`` and prints the
exact FACT witness labels per move, so the curated test asserts a hand-checked
set, not a guessed one.
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.evidence import to_argument_evidence
from dialectical_checkers.scheme import Tier
from dialectical_checkers.witnesses import probe_moves

# King / deep positions verified by scripts/verify_king_deep_shots.py.
POSITIONS: list[tuple[str, str]] = [
    ("king_single_capture", "B:W18:BK15"),
    ("king_double_jump", "B:W7,15:BK2"),
    ("king_triple_jump", "B:W18,25,26:BK14"),
    ("deep_three_ply_king_finish", "B:WK15,22:B18,19,K27,31"),
]


def fact_labels(probe: object) -> set[str]:
    labels = [
        *probe.reasons,  # type: ignore[attr-defined]
        *probe.objections,  # type: ignore[attr-defined]
        *probe.reply_attacks,  # type: ignore[attr-defined]
        *probe.defenses,  # type: ignore[attr-defined]
    ]
    out: set[str] = set()
    for label in labels:
        ev = to_argument_evidence(label)
        assert ev.tier is Tier.FACT, label
        out.add(label)
    return out


def main() -> None:
    for name, fen in POSITIONS:
        board = CheckersBoard.from_fen(fen)
        print(f"=== {name}: {fen} ===")
        for probe in probe_moves(board):
            print(f"  {probe.pdn}: {sorted(fact_labels(probe))}")
        print()

    # Walk the deep 3-ply line move by move and print labels at each node.
    print("=== deep_three_ply forced line, node by node ===")
    board = CheckersBoard.from_fen("B:WK15,22:B18,19,K27,31")
    for pdn in ("18x25", "15x24", "27x20"):
        probes = {p.pdn: p for p in probe_moves(board)}
        assert pdn in probes, (pdn, sorted(probes))
        print(f"  move {pdn}: {sorted(fact_labels(probes[pdn]))}")
        moves = {m.pdn(): m for m in board.legal_moves()}
        board = board.apply(moves[pdn])
    print(f"  after line: terminal={board.is_terminal()} winner={board.winner()}")


if __name__ == "__main__":
    main()
