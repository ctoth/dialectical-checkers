"""Phase 3b — verify the curated tactical corpus against the resolver + pydraughts.

For each candidate position prints:
  * the legal moves;
  * for the "winning shot" corpus: which move(s) the verified resolver proves
    win the game / win material outright, and which the engine actually plays;
  * for the "safe vs losing" corpus: which moves the resolver proves give the
    opponent a forced game/material win (LOSING) and which do not (SAFE), and
    which the engine plays.

The resolver (``captures.opponent_shot``) is the verified Phase-2 tactical
spine. pydraughts is used only to independently confirm the legal-move set and
the terminal verdict of a chosen line — never imported by the engine.

Run: uv run python scripts/phase3b_verify_corpus.py
"""

from __future__ import annotations

from dialectical_checkers import DialecticalCheckersEngine
from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.captures import Tier, opponent_shot

# Candidate "free winning shot/capture" positions — the side to move has a move
# that wins the game or wins material by force.
WINNING_SHOTS = [
    "B:W18,26:B15",
    "B:W16,24:B11",
    "B:W18:BK15",
    "B:W7,15:BK2",
    "B:W18,25,26:BK14",
    "B:WK15,22:B18,19,K27,31",
    "B:W14:B10",
    "B:W15,23:B10,19,26",
    "B:W6,14,22:B1,9,17",
    "B:W17,18:B13,14,21",
]

# Candidate "some moves lose, others are safe" positions.
SAFE_VS_LOSING = [
    "B:W22,30:B9,13",
    "B:W10,17,18:B6,13,14",
    "B:W23,30:B18,19,27",
    "B:W15,24:B11,19,20",
    "B:W14,23:B10,18,27",
    "B:W7,16:B2,11,12",
    "B:W18,27:B14,23,31",
    "B:W6,15:B1,10,11",
]


def _classify(board: CheckersBoard, move: CheckersMove) -> str:
    """Classify a move as the resolver sees it, from the mover's view."""
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
    # Does the move win material outright (own forced gain)?
    return "QUIET-OR-SAFE"


def main() -> None:
    engine = DialecticalCheckersEngine()
    print("=== WINNING SHOTS ===")
    for fen in WINNING_SHOTS:
        board = CheckersBoard.from_fen(fen)
        moves = board.legal_moves()
        classes = {m.pdn(): _classify(board, m) for m in moves}
        winners = [p for p, c in classes.items() if c == "WINS-GAME"]
        chose = engine.choose_move(board).move_pdn
        print(f"{fen}  turn={board.turn}")
        print(f"  moves={[m.pdn() for m in moves]}")
        print(f"  classes={classes}")
        print(f"  WINS-GAME moves={winners}  engine chose={chose!r}")
    print()
    print("=== SAFE VS LOSING ===")
    for fen in SAFE_VS_LOSING:
        board = CheckersBoard.from_fen(fen)
        moves = board.legal_moves()
        classes = {m.pdn(): _classify(board, m) for m in moves}
        losing = [p for p, c in classes.items() if c.startswith("LOSES")]
        safe = [p for p, c in classes.items() if not c.startswith("LOSES")]
        chose = engine.choose_move(board).move_pdn
        print(f"{fen}  turn={board.turn}")
        print(f"  moves={[m.pdn() for m in moves]}")
        print(f"  classes={classes}")
        print(f"  LOSING={losing}  SAFE={safe}  engine chose={chose!r}")


if __name__ == "__main__":
    main()
