"""Phase 3b — confirm the FINAL curated corpus: engine picks correctly + oracle.

For every curated position this prints whether:
  * the engine's chosen move is a winning move (winning-shot corpus) or a safe
    move (safe-vs-losing corpus), classified by the verified resolver;
  * pydraughts independently agrees on the legal-move set (the chosen move is
    a legal move in the oracle's own move generation).

This is the script the curated-corpus pytest assertions in
``tests/test_engine.py`` are derived from. pydraughts is used here only as an
independent legal-move oracle; it is never imported by the engine.

Run: uv run python scripts/phase3b_confirm_corpus.py
"""

from __future__ import annotations

from draughts import Board, Move  # type: ignore[import-untyped]

from dialectical_checkers import DialecticalCheckersEngine
from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.captures import Tier, opponent_shot, own_shot

# Final winning-shot corpus: the side to move has a forced win (game or
# material). For multi-move positions exactly the listed move(s) win.
WINNING_SHOTS = [
    "B:W18,26:B15",
    "B:W16,24:B11",
    "B:W18:BK15",
    "B:W7,15:BK2",
    "B:W18,25,26:BK14",
    "B:W14:B10",
    "B:W16,21,22,24,25,27,28,29,30,31,32:B1,2,3,4,5,7,8,11,12,14",
    "B:W11,19,21,22,25,26,29,30,31,32:B1,2,3,4,5,6,7,8,12",
    "B:W10,19,21,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,12,15,16",
    "W:W21,22,23,24,25,27,28,29,30,31,32:B1,2,3,4,5,7,8,11,12,14,19",
]

# Final safe-vs-losing corpus: the side to move has at least one move the
# resolver proves loses (game/material) and at least one move that does not.
SAFE_VS_LOSING = [
    "B:W22,30:B9,13",
    "W:W18,21,22,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,11,19",
    "B:W18,21,22,25,26,29,31,32:B1,2,3,4,5,6,7,9,19,28",
    "W:W18,21,22,25,26,29,31,32:B1,2,3,4,5,7,9,10,19,28",
    "B:W18,21,22,23,25,29,31:B1,3,4,5,6,7,9,10,26,28",
    "W:W17,18,22,23,25,29,31:B1,4,5,6,8,9,10,11,26,28",
]


def _classify(board: CheckersBoard, move: CheckersMove) -> str:
    mover = board.turn
    child = board.apply(move)
    if child.is_terminal() and child.winner() == mover:
        return "WINS-GAME"
    own = own_shot(board, move)
    if own is not None and own.tier is Tier.FACT and (
        own.terminal == mover or own.material_net > 0
    ):
        if own.terminal == mover:
            return "WINS-GAME"
        return f"WINS-MAT-{own.material_net}"
    shot = opponent_shot(board, move)
    if shot is not None and shot.tier is Tier.FACT:
        if shot.terminal is not None and shot.terminal != mover:
            return "LOSES-GAME"
        if shot.terminal is None and shot.material_net > 0:
            return f"LOSES-MAT-{shot.material_net}"
    return "SAFE"


def _oracle_legal(fen: str) -> set[str]:
    """The legal-move PDN set from pydraughts' English-variant generator."""
    board = Board(variant="english", fen=fen)
    out: set[str] = set()
    for mv in board.legal_moves():
        # pydraughts Move exposes the steps; render as the engine's PDN.
        steps = mv.steps_move
        sep = "x" if mv.captures else "-"
        out.add(sep.join(str(s) for s in steps))
    return out


def main() -> None:
    engine = DialecticalCheckersEngine()
    failures: list[str] = []

    print("=== WINNING-SHOT corpus ===")
    for fen in WINNING_SHOTS:
        board = CheckersBoard.from_fen(fen)
        classes = {m.pdn(): _classify(board, m) for m in board.legal_moves()}
        chose = engine.choose_move(board).move_pdn
        chose_class = classes.get(chose, "<none>")
        wins = chose_class.startswith("WINS")
        try:
            oracle = _oracle_legal(fen)
            oracle_ok = chose in oracle
        except Exception as exc:  # pragma: no cover - diagnostic
            oracle = set()
            oracle_ok = f"oracle-error: {exc}"  # type: ignore[assignment]
        print(f"{fen}\n  classes={classes}\n  chose={chose!r} -> {chose_class}"
              f"  oracle_legal_ok={oracle_ok}")
        if not wins:
            failures.append(f"WINNING-SHOT {fen}: engine chose {chose!r} ({chose_class})")

    print()
    print("=== SAFE-VS-LOSING corpus ===")
    for fen in SAFE_VS_LOSING:
        board = CheckersBoard.from_fen(fen)
        classes = {m.pdn(): _classify(board, m) for m in board.legal_moves()}
        chose = engine.choose_move(board).move_pdn
        chose_class = classes.get(chose, "<none>")
        safe = not chose_class.startswith("LOSES")
        try:
            oracle = _oracle_legal(fen)
            oracle_ok = chose in oracle
        except Exception as exc:  # pragma: no cover - diagnostic
            oracle = set()
            oracle_ok = f"oracle-error: {exc}"  # type: ignore[assignment]
        print(f"{fen}\n  classes={classes}\n  chose={chose!r} -> {chose_class}"
              f"  oracle_legal_ok={oracle_ok}")
        if not safe:
            failures.append(f"SAFE-VS-LOSING {fen}: engine chose {chose!r} ({chose_class})")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  {f}")
        raise SystemExit(1)
    print("phase3b corpus confirmed: engine picks correctly on every position")


if __name__ == "__main__":
    main()
