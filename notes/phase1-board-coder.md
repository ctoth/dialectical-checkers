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

### DONE
- Committed: 4f070ea44166cfd49867359930fccb557490e21b
- Gate: uv sync OK; pytest 41 passed (23 unit / 3 property / 15 differential);
  pyright 0 errors.
- Report: dialectical-chess/reports/phase1-board-coder.md

## 2026-05-20 — Phase 1 FIX cycle (Coder)

### Baseline reproduced
- `uv run pytest` clean master: 41 passed.
- Oracle bug confirmed: `B:W17,18,25,26:BK14`
  engine `['14x21x30x23','14x23x30x21']`
  oracle `['14x21x30x23x14','14x23x30x21x14']` — chain stops one capture early.

### Root cause (CRITICAL)
`_expand_jumps` line 272 read `self.cells[land]` (the STATIC original board).
The moving king's origin (path[0]) stays occupied through recursion, so a
circular jump landing back on the now-empty origin is wrongly blocked.

### Fix applied
In `_expand_jumps`: landing square is occupied iff
`self.cells[land] is not None AND land != path[0]`. The origin (path[0]) is
empty after the first hop — the piece left it. Captured squares already
handled by `land in captured`. ROOT CAUSE, not symptom.

### Remaining work
- MAJOR: replace test_captured_square_blocks_landing /
  test_captured_pieces_block_landing_in_chain with real multi-jump tests.
- MAJOR: add king backward/multijump/loop EDGE_CASES incl. B:W17,18,25,26:BK14.
- MAJOR: oracle-driven differential walk, >=300 positions, deterministic seed.
- MINOR: from_fen reject empty/doubled/trailing-comma tokens + invalid-FEN tests.
- MINOR: _position_hash store stable tuple, not randomized hash.
- Gate: uv sync / pytest / pyright / perft d=1..6.

### Progress (fix cycle)
- CRITICAL fix applied + verified: oracle case now
  `['14x21x30x23x14','14x23x30x21x14']`. perft d1..6 unchanged.
- MINOR position-id fix applied: `_position_id()` returns `(cells, turn)`
  tuple; history typed `tuple[PositionId, ...]`; 3 callsites updated.
- MINOR from_fen fix applied: empty/doubled/trailing-comma tokens now raise
  ValueError; non-numeric tokens raise ValueError with clear message.
- CRITICAL fix exposed a real apply/test interaction: circular king jump has
  origin == destination, so `test_property_apply_yields_valid_board` line 425
  assertion `after.cells[move.origin-1] is None` was false. apply() is CORRECT
  (verified: all 4 White captured, Red king back on 14). Fixed the test
  assertion to skip the origin-empty check when origin == destination — this
  is correcting an assertion the prior code never exercised, NOT weakening.

### Remaining
- Replace 2 captured-piece tests with real multi-jump continuation tests.
- Add king EDGE_CASES (backward/multijump/loop incl B:W17,18,25,26:BK14).
- Add oracle-driven differential walk >=300 positions.
- Add invalid-FEN tests.
- Final gate.

### Fix-cycle progress 2
- All 5 engine/test edits done. pyright 0 errors. 61 passed / 1 failed.
- The 1 failure was MY new test: asserted captured==(18,25,26) but engine
  emits sequence order (18,26,25) — 18 jumped first, then 26, then 25.
  pdn `14x23x30x21` is correct. Fixed test assertion to (18,26,25).
- New tests: test_captured_square_stays_occupied_during_chain,
  test_circular_king_jump_lands_on_emptied_origin,
  test_differential_oracle_driven_walk,
  test_from_fen_rejects_empty_square_tokens,
  test_from_fen_rejects_malformed_fen; 3 new EDGE_CASES.

### FIX CYCLE DONE
- Gate: uv sync OK; pytest 62 passed (40 unit / 3 property / 19 differential);
  pyright 0 errors; perft d1..6 = [7,49,302,1469,7361,36768].
- All 5 analyst findings addressed.
- Report: dialectical-chess/reports/phase1-board-fix.md

### Blockers
None.
