"""Phase 7 — extract specific report details: opening-loss case, draw reasons.

Confirms game 12 vs Minimax4's loss began from the opening position itself,
and tallies the draw-reason breakdown vs Minimax4. No oneliners.
"""

from __future__ import annotations

from collections import Counter

from dialectical_checkers.match import MinimaxPlayer
from dialectical_checkers.strength_eval import evaluate_matchup


def main() -> None:
    mm4 = evaluate_matchup(
        opponent_factory=lambda: MinimaxPlayer(depth=4),
        opponent_name="MinimaxPlayer(depth=4)", games=48, seed=3)
    reasons = Counter(g.reason for g in mm4.games_played)
    print(f"vs Minimax4 game-end reasons: {dict(reasons)}")
    plies = [g.ply_count for g in mm4.games_played]
    print(f"vs Minimax4 ply counts: min={min(plies)} max={max(plies)} "
          f"mean={sum(plies)/len(plies):.1f}")

    # Game 12 (index 11) — its starting position.
    g12 = mm4.games_played[11]
    print(f"game 12 start: {g12.positions[0].to_fen()}")
    print(f"game 12 outcome={g12.outcome} reason={g12.reason} "
          f"plies={g12.ply_count}")

    # vs Minimax1 and Minimax2 reason tallies.
    for depth, seed in ((1, 1), (2, 2)):
        mm = evaluate_matchup(
            opponent_factory=lambda d=depth: MinimaxPlayer(depth=d),
            opponent_name=f"mm{depth}", games=48, seed=seed)
        rc = Counter(g.reason for g in mm.games_played)
        print(f"vs Minimax{depth} game-end reasons: {dict(rc)}")


if __name__ == "__main__":
    main()
