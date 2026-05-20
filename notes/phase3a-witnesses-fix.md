# Phase 3a witness fix — Coder notes

## 2026-05-20 — state

Task: fix 3 analyst findings on `master` of dialectical-checkers. No branch.

### Findings
1. MAJOR — `tests/test_witnesses.py:386` hollow tier test. Replace with a test
   that drives a HEURISTIC ShotResult through `probe_moves()` via monkeypatch of
   `own_shot`/`opponent_shot`. Must confirm guard-removal experiment.
2. MINOR — `evidence.py:110` `int(tail)` accepts signed/zero/`+` magnitudes.
   Reject them (positive ints only).
3. MINOR — add curated king/deep witness tests.

### Verified from source
- `witnesses.py:149-151` own_shot -> pro:shot_setup under `setup.tier is Tier.FACT`.
- `witnesses.py:157-178` opponent_shot -> objections/replies/defenses under
  `shot.tier is Tier.FACT`.
- witnesses.py imports `own_shot, opponent_shot` from captures into its OWN
  namespace, so monkeypatch target is `dialectical_checkers.witnesses.own_shot`
  / `.opponent_shot`.
- `ShotResult` fields: material_net, forced, truncated, terminal, tier.
- `evidence.py:110` `magnitude = int(tail)` — the bug.

### King/deep positions (verified by verify_king_deep_shots.py)
- king_single_capture `B:W18:BK15` Red `15x22`: swing 100, terminal r, king cap.
- king_double_jump `B:W7,15:BK2` Red `2x11x18`: swing 200, terminal r.
- king_triple_jump `B:W18,25,26:BK14` Red `14x23x30x21`: swing 300, terminal r.
- deep_three_ply `B:WK15,22:B18,19,K27,31` Red `18x25` then forced
  `15x24`,`27x20`: swing 150, terminal r, 3 plies.

### Status — 2026-05-20 progress
- Baseline gates: 179 passed, pyright 0 errors.
- Verified king/deep labels via scripts/phase3a_verify_king_witness_labels.py:
  - king_single_capture 15x22: pro:material:100, pro:shot_setup:100, pro:terminal_win
  - king_double_jump 2x11x18: pro:material:200, pro:shot_setup:200, pro:terminal_win
  - king_triple_jump 14x23x30x21: pro:material:300, pro:shot_setup:300, pro:terminal_win
  - deep 3-ply: 18x25 = pro:material:100,pro:shot_setup:150; 15x24 =
    obj:terminal_loss,pro:material:100,reply:terminal_loss; 27x20 =
    pro:material:150,pro:shot_setup:150,pro:terminal_win.
- Confirmed monkeypatch approach via scripts/phase3a_verify_heuristic_witness.py:
  HEURISTIC own_shot/opponent_shot -> no FACT witness; FACT control emits them.
- DONE: Finding 2 (evidence.py isascii+isdecimal+>0 check) + tests.
- DONE: Finding 1 (replaced hollow test with 5 monkeypatch tests).
- DONE: Finding 3 (4 curated king/deep tests + 4 FENs added to CONSISTENCY_FENS).
- DONE: guard-removal experiment — both guards confirmed:
  - remove witnesses.py:150 guard -> test_heuristic_own_shot_* +
    test_heuristic_resolver_result_* FAIL; restore -> pass.
  - remove witnesses.py:158 guard -> test_heuristic_opponent_shot_* +
    test_heuristic_resolver_result_* FAIL; restore -> pass.
  - git diff witnesses.py empty after restore — production unchanged.
- TODO: final gates as last action; commit; report.
