"""Verify the corrected NET-outcome loss oracle for the Phase 3b property test.

Run: ``uv run python scripts/phase3b_verify_loss_oracle.py``

The old ``_gives_opponent_forced_win`` treated any opponent FACT material gain
as a loss, ignoring the mover's own capture. The corrected oracle nets the
mover's own immediate capture gain against the opponent's forced reply.

For each move on the analyst position ``B:W10,17,18:B6,13,14`` this prints:
  * the opponent's forced reply (``opponent_shot``);
  * the mover's own immediate gain on the move;
  * the NET swing for the mover;
  * the OLD verdict (any opponent gain -> loss) vs the NEW verdict (net < 0).

Expected: ``6x15x22`` — opponent reply nets 100, mover's own gain 200, NET
+100 -> NEW verdict NOT losing (the old verdict wrongly called it losing).
"""

from __future__ import annotations

from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.captures import Tier, opponent_shot, resolve

FEN = "B:W10,17,18:B6,13,14"


def _net_material(board: CheckersBoard, side: str) -> int:
    """Weighted material balance for ``side`` (man=100, king=150)."""
    other = "w" if side == "r" else "r"

    def mat(s: str) -> int:
        total = 0
        for cell in board.cells:
            if cell is None or cell[0] != s:
                continue
            total += 150 if cell[1] else 100
        return total

    return mat(side) - mat(other)


def old_oracle(board: CheckersBoard, move: CheckersMove) -> bool:
    """The OLD classifier: any opponent FACT material gain -> loss."""
    shot = opponent_shot(board, move)
    if shot is None or shot.tier is not Tier.FACT:
        return False
    mover = board.turn
    wins_game = shot.terminal is not None and shot.terminal != mover
    wins_material = shot.terminal is None and shot.material_net > 0
    return wins_game or wins_material


def new_oracle(board: CheckersBoard, move: CheckersMove) -> bool:
    """The corrected NET-outcome classifier.

    Resolve the whole forced line after ``move`` and net the mover's own
    immediate capture gain against the opponent's forced continuation.
    """
    mover = board.turn
    child = board.apply(move)
    line = resolve(child)
    if line.tier is not Tier.FACT:
        # The resolver did not prove the line — not a proven forced loss.
        return False
    if line.terminal is not None:
        return line.terminal != mover
    # ``line.material_swing`` is from the opponent's perspective (the side to
    # move at ``child``). The mover's own immediate gain across ``move`` is the
    # change in the mover's balance from root to child. NET for the mover is
    # that gain minus what the opponent then forces.
    mover_immediate_gain = _net_material(child, mover) - _net_material(
        board, mover
    )
    net_for_mover = mover_immediate_gain - line.material_swing
    return net_for_mover < 0


def main() -> None:
    board = CheckersBoard.from_fen(FEN)
    print(f"position: {FEN}  (mover = {board.turn})")
    for move in board.legal_moves():
        child = board.apply(move)
        line = resolve(child)
        mover = board.turn
        gain = _net_material(child, mover) - _net_material(board, mover)
        net = gain - line.material_swing
        print(f"  move {move.pdn()}")
        print(f"    opponent forced swing : {line.material_swing} "
              f"terminal={line.terminal} tier={line.tier.value}")
        print(f"    mover own gain        : {gain}")
        print(f"    NET for mover         : {net}")
        print(f"    OLD verdict (losing?) : {old_oracle(board, move)}")
        print(f"    NEW verdict (losing?) : {new_oracle(board, move)}")


if __name__ == "__main__":
    main()
