"""Phase 7 — inspect whether lost games had an AVOIDABLE turning point.

The 48-game run flagged turning points whose move was a forced capture
('safe alternatives: none') — meaning the loss was already locked in by then.
This script replays each lost game and reports, for every engine ply, whether
the engine had a choice and whether the chosen move conceded a shot, so the
loss-mining diagnostic can be refined to point at the AVOIDABLE blunder ply.
Measurement script, no oneliners.
"""

from __future__ import annotations

from dialectical_checkers.loss_mining import move_allows_shot
from dialectical_checkers.match import MinimaxPlayer, RED_WIN
from dialectical_checkers.strength_eval import evaluate_matchup


def main() -> None:
    matchup = evaluate_matchup(
        opponent_factory=lambda: MinimaxPlayer(depth=4),
        opponent_name="MinimaxPlayer(depth=4)", games=48, seed=3)
    half = matchup.engine_red_games
    for gi, game in enumerate(matchup.games_played, start=1):
        engine_is_red = (gi - 1) < half
        engine_won = (game.outcome == RED_WIN) == engine_is_red
        if engine_won or game.outcome == "draw":
            continue
        engine_side = "r" if engine_is_red else "w"
        print(f"--- game {gi} ({engine_side}), {game.ply_count} plies, "
              f"outcome {game.outcome} ---")
        for ply, move in enumerate(game.moves, start=1):
            board = game.positions[ply - 1]
            if board.turn != engine_side:
                continue
            legal = board.legal_moves()
            shot = move_allows_shot(board, move)
            had_choice = len(legal) > 1
            safe = [m.pdn() for m in legal
                    if move_allows_shot(board, m) is None]
            if shot is not None:
                print(f"  ply {ply}: {move.pdn()} CONCEDES "
                      f"(choice={had_choice}, safe={safe})")
                break
        else:
            print("  no conceding engine ply found")


if __name__ == "__main__":
    main()
