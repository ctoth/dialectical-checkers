"""Analyze the three winning-shot corpus positions the selector fix changed.

Run: ``uv run python scripts/phase3b_analyze_corpus_failures.py``

For each position the test expects a specific winning move; the selector fix
changed the engine's pick. This script prints, for every legal move, the probe
witnesses, the crisp survivor status, the selection key, and the NET material
swing of the move resolved by the verified resolver — so it can be judged
whether the engine's NEW pick is an equally-good (or better) winning move or a
genuine regression.
"""

from __future__ import annotations

from dialectical_checkers import DialecticalCheckersEngine
from dialectical_checkers.arguments import build_root_argument_graph
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import Tier, resolve
from dialectical_checkers.selection import _selection_key
from dialectical_checkers.witnesses import probe_moves

CASES: list[tuple[str, str]] = [
    ("B:W11,19,21,22,25,26,29,30,31,32:B1,2,3,4,5,6,7,8,12", "8x15x24"),
    (
        "B:W10,19,21,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,12,15,16",
        "7x14",
    ),
    ("W:W21,22,23,24,25,27,28,29,30,31,32:B1,2,3,4,5,7,8,11,12,14,19", "24x15"),
]


def _mover_net(board: CheckersBoard, move_pdn: str) -> tuple[int, str | None, str]:
    """The mover's NET material swing for ``move_pdn``, plus terminal + tier.

    Resolve the whole forced line after the move; net the mover's own immediate
    capture gain against the opponent's forced reply.
    """
    move = {m.pdn(): m for m in board.legal_moves()}[move_pdn]
    mover = board.turn

    def mat(b: CheckersBoard, side: str) -> int:
        other = "w" if side == "r" else "r"

        def w(s: str) -> int:
            return sum(
                (150 if c[1] else 100)
                for c in b.cells
                if c is not None and c[0] == s
            )

        return w(side) - w(other)

    child = board.apply(move)
    line = resolve(child)
    gain = mat(child, mover) - mat(board, mover)
    if line.terminal is not None:
        return (gain, line.terminal, line.tier.value)
    return (gain - line.material_swing, None, line.tier.value)


def main() -> None:
    engine = DialecticalCheckersEngine()
    for fen, expected in CASES:
        board = CheckersBoard.from_fen(fen)
        probes = list(probe_moves(board))
        graph = build_root_argument_graph(probes)
        chosen = engine.choose_move(board).move_pdn
        print(f"position: {fen}")
        print(f"  corpus expected: {expected}   engine chose: {chosen}")
        print(f"  crisp survivors: {sorted(graph.survivors)}")
        for probe in probes:
            net, terminal, tier = _mover_net(board, probe.pdn)
            key = _selection_key(probe, graph, board)
            mark = ""
            if probe.pdn == expected:
                mark += " <-EXPECTED"
            if probe.pdn == chosen:
                mark += " <-CHOSEN"
            print(
                f"    {probe.pdn:14s} net={net:5d} terminal={terminal} "
                f"tier={tier:9s} key={key}{mark}"
            )
        print()


if __name__ == "__main__":
    main()
