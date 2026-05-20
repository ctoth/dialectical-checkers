"""Probe the pydraughts English-variant API for the Phase 2 capture tests.

Run: ``uv run python scripts/probe_pydraughts_captures.py``

We need, for the cross-check tests in ``tests/test_captures.py``:

* how to enumerate legal moves and tell captures from quiet moves;
* how to apply a move identified by a PDN string;
* how to read material (men/king counts per side) off a position;
* how to detect a terminal (no-move / game-over) position.

Everything printed here is an OBSERVATION used to write the test helpers; the
test file imports pydraughts only inside the test, never the engine.
"""

from __future__ import annotations

from draughts import Board as OracleBoard


def describe(fen: str) -> None:
    print(f"--- FEN {fen} ---")
    b = OracleBoard(variant="english", fen=fen)
    print(f"  type(board) = {type(b)}")
    print(f"  board attrs = {[a for a in dir(b) if not a.startswith('_')]}")
    moves = b.legal_moves()
    moves = list(moves)
    print(f"  legal_moves count = {len(moves)}")
    for m in moves[:6]:
        print(
            f"    move: steps_move={getattr(m, 'steps_move', '?')} "
            f"has_captures={getattr(m, 'has_captures', '?')} "
            f"attrs={[a for a in dir(m) if not a.startswith('_')]}"
        )
    # game-over probes
    for name in ("is_over", "is_draw", "winner", "game_over"):
        if hasattr(b, name):
            attr = getattr(b, name)
            try:
                val = attr() if callable(attr) else attr
            except Exception as exc:  # noqa: BLE001
                val = f"<error {exc}>"
            print(f"  board.{name} -> {val}")


def main() -> None:
    # Start position.
    describe("B:W21,22,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,11,12")
    # A forced single capture.
    describe("B:W18:B15")
    # A double jump.
    describe("B:W16,24:B11")
    # A terminal position (Red to move, no move).
    describe("B:W5,6,9,10:B1")
    # Probe applying a move.
    b = OracleBoard(variant="english", fen="B:W18:B15")
    mv = list(b.legal_moves())[0]
    print(f"\nApplying move {mv.steps_move} to B:W18:B15")
    b.push(mv)
    print(f"  after fen = {b.fen}")
    print(f"  after legal_moves = {len(list(b.legal_moves()))}")


if __name__ == "__main__":
    main()
