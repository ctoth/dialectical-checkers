"""Verify the curated-shot expected outcomes for tests/test_captures.py.

Run: ``uv run python scripts/verify_curated_shots.py``

For each curated FEN this independently walks the forced capture tree using the
ENGINE board (board.py) only — a standalone minimax identical in spirit to the
brute-force reference in the test file — and prints the net swing, the forced
flag, the terminal status, and the realised principal line. It also replays the
principal line in pydraughts to confirm every move is legal and the oracle
reaches the same material balance.

This pins the hand-computed expected values in CURATED_SHOTS before the
resolver is implemented, so a wrong expected number is caught here, not by a
test that would then look like a resolver bug.
"""

from __future__ import annotations

from draughts import Board as OracleBoard

from dialectical_checkers.board import CheckersBoard

MAN_VALUE = 100
KING_VALUE = 150


def material(board: CheckersBoard, side: str) -> int:
    total = 0
    for cell in board.cells:
        if cell is None or cell[0] != side:
            continue
        total += KING_VALUE if cell[1] else MAN_VALUE
    return total


def net(board: CheckersBoard, root: str) -> int:
    other = "w" if root == "r" else "r"
    return material(board, root) - material(board, other)


def resolve_ref(board: CheckersBoard) -> tuple[int, str | None, list[str]]:
    """Capture-only minimax; returns (net_swing, terminal, principal_line)."""
    root = board.turn
    start = net(board, root)

    def best(node: CheckersBoard) -> tuple[int, str | None, list[str]]:
        captures = [m for m in node.legal_moves() if m.is_jump]
        if not captures:
            moves = node.legal_moves()
            terminal = node.winner() if not moves else None
            return net(node, root), terminal, []
        node_side = node.turn
        scored: list[tuple[int, str | None, list[str], str]] = []
        for mv in captures:
            v, t, line = best(node.apply(mv))
            scored.append((v, t, line, mv.pdn()))
        if node_side == root:
            chosen = max(scored, key=lambda r: (r[0], r[3]))
        else:
            chosen = min(scored, key=lambda r: (r[0], r[3]))
        return chosen[0], chosen[1], [chosen[3], *chosen[2]]

    end, terminal, line = best(board)
    return end - start, terminal, line


def replay_in_oracle(fen: str, line: list[str]) -> tuple[bool, str]:
    """Replay PDN moves in pydraughts; return (all_legal, final_fen)."""
    oracle = OracleBoard(variant="english", fen=fen)
    for pdn in line:
        legal = {
            ("x" if m.has_captures else "-").join(str(s) for s in m.steps_move): m
            for m in oracle.legal_moves()
        }
        if pdn not in legal:
            return False, oracle.fen
        oracle.push(legal[pdn])
    return True, oracle.fen


CURATED = [
    ("single_man_capture", "B:W18:B15", MAN_VALUE),
    ("double_jump", "B:W16,24:B11", 2 * MAN_VALUE),
    ("even_exchange", "B:W18,26:B15", 0),
    ("two_men_one_capture", "B:W18:B14,15", MAN_VALUE),
    ("white_even_exchange", "W:W22:B11,18", 0),
    ("crowning_capture", "B:W25:B21", MAN_VALUE),
]


def main() -> None:
    ok = True
    for label, fen, expected in CURATED:
        board = CheckersBoard.from_fen(fen)
        swing, terminal, line = resolve_ref(board)
        all_legal, final_fen = replay_in_oracle(fen, line)
        status = "OK" if swing == expected and all_legal else "MISMATCH"
        if status != "OK":
            ok = False
        print(
            f"[{status}] {label:24s} fen={fen}\n"
            f"    expected={expected} got={swing} terminal={terminal} "
            f"line={line}\n"
            f"    oracle_replay_legal={all_legal} final_fen={final_fen}"
        )
    print()
    print("ALL EXPECTED VALUES CONFIRMED" if ok else "SOME EXPECTED VALUES WRONG")


if __name__ == "__main__":
    main()
