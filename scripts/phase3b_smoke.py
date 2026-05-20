"""Phase 3b smoke check: the engine plays a move from a spread of positions.

Not a test — a developer probe. Confirms ``analyze`` / ``choose_move`` run end
to end and return a legal move (or a null decision at a terminal position).
"""

from __future__ import annotations

from dialectical_checkers import DialecticalCheckersEngine
from dialectical_checkers.board import CheckersBoard

FENS = [
    None,  # the opening
    "B:W18,26:B15",  # free winning shot — engine must take 15x22x31
    "B:W16,24:B11",  # forced double jump
    "B:W22,30:B6,9,13,14",  # a move allows a shot
    "B:W22,30:B9,13",  # 13-17 loses the game; 9-14 etc may be safe
    "B:W21:B27",  # crowning available
    "W:WK10:B5",  # white king vs red man
]


def main() -> None:
    engine = DialecticalCheckersEngine()
    for fen in FENS:
        board = CheckersBoard.initial() if fen is None else CheckersBoard.from_fen(fen)
        legal = [m.pdn() for m in board.legal_moves()]
        decision = engine.choose_move(board)
        analysis = engine.analyze(board)
        if not legal:
            ok = decision.move_pdn == "" and decision.selected is None
        else:
            ok = decision.move_pdn in legal
        print(
            f"fen={fen!r} turn={board.turn} legal={len(legal)} "
            f"chose={decision.move_pdn!r} survivors={len(analysis.graph.survivors)} "
            f"args={len(analysis.graph.arguments)} ok={ok}"
        )
        if not ok:
            raise SystemExit(f"FAIL: bad decision for {fen!r}: {decision.move_pdn!r}")
    print("phase3b smoke: all positions returned a legal/null decision")


if __name__ == "__main__":
    main()
