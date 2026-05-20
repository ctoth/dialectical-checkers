"""Phase 7 fix — re-mine the Minimax(4) matchup losses, seed 0, 48 games.

Reproduces exactly the loss-mining the strength report's §4 cites: the
``run_strength_eval(games_per_matchup=48, seed=0, minimax_depths=(1, 2, 4))``
Minimax(4) matchup is ``evaluate_matchup(..., seed=0+3)``. This script replays
that matchup, mines every lost game's turning point with the verified
``mine_losses`` diagnostic, and prints — for each turning point — the game
index, ply, played move and proven material net.

Purpose: confirm the exact count and move of the ply-12 Minimax(4) losses so
the strength report states the measured fact (NO oneliner; port-plan §8).
"""

from __future__ import annotations

from collections import Counter

from dialectical_checkers.loss_mining import mine_losses
from dialectical_checkers.match import MinimaxPlayer
from dialectical_checkers.strength_eval import evaluate_matchup


def main() -> None:
    # The Minimax(4) matchup of the 48-game seed-0 run: run_strength_eval
    # derives its per-matchup seed as seed + offset; depth 4 is the third
    # minimax depth (offset 3), so the matchup seed is 0 + 3 = 3.
    matchup = evaluate_matchup(
        opponent_factory=lambda: MinimaxPlayer(depth=4),
        opponent_name="MinimaxPlayer(depth=4)",
        games=48,
        seed=3,
    )
    half = matchup.engine_red_games
    pairs = [
        (game, index < half)
        for index, game in enumerate(matchup.games_played)
    ]
    points = mine_losses(pairs)

    print(f"Minimax(4) matchup: {matchup.summary()}")
    print(f"resolvable turning points: {len(points)} of {matchup.losses} losses")
    print()

    ply_moves: Counter[tuple[int, str, int]] = Counter()
    for point in points:
        print(
            f"  game {point.game_index} ply {point.ply} ({point.side}): "
            f"{point.played_move} loses {point.shot_material_net} material; "
            f"was_avoidable={point.was_avoidable}"
        )
        ply_moves[(point.ply, point.played_move, point.shot_material_net)] += 1

    print()
    print("ply-12 breakdown:")
    for (ply, move, net), n in sorted(ply_moves.items()):
        if ply == 12:
            print(f"  {n}x  ply 12  {move}  loses {net} material")


if __name__ == "__main__":
    main()
