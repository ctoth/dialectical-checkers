# Phase 7 — strength evaluation (Coder) notes

## 2026-05-20

Worker: gauntlet Coder, Phase 7 (final). Build strength-eval harness, RUN it,
write honest measured strength report. Work on `master`, no branch.

### Repo facts observed
- Actual repo: `C:\Users\Q\code\dialectical-checkers` (NOT dialectical-chess).
- Branch `master`, ahead of origin. uv-managed.
- Existing modules verified present: board, captures, engine, match, pdn,
  selection, witnesses, arguments, scheme, search.
- `match.py` ships: `play_game`, `play_match`, `RandomPlayer` (seeded),
  `MinimaxPlayer(depth)`, `EnginePlayer`, `MatchReport`, `GameResult`.
- `[project.scripts]` already has `dchk-match`. Need to add `dchk-eval`.
- pytest markers: unit, property, differential.
- captures.resolve()/opponent_shot/own_shot exist for loss-mining.
- No `loss_mining.py` in checkers yet — must port from chess
  (chess version uses `chess.pgn` + `has_forced_mate`; checkers analog uses
  captures.resolve / board for turning-point classification).

### Plan
1. `dialectical_checkers/strength_eval.py` — harness module: engine vs
   RandomPlayer + MinimaxPlayer at >=2 depths, both colours equal share,
   seeded/deterministic, tabulate W/D/L.
2. `dialectical_checkers/loss_mining.py` — port loss-mining: analyse engine
   LOST games for turning point (ply where non-losing move became losing),
   classify via captures.resolve / board.
3. `dialectical_checkers/cli/eval_cli.py` + `dchk-eval` script entry.
4. Tests: test_strength_eval.py, test_loss_mining.py (TDD).
5. RUN the eval, write `notes/strength-report.md` with HONEST measured numbers.

### Status
- Baseline: 657 passed in 5.37s.
- Timing: engine vs random ~0.02s/game, vs minimax2 ~0.07s, vs minimax4 ~0.43s.
- CRITICAL determinism finding: EnginePlayer + MinimaxPlayer have NO RNG.
  Two engine-vs-minimax games from the same start are BYTE-IDENTICAL. N
  repeated games of a deterministic matchup give zero signal.
- Fix: opening diversification. 7 opening plies, 49 distinct positions after
  2 plies. Each game starts from a distinct seed-sampled 2-ply opening so
  deterministic matchups produce N distinct games. Seed -> reproducible.
- Engine plays Red in half the games, White in the other half (equal share).
- Design: strength_eval.py builds a deterministic opening pool, plays each
  matchup over the pool with engine on both colours, tabulates W/D/L from the
  ENGINE's perspective.

### Progress (continued)
- strength_eval.py written: opening_pool, evaluate_matchup, run_strength_eval,
  MatchupResult, StrengthReport. 11 tests pass.
- loss_mining.py written: move_allows_shot (wraps captures.opponent_shot),
  mine_turning_point, mine_losses, LossTurningPoint. 5 tests pass.
- Blunder fixture validated at runtime: B:W17:B9, Red 9-14 blunder (17x10
  wins), 9-13 safe. White-seat: W:W17:B9, White 17-14 blunder.
- All 16 new tests green. Baseline 657 still to re-confirm at end.
- dchk-eval CLI written + [project.scripts] entry added. test_eval_cli.py: 4
  tests.
- EVAL RAN (48 games/matchup, seed 0, depths 1/2/4, ~46s):
  vs Random 48W-0D-0L; vs Minimax1 35W-12D-1L; vs Minimax2 11W-34D-3L;
  vs Minimax4 0W-40D-8L.
- REFINEMENT: loss-mining first version flagged FORCED captures as turning
  points (symptom not cause). Added `was_avoidable` field: True iff a
  non-conceding move existed; mine_turning_point now prefers the first
  AVOIDABLE blunder, falls back to first unavoidable conceding ply flagged
  honestly. Unavoidable fixture: B:W11,20:B7 (Red forced 7x16, White 20x11).
- NEXT: run new tests, full 657+ suite, re-run eval with refined diagnostic,
  write notes/strength-report.md, gates, commit.
