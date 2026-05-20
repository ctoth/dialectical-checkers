# Dialectical checkers — measured strength report (Phase 7)

## 2026-05-20

Author: Phase 7 (Coder). This report contains **only numbers actually
measured** by the strength-evaluation harness
(`dialectical_checkers/strength_eval.py`). It states no Elo. The honesty rule of
the Phase 7 prompt governs every claim here: where the data says the engine is
weak, the report says so.

---

## 1. What was measured

The dialectical engine (`DialecticalCheckersEngine`, default `EngineSettings`,
`selector_mode="argument"`) was played against the three verified Phase 6
baselines from `dialectical_checkers/match.py`:

- `RandomPlayer` — picks a uniformly random legal move (seeded).
- `MinimaxPlayer(depth=1)` — fixed-depth material negamax over
  `search.static_evaluation` (man = 100, king = 150).
- `MinimaxPlayer(depth=2)`.
- `MinimaxPlayer(depth=4)`.

Two MinimaxPlayer depths are the Phase 7 minimum; three (1, 2, 4) were run to
show the strength curve.

### Exact conditions

- **Games per matchup:** 48.
- **Seed:** 0. The whole evaluation is a deterministic function of this seed —
  re-running with seed 0 yields byte-identical results. This is verified by
  `scripts/phase7_verify_reproducible.py`, which runs the full reported
  evaluation (48 games per matchup, MinimaxPlayer depths 1/2/4, loss mining
  included) twice and confirms the two formatted reports are byte-identical.
- **Colour split:** the engine plays Red in 24 games and White in 24 games of
  every matchup — an exact, equal split.
- **Opening diversification:** `EnginePlayer` and `MinimaxPlayer` are *fully
  deterministic* (neither holds an RNG). Two engine-vs-minimax games from the
  same start position are byte-identical, so replaying one matchup N times from
  the standard start would give N copies of one game and **zero** statistical
  signal. The harness therefore starts each game from a distinct opening drawn
  deterministically (seed-derived) from the pool of positions reached 2 plies
  into the game. There are exactly 49 distinct such positions; 48 (the largest
  even number that fits) is the per-matchup game count. This is the cause of the
  48-game cap and is reported here as a **sample-size limitation** (see §6).
- **Per-matchup wall time** (one machine, measured):
  vs Random 1.0 s; vs Minimax(1) 1.8 s; vs Minimax(2) 4.2 s;
  vs Minimax(4) 47.0 s. Total ~54 s.
- **Runner:** `dialectical_checkers/strength_eval.py`, CLI `dchk-eval`.

---

## 2. Measured win/draw/loss — from the engine's point of view

| Opponent              | Games | W  | D  | L | Win rate | Draw rate | Loss rate | Match score |
|-----------------------|------:|---:|---:|--:|---------:|----------:|----------:|------------:|
| RandomPlayer          |    48 | 48 |  0 | 0 |   100.0% |      0.0% |      0.0% |      100.0% |
| MinimaxPlayer(depth=1)|    48 | 35 | 12 | 1 |    72.9% |     25.0% |      2.1% |       85.4% |
| MinimaxPlayer(depth=2)|    48 | 11 | 34 | 3 |    22.9% |     70.8% |      6.2% |       58.3% |
| MinimaxPlayer(depth=4)|    48 |  0 | 40 | 8 |     0.0% |     83.3% |     16.7% |       41.7% |

`Match score` = (wins + 0.5 x draws) / games. W + D + L = 48 in every row
(checked by `test_strength_eval.py`).

### Game-end reasons (measured)

- vs Random: all 48 ended `terminal` (a side with no legal move).
- vs Minimax(1): 36 `terminal`, 12 `threefold-repetition`.
- vs Minimax(2): 14 `terminal`, 34 `threefold-repetition`.
- vs Minimax(4): 8 `terminal`, 40 `threefold-repetition`. The 8 terminals are
  exactly the 8 engine losses; every other game was a repetition draw. Mean
  game length vs Minimax(4): 77.4 plies (min 41, max 103).

No Elo figure is given. Win rates of 0% and 100% saturate against the formula
`Elo = -400 log10(1/score - 1)` (it diverges), and a 48-game sample is too
small to pin a rating with a meaningful confidence interval. The plain
W/D/L counts above are the honest measurement.

---

## 3. Honest characterisation of the engine's measured strength

The dialectical checkers engine is **tactically sound but positionally weak,
and it does not out-search a shallow brute-force minimax.** The data shows a
clean monotone decline as the baseline gets stronger: it crushes a random
mover (100%), beats a 1-ply minimax clearly (72.9% wins, one loss), is already
only break-even-plus against a 2-ply minimax (22.9% wins, mostly draws), and
**never wins a single game** against a 4-ply minimax — it draws 40 of 48 and
loses the other 8. Against the strongest baseline its match score is *below*
50% (41.7%), i.e. depth-4 minimax is the stronger player by this measurement.

This is consistent with the engine's design: its FACT-tier argument layer
proves and avoids *forced* tactical losses well (it almost never hangs material
to a shot — see §4), which is why it does not collapse and instead draws most
games against deeper opponents. But it has no lookahead beyond the
forced-capture resolver, so a 4-ply minimax simply calculates further in quiet
positions and steers the engine into repetition or, occasionally, into a
position from which a forced loss becomes unavoidable. The engine is, in short,
about as strong as a 2-ply material search and clearly weaker than a 4-ply one.
That is a modest measured strength, and it is reported as such — no flattery.

---

## 4. Loss-mining findings

The loss-mining diagnostic (`dialectical_checkers/loss_mining.py`) analysed
every game the engine lost (1 + 3 + 8 = 12 losses) for its turning point — the
ply at which a non-losing move became a losing one, classified with the
verified `captures.opponent_shot` / `captures.resolve` forced-capture resolver.

**Measured result: all 12 losses had a resolvable conceding ply, and in all 12
that ply was classified `was_avoidable = False`.** That is, at the ply the
resolver flags, *every* legal move conceded a forced loss — the flagged move
was itself a mandatory capture with no safe alternative. Examples:

- vs Minimax(1), game 14, ply 3: `11x18` — a forced capture, loses 100
  material.
- vs Minimax(2), game 15, ply 17: `14-17` loses 200 material; game 24, ply 23:
  `2x9` loses 100; game 46, ply 20: `24-20` loses 100.
- vs Minimax(4): four of the eight losses are flagged at ply 12 — three of
  them (games 30, 32, 40) with the identical forced capture `22x15` losing 250
  material, and the fourth (game 27) with the forced capture `18x11` losing 100
  material; game 12 is flagged at ply 1 — the engine's very first move from a
  normal 12-vs-12 opening was a forced capture that began a lost line.

**Honest interpretation.** The loss-mining diagnostic catches the moment a loss
becomes a *proven hard fact* (a forced capture sequence the resolver can see
end-to-end). It found that, in every lost game, that moment is a forced move —
which means the **real decision error happened earlier**, on a quiet
positional move that the capture resolver, by construction, cannot evaluate.
The engine did not blunder material into a shot it could have declined; it was
*manoeuvred* into positions where a losing capture was forced. This is itself a
measured finding and it agrees with §3: the engine's weakness is positional
(quiet-move judgement and lack of lookahead), not tactical (forced-sequence
calculation). The diagnostic reports `was_avoidable = False` truthfully rather
than blaming a move the engine had no choice about.

---

## 5. Confirmation: no Phase 0-6 behaviour changed

Phase 7 added only evaluation tooling:

- `dialectical_checkers/strength_eval.py` (new)
- `dialectical_checkers/loss_mining.py` (new)
- `dialectical_checkers/cli/eval_cli.py` (new) + the `dchk-eval`
  `[project.scripts]` entry
- `tests/test_strength_eval.py`, `tests/test_loss_mining.py`,
  `tests/test_eval_cli.py` (new)

No verified Phase 0-6 module (`board.py`, `captures.py`, `engine.py`,
`witnesses.py`, `arguments.py`, `scheme.py`, `selection.py`, `search.py`,
`pdn.py`, `match.py`) was modified. The engine's move selection is unchanged.
All 657 prior tests still pass alongside the 21 new ones — the Phase 7 gate
measured 678 passing tests and `pyright` reporting 0 errors.

---

## 6. Limitations of this evaluation (stated honestly)

1. **Sample size.** 48 games per matchup. This is bounded by the 49 distinct
   2-ply opening positions available for diversification; with deterministic
   players a larger sample needs deeper opening diversification, which was not
   done in this phase. 48 games gives a clear *direction* (the monotone curve
   in §2 is unambiguous) but the exact percentages carry real sampling
   uncertainty — e.g. the single loss vs Minimax(1) is 1/48 = 2.1% and should
   not be over-read.
2. **No external engine.** The Phase 7 plan permitted "if available, an
   external checkers engine". None was wired in; the baselines are the Phase 6
   `RandomPlayer` and `MinimaxPlayer` only. The strength claim is therefore
   *relative to a fixed-depth material minimax*, not to any rated human or
   established engine.
3. **No Elo.** Deliberately. See §2 — the win rates saturate and the sample is
   too small for a meaningful rating interval. Reporting an Elo here would
   violate the Phase 7 honesty rule.
4. **Opening set, not full games from the start.** Games start 2 plies in, from
   a seed-sampled subset of openings. The standard starting position itself is
   one node above this pool; results are over the diversified pool, not the
   single canonical opening.
5. **Loss-mining horizon.** The diagnostic sees only forced-capture sequences
   (`captures.resolve`'s domain). It correctly reports that it cannot localise
   the quiet positional move that *caused* each loss — it is honest about that
   blind spot rather than guessing a turning point.

---

## 7. Reproducing this evaluation

```
uv run dchk-eval -n 48 --seed 0 --minimax-depths 1,2,4 --mine-losses
```

Same seed => same results (verified). The numbers in §2 and §4 are the exact
output of that command.
