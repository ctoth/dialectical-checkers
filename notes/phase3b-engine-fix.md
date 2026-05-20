# Phase 3b engine fix — Coder notes

## 2026-05-20

### Task
Fix 3 MAJOR + 1 MINOR from `reports/phase3b-engine-analyst.md`. Work on `master`, commit there.

### Findings observed (verified by reading source)

**MAJOR 1 — selector** (`selection.py:67-93`, `_worst_fact_objection_magnitude`):
counts EVERY FACT objection/reply on a probe, even when the move is a grounded
crisp survivor (defense defeated the reply). Design §7 term 1 must be 0 for any
grounded survivor; non-zero only in empty-survivor fallback. Root cause: the
function works off `probe` alone, no knowledge of the graph / grounded status.
Fix: `_selection_key` / `choose_move` must pass grounded info; term 1 is 0 for
grounded survivors, and in the fallback ranks by worst UNDEFEATED FACT
objection/reply magnitude.

**MAJOR 2 — defense over-defeats** (`arguments.py:178-184`, `witnesses.py:175`):
`defense:holds_exchange` carries no target identity. `build_root_argument_graph`
adds `defense -> attacked` for EVERY attacker on the move. Root cause:
`witnesses.py` emits `defense:holds_exchange` un-keyed. Fix: `witnesses.py` must
emit the defense keyed to the specific reply it answers. The defense in
witnesses.py is created at line 171-175 when `mover_swing >= 0` — it answers the
`reply:material:{shot.material_net}` emitted at line 165. Keying scheme (per
dialectical-chess pattern `defense:{move}:{answered_attack}`): emit
`defense:holds_exchange:{answered_label}` so the answered reply label is
recoverable. `arguments.py` must wire `defense -> only its keyed target`.

**MAJOR 3 — loss oracle** (`tests/test_engine.py:93-111`,
`_gives_opponent_forced_win`): treats any opponent FACT material gain as a loss,
ignoring mover's own capture. Fix: use NET swing. For a capture move, mover's
net = own immediate gain - opponent recapture; defended even/favourable exchange
is NOT a loss. `captures.resolve()` on the position AFTER the move gives the
opponent-perspective swing; need to combine with mover's own gain. Better: use
`resolve()` directly on a position — but the move is already applied. The
`opponent_shot` swing is opponent-perspective AFTER move. The mover's own capture
gain on the move itself = net_material(child,mover) - net_material(board,mover).
Net for mover = mover_immediate_gain - opponent_shot.material_net. Loss iff < 0
(material) or opponent wins game.

**MINOR** — no direct selector contract tests. Add `tests/test_selection.py`.

### Evidence parser note
`evidence.to_argument_evidence` rpartition's on last `:`. A label
`defense:holds_exchange:reply:material:100` would rpartition badly. Defense
labels are FACT via `_FIXED` exact match — keyed form will not match. Need to
register keyed defense form in evidence.py OR keep `_is_fact` working. Currently
`arguments._is_fact` calls `to_argument_evidence`. MUST update evidence.py to
parse keyed defense labels, or arguments.py drops them. INVESTIGATE.

### Baseline
- Pre-existing untracked: `pyghidra_mcp_projects/`, `scripts/phase2_verify_critical.py`.
- git log head: f615e26. Branch: master (need to confirm).
- Analyst says 250 passed, pyright clean. Need to run baseline myself.

### State / progress
- Baseline: 250 passed, branch master, head f615e26.
- Reproduce script confirms: `6x15x22` key (100,...), `14x23` key (50,...), both
  grounded survivors; engine wrongly picks `14x23`.
- Defense keying scheme CHOSEN: `defense:holds_exchange@{answered_reply_label}`,
  `@` separator. evidence.py parses keyed form, adds `answered` field. DONE.
- witnesses.py emits keyed defense. DONE.
- arguments.py docstring updated; NEXT: wire `defense -> only keyed target`.
- Then MAJOR 1 selector (term 1 = 0 for grounded survivors), MAJOR 3 oracle.
- Existing tests asserting bare `defense:holds_exchange`:
  test_witnesses.py:288, :276; test_arguments.py:107 (defenses tuple value).
  These need updating to keyed form — NOT weakening, a rename per CLAUDE.md.

### Progress 2
- evidence.py: keyed defense `defense:holds_exchange@{answered}`, `answered`
  field. DONE.
- witnesses.py: emits keyed defense. DONE.
- arguments.py: `_obj_arg`->`obj_arg_id`, `_reply_arg`->`reply_arg_id` public;
  defense wires to only keyed target via `attacker_by_label`. DONE.
- selection.py: `_worst_fact_objection_magnitude(probe, graph)` — 0 for
  grounded survivor, else worst UNDEFEATED attacker. `_selection_key` takes
  graph. DONE.
- NEXT: fix reproduce script signature; run; MAJOR 3 oracle in test_engine.py;
  update existing tests asserting bare defense label; add new tests
  (test_selection.py, regression in test_arguments.py + test_engine.py).

### Progress 3 — CORPUS FAILURE INVESTIGATION (BLOCKER decision point)
After MAJOR 1+2+3 fixes: 5 test failures. 2 are bare-defense-label renames
(easy). 3 are `test_engine_takes_the_free_winning_shot` corpus failures.

Diagnostic `phase3b_analyze_corpus_failures.py` shows the ROOT CAUSE:
- pos1: expected 8x15x24 (NET +200), engine picks 7x16x23 (NET +100). BOTH
  have key term `large_material`=-200 (the pro:material:200 from the move's
  IMMEDIATE jumps), but 7x16x23 then loses 100 back. The selector's term-2
  `pro:material` is the move's IMMEDIATE capture, NOT the net. So a move that
  grabs 200 then gives 100 back ties on term2 with a move that grabs 200 clean.
- pos2: expected 7x14 (NET +100), engine picks 15x24 (NET 0, even trade).
  Both key (0,0,0,0,-100,0,...) — IDENTICAL except PDN. 7x14 is pro:material:100
  clean; 15x24 is pro:material:100 then gives 100 back (defense:holds_exchange).
  Selector cannot tell a clean +100 from a held-even 0.
- pos3: same as pos2 — 24x15 NET+100 vs 23x16 NET 0, identical keys.

ROOT CAUSE: selector term 2 (`_fact_pro_priority`) keys on the move's IMMEDIATE
`pro:material` magnitude and ignores that a `reply:material` (defended) means
the mover gives some of it back. A grounded survivor with a defended reply
nets LESS than its pro:material suggests. The static-eval tiebreak (term 6) is
NOT enough — pos2/pos3 it ties at 0 too (or the eval doesn't separate them).

This is squarely MAJOR 1 territory: design §7 term 1 is "worst unavoidable
FACT loss" and term 2 is "FACT pro value". A defended exchange that nets even
is genuinely worse than a clean material gain. The selector must account for
the defended-reply giveback in the pro VALUE, i.e. use NET pro material, not
gross. DECISION: fix term 2 to use net FACT material (immediate pro minus the
defended reply it gave back). This is the correct root-cause fix and makes the
corpus pass without weakening it.

### Progress 4 — ALL 3 MAJOR + corpus fixed
- selection.py term 2: `_defended_reply_giveback` + net material. DONE.
- All 3 corpus positions pass; reproduce shows engine -> 6x15x22. DONE.
- 2 bare-defense-label tests renamed to keyed form (test_witnesses.py:288,
  test_arguments.py:107). NOT weakening — rename per CLAUDE.md. DONE.
- FULL SUITE: 250 passed.
- NEXT: MINOR — add tests/test_selection.py (selector contract); add
  regression tests (B:W10,17,18 -> 6x15x22; MAJOR 2 two-attack-one-defense
  graph). Then run gates, commit.

### Progress 5 — all tests added
- tests/test_selection.py — 14 selector-contract tests (MINOR). DONE.
- test_engine.py — regression test_engine_chooses_verified_better_defended_capture.
- test_arguments.py — 3 MAJOR-2 keyed-defense regression tests.
- test_evidence.py — keyed-defense parsing tests.
- BUG IN MY OWN TESTS: single-probe non-grounded move IS in `survivors` via
  §6 empty-survivor fallback. FIXED — added a clean co-probe so fallback stays
  dormant; assert `survivors == frozenset({clean})`.
- NEXT: rerun full suite, then run gates (uv sync, pytest, pyright) as LAST
  action, commit, write report.



