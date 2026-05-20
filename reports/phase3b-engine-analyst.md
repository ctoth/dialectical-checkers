# Phase 3b crisp layer + engine analyst review

Workflow actually used: I read the controlling prompt, reviewed the Phase 3b implementation/tests/notes, ran the claimed gates, constructed and played additional positions against `DialecticalCheckersEngine.choose_move`, and did not modify code or tests.

## Findings

### MAJOR - Selector penalizes defeated FACT replies outside the empty-survivor fallback

File/line: `dialectical_checkers/selection.py:67`, `dialectical_checkers/selection.py:81`, `dialectical_checkers/selection.py:174`, `dialectical_checkers/selection.py:186`

What is wrong: `_worst_fact_objection_magnitude()` counts every FACT `reply_attack` on the probe, even when that reply is defeated by a FACT `defense:` and the move is a grounded crisp survivor. Design §7 says this key term is `0 if clean` and non-zero only in the §6 empty-survivor fallback (`notes/checkers-design.md:334`). A defended survivor is not carrying an unavoidable objection, but the selector still gives it a non-zero first key component.

Why it matters: this inverts the selector before FACT pro-value is considered. Concrete engine position I played:

`B:W10,17,18:B6,13,14`

Legal moves: `6x15x22`, `13x22`, `14x21`, `14x23`.

The crisp layer grounds `6x15x22` and `14x23`; both have `defense:holds_exchange`. The selector keys were:

- `6x15x22`: `(100, 0, -200, 0, -100, -200, '6x15x22')`, reasons `('pro:material:200', 'pro:shot_setup:100')`, reply `('reply:material:100',)`, defense `('defense:holds_exchange',)`.
- `14x23`: `(50, 0, 0, 0, -100, -100, '14x23')`, reasons `('pro:material:100', 'pro:shot_setup:50')`, reply `('reply:material:50',)`, defense `('defense:holds_exchange',)`.

The engine chose `14x23`. Under the specified key, the first term should be `0` for both grounded defended survivors, and then `6x15x22` should win by larger FACT material and static eval. This is an actual bad move caused by the selector, not only a test gap.

### MAJOR - A defense defeats every same-move attacker instead of the objection/reply it answers

File/line: `dialectical_checkers/arguments.py:178`, `dialectical_checkers/arguments.py:183`

What is wrong: `build_root_argument_graph()` builds one `defense:{pdn}:{label}` argument and adds `defense -> attacked` for every FACT objection and reply in `attacker_ids`. Design §6 says a defense defeats the objection/reply `x` it answers (`notes/checkers-design.md:291`). The current implementation has no target identity and over-defeats.

Why it matters: a single defense can incorrectly restore a move with multiple independent FACT attacks. I confirmed with a hand-built probe carrying two replies and one defense: the graph produced both `defense -> reply:material:100` and `defense -> reply:material:200`, grounded the move, and returned it as a survivor. The same happens with one objection plus one reply. That violates the required "AND ONLY that one" edge shape and will become unsound as soon as the witness layer can emit multiple independent FACT attacks where only one is answered.

### MAJOR - The NO-AVOIDABLE-FORCED-LOSS property classifier is independent, but not a correct loss oracle

File/line: `tests/test_engine.py:93`, `tests/test_engine.py:105`, `tests/test_engine.py:109`

What is wrong: `_gives_opponent_forced_win()` calls `opponent_shot()` and treats any FACT opponent material gain as a losing move. For capture moves, that ignores the mover's immediate capture gain and the witness-layer defense rule at `dialectical_checkers/witnesses.py:171` through `dialectical_checkers/witnesses.py:175`, where an apparent opponent recapture is defended when the whole exchange is even or favorable.

Why it matters: the property is not using the engine selector, so it is not hollow in the narrow "same choose path" sense. But it is still not a valid oracle for "this move gives the opponent a forced win/loss." On `B:W10,17,18:B6,13,14`, the classifier marks defended favorable captures such as `6x15x22` and `14x23` as losing merely because the opponent has some forced material reply. That can hide the selector bug above or create misleading failures/passes; it does not prove the engine avoids net forced losses.

### MINOR - Selector behavior has no direct tests for the Phase 3b key contract

File/line: `tests/test_engine.py:293`, `tests/test_arguments.py:93`

What is wrong or untested: the test suite checks curated engine outcomes and one defended-reply graph case, but I found no direct tests for `_selection_key()` / `selection.choose_move()` proving:

- the first key term is non-zero only in the empty-survivor fallback;
- defeated replies on grounded survivors do not count as unavoidable losses;
- clean FACT pro ordering is `winning > large material > crown > small material`.

Why it matters: a direct synthetic selector check catches the current inversion immediately. Clean ordering itself works in a synthetic check, but defended-reply ordering does not.

## Sound checks verified

- `uv run pytest --timeout=120`: 250 passed.
- `uv run pyright`: 0 errors, 0 warnings, 0 informations.
- No `doubt:` node or copy arguments found in `build_root_argument_graph`; argument ids embed PDN and graph arguments are stored as a `frozenset`.
- Empty probes produce an empty graph; engine terminal position returns a null decision through the existing test and code path.
- Determinism is covered by `tests/test_engine.py:165` and the selector has a total PDN tiebreak.

## Positions I played

- Free terminal winning move: `B:W5:B1,12,19,23,28,K29,K32`. Engine chose `12-16`; this was one of several `pro:terminal_win` legal moves.
- Exactly one safe move: `W:W11,17,21,22,25:B1,4,5,6,10,13,K27,28`. Legal moves were `11-7`, `11-8`, `17-14`, `22-18`; only `11-7` was safe, and the engine chose `11-7`.
- Multi-move empty-survivor fallback: `B:WK4,5,21,22,24,25,27,28,30,31:B1,3,6,7,12,18`. Every legal move had an undefeated `obj:allows_shot`; no move argument was grounded, survivors fell back to all moves, and the engine chose one of the least-magnitude losses (`12-16`, tied at 100).
- Selector inversion / bad engine play: `B:W10,17,18:B6,13,14`. Engine chose `14x23` over the better defended `6x15x22` because defeated reply magnitude was incorrectly used as the first selector key term.

I did not produce a literal "immediate material capture vs quiet move" position because English draughts mandatory capture makes that legal-move mix impossible: `CheckersBoard.legal_moves()` returns only jumps whenever any jump exists (`dialectical_checkers/board.py:205` through `dialectical_checkers/board.py:212`), matching WCDF rule notes in `notes/checkers-port-plan.md:149`.
