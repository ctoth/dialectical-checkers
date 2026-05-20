# Phase 5 — graded Categoriser layer + selection modes

## 2026-05-20 — Coder (gauntlet)

### State / findings
- Branch `master`, working tree has pre-existing uncommitted notes + untracked
  scripts from prior phases. MUST `git add` only my own changed files.
- `categoriser_scores` IS in the library: `argumentation.ranking.categoriser_scores`
  -> `RankingResult(scores: dict[str,float], ranking, converged, iterations,
  semantics)`. Besnard-Hunter / Bonzon 2016 Def 9. Iterative fixpoint.
  `ArgumentationFramework(arguments, defeats, attacks=None)` from
  `argumentation.dung`. `categoriser_scores` reads `attacks` if set else `defeats`.
- `arguments.py` crisp layer is VERIFIED & unchanged. `RootArgumentGraph.ranking`
  is the empty seam for the graded layer.
- `selection.py` has `_PHASE4_SEAM` (named phase4 but it is THIS phase's seam):
  terms 3-4 slot between FACT term 2 and the static-eval tiebreak.
  `SELECTOR_MODES = {argument, score, grounded, support, categoriser, optimizer}`.
- `witnesses.py` already emits HEURISTIC objections + HEURISTIC pro-reasons
  (Phase 4 done). HEURISTIC objections: obj:loses_opposition, obj:back_rank_break,
  obj:single_corner_drift, obj:exposes_man. HEURISTIC pros: pro:opposition,
  pro:back_rank_hold, pro:center:{n}, pro:mobility:{n}, pro:formation:{kind}.
- `evidence.to_argument_evidence` types every label with Value+Tier.

### Plan
1. arguments.py: add `build_graded_layer` over crisp survivors — 2nd Dung AF,
   nodes = surviving move: + HEURISTIC obj: nodes, edges heuristic obj->move.
   Run `categoriser_scores`. Expose per-move Cat score on RootArgumentGraph
   (use the `ranking` dict field).
2. selection.py: fill `_PHASE4_SEAM` — term 3 = -Cat(move), term 4 =
   -value-weighted accepted-heuristic-pro count. Terms 1-2 FACT unchanged,
   come first; tiebreak last.
3. selector modes: argument (default full key), categoriser, score, grounded,
   plus existing support/optimizer. Each deterministic over crisp survivors.
4. engine.py: default argument mode now uses full key (already wired via
   choose_move; just the key changes).
5. FACT preservation: graded layer only ranks crisp survivors; never resurrects.

### Progress (checkpoint 2)
- Baseline: 573 passed, pyright 0 errors. Clean.
- `test_arguments.py:298 test_ranking_seam_left_empty_for_phase4` asserts
  `graph.ranking == {}` — Phase 5 fills ranking, so this test MUST be updated
  (it pins the now-deleted seam; not a weakening — the seam is the thing the
  phase removes). Will rewrite it to assert the graded layer is present.
- dialectical-chess modes: argument(default=categoriser key), score, grounded,
  support, categoriser, optimizer. checkers SELECTOR_MODES already = same six.
- IN PROGRESS: arguments.py — added _is_heuristic, updated docstrings,
  imported categoriser_scores. Next: build_graded_layer + wire into
  build_root_argument_graph.
- Term-4 "accepted heuristic pro" decision: heuristic pros never enter any AF
  (Dung = attacks only). Per design §7 v1 every emitted heuristic pro on a
  surviving move counts; value-weighted by its Value. NOT a QBAF.

### Progress (checkpoint 3)
- arguments.py DONE: build_graded_layer added, wired into
  build_root_argument_graph. Probe script confirms: heuristic obj lowers Cat
  1.0->0.5, clean stays 1.0. ranking dict has scores/move_scores/arguments/
  defeats/converged/iterations.
- selection.py DONE: _PHASE4_SEAM removed; terms 3 (Cat score) + 4
  (value-weighted heuristic-pro count) added to _selection_key. Multi-mode
  choose_move: argument(full), categoriser, score, grounded, support,
  optimizer(=argument alias). Each restricts to crisp survivors, deterministic.
- Term-5 sign: _static_eval_int returns static_evaluation(child) directly;
  matches old _selection_key behavior (old returned -(-stateval)=stateval).
- UNDER-SPEC RESOLVED: design §7 says "value-weighted" heuristic-pro count but
  names NO per-value weight for TEMPO/STRUCTURE/MOBILITY. Resolution: uniform
  weight 1 (the only zero-discretion reading; = design line 329 "a count of
  accepted heuristic pro-reasons"). Documented in code + will report.
- TODO: update test_arguments.py:298 (ranking seam now filled), write Phase 5
  tests, run gates.

### Progress (checkpoint 4)
- Phase 4 regression test was 48 failures: 47 quiet-position play changes
  (intended by design §7) + 1 ranking-seam test. Classify script proved:
  47 changed moves, 0 resurrections (every new move IS a crisp survivor),
  0 FACT regressions (every changed position has FACT key (0,0,0,0,0) for
  both old & new = quiet, FACT terms tie, graded broke the tie). CORRECT.
- Removed obsolete test_phase4_regression.py (git rm). Created
  test_phase5_regression.py: Phase 5 baseline (same 120 FENs, P5 moves) +
  the still-valid crisp-layer structural test.
- Updated test_arguments.py ranking-seam test -> now asserts graded layer
  present.
- Suite: 573 passed, pyright 0. Back to green.
- TODO: write Phase 5 dedicated tests: graded-AF unit tests, selector-mode
  consistency/determinism, FACT-PRESERVATION property test (>=200 seeded),
  graded-improvement curated quiet positions. Then gates + commit.

### Progress (checkpoint 5)
- Tests written:
  - test_arguments.py: +7 graded-layer unit tests (all pass, 23 total).
  - test_selection.py: +graded-term + multi-mode tests (32 pass).
  - test_phase5_fact_preservation.py: 4 property tests (>=200 seeded) — all
    pass: never-resurrects, never-overrides-FACT, best-FACT-key-tier,
    argument==grounded when FACT decides.
  - test_phase5_graded_improvement.py: CAT_IMPROVEMENT (4 FENs, FACT-only move
    has obj:exposes_man Cat 0.5, P5 picks clean Cat 1.0) + PRO_IMPROVEMENT
    (4 FENs, P5 has more heuristic pros). _fact_only_choice reconstructs the
    pre-P5 selector.
- TODO: run full suite + graded_improvement test, then gates + commit.

### Blockers
None.
