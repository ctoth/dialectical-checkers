# dialectical-checkers

An experimental, UCI-free **English-draughts** (8×8 American checkers) engine
that chooses its moves through a formal **argumentation framework** instead of a
single scalar evaluation. Each candidate move is an argument; the engine builds
a graph of reasons for and objections against, resolves it, and plays the move
that survives the debate.

It is the second concrete game in the *dialectical-games* line (after
[dialectical-chess](https://github.com/ctoth/dialectical-chess)) and is
**research code — experimental and a work in progress.**

## Why argumentation instead of an evaluation number

A conventional engine collapses a position into one number and maximises it.
This engine keeps the *reasons* separate and lets them argue. The design is
built on a corpus of formal-argumentation papers (see
[`notes/checkers-papers-findings.md`](notes/checkers-papers-findings.md)) and
deliberately drops two anti-patterns the prior chess engine had: there is **no
`doubt` node** and **no copy-counting** of arguments to fake weights.

Checkers is a better fit for this approach than chess: because captures are
mandatory and jump chains are forced, a capture sequence is an *exact, bounded*
computation. That lets the engine prove certain tactical facts rather than
merely estimating them.

## How a move is chosen

Every legal move is treated as one presumptive argument under Atkinson's AS2
practical-reasoning scheme. Objections are answers to a closed set of *critical
questions*. Each witness (reason or objection) carries a **value** it
promotes/demotes and a **tier**:

- `FACT` — proven by the forced-capture resolver or a terminal condition.
- `HEURISTIC` — positional judgement, not proven.

The engine then evaluates two layers:

1. **Crisp layer** — a Dung argumentation framework over `FACT`-tier defeaters
   only, resolved by the grounded extension. A move survives iff no undefeated
   fact-tier objection refutes it. This layer can *eliminate* a move ("provably
   refuted") but a fact is a fact, so it never does so on a guess.

2. **Graded layer** — over the crisp survivors *only*. As of **v1.5** this is an
   opinion-valued layer: a `doxa.BipolarOpinionGraph` of the surviving moves and
   their `HEURISTIC` witnesses, resolved by `doxa.evaluate` to a per-move Jøsang
   `Opinion`. The graded layer **only ranks** survivors — it can never resurrect
   a move the crisp layer eliminated.

A lexicographic selector key combines the two: minimise unavoidable fact loss,
maximise fact-tier pro-value, then rank by graded opinion strength, with static
evaluation and the PDN string as deterministic tie-breaks.

Full design rationale: [`notes/checkers-design.md`](notes/checkers-design.md).

## Measured strength

The engine has been measured against fixed-depth material-minimax baselines
(48 games per matchup, seed 0 — see
[`notes/strength-report.md`](notes/strength-report.md)). Reported honestly:

| Opponent              | Win rate | Draw rate | Loss rate |
|-----------------------|---------:|----------:|----------:|
| RandomPlayer          |   100.0% |      0.0% |      0.0% |
| MinimaxPlayer depth 1 |    72.9% |     25.0% |      2.1% |
| MinimaxPlayer depth 2 |    22.9% |     70.8% |      6.2% |
| MinimaxPlayer depth 4 |     0.0% |     83.3% |     16.7% |

The engine is **tactically sound but positionally weak**: its fact-tier layer
reliably avoids *forced* material loss, so it rarely collapses, but it has no
lookahead beyond the forced-capture horizon and is out-searched by a 4-ply
minimax. No Elo is claimed — the sample is small and the win rates saturate.

## Install

This is a development checkout, not a published package. It is managed with
[`uv`](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/ctoth/dialectical-checkers.git
cd dialectical-checkers
uv sync
```

> **Note on dependencies.** The engine depends on two sibling research
> libraries: [`formal-argumentation`](https://github.com/ctoth/argumentation)
> (a pinned git dependency, fetched automatically) and `doxa` (currently a
> **local path dependency** — `pyproject.toml` expects a `doxa` checkout at
> `../doxa`). Without that local checkout `uv sync` cannot resolve `doxa`. This
> is a known interim state; see the comment in `pyproject.toml`.

## Usage

### Command line

Two console scripts are installed by `uv sync`:

```sh
# Play a self-play match between two players (random | minimax[:N] | engine)
uv run dchk-match --red engine --white minimax:2 -n 10 --seed 0

# Measure engine strength against the minimax baselines
uv run dchk-eval -n 48 --seed 0 --minimax-depths 1,2,4 --mine-losses
```

Both are fully deterministic under `--seed`: the same seed reproduces the same
games and the same report.

### Library

```python
from dialectical_checkers import DialecticalCheckersEngine, EngineSettings
from dialectical_checkers.board import CheckersBoard

engine = DialecticalCheckersEngine(EngineSettings())
board = CheckersBoard.initial()

decision = engine.choose_move(board)
print(decision.move_pdn)          # the chosen move in PDN notation

analysis = engine.analyze(board)  # full per-position analysis
print(analysis.probes)            # one MoveProbe per legal move
print(analysis.graph)             # the argument graph behind the choice
```

## Project layout

```
dialectical_checkers/
  board.py        CheckersBoard, move generation, mandatory capture, PDN-FEN
  captures.py     forced-capture resolver — the exact tactical spine
  scheme.py       AS2 reasoning scheme: Value, CriticalQuestion, Tier
  witnesses.py    critical-question-derived witness producers
  evidence.py     typed ArgumentEvidence (value + tier)
  arguments.py    crisp Dung layer + graded opinion-valued layer
  selection.py    selector modes + the lexicographic selection key
  search.py       negamax skeleton + checkers static evaluation
  engine.py       orchestration: probe -> graph -> choose
  pdn.py          PDN game I/O + loss-mining diagnostic
  match.py        self-play harness and players
  strength_eval.py / loss_mining.py / graded_tuning.py
  cli/            dchk-match, dchk-eval entry points
notes/            design documents, paper findings, build log
tests/            unit / property / differential tests
```

## Development

```sh
uv run pytest          # 682 tests: unit, property (Hypothesis), differential
uv run pyright         # type checking, basic mode
```

Test markers (`pyproject.toml`): `unit`, `property`, `differential`. The
differential tests compare move generation against `pydraughts` as an oracle —
the oracle is a *test-only* dependency and is never imported by the engine's
decision path.

## Status

Phases 0–7 of the [build plan](notes/checkers-port-plan.md) are complete
(board, capture resolver, witnesses, both argument layers, PDN I/O, self-play
harness, strength evaluation), plus the v1.5 opinion-valued graded layer. This
remains experimental research code; interfaces may change without notice and
there is not yet a license file.
