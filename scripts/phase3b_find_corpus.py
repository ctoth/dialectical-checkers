"""Phase 3b — mine seeded reachable positions for curated-corpus candidates.

Walks deterministic random games from the opening, and reports two kinds of
position the curated tactical corpus needs:

  * WINNING-SHOT: the side to move has >=2 legal moves and exactly one (or a
    proper subset) wins the game by force / wins material outright, while at
    least one other move does not — so "take the shot" is a real choice.
  * SAFE-VS-LOSING: the side to move has both at least one move the resolver
    proves gives the opponent a forced game/material win and at least one move
    that does not — a genuine "pick the safe move" choice.

The resolver (``captures.opponent_shot`` / ``own_shot``) is the verified
Phase-2 tactical spine. pydraughts is not used here — the seeded walk only
needs legal-move generation, already verified in Phase 1.

Run: uv run python scripts/phase3b_find_corpus.py
"""

from __future__ import annotations

import random

from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.captures import Tier, opponent_shot, own_shot


def _classify(board: CheckersBoard, move: CheckersMove) -> str:
    mover = board.turn
    child = board.apply(move)
    if child.is_terminal() and child.winner() == mover:
        return "WINS-GAME"
    shot = opponent_shot(board, move)
    if shot is not None and shot.tier is Tier.FACT:
        if shot.terminal is not None and shot.terminal != mover:
            return "LOSES-GAME"
        if shot.terminal is None and shot.material_net > 0:
            return f"LOSES-MAT-{shot.material_net}"
    own = own_shot(board, move)
    if own is not None and own.tier is Tier.FACT:
        if own.terminal == mover:
            return "WINS-GAME"
        if own.material_net > 0:
            return f"WINS-MAT-{own.material_net}"
    return "SAFE"


def _reachable(seed: int, max_plies: int) -> list[CheckersBoard]:
    rng = random.Random(seed)
    board = CheckersBoard.initial()
    out = [board]
    for _ in range(max_plies):
        moves = board.legal_moves()
        if not moves:
            break
        board = board.apply(rng.choice(moves))
        out.append(board)
        if board.is_draw():
            break
    return out


def main() -> None:
    winning_shots: list[str] = []
    safe_vs_losing: list[str] = []
    seen: set[str] = set()
    for seed in range(2000):
        for depth in (10, 18, 26, 34, 42):
            for board in _reachable(seed, depth):
                fen = board.to_fen()
                if fen in seen:
                    continue
                seen.add(fen)
                moves = board.legal_moves()
                if len(moves) < 2:
                    continue
                classes = [_classify(board, m) for m in moves]
                wins = [c.startswith("WINS") for c in classes]
                loses = [c.startswith("LOSES") for c in classes]
                if any(wins) and not all(wins) and len(winning_shots) < 12:
                    winning_shots.append(fen)
                if any(loses) and not all(loses) and len(safe_vs_losing) < 12:
                    safe_vs_losing.append(fen)
        if len(winning_shots) >= 12 and len(safe_vs_losing) >= 12:
            break
    print("WINNING-SHOT candidates (>=2 moves, some win, some do not):")
    for fen in winning_shots:
        board = CheckersBoard.from_fen(fen)
        cl = {m.pdn(): _classify(board, m) for m in board.legal_moves()}
        print(f"  {fen}  {cl}")
    print()
    print("SAFE-VS-LOSING candidates (>=2 moves, some lose, some safe):")
    for fen in safe_vs_losing:
        board = CheckersBoard.from_fen(fen)
        cl = {m.pdn(): _classify(board, m) for m in board.legal_moves()}
        print(f"  {fen}  {cl}")


if __name__ == "__main__":
    main()
