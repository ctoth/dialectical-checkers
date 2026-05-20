# Dialectical Checkers — detailed design (v1)

## 2026-05-20

Concrete, implementable design for `dialectical-checkers` (English draughts).
Companion to `checkers-port-plan.md` (strategy/phasing) and
`checkers-papers-findings.md` (the corpus triage this design is built on).
Where this doc and `checkers-port-plan.md §5.4` disagree on the witness
vocabulary, **this doc wins** — §5.4 predates the paper triage.

Rules are the verified WCDF set in `checkers-port-plan.md §5.1`.

---

## 0. What changed because of the papers

The port plan assumed a near-verbatim copy of dialectical-chess's argument
graph. The corpus triage changed three things, and they are load-bearing:

1. **No "doubt" node, no copy-counting.** dialectical-chess fakes support as
   "reason defeats a doubt that defeats the move", and weights arguments by
   duplicating them. The corpus calls both anti-patterns (`Brewka_2010`,
   `Prakken_2019`, `Bonzon_2016`). Gone. See §6, §7.
2. **Two explicit layers** (`Dung_1995` + `Besnard_2001` Categoriser): a crisp
   Dung-grounded layer for *provable* (fact-tier) defeaters, and a graded
   Categoriser layer that only *ranks the survivors*. The graded layer can
   never resurrect a crisply-eliminated move.
3. **The witness vocabulary is derived from an argument scheme, not invented
   per producer.** The engine is structured as Atkinson's AS2 practical-
   reasoning scheme over a game-AATS (`Atkinson_2007`); objections are answers
   to a closed set of critical questions; every witness carries a *value* it
   promotes/demotes and a *tier* (`Bench-Capon_2003` fact-as-highest-value).
   See §4, §5.

Build against: `Dung_1995`, `Besnard_2001`, `Bonzon_2016`, `Baroni_2019`,
`Atkinson_2007`, `Bench-Capon_2003`, `Brewka_2010`. Library (`formal-
argumentation`) already provides `grounded_extension` and `categoriser_scores`
— the two evaluators v1 needs. Nothing else from the corpus is required for v1.

---

## 1. Module layout

New sibling repo `dialectical-checkers`; uv-managed; depends on the same
`formal-argumentation` pinned SHA. Package `dialectical_checkers/`:

| Module | Responsibility | Ported from |
|---|---|---|
| `board.py` | `CheckersBoard`, `CheckersMove`, move-gen, PDN-FEN, perft | board.py (rewrite) |
| `captures.py` | Forced-capture resolver — the exact tactical spine | new (§3) |
| `scheme.py` | AS2 scheme: `Value` enum, `CriticalQuestion` enum, `Tier` | new (§4) |
| `witnesses.py` | CQ-derived witness producers → `MoveProbe` | probe.py (rewrite) |
| `evidence.py` | witness label → typed `ArgumentEvidence` | evidence.py (reshape) |
| `arguments.py` | crisp Dung layer + graded Categoriser layer | arguments.py (rewrite) |
| `selection.py` | selector modes + selection keys | arguments.py choose_move |
| `search.py` | negamax skeleton + checkers static eval | search.py (copy skeleton) |
| `engine.py` | orchestration: probe → graph → choose | engine.py (copy, rename) |
| `pdn.py` | PDN game I/O, loss-mining diagnostic | adapters.py + loss_mining.py |
| `match.py`, CLIs | self-play harness, benchmark runner | bench.py / matches.py |

`engine.py` and the `search.py` recursion skeleton are copied near-verbatim
(generic). Everything else is rewritten. No z3, no UCI (per port plan §6).
Keep `notes/ported-from-chess.md` recording exactly which files were copied
and from which dialectical-chess revision — the diff target for the eventual
core extraction.

---

## 2. Board representation (`board.py`)

### 2.1 Squares

32 playable (dark) squares, PDN numbering 1-32. Internal index `0..31`
(PDN square = index + 1). A **precomputed neighbour table** replaces
dialectical-chess's file/rank arithmetic:

```
STEP[idx][dir]  -> neighbour index or None     # dir in NE,NW,SE,SW
JUMP[idx][dir]  -> (over_idx, land_idx) or None # the square jumped + landing
```

Both tables are static, computed once from the 8x8 dark-square geometry. This
sidesteps every dark-square parity bug — move-gen never does coordinate math,
it walks tables. (dialectical-chess's `square_from_file_rank` parity logic is
the thing being designed out.)

### 2.2 State — immutable frozen dataclass (mirrors `OwnedBoard`)

```
CheckersBoard:
    cells: tuple[Cell | None, ...]   # length 32; Cell = (color, is_king)
    turn: str                        # "r" | "w"  (Red moves first)
    no_progress: int                 # plies since last man-move or capture
    history: tuple[int, ...]         # position hashes, for threefold repetition
```

`color` is `"r"`/`"w"`; `is_king` bool. Red's king-row is the high-numbered
rank, White's the low — fixed from the WCDF start (Red 1-12, White 21-32).

### 2.3 Move type

```
CheckersMove:
    path: tuple[int, ...]       # squares visited; len 2 simple, len >=2 jump chain
    captured: tuple[int, ...]   # captured square indices; () for a simple move
```

`is_jump = bool(captured)`. PDN render: simple `a-b`, jump `aXbX...`.
Equality/ordering by `(path, captured)` for deterministic move ordering.

### 2.4 Move generation — the rules that bite

`legal_moves()` algorithm:

1. Generate all **jump** sequences for the side to move (§2.5). If any exist,
   that set IS the legal move set — **mandatory capture** (WCDF 1.20).
2. Otherwise generate **simple moves**: men one step diagonally forward;
   kings one step any diagonal. (Men forward-only — WCDF 1.15/1.25.4.)

No self-check filter is needed — checkers has no check. This is *simpler* than
dialectical-chess's pseudo-legal-then-filter pipeline.

### 2.5 Multi-jump expansion — the subtle part

Depth-first from each piece. Carry a running `captured` set. At each step,
for each capture direction valid for the piece (men: forward only; kings:
all four):

- `JUMP[cur][dir]` must exist; `over_idx` holds an enemy piece; that enemy
  must not already be in `captured` (a piece is jumped at most once — WCDF
  1.20); `land_idx` must be empty **and not the square of an already-captured
  piece** (captured pieces are removed only at sequence end — WCDF 1.19, so
  their squares stay occupied during expansion).
- **Crowning ends the turn** (WCDF 1.16/1.19/1.25.7): if a *man* lands on its
  king-row, the sequence terminates here even if further jumps exist. Kings
  continue normally.
- If no continuation exists, emit the `CheckersMove`.

`apply(move)`: move the piece along `path`, remove `captured` at the end,
crown if a man finished on its king-row, flip `turn`, update `no_progress`
(reset to 0 on any man move or any capture, else +1), append the position
hash to `history`.

### 2.6 Terminal & draw

- `is_loss_for(side)`: `side` to move has no legal move → `side` **loses**
  (WCDF 1.30). There is no stalemate draw — this is the single biggest
  terminal-handling difference from chess.
- `is_draw()`: threefold repetition via `history`; or `no_progress` reaching
  the WCDF 1.32.2 threshold (40 moves each side with no man-advance and no
  capture → 80 plies on the counter).

### 2.7 PDN-FEN I/O + perft

Parse/serialize the PDN FEN tag `"[turn]:W...:B..."` (kings prefixed `K`).
`perft(depth)` + `compare_to_oracle(fen)` against **pydraughts** (test-only;
verify pydraughts exposes the English variant — if not, fall back to
hand-built fixtures from an authoritative engine). Mirrors board.py's
`oracle_perft`/`compare_to_oracle` — the oracle is a *test* dependency only,
never imported by the engine decision path (the non-oracle-strength stance).

---

## 3. Forced-capture resolver (`captures.py`)

The tactical spine. Because captures are mandatory and jump chains are forced,
a capture sequence is an **exact, bounded** computation — checkers' analog of
quiescence search, but *complete within a chain*, not heuristic.

Core function `resolve(board) -> ResolvedLine`:
- If the side to move has captures, every line is forced-ish (a small set);
  recurse through the mandatory captures of both sides until a position with
  no capture is reached ("quiet").
- Returns: the net material swing (man/king weighted), whether the line is
  *forced* (the losing side had no non-capturing alternative at each of its
  turns), and the terminal status if the line ends the game.

Two derived queries the witness layer consumes:

- `opponent_shot(board, move) -> ShotResult | None`: apply `move`, resolve;
  if the opponent has a forced sequence netting material or the game, return
  it. This is the **provable `obj:allows_shot`** — the hard, fact-tier
  defeater that the heuristic chess objections could never be.
- `own_shot(board, move) -> ShotResult | None`: does `move` *initiate* a
  forced winning sequence? The `pro:shot_setup` reason.

Budget: bound recursion depth and node count (mirror `ReplyAnalysisCache`),
mark a line `truncated` if the budget is hit — a truncated line yields a
heuristic-tier witness, not a fact-tier one (honesty about what was proven).

This replaces dialectical-chess's `reply_mate_*`, `has_forced_mate`, and the
vestigial z3 fork witnesses with one exact mechanism.

---

## 4. The reasoning scheme (`scheme.py`)

The engine is structured as **Atkinson's AS2 practical-reasoning scheme over a
game-AATS** (`Atkinson_2007`). This is not relabelling — it makes the witness
vocabulary a *closed taxonomy* instead of an open-ended pile of strings.

- **AATS:** states = checkers positions; actions = legal moves; the transition
  function τ is `apply` refined by the forced-capture resolver; the value
  valuation δ tags each move with which values it promotes/demotes.
- **AS1 argument for a move:** "in position R, play move A, reaching S, which
  promotes value V." Every candidate move is one presumptive AS1 argument.
- **Critical questions** generate the objections. A move's AS1 argument stands
  until a CQ is answered against it.

```
Value     = winning | material | king_count | tempo | mobility | structure
Tier      = FACT       # proven by the forced-capture resolver / terminal
          | HEURISTIC  # positional judgement, not proven
CriticalQuestion =
    CQ2_3   # does the move actually have the claimed effect / reach the goal
    CQ8_9   # the move has a side effect demoting some value
    CQ17    # the opponent's reply (its part of the joint action)
    CQ5_6_11  # an alternative move is as good or better  -- COMPARATIVE
```

`CQ5_6_11` is deliberately **not** a per-move witness — "a better move exists"
is a comparison, and comparison is the job of the ranking layer (§7), not a
node in any one move's graph. The findings (`checkers-papers-findings.md` D)
make this explicit. So `witnesses.py` only ever emits CQ2_3 / CQ8_9 / CQ17
objections plus AS1 pro-reasons.

`Bench-Capon_2003`'s **fact-as-highest-value**: a `FACT`-tier witness outranks
every `HEURISTIC` one regardless of which value it carries. That is the bridge
between the two evaluation layers (§7) — it is implemented as the `Tier`
field, not as a separate mechanism.

---

## 5. Witness taxonomy (`witnesses.py`)

`probe_moves(board)` → one `MoveProbe` per legal move. `MoveProbe` keeps the
dialectical-chess shape (`uci`→`pdn`, `reasons`, `objections`, `reply_attacks`)
but **every label is typed by `evidence.py` with a `Value` and a `Tier`** —
no more guessing from string prefixes.

AS1 pro-reasons:

| Label | AS1 role / value | Tier | Source |
|---|---|---|---|
| `pro:terminal_win` | realises `winning` | FACT | move ends game |
| `pro:material:{n}` | promotes `material` | FACT | resolver: net `n` this move |
| `pro:crown` | promotes `king_count` | FACT | a man reaches king-row |
| `pro:shot_setup:{n}` | promotes `material` | FACT | `own_shot` proves forced gain |
| `pro:opposition` | promotes `tempo` | HEURISTIC | parity/opposition calc |
| `pro:back_rank_hold` | promotes `structure` | HEURISTIC | keeps king-row men |
| `pro:center:{n}` | promotes `structure` | HEURISTIC | central-square occupation |
| `pro:mobility:{n}` | promotes `mobility` | HEURISTIC | legal-move-count gain |
| `pro:formation:{kind}` | promotes `structure` | HEURISTIC | bridge / phalanx / echelon |

CQ-derived objections:

| Label | CQ / value demoted | Tier | Source |
|---|---|---|---|
| `obj:terminal_loss` | CQ8_9 — `winning` | FACT | move leaves self with no reply |
| `obj:allows_shot:{n}` | CQ8_9 — `material` | FACT | `opponent_shot` proven forced |
| `obj:loses_exchange:{n}` | CQ8_9 — `material` | FACT | resolver: forced net loss `n` |
| `obj:loses_opposition` | CQ8_9 — `tempo` | HEURISTIC | parity calc |
| `obj:back_rank_break` | CQ8_9 — `structure` | HEURISTIC | premature king-row man move |
| `obj:single_corner_drift` | CQ8_9 — `structure` | HEURISTIC | driven toward single corner |
| `obj:exposes_man` | CQ8_9 — `material` | HEURISTIC | man capturable, compensation unproven |
| `reply:{...}` | CQ17 — varies | FACT if the reply is a proven forced win/gain, else HEURISTIC | resolver applied to opponent |
| `defense:{...}` | answers a CQ8_9/CQ17 | FACT | resolver proves the objection's line is itself refuted |

Note `obj:exposes_man` vs `obj:allows_shot`: if the resolver *proves* the man
is lost in a forced line it is `allows_shot` (FACT); if it only *looks* loose,
it is `exposes_man` (HEURISTIC). The tier is determined by what the resolver
actually proved — never asserted.

Start v1 with the FACT rows only plus `pro:terminal_win`/`pro:material`/
`pro:crown` (port plan phase 3). Add HEURISTIC rows in phase 5. dialectical-
chess started material-only and grew; so does this.

---

## 6. Crisp layer — Dung AF of fact-tier defeaters (`arguments.py`)

A plain Dung `ArgumentationFramework`. **No `doubt` node. No copies.**

Arguments and defeats:

- `move:{pdn}` for every legal move.
- For every **FACT-tier** objection `o` on a move: argument `obj:{...}`,
  defeat `obj → move`.
- For every **FACT-tier** reply attack `r`: argument `reply:{...}`,
  defeat `reply → move`.
- For every proven `defense:d` answering objection/reply `x`: argument
  `defense:{...}`, defeat `defense → x`.
- HEURISTIC witnesses do **not** enter this layer.

`grounded_extension` (already in `formal-argumentation`) → a `move:` argument
is accepted iff no undefeated fact-tier objection/reply attacks it. That is
exactly "this move is not provably refuted" — and it is what the `doubt` node
was clumsily trying to approximate. With soft reasoning moved to its own layer
(§7), the `doubt` node has no remaining job (`checkers-papers-findings.md` B).

Why this is sound and was not, in chess: chess objections are heuristic, so a
crisp grounded layer over them would eliminate moves on guesses. Checkers
fact-tier objections are *proven by the resolver* — eliminating on them is
correct.

**Empty-survivor fallback.** If every move carries an undefeated fact-tier
objection (e.g. every move loses material), the grounded extension contains no
`move:` node. Then the crisp layer returns *all* moves, and the selector (§7)
must rank by *magnitude* of the unavoidable fact loss — a forced loss is still
chosen least-bad. So fact objections feed the selector even when they cannot
eliminate. (Analogous to dialectical-chess `grounded_candidates` falling back
to all probes.)

---

## 7. Graded layer + selection (`arguments.py`, `selection.py`)

Over the crisp survivors only. Ranks; never resurrects.

**v1 — uses only library features.** Build a second plain Dung AF: nodes =
surviving `move:` + HEURISTIC `obj:` nodes; edges = heuristic `obj → move`.
Run `categoriser_scores`. `Cat(move:A) = 1/(1 + Σ Cat(attackers))` is high
when a move has few/weak heuristic objections. `Bonzon_2016` proves the
Categoriser satisfies Cardinality Precedence — N independent objections lower
the score monotonically, *with no copy-counting*. This is the principled
replacement for `severe_objection_weight` + copy multiplication.

Heuristic **pro-reasons** cannot enter a Dung AF (it has only attacks). For
v1 they are a selector-key term: a value-weighted count of accepted heuristic
pro-reasons. Honest about the limitation — see v1.5.

**Selector key** per surviving move, lexicographic:

1. minimise the worst unavoidable FACT-objection magnitude (0 if clean —
   non-zero only in the §6 fallback).
2. maximise FACT-tier pro value, as a value-priority tuple:
   `winning > large material > crown > small material`.
3. maximise `Cat(move:A)` — fewest/weakest heuristic objections.
4. maximise value-weighted accepted-heuristic-pro count (the v1 support proxy).
5. tie-break: static eval (§8), then PDN string for determinism.

Keep the dialectical-chess multi-mode `choose_move` surface (`grounded`,
`categoriser`, `score`, …) for differential testing, with the lexicographic
key above as the default (`argument`) mode.

**v1.5 — deferred, named.** Replace key terms 3-4 with a single QBAF strength
that models heuristic pro-reasons as first-class **support** (`Baroni_2019`
QBAF; evaluate with DF-QuAD `Rago_2016` or Potyka's quadratic-energy model
`Potyka_2018`). The Categoriser (AF, attacks only) cannot represent support;
a QBAF can. This needs a ~50-line evaluator that is *not* in the library.
Build it only when phase-5 measurements show heuristic pro-support actually
moves playing strength — observe first, do not theorise the upgrade.

**Rejected, on record:** `Dunne_2011` weighted-attack *budget* semantics — a
budget would let the engine spend its way past a *proven* refutation. The
crisp layer stays at budget β = 0.

---

## 8. Search & static evaluation (`search.py`)

- Copy the negamax/alphabeta recursion skeleton from dialectical-chess
  `search.py` verbatim (generic). **One required change:** the terminal
  branch — chess returns `0` for stalemate; checkers has no stalemate, so
  "no legal moves" is always a loss for the side to move (§2.6). The
  `terminal_or_leaf_result` analog returns a loss score, never 0, for the
  no-moves case.
- `static_evaluation`: material first — man = 100, king = 150 (kings ≈ 1.5
  men; tune later). Add positional terms (back-rank men, advancement, trapped
  kings, runaway men) only after the material baseline plays correctly.
- Move ordering is near-trivial: captures are mandatory, so when they exist
  the move set is already the captures; order multi-jumps by net material.

Search is a *witness source* (it produces `pro:`/`obj:` search labels for
moves beyond the exact forced horizon), exactly as in dialectical-chess — not
the decision maker. The decision is the argument layers.

---

## 9. Library capability map

Reused from `formal-argumentation` as-is:
- `grounded_extension` — crisp layer (§6). `Dung_1995`.
- `categoriser_scores` — graded layer (§7). `Besnard_2001`/`Bonzon_2016`.

Built in `dialectical-checkers`:
- Everything in §1's table except the engine shell and search skeleton.

Built only when measurements justify it (deferred, named):
- QBAF + DF-QuAD/Potyka base-score evaluator — v1.5 support modelling (§7).
- ADF engine with weighted acceptance conditions (`Brewka_2010`) — the
  long-term target that unifies both layers into one framework; adopt the
  *modelling idea* (a per-move acceptance condition) now, the *engine* later.
- `Prakken_2019` accrual-set machinery — only if cumulative-vs-convergent
  pro-reason double-counting becomes a measured problem.
- Endgame databases — only on explicit opt-in; isolated witness producer,
  never the decision path (non-oracle stance).

---

## 10. Mapping to the port-plan phases

This design slots into `checkers-port-plan.md §8`:

- Phase 1 → §2 (`board.py`).
- Phase 2 → §3 (`captures.py`).
- Phase 3 → §5 FACT rows + §6 (crisp layer). Gate: never plays illegal, never
  walks into a proven loss, always takes a free winning shot.
- Phase 4 → §7 (graded layer + selection).
- Phase 5 → §5 HEURISTIC rows; v1.5 QBAF if measured worthwhile.
- Phases 6-7 → `pdn.py`, harness, strength evaluation.

---

## 11. What this design tells the eventual generalized core

Recorded as an observation, not a commitment — the core is extracted after
2-3 games, not designed now. The checkers design suggests the generic backbone
is: an **AATS** (`Game` protocol: states, legal actions, τ, terminal), an
**AS2 scheme instance** (a game's `Value` set + `CriticalQuestion` set +
witness producers tagged by CQ/value/tier), a **two-layer evaluator** (crisp
Dung grounded over fact-tier defeaters + graded Categoriser/QBAF over
survivors), and a selector. The part that stays per-game is the witness
producers and the value set. If the third game (Othello — port plan §7)
confirms the AATS + CQ-tier structure carries over, that structure is the
core. The chess engine's `doubt` node and copy-counting are now understood as
artifacts of having only heuristic objections and no tier distinction — they
should not appear in the core.
