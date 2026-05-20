"""Phase 4 — determine the Single Corner / Double Corner squares precisely.

The double corner is the corner with TWO playable squares forming a short
diagonal (a 'double corner'); the single corner has one. On the 8x8 board with
PDN numbering, the four physical corners of the 8x8 grid: (0,0),(0,7),(7,0),
(7,7). Only dark squares are playable. Print, for each grid corner, whether it
is a dark playable square and its diagonal neighbours, so the double corner
(the one whose corner square has a playable diagonal partner forming the
2-square corner) is identified.
"""

from __future__ import annotations

from dialectical_checkers.board import NUM_SQUARES, STEP, _coord

idx_to_pdn = {i: i + 1 for i in range(NUM_SQUARES)}
coord_to_idx = {_coord(i): i for i in range(NUM_SQUARES)}


def main() -> None:
    print("Grid corners and their playable status:")
    for corner in [(0, 0), (0, 7), (7, 0), (7, 7)]:
        idx = coord_to_idx.get(corner)
        if idx is None:
            print(f"  {corner}: NOT a dark playable square")
        else:
            print(f"  {corner}: PDN {idx + 1}")
    print()
    # The double corner is the side with two adjacent playable corner squares.
    # White's home rows are 5,6,7. White's near edge row 7 = squares 29-32.
    # Square 32 at (7,6); its single diagonal up-left neighbour and the corner.
    print("Row 7 (White near edge): squares 29-32")
    for pdn in (29, 30, 31, 32):
        idx = pdn - 1
        row, col = _coord(idx)
        nb = [idx_to_pdn.get(s) for s in STEP[idx] if s is not None]
        print(f"  PDN {pdn} at ({row},{col}) step-neighbours -> {nb}")
    print("Row 0 (Red near edge): squares 1-4")
    for pdn in (1, 2, 3, 4):
        idx = pdn - 1
        row, col = _coord(idx)
        nb = [idx_to_pdn.get(s) for s in STEP[idx] if s is not None]
        print(f"  PDN {pdn} at ({row},{col}) step-neighbours -> {nb}")
    # Double corner: the corner square that has only ONE board-edge — actually
    # the double corner is where two playable squares sit at the corner. PDN 4
    # at (0,7) is a true grid corner; PDN 1 at (0,1) is not. PDN 29 at (7,0) is
    # a grid corner; PDN 32 at (7,6) is not.
    print()
    print("True 8x8 grid-corner playable squares: PDN 4 (0,7) and PDN 29 (7,0)")
    print("Port-plan 5.1: 'square 32 is the nearest double-corner square'")
    print("=> White double corner region = squares 28,32 (the 2-square corner")
    print("   at the (7,7) end, since (7,7) is light so 28+32 form it).")


if __name__ == "__main__":
    main()
