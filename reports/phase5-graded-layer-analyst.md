# Phase 5 Graded Categoriser Layer - Analyst Review

## Verdict

No CRITICAL, MAJOR, or MINOR findings.

Workflow actually used: I read `C:\Users\Q\code\dialectical-chess\prompts\phase5-graded-layer-analyst.md`, inspected the Phase 5 implementation, tests, design section 7 and section 9, the removed Phase 4 regression test from git history, ran the required gates, ran the existing quiet-position scanner, and ran independent constructed-position probes against the current engine. I did not modify code or tests.

## Gates

- `uv run pyright`: passed, `0 errors, 0 warnings, 0 informations`.
- `uv run pytest`: passed, `613 passed in 4.73s`.

## Source Review

The graded layer is built where claimed. `dialectical_checkers/arguments.py:195` defines `build_graded_layer`; it filters to `survivor_probes` at `arguments.py:229`, adds surviving `move:` nodes and HEURISTIC `obj:` attackers at `arguments.py:233`, runs `categoriser_scores` at `arguments.py:249`, exposes per-PDN `move_scores` at `arguments.py:254`, and `build_root_argument_graph` stores the result at `arguments.py:368`.

The graded layer is consumed by selection. `dialectical_checkers/selection.py:250` defines `_categoriser_score`, `selection.py:293` defines `_accepted_heuristic_pro_count`, and the full default key calls both at `selection.py:363` and `selection.py:366`. The `categoriser` and `support` modes also call them at `selection.py:463` to `selection.py:481`. Candidate selection is restricted to `graph.survivors` at `selection.py:484`, and `choose_move` routes the modes at `selection.py:555` to `selection.py:564`.

The engine passes the requested mode into the selector at `dialectical_checkers/engine.py:86`. The default `EngineSettings.selector_mode` is `argument` at `engine.py:34`.

The design matches this shape: `notes/checkers-design.md:318` says the graded layer is over crisp survivors only, `notes/checkers-design.md:320` specifies the second Dung AF, `notes/checkers-design.md:328` places heuristic pro-reasons in the selector key, `notes/checkers-design.md:332` to `notes/checkers-design.md:342` gives the ordered selector terms and multi-mode surface, and `notes/checkers-design.md:382` lists `categoriser_scores` as reused library capability.

## Graded Layer Wiring Evidence

Constructed quiet Categoriser case:

- FEN: `W:W18,21,23,24,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,16`
- Legal moves: `18-14`, `18-15`, `21-17`, `23-19`, `24-19`, `24-20`, `26-22`, `29-25`, `30-25`
- Survivors: all legal moves.
- `24-19`: FACT key `(0,0,0,0,0)`, Cat `1.0`, heuristic pros `6`, full key starts with Cat term `-1000000000`.
- `18-14`: FACT key `(0,0,0,0,0)`, Cat `0.5`, heuristic pros `3`, carries `obj:exposes_man`, full key has Cat term `-500000000`.
- `argument` mode chose `24-19`; `optimizer` chose `24-19`; `categoriser` chose `24-19`.
- `grounded` and `score` chose `18-14`; the reconstructed FACT-only choice was `18-14`.

That proves the graded Categoriser term is not dead code: the FACT-only/grounded decision would select `18-14`, but default `argument` selects `24-19` because `_categoriser_score` is in the key.

Constructed quiet support-term case:

- FEN: `W:WK4,5,21,23,25,28,31:B1,10,12`
- Survivors: all legal moves.
- `23-18`: FACT key `(0,0,0,0,0)`, Cat `1.0`, heuristic pros `2`.
- `21-17`: FACT key `(0,0,0,0,0)`, Cat `1.0`, heuristic pros `1`.
- `argument`, `categoriser`, `support`, and `optimizer` chose `23-18`; `grounded`, `score`, and reconstructed FACT-only chose `21-17`.

That proves term 4 is also wired into move selection when the Categoriser score ties.

## FACT Preservation

No resurrection was observed. Constructed eliminated-move case:

- FEN: `W:W18,21,22,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,11,19`
- Legal moves: `18-14`, `18-15`, `21-17`, `22-17`, `26-23`, `27-23`, `27-24`, `28-24`
- Crisp survivors: `18-15`, `21-17`, `22-17`, `26-23`, `27-23`, `27-24`
- Eliminated: `18-14`, `28-24`
- Mode choices: `argument=21-17`, `grounded=18-15`, `categoriser=21-17`, `support=26-23`, `score=18-15`, `optimizer=21-17`

Every mode selected a crisp survivor. The independently classified losing moves in the same position were exactly `18-14` and `28-24`; the engine chose safe move `21-17`.

FACT-decided case:

- FEN: `B:W18,21,22,25,26,27,29,31:B1,2,3,4,5,7,9,10,19,28`
- Unique best FACT-key survivor: `28-32`, key `(0,0,0,-1,0)`.
- All other survivor FACT keys were `(0,0,0,0,0)`.
- `argument` chose `28-32`; `grounded` chose `28-32`.

Free winning shot:

- FEN: `B:W10:B6`
- Legal move: `6x15`
- Engine chose `6x15`.

The committed tests also cover the broad gates: no resurrection and no FACT override in `tests/test_phase5_fact_preservation.py:100`, `:137`, `:183`, and `:219`; legal move / no avoidable forced loss / free winning shot in `tests/test_engine.py:227`, `:248`, `:344`, and `:364`.

## Removed Phase 4 Test

The removal of `tests/test_phase4_regression.py` is legitimate. The old test's controlling premise was "engine play unchanged by the HEURISTIC layer" (`git show a8e0139:tests/test_phase4_regression.py`, line 1; old assertion at line 179). Phase 5 intentionally makes quiet-position play change once graded terms are wired, so preserving that exact assertion would test the opposite of the Phase 5 design.

The valid parts were retained or replaced:

- The 120-position deterministic regression snapshot still exists as a Phase 5 snapshot in `tests/test_phase5_regression.py:47` and is asserted at `tests/test_phase5_regression.py:180`.
- The crisp-layer "FACT witnesses only" structural guard was preserved at `tests/test_phase5_regression.py:198`.
- The new FACT-preservation properties were added in `tests/test_phase5_fact_preservation.py:100`, `:137`, `:183`, and `:219`.
- The quiet graded-improvement tests explicitly compare Phase 5 against reconstructed FACT-only selection at `tests/test_phase5_graded_improvement.py:93`, `:134`, and `:167`.

I did not find evidence that the Phase 4 test was removed to dodge a still-valid failure.

## Categoriser Usage

The soft AF construction matches design section 7. It includes only surviving moves plus HEURISTIC `obj:` nodes, with `obj -> move` defeats. FACT objections remain in the crisp layer, and heuristic pro-reasons are not forced into an attack-only AF. The constructed Categoriser case above also showed the actual graded defeats, including `obj:18-14:obj:exposes_man -> move:18-14`, and the score drop from `1.0` to `0.5`.

`categoriser_scores` is consumed correctly through `graph.ranking["move_scores"]`, not just computed and ignored. The default selector's term 3 changes a real engine decision.

## Selector Modes

The modes are deterministic and internally consistent. Source routing is at `selection.py:555` to `selection.py:564`; committed tests cover deterministic modes, crisp-survivor restriction, default `argument`, `optimizer` aliasing, and non-vacuous divergence at `tests/test_selection.py:399`, `:417`, `:427`, and `:442`.

No mode can resurrect a crisply eliminated move when used with a graph from `build_root_argument_graph`, because all modes rank the same survivor candidate set.

## Term 4 Under-Specification

Uniform weight 1 for accepted HEURISTIC pro-reasons is a defensible v1 reading. Design section 7 requires a "value-weighted accepted-heuristic-pro count" but does not define numeric weights for TEMPO, STRUCTURE, or MOBILITY. The implementation's uniform count preserves the specified ordering boundary: FACT terms first, Categoriser attacks next, heuristic support after that. A different value weighting would be a new design choice, not something required by the current spec.

