# Phase 4 — HEURISTIC witness layer FIX cycle (Coder)

## 2026-05-20

### State
Coder in gauntlet FIX cycle. Work list = analyst report
`reports/phase4-heuristic-witnesses-analyst.md`: 4 MAJOR + 1 MINOR, all in
`witnesses.py`. Fix ROOT CAUSES, additive, never weaken a test. master, no
branch. NO ONELINERS — all Python in scripts/.

### Findings to fix (verified by reading witnesses.py)
1. MAJOR `_opposition_holder` (309-323): only checks count==1 each side. Must
   require EQUAL FORCE — both single pieces same type (man-man OR king-king).
   man-vs-king => return None.
2. MAJOR back-rank (`_home_rank_count` 326-337, `back_rank_break` 488-494):
   counts kings as guard men. Must count ONLY MEN on home rank; back_rank_break
   fires only when a MAN leaves home rank.
3. MAJOR `obj:exposes_man` (511-516): fires when exposed capturable piece is a
   king. Must verify the capturable mover piece is a MAN.
4. MAJOR `obj:loses_opposition` (472-486): dead — no firing case found. Must
   fire correctly as mirror of pro:opposition under equal-force 1v1. Prove with
   positive firing test.
5. MINOR: add edge-case tests (opposition silent man-vs-king; positive
   loses_opposition; back-rank with kings on home rank not firing;
   exposes_man with capturable mover king not firing).

### Root-cause analysis of loses_opposition deadness
holder is turn-independent. For a 1v1 ending, EVERY non-capture move changes
separation parity by exactly 1 (a king step is one Chebyshev unit), so it
ALWAYS flips the holder. So if holder(R)==mover, every legal move M has
holder(child)!=mover — UNLESS the move captures (ends the 1v1) or crowns. The
deadness: `keeps_exist` requires a SIBLING that keeps the opposition. But if
the mover holds it, NO sibling keeps it (every move flips). So keeps_exist is
always False => witness never fires. ROOT CAUSE: the `keeps_exist` clause is
wrong. When the mover holds the opposition in a 1v1, the mover CANNOT avoid
losing it — so "a keeping alternative existed" is structurally impossible.
The witness as the mirror of pro:opposition should fire whenever the mover
held the opposition and the move surrendered it. The keeps_exist gate must go.

### Progress
- Baseline: 568 passed, pyright 0 errors.

### loses_opposition — DEEP INVESTIGATION (scripts/phase4fix_*)
- holder() current rule is TURN-DEPENDENT: holder flips with separation
  parity AND with turn. A quiet move flips BOTH (king step changes Chebyshev
  by ±1; turn alternates) => holder is INVARIANT under any quiet move.
  Verified: phase4fix_noncapture_opposition.py = 0 quiet moves surrender a
  held opposition out of 3800 (kk+mm).
- Therefore in a 1v1, if holder(R)==mover, EVERY quiet move keeps it; only a
  CAPTURE flips it (and a capture in 1v1 removes the enemy => holder(S)=None).
  phase4fix_loses_opposition_probe.py: 144 firings, ALL captures (winning the
  game) — wrong to label as "losing tempo".
- The current keeps_exist gate is structurally unsatisfiable: mandatory-capture
  means the legal set is EITHER all-quiet OR all-capture, never mixed. So you
  can never have a keeper (quiet) and a loser (capture) as siblings. THAT is
  the literal deadness root cause.
- A turn-INDEPENDENT holder would make both witnesses reachable for quiet king
  moves, but would BREAK test_opposition_held_by_side_to_move (B:WK4:BK15
  asserts pro:opposition on EVERY Red move). Cannot weaken that test.
### loses_opposition — EXHAUSTIVE PROOF + RESOLUTION
Four independent exhaustive sweeps:
- phase4fix_noncapture_opposition.py: 0/3800 quiet moves surrender a held
  opposition in 1v1.
- phase4fix_loses_opposition_probe.py: 144 firings of holder(R)==mover &
  holder(S)!=mover in 1v1 kk — ALL captures (= winning the game).
- phase4fix_quiet_surrender_exhaustive.py: the ONLY quiet surrenders are 210
  CROWNINGS (man reaches king-row, board becomes king-vs-man); 0 parity, 0
  other. Crowning is a strictly good move.
- phase4fix_capture_into_1v1.py (full 2v2 with kings): 0 roots have split
  1v1-child holders — no move ever secures an opposition a sibling fails.

CONCLUSION: holder() is turn-dependent and a quiet move flips parity AND turn
=> holder is invariant under any quiet move. So "held the opposition and a
quiet move surrendered it" is geometrically impossible except by crowning
(good) or capturing (winning). The strict mirror is genuinely dead for any
CORRECT firing.

ROOT CAUSE of deadness, precisely: the current rule requires holder(R)==mover
AND holder(S)!=mover AND a sibling keeps it. (a) holder(R)==mover&holder(S)!=
mover already isolates ONLY captures/crownings; (b) the keeps_exist sibling
gate is additionally unsatisfiable — mandatory-capture makes the legal set
all-quiet or all-capture, never mixed.

RESOLUTION (correct, reachable, mirror-faithful): the genuine dual of
pro:opposition is the SAME-POSITION dual, not a cross-move one. pro:opposition
says "after M the mover holds the 1v1 opposition". Its objection mirror:
"after M it is a 1v1 equal-force ending and the OPPONENT holds the opposition"
— i.e. holder(S) == opponent (S is 1v1 equal force, mover does NOT hold it).
This fires on a move that LANDS in a 1v1 ending the mover has lost the
opposition of. It is reachable (any move ending in a 1v1 the opponent holds),
correct (the mover is now the one in zugzwang), and the precise dual of
pro:opposition. It is NOT "held then threw away" (impossible) — it is
"reached a 1v1 ending without the opposition", the move-channel statement of
the tempo deficit. CONFIRMED reachable: B:WK8:BK15 (sep 2 even, holder=White)
— Red's moves reach 1v1 kk endings White holds => obj:loses_opposition fires.
Quiet, non-absurd, deterministic, in the equal-force 1v1 case.

### Implementation progress (witnesses.py edited)
- FIX#1 _opposition_holder: added `if reds[0][1] != whites[0][1]: return None`
  (man-vs-king => unequal force => no claim). Docstring updated.
- FIX#2 _home_rank_count: skips kings (counts only men). back_rank_break: now
  requires the moving piece be a MAN on the home rank. Docstring TODO.
- FIX#3 obj:exposes_man: now checks the captured square holds a MAN
  (not child.cells[cap-1][1]) across opponent jumps. Docstring updated.
- FIX#4 obj:loses_opposition: replaced dead root-vs-child+keeps_exist rule
  with S-based mirror: fires iff holder(S) defined & holder(S)!=mover.
  Removed unused `siblings` param from _heuristic_objections + caller.
  Module docstring updated with full rationale.
- Positive firing test position for report: B:WK8:BK15, move 15-18 (quiet,
  non-terminal) => obj:loses_opposition (sep 2 even, White holds 1v1 kk).
### Verified state
- pyright: 0 errors. pytest: 568 passed (all existing tests, incl. the
  test_phase4_regression.py 120-position engine-play baseline => engine play
  CONFIRMED unchanged, additive).
- scripts/phase4fix_verify_all.py: all 4 MAJOR fixes verified on the analyst's
  exact constructed positions + regression-guard positions. ALL PASS.
- Helper added: _captures_a_man (pyright-clean man-capture check).

### TODO
- Add MINOR edge-case tests to test_witnesses.py: opposition silent
  man-vs-king; positive obj:loses_opposition firing; back-rank with kings on
  home rank not firing; obj:exposes_man with capturable mover king not firing.
- Run gate as LAST action, commit.

