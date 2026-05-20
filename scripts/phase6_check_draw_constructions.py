"""Phase 6: verify the constructed draw-rule test positions actually draw.

Checks the no-progress and lone-king-shuffle constructions used in
test_match.py reach a genuine WCDF draw (not a terminal, not the ply cap).
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.match import RandomPlayer, play_game


class Scripted:
    def __init__(self, name, picker):  # type: ignore[no-untyped-def]
        self.name = name
        self._picker = picker

    def choose(self, board: CheckersBoard) -> CheckersMove:
        return self._picker(board)


def roam(board: CheckersBoard) -> CheckersMove:
    legal = sorted(board.legal_moves(), key=lambda m: m.pdn())
    idx = board.no_progress % len(legal)
    return legal[idx]


def main() -> None:
    # No-progress construction: four kings.
    start = CheckersBoard.from_fen("B:WK28,K32:BK1,K5")
    result = play_game(Scripted("R", roam), Scripted("W", roam), start=start)
    print(
        f"four-king roam: outcome={result.outcome} reason={result.reason} "
        f"plies={result.ply_count} final_no_progress="
        f"{result.positions[-1].no_progress}"
    )

    # Lone-king construction.
    start2 = CheckersBoard.from_fen("B:WK20:BK12")
    result2 = play_game(
        RandomPlayer(seed=3), RandomPlayer(seed=4), start=start2
    )
    print(
        f"lone-king random: outcome={result2.outcome} "
        f"reason={result2.reason} plies={result2.ply_count}"
    )

    # Try several seeds for the lone-king position to see if it ever wins.
    outcomes = {}
    for seed in range(20):
        r = play_game(
            RandomPlayer(seed=seed), RandomPlayer(seed=seed + 1), start=start2
        )
        outcomes[r.outcome] = outcomes.get(r.outcome, 0) + 1
    print(f"lone-king 20-seed outcome tally: {outcomes}")


if __name__ == "__main__":
    main()
