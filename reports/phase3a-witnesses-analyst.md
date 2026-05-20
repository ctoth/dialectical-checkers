# Phase 3a witness layer - independent Analyst review

Workflow actually used: read `C:\Users\Q\code\dialectical-chess\prompts\phase3a-witnesses-analyst.md`, reviewed the named Phase 3a implementation/tests/design files in `C:\Users\Q\code\dialectical-checkers`, ran the repository verification commands and targeted existing diagnostic scripts, and did not modify code or tests.

## Summary

I did not find a current production-path bug in `probe_moves()` tier discipline, resolver consistency, terminal-side handling, material magnitudes, crowning, or the `allows_shot` / `loses_exchange` partition. The witness implementation gates resolver-derived FACT labels on `captures.Tier.FACT`, calls `own_shot()` / `opponent_shot()` directly, and the checked concrete positions matched the resolver outputs.

I did find one MAJOR coverage problem around the critical truncation rule, one MINOR parser robustness bug, and one MINOR witness-test coverage gap for king/deep tactical lines.

## Findings

### MAJOR - The witness tier-discipline test does not exercise a truncated resolver result

File and line: `tests/test_witnesses.py:386`

`test_no_truncated_resolver_result_becomes_a_fact_witness()` claims to cover the rule that a truncated / `captures.Tier.HEURISTIC` resolver result must never become a FACT witness, but the test only iterates the normal `CONSISTENCY_FENS` at `tests/test_witnesses.py:299` and reparses whatever labels were emitted. It never creates, injects, or observes a `ShotResult(tier=ResolverTier.HEURISTIC)` at the witness boundary.

Why this matters: this is the highest-risk Phase 3a rule. A future regression that removed the `setup.tier is Tier.FACT` or `shot.tier is Tier.FACT` guards in `dialectical_checkers/witnesses.py:150` and `dialectical_checkers/witnesses.py:158` would still pass this test as long as the sampled positions resolve within the default budget. The resolver does have a real truncation fixture (`tests/test_captures.py:688`, `tests/test_captures.py:700`), but the witness tests do not drive that condition through `probe_moves()`.

Current implementation status: sound by inspection. `witnesses.py` imports the resolver's internal `captures.Tier` at `dialectical_checkers/witnesses.py:71` and emits resolver-derived witnesses only under `Tier.FACT` checks at `dialectical_checkers/witnesses.py:150` and `dialectical_checkers/witnesses.py:158`.

Verification performed: `uv run python scripts/find_truncation_position.py` produced positions whose tiny-budget resolve is `tier=heuristic`; the repository's truncation tests passed. I did not find an exposed `probe_moves()` budget parameter, so current witness truncation coverage would need a direct boundary test or monkeypatched resolver call.

### MINOR - `to_argument_evidence()` accepts signed and zero magnitudes as valid FACT evidence

File and line: `dialectical_checkers/evidence.py:110`

Magnitude parsing uses plain `int(tail)` and returns the parsed value without validating it at `dialectical_checkers/evidence.py:110` through `dialectical_checkers/evidence.py:118`. That means labels such as `pro:material:-100`, `obj:allows_shot:-100`, `reply:material:+100`, or `pro:shot_setup:0` are accepted as typed FACT-tier evidence if presented to the parser.

Why this matters: the design tables describe `{n}` as a material gain/loss magnitude, and the witness producers only emit positive magnitudes. Accepting negative or zero magnitudes weakens the "malformed labels are rejected, never silently mistyped" contract in `dialectical_checkers/evidence.py:90`. There is no current `probe_moves()` production path that emits these malformed labels, so this is not a current move-probe correctness bug.

Coverage note: `tests/test_evidence.py:110` checks empty, unknown, missing-magnitude, and non-numeric labels, but it does not check signed or zero magnitudes.

### MINOR - Witness tests do not cover king-shot or 3+ ply resolver lines

File and line: `tests/test_witnesses.py:299`

The witness consistency sample at `tests/test_witnesses.py:299` through `tests/test_witnesses.py:309` contains no `K` pieces, and the curated witness tests at `tests/test_witnesses.py:122` through `tests/test_witnesses.py:289` also do not assert king-capture witness labels or a 3+ ply forced line through `probe_moves()`.

Why this matters: the resolver has separate diagnostics and tests for king/deep tactics, but the witness layer is where those resolver facts become labels such as `pro:material:150`, `pro:shot_setup:300`, `reply:material:{n}`, or `obj:terminal_loss`. A witness-layer regression in material labeling, reply labeling, or terminal-side handling on king/deep lines would not be caught by the current witness suite.

Evidence: `uv run python scripts/verify_king_deep_shots.py` produced verified king and deep positions, including king double/triple jumps and a 3-ply line (`18x25`, `15x24`, `27x20`). Those positions are not included in `CONSISTENCY_FENS` or curated `probe_moves()` assertions.

## Checks that passed

- `uv run pytest`: 179 passed.
- `uv run pyright`: 0 errors, 0 warnings, 0 informations.
- `uv run pytest tests/test_captures.py::test_budget_truncation_yields_heuristic_tier tests/test_captures.py::test_truncated_result_is_not_a_false_fact tests/test_witnesses.py::test_no_truncated_resolver_result_becomes_a_fact_witness -q`: 11 passed.
- `uv run python scripts/phase3a_verify_test_values.py`: confirmed the asserted `allows_shot`, `loses_exchange`, terminal-loss, reply, and defense magnitudes for the curated witness positions.
- `uv run python scripts/phase3a_verify_positions3.py`: confirmed quiet `allows_shot` positions, safe quiet moves, even trade defense, and a capture with own `pro:shot_setup`.
- `uv run python scripts/verify_king_deep_shots.py`: confirmed resolver-side king/deep tactical positions exist and agree with the oracle, but are not wired into witness tests.

## Reviewed implementation points

- Tier bridge: `dialectical_checkers/witnesses.py:150` and `dialectical_checkers/witnesses.py:158` correctly require resolver `Tier.FACT` before emitting `pro:shot_setup`, objections, replies, or defenses.
- Resolver consistency: `dialectical_checkers/witnesses.py:149` calls `own_shot(board, move)` and `dialectical_checkers/witnesses.py:157` calls `opponent_shot(board, move)`; I found no local reimplementation of shot detection in the witness layer.
- `allows_shot` / `loses_exchange` partition: `dialectical_checkers/witnesses.py:166` through `dialectical_checkers/witnesses.py:178` partitions material-shot objections on `move.is_jump`. Given the Phase 3a under-spec resolution stated in the prompt, this is coherent: quiet concessions become `obj:allows_shot:{n}`, capture moves that come out behind become `obj:loses_exchange:{n}`.
- Terminal-side handling: `dialectical_checkers/witnesses.py:128` checks child terminal wins for the mover; `dialectical_checkers/witnesses.py:159` checks resolver terminal results against the mover before emitting terminal loss.
- Evidence mapping: all current FACT labels map to the expected `Value` and `scheme.Tier.FACT`; malformed signed/zero magnitudes are the parser gap noted above.
