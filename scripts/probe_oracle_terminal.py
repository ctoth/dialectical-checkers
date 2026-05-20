"""Probe pydraughts' terminal / no-move API for the cross-check rewrite.

Run: ``uv run python scripts/probe_oracle_terminal.py``

The MAJOR fix needs the pydraughts replay to *independently* confirm the
resolver's claimed terminal status. This checks how pydraughts reports a
position where the side to move has no legal move:

* whether ``OracleBoard.legal_moves()`` is empty at such a position;
* whether any ``is_over`` / ``winner`` style attribute exists.

It replays the resolver's claimed line for ``W:W13,14,21:B1,9`` (13x6,
1x10x17, 21x14) and prints the oracle's state at the quiet end position.
"""

from __future__ import annotations

from draughts import Board as OracleBoard

from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import resolve

ORACLE_FEN = "W:W13,14,21:B1,9"


def oracle_move_index(oracle: OracleBoard) -> dict[str, object]:
    """Map a PDN move string -> the pydraughts move object."""
    out: dict[str, object] = {}
    for m in oracle.legal_moves():
        key = ("x" if m.has_captures else "-").join(
            str(s) for s in m.steps_move
        )
        out[key] = m
    return out


def main() -> None:
    board = CheckersBoard.from_fen(ORACLE_FEN)
    line = resolve(board)
    print(f"resolve({ORACLE_FEN}):")
    print(f"  material_swing={line.material_swing} terminal={line.terminal!r}")
    print(f"  principal_line={[m.pdn() for m in line.principal_line]}")
    print()

    oracle = OracleBoard(variant="english", fen=board.to_fen())
    print("pydraughts OracleBoard attributes of interest:")
    for attr in ("is_over", "winner", "is_draw", "game_over"):
        print(f"  has {attr!r}: {hasattr(oracle, attr)}")
    print()

    node = board
    for mv in line.principal_line:
        idx = oracle_move_index(oracle)
        legal = mv.pdn() in idx
        print(f"  replay {mv.pdn():12s} legal-in-pydraughts={legal}")
        assert legal, (mv.pdn(), sorted(idx))
        oracle.push(idx[mv.pdn()])  # type: ignore[arg-type]
        node = node.apply(mv)

    print()
    print(f"  oracle final FEN: {oracle.fen}")
    print(f"  oracle legal_moves() empty: {len(oracle.legal_moves()) == 0}")
    if hasattr(oracle, "is_over"):
        print(f"  oracle.is_over(): {oracle.is_over()}")
    print(f"  engine final FEN: {node.to_fen()}")
    print(f"  engine is_terminal: {node.is_terminal()}  winner: {node.winner()!r}")


if __name__ == "__main__":
    main()
