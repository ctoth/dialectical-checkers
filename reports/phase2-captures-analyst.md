# Phase 2 captures.py - independent analyst review

Workflow actually used:
- Read the controlling prompt at `C:\Users\Q\code\dialectical-chess\prompts\phase2-captures-analyst.md`.
- Reviewed `dialectical_checkers/captures.py`, `tests/test_captures.py`, `dialectical_checkers/board.py`, `notes/checkers-design.md` section 3, and `notes/checkers-port-plan.md` section 5.1.
- Ran `uv run pytest tests/test_captures.py`: 26 passed.
- Ran `uv run pyright`: 0 errors.
- Ran `uv run pytest`: 88 passed.
- Ran temporary diagnostic probes outside the repository to check terminal/material branch conflicts and coverage composition.

## Findings

### CRITICAL - Material-only minimax can choose a non-terminal material gain over a forced terminal win

Files and lines:
- `dialectical_checkers/captures.py:197-202`
- `tests/test_captures.py:105-110`

What is wrong:

`_resolve_balance()` chooses among capture alternatives using only weighted material balance. It does not rank terminal game wins above non-terminal material gains. The in-file brute-force reference has the same selection rule, so the 302-position differential can pass while both implementations choose the same wrong branch.

Concrete verified position:

`W:W13,14,21:B1,9`

White has two legal captures:
- `13x6` initiates a forced terminal line: `13x6`, Red forced `1x10x17`, White forced `21x14`. Red is then out of pieces, so White wins the game. The line's net material swing is 0.
- `14x5` captures Red 9 and leaves `B:W5,13,21:B1`, non-terminal, with material swing +100.

Current `resolve()` returns:

`ResolvedLine(material_swing=100, forced=True, truncated=False, terminal=None, tier=Tier.FACT)`

That result hides the terminal-winning line. Under the design, terminal status is a first-class result of the forced-capture resolver, and derived witnesses distinguish material gain from winning the game. A terminal win should not be lost because a different capture has a larger material swing.

Why the suite misses it:

The brute-force oracle in `tests/test_captures.py` makes the same material-only choice with `max(..., key=lambda r: r[0])` / `min(..., key=lambda r: r[0])`. It is therefore not independent for this rule question, including the `terminal` field. The same defect is symmetric at opponent/minimizing nodes: a side can be modeled as choosing a material-preferred branch over a game-winning branch.

### MAJOR - The pydraughts principal-line cross-check is not an independent check of the resolver's selected line

File and lines:
- `tests/test_captures.py:219-230`

What is wrong:

The pydraughts replay helper calls `resolve(node.apply(mv))` while choosing the line to replay, so it depends on the implementation under review. Its `line_value()` also uses only the child's continuation swing and omits the immediate material delta of the candidate capture. When different captures have different immediate material results or terminal outcomes, this helper can replay a line that is not selected by the resolver's actual root-perspective end-balance computation.

Why it matters:

This means the pydraughts tests are useful for checking that replayed moves are legal and that a replayed material total is coherent, but they are not a fully independent oracle for the resolver's minimax choice. In the terminal-conflict position above, the helper's selection logic does not force inspection of the terminal-winning branch.

### MINOR - High-risk king/deep coverage is thin and mostly not in the curated shot suite

Files and lines:
- `tests/test_captures.py:310-339`
- `tests/test_captures.py:397-404`
- `tests/test_captures.py:431-468`

What is untested or under-tested:

The six curated shots are all man-capture positions. They include crowning by a man, but no king captures, no king multi-jump shots, and no 3+ ply forced reply sequences. The explicit pydraughts multi-capture list does contain king positions, and the seeded differential sample does include some kings, but coverage is thin relative to the risk area.

Measured coverage from the current generated sample:
- `differential_positions(target=260)` returns 302 positions.
- 98 positions have captures.
- 8 positions have a king capture available.
- 3 positions have a king multi-jump available.
- 10 positions have capture-only depth of at least 3 plies.
- The curated shot set has 0 king captures, 0 king multi-jump positions, and max capture-only depth 1.

Why it matters:

Phase 1 already identified seeded start-position walks as a weak way to exercise kings. The current suite has some king/deep coverage, but the strongest hand-curated assertions do not cover the king/deep cases most likely to expose resolver-selection and oracle-independence bugs.

## Verified behavior without findings

- Mandatory capture and multi-jump mechanics are delegated to `board.legal_moves()` / `board.apply()`, which match the checked WCDF rules in the reviewed board code: men capture forward only, kings capture one square any diagonal, captured pieces are removed at sequence end, and crowning ends a man's turn.
- The basic root-perspective material sign handling is coherent for ordinary material-only capture lines: root-side nodes maximize root balance and opponent nodes minimize it.
- Crowning material accounting is coherent for the reviewed implementation path: `board.apply()` crowns on the destination king row, and `_net_material()` values the crowned piece as 150 at the resolved end position.
- Budget hits in `_resolve_balance()` set `budget.hit`, and `resolve()` maps that to `truncated=True` and `Tier.HEURISTIC`. I did not find a path that labels a budget-hit line as `Tier.FACT`.
- `opponent_shot()` and `own_shot()` preserve the returned tier/truncation fields; truncated results are not fact-tier. Their correctness still depends on the resolver's branch-selection semantics above.
