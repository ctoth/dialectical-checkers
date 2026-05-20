"""Phase 3b — dump probe_moves witnesses + crisp survivors for given FENs.

Developer probe: prints, per legal move, the FACT witness channels and the
crisp-layer survivor set, so a curated test FEN can be picked with full
knowledge of what the verified witness layer actually emits.

Run: uv run python scripts/phase3b_probe_dump.py
"""

from __future__ import annotations

from dialectical_checkers.arguments import build_root_argument_graph
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.witnesses import probe_moves

FENS = [
    "B:W10,17,18:B6,13,14",
    "B:W23,30:B18,19,27",
    "B:W14,23:B10,18,27",
    "B:W18,27:B14,23,31",
]


def main() -> None:
    for fen in FENS:
        board = CheckersBoard.from_fen(fen)
        probes = list(probe_moves(board))
        graph = build_root_argument_graph(probes)
        print(f"=== {fen}  turn={board.turn} ===")
        for p in probes:
            print(
                f"  {p.pdn}: reasons={p.reasons} obj={p.objections} "
                f"reply={p.reply_attacks} def={p.defenses}"
            )
        print(f"  survivors={sorted(graph.survivors)}")
        grounded_moves = sorted(
            pdn
            for pdn, a in graph.move_arguments.items()
            if a in graph.grounded_extension
        )
        print(f"  grounded_moves={grounded_moves}")
        print()


if __name__ == "__main__":
    main()
