# Phase 1 board.py — Coder notes

## 2026-05-20

### State
- Repo `dialectical-checkers` on branch `master`, working tree clean at start.
- Baseline VERIFIED on clean master: `uv run pytest` 2 passed; `uv run pyright`
  0 errors, 0 warnings.
- Phase-0 skeleton `board.py` has `CheckersMove`, `CheckersBoard`,
  `perft` stubs raising NotImplementedError.

### Square numbering decision (directive 4)
- Design §2.1 (PDN 1-32, internal idx = PDN-1) AND pydraughts English variant
  (scout report) AGREE. No discrepancy. Standard English-draughts numbering:
  square 1 top-left dark region, 4 dark squares per row, increasing
  left-to-right top-to-bottom. Red/BLACK = 1-12 moves first toward higher
  numbers; White = 21-32. NO STOP NEEDED.

### Plan
1. Preliminary: add `extraPaths=["."]` to [tool.pyright]; add pydraughts to dev
   group; uv sync.
2. Implement board.py per design §2 with TDD.
3. STEP/JUMP tables computed from 8x8 dark-square geometry.
4. tests/test_board.py — unit/property/differential/perft markers.

### Perft gate target (verified, scout report)
d=1..6 = [7, 49, 302, 1469, 7361, 36768]

### Progress
- Geometry derived from coords formula, VERIFIED reproduces pydraughts
  adjacency for all 32 squares.
- board.py implemented: STEP/JUMP tables, legal_moves, multi-jump expansion,
  apply, terminal/draw, PDN-FEN, perft.
- perft d=1..6 = [7,49,302,1469,7361,36768] — MATCHES gate exactly.
- First pytest run: 39 passed, 2 failed — both were TEST bugs not engine bugs:
  * test_shorter_capture_allowed: expected "11x27" but real double-jump path
    is "11x18x27" (path visits intermediate landing). Engine == oracle. Fixed.
  * test_property_apply_yields_valid_board: piece-conservation assertion
    counted wrong side. Fixed.

### Blockers
None.
