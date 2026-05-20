# Dialectical Checkers — comprehensive port plan

## 2026-05-20

Author: planning pass. Q wants a comprehensive plan to build the
dialectical-chess architecture for **English draughts** (8x8 American
checkers). Planning only — no implementation. Eventual goal is a generalized
`dialectical-games` core, but the agreed strategy is: **build Checkers (and a
few more games) first, then extract the core from observed commonality.** Do
not theorize the abstraction up front.

---

## 1. Objective & constraints

- Build a self-contained dialectical **English-draughts** engine that mirrors
  the dialectical-chess architecture: moves selected through a Dung
  argumentation framework, not a scalar evaluation.
- Variant is fixed: English/American draughts (8x8). NOT international (10x10),
  NOT pool/Spanish/etc.
- "Non-oracle strength" stance (carried from branch
  `experiment/non-oracle-strength`): the engine owns its move generation and
  its reasoning. Any reference implementation (pydraughts) or endgame database
  is allowed ONLY at the test/oracle seam, never in the decision path.
- Deliberately **do not** build the generalized core yet. Copy generic-looking
  code rather than abstract it. The core is extracted later from 2-3 concrete
  games.

---

## 2. What dialectical-chess is (verified by reading all core source)

Pipeline, per position:

1. `probe_moves` (probe.py, 1159 LOC) — for every legal move, run ~30 witness
   producers. Each move becomes a `MoveProbe` with `reasons` (pro labels),
   `objections` (con labels), `reply_attacks` (opponent's strong replies), and
   an integer `score`. Labels are stringly-typed with prefixes
   (`material:capture:300`, `tactical:allows_reply_mate_in_one:...`, etc.).
2. `build_root_argument_graph` (arguments.py, 653 LOC) — turns the probes into
   a Dung Argumentation Framework. Argument families: `move:`, `doubt:`
   (defeats every move; reasons must defeat the doubt), `reason:`, `objection:`,
   `defeater:` (defeats objections), `reply_attack:`, `defense:`, `support:`.
   Soft weighting is done by **duplicating arguments** (copy counts).
3. `formal-argumentation` (external lib, Q's own, pinned SHA) computes the
   `grounded_extension` (which moves survive) and `categoriser_scores`
   (ranking that breaks ties).
4. `choose_move` (arguments.py) — 6 selector modes (`argument`, `score`,
   `grounded`, `support`, `categoriser`, `optimizer`) apply lexicographic
   selection keys over the surviving moves.
5. `DialecticalChessEngine` (engine.py, 84 LOC) — thin orchestration:
   probe -> graph -> choose. Consumed by UCI, bench, probe CLI.

Supporting layers: `board.py` (OwnedBoard — own move-gen, FEN, perft, oracle
compare vs python-chess), `search.py` (negamax/alphabeta + the bounded reply
analysis `bounded_reply_attacks`/`has_bounded_defense`), `smt.py` (Z3
witnesses), `evidence.py` (label -> typed `ArgumentEvidence` comorphism),
`optimizer.py` (optional ILP selector), `loss_mining.py` (`has_forced_mate`).

The **architecture-review.md** (existing notes) records a key flaw, verified:
the copy-count weighting "reinvents weighted-AF with magic numbers"; under
grounded semantics the copies are **inert** (a move is defeated iff >=1
objection copy is undefeated iff the original is) — copies only move the
categoriser scores. This is a defect the checkers port should NOT inherit.

---

## 3. Generic / chess-specific seam (the load-bearing analysis)

| File | Verdict | Notes |
|---|---|---|
| `formal-argumentation` (dep) | **Generic** | Already a standalone package. The one shared piece. |
| `engine.py` | **Generic shape** | Orchestration only. Settings fields are chess-named; rename. |
| `arguments.py` graph **topology** | **Generic** | move/doubt/reason/objection/defeater/reply/defense families + defeat wiring. |
| `arguments.py` weight tables, `severe_objection_weight` | **Chess-specific** | Prefix dispatch + magic numbers. Do not port. |
| `evidence.py` **shape** (label -> typed evidence) | **Generic** | The comorphism pattern. |
| `evidence.py` prefix lists, world enum | **Chess-specific** | Vocabulary. |
| `search.py` negamax/alphabeta + reply recursion | **Generic skeleton** | Eval + piece values are chess-specific. |
| `optimizer.py` | **Generic adapter** | Objective list is chess-specific. |
| `selection_key` family | **Concept generic** | Specific tuple orders are chess-tuned. |
| `board.py` | **Fully chess-specific** | Rewrite entirely. |
| `probe.py` | **Fully chess-specific** | The witness vocabulary IS chess domain knowledge. Rewrite. |
| `smt.py` | **Chess-specific — and recommend dropping** | See section 6. |
| `loss_mining.py` `has_forced_mate` | **Chess-specific** | Rewrite as forced-win search. |
| `uci.py`, `adapters.py`, `bench.py`, CLIs | **Chess-specific I/O** | No UCI for draughts; PDN not PGN. |

The seam is already fairly clean. The reusable nucleus is roughly:
`formal-argumentation` + the graph topology + the engine shape + the search
skeleton + the evidence shape. Everything that encodes *what a good move is*
is domain-specific — exactly the part that must be rebuilt per game.

---

## 4. Why checkers is a GOOD second target (not just "different")

The single most important design fact: **captures are mandatory in checkers.**
This is not a nuisance — it makes the dialectical framing *sharper* than it is
in chess.

- In chess, the move space is large and tactics are *optional opportunities*
  you argue heuristically for. dialectical-chess objections are therefore
  mostly heuristic guesses (`opening:premature_queen`, `king_safety:...`) —
  stringly-typed, fuzzy, needing the magic-number weighting that
  architecture-review.md criticizes.
- In checkers, when a capture exists the legal move set collapses to captures
  only — often 1-3 moves. Multi-jumps are forced chains. This means an
  objection of the form "this move allows the opponent a forced N-for-M shot"
  is **provable**, not heuristic: you resolve the mandatory-capture sequence
  exactly with a small bounded search.
- So in checkers the AF's defeat edges are largely **hard** (proven forced
  loss of material / game). The fuzzy-weighting problem that plagues
  dialectical-chess *substantially dissolves*. Soft ranking is still needed
  for quiet-position positional arguments, but the categoriser already exists
  for that — no copy-count hack required.

Conclusion: checkers is an excellent second implementation because it
stress-tests the architecture in the *opposite* regime (forced/decidable
tactics vs heuristic tactics). That contrast is precisely what will reveal the
true core later: the core needs **hard defeaters for provable refutations**
AND **ranking-based weighting for soft arguments** — two mechanisms the chess
project conflated into one messy copy-count kludge.

---

## 5. Checkers-specific design

### 5.1 Rules — VERIFIED against the WCDF official "Rules of Draughts (Checkers)"

Confirmed 2026-05-20 against the World Checkers Draughts Federation official
rules (wcdf.net/rules/rules_of_checkers_english.pdf). Rule numbers cited. All
eight originally-flagged points held — the verification earned confidence
rather than catching an error — with three refinements (marked *).

- **Board (1.1, 1.5):** 8x8, 32 dark playable squares numbered 1-32. The
  near-left playing corner is the "Single Corner", near-right the "Double
  Corner" (1.4) — official named features, load-bearing for the strategic
  witnesses in 5.5.
- **Start (1.11):** Red on squares 1-12, White on 21-32, 13-20 empty. Square
  32 is the nearest double-corner square.
- **First move (1.13):** **Red** moves first. (Literature also calls Red
  "Black"; the engine should use Red/White to match the numbering system.)
- **Man move (1.15):** diagonally forward one square only. Moving an uncrowned
  man backward is explicitly an illegal move (1.25.4).
- **Man capture (1.18):** **forward only** — "over a diagonally adjacent and
  forward square". CONFIRMED — men capture forward only in English draughts.
- **King move & capture (1.17, 1.21):** one square diagonally, forward OR
  backward. **Non-flying** — exactly one square, no long-range move. (Flying
  kings are international draughts, not this game.)
- **Mandatory capture (1.20):** "All capturing moves are compulsory."
- **No maximum-capture rule (1.20):** "a player may select any one [jump]
  that they wish, not necessarily that which gains the most pieces."
  CONFIRMED — any legal capture is acceptable; max-capture is international-only.
- **Multi-jump (1.19, 1.20):** if a jump creates a further capture the piece
  continues until none remain; once started a multi-jump must be completed.
- *(refinement)* **Captured pieces are removed at the END of the sequence
  (1.19), and a piece may be jumped only once (1.20).** Move-gen consequence:
  during multi-jump expansion the captured pieces stay on the board (their
  squares are occupied — landing squares must avoid them) and are flagged
  un-jumpable; removal happens when the sequence terminates.
- *(refinement)* **Crowning ends the TURN, not merely the jump (1.16, 1.19,
  1.25.7).** A man reaching the king-row is crowned and the turn ends — even
  mid-multi-jump. A jump landing on the king-row terminates the sequence; the
  new king cannot jump again until the opponent has moved.
- *(refinement)* **Terminal = LOSS, never a stalemate draw (1.30).** "The game
  is won by the player who can make the last move" — the side to move with no
  legal move (all pieces captured OR all blocked) **loses**. No chess-style
  stalemate draw. This simplifies terminal handling and means the search
  skeleton's stalemate=0 branch (search.py `terminal_or_leaf_result`) must
  become no-moves=loss.
- **Draw (1.29, 1.32):** only by agreement, threefold repetition (1.32.1), or
  the 40-move no-progress rule (1.32.2): drawn if, across each player's own
  previous 40 moves, neither advanced an uncrowned man toward the king-row AND
  no piece was captured. The board therefore needs a no-progress counter
  (reset on any man move or any capture) plus position history for repetition
  — the analogs of chess's halfmove clock and repetition history.

Deliverable achieved: a confirmed, cited rule set. Phase 1's differential test
against pydraughts remains the implementation-level safety net.

### 5.2 Board representation (`board.py` analog)

- 8x8, 32 dark playable squares. Use standard English-draughts numbering 1-32.
- Internal state: immutable frozen dataclass (mirror `OwnedBoard`): tuple of
  32 cells, each `None | man | king` x `{black, white}`; side to move.
- Position I/O: PDN FEN tag form `B:Wxx,xx,Kxx:Bxx,xx,Kxx`. Implement
  parse/serialize.
- Move-gen: `pseudo_moves` -> `legal_moves` where legality = (a) if any
  capture exists, only capture sequences are legal; (b) capture sequences are
  fully expanded multi-jumps.
- `apply(move)` returns a new board; handles capture removal, crowning,
  side-to-move flip, no-progress counter.
- `perft` + `compare_to_oracle` against pydraughts (test-only).

### 5.3 Forced-capture resolution engine (the tactical spine)

A bounded search that, given a position, resolves all **forced** capture
sequences exactly. Because captures are mandatory, this is *complete within a
capture chain* — it is the checkers analog of quiescence search but exact, not
heuristic. It answers:

- "After my move, does the opponent have a capture? What does the forced
  exchange net?" -> `reply_attack` / `objection` labels.
- "Does my move initiate a forced sequence that wins material/the game?" ->
  `shot:setup` reason.

This replaces, far more rigorously, what dialectical-chess does with
`reply_mate_in_one_objections` + `has_forced_mate` + the Z3 fork witnesses.

### 5.4 Witness vocabulary (`probe.py` analog)

> SUPERSEDED by `checkers-design.md §5`. The paper triage
> (`checkers-papers-findings.md`) showed the vocabulary should be *derived
> from* Atkinson's critical-question taxonomy and tier-tagged (fact vs
> heuristic), not invented per producer. The list below is the pre-triage
> sketch, kept for history. Use `checkers-design.md §4-5`.

Start MINIMAL (the chess project started material-only and grew). Phase in:

REASONS (pro):
- `terminal:win` — opponent has no reply.
- `material:capture:N` — net pieces won by the forced sequence this move
  starts (weight king > man).
- `promotion:crown` — reaches king row.
- `shot:setup:net:N` — move forces a winning capture sequence next.
- (later, positional) `tempo:opposition`, `structure:bridge`,
  `structure:phalanx`, `back_rank:hold`, `center:control`, `mobility:gain`,
  `runaway:man` (uncatchable man heading to crown).

OBJECTIONS (con):
- `terminal:loss` — move leaves you with no legal reply.
- `tactical:allows_shot:net:N` — opponent has a forced winning sequence
  (the hard defeater — provable).
- `tactical:loses_exchange:N` — forced sequence nets the opponent material.
- (later, positional) `tempo:loses_opposition`, `back_rank:premature_break`,
  `structure:exposes_man`, `endgame:driven_to_single_corner`.

REPLY ATTACKS: the opponent's forcing captures after our move, resolved by
the forced-capture engine.

Key contrast with chess: most checkers objections are **provable**, so they
become **hard** defeat edges in the AF — no weighting needed. Only the
positional reasons (phase 5) need soft ranking, handled by the categoriser.

### 5.5 Endgame / opposition reasoning

Checkers strength in quiet/endgame positions is dominated by **"the move"
(opposition)** — a parity concept: whoever holds the opposition can force the
other to give ground. This is computable from piece counts and positions and
should emit `tempo:opposition` reasons / `tempo:loses_opposition` objections.
Other endgame motifs: first-vs-second-position king endings, single-corner vs
double-corner. Build a parity/opposition calculator; defer deep endgame theory.

Optional, fenced-off: Chinook-style WLD endgame databases exist (English
draughts is *solved*). Per the non-oracle stance, an endgame DB may be a
witness source ONLY if Q explicitly opts in, and even then it should be a
clearly isolated witness producer, not woven into the core decision logic.
Default plan: no endgame DB.

### 5.6 Static evaluation & search

- `static_evaluation`: material first (man = 100, king ~= 150-175 — kings are
  worth roughly 1.5 men; tune later). Add positional terms only after the
  material baseline plays correctly.
- negamax/alphabeta skeleton ports directly from search.py. Move ordering is
  near-trivial (captures are mandatory; order multi-jumps by net material).

---

## 6. What to drop / change relative to chess

- **Drop Z3 / smt.py.** Verified: in dialectical-chess the SMT layer is
  near-vestigial — `smt_mate_in_one_moves` wraps already-computed checkmates
  in a trivial SAT solve; `smt_fork_witnesses` does the real work in plain
  Python and the solver just rubber-stamps it. Checkers forced sequences are
  computed exactly by the mandatory-capture resolver — a SAT solver adds
  nothing. Recommend no z3 dependency. (If Q wants an SMT angle later, the
  honest use would be encoding shot-existence as a constraint problem, but
  plain exact search is simpler and complete. Flag for Q.)
- **Drop UCI.** There is no UCI for draughts. De facto protocols: the Hub
  protocol (Scan engine), DXP/Damexchange, and CheckerBoard's engine API
  (a Windows DLL ABI — the standard for American checkers GUIs). Recommend:
  ship a plain text/JSON protocol + PDN file I/O first; defer any GUI/DLL
  integration. Flag for Q.
- **PGN -> PDN** (Portable Draughts Notation) for game I/O and the loss-mining
  diagnostic.
- **Do not port the copy-count weighting.** Use hard defeat edges for provable
  objections; use the categoriser ranking (already provided by
  formal-argumentation) for soft positional arguments. This is a concrete
  improvement the checkers domain *enables*.
- **Forced-win search runs on the owned board, no oracle.** dialectical-chess
  inconsistently borrows python-chess inside `reply_forced_mate_objections`
  (`has_forced_mate(chess.Board(...))`). Checkers should keep all decision-path
  search on its own board representation.

---

## 7. Repo layout & the copy-don't-abstract discipline

- New sibling repo: `C:\Users\Q\code\dialectical-checkers`. uv-managed,
  mirrors dialectical-chess project conventions (pyproject, pyright basic,
  pytest markers).
- Depend on the **same** `formal-argumentation` lib, pinned to a SHA. That is
  the one piece that is already correctly a shared package.
- **Deliberately copy** the generic-looking files (engine shape, the
  `build_root_argument_graph` topology, the search skeleton, the
  evidence-comorphism shape). Copying is the *correct* move here: Q wants to
  observe what genuinely repeats across 2-3 games before committing to an
  abstraction. Premature DRY would freeze the wrong seam.
- Keep a `notes/ported-from-chess.md` manifest listing exactly which files
  were copied and from which dialectical-chess revision, so the eventual
  core-extraction has a precise diff target.
- After checkers + a third game, do a three-way diff -> extract
  `dialectical-games`. Suggested third game: **Othello/Reversi** — maximally
  different (placement + flips, no movement, no material), which will
  stress-test the core hardest. Nine Men's Morris is a milder alternative.
  Q's call.

---

## 8. Phased build plan

Each phase has a hard verification gate. Do not start phase N+1 until phase N's
gate passes. Establish a clean-baseline test run before each phase.

**Phase 0 — Scaffold.** New repo, uv, pin formal-argumentation, port the
engine orchestration shell + the empty argument-graph builder. Gate:
`uv run pytest` green on a trivial smoke test; `uv run pyright` clean.

**Phase 1 — Board substrate.** CheckersBoard: move-gen with mandatory capture,
multi-jump expansion, crowning, terminal detection; PDN-FEN I/O; perft. Gate:
perft matches published English-draughts perft values AND a differential
`compare_to_oracle` against pydraughts passes on a curated position set
(start, multi-jump, crowning, forced-capture, near-terminal). pydraughts is
test-only — verify it supports the English variant; if not, fall back to
hand-built fixtures from an authoritative engine.

**Phase 2 — Forced-capture resolution.** The exact bounded capture-sequence
resolver (section 5.3). Gate: resolves a corpus of known "stroke"/shot puzzles
to the correct forced outcome.

**Phase 3 — Minimal witnesses + argument graph.** Witnesses: terminal,
material-capture, promotion, `allows_shot`, reply attacks. Port
`build_root_argument_graph` topology; wire grounded extension + categoriser.
Gate: engine never plays an illegal move, never walks into a 1-ply forced
loss, always takes a free winning shot, in a tactical test corpus.

**Phase 4 — Selection.** Selector modes + selection keys adapted to checkers.
Gate: differential test that each selector mode is internally consistent;
`argument` mode is the default decider.

**Phase 5 — Positional / strategic witnesses.** Opposition/tempo, back-rank
hold, center, formations, runaway men. This is where quiet-position strength
comes from. Gate: measurable self-play improvement vs the phase-3 engine.

**Phase 6 — Harness.** PDN I/O, self-play match runner, a tactical puzzle
benchmark corpus (checkers stroke problems are abundant with known solutions —
an excellent EPD-analog), loss-mining diagnostic. Gate: benchmark runs end to
end and reports.

**Phase 7 — Strength evaluation.** Self-play ladders; play vs a simple
fixed-depth minimax baseline and, if available, an external checkers engine.
Honest, measured strength report. Gate: a written strength baseline, no
unverified Elo claims.

---

## 9. Test strategy

- Mirror dialectical-chess markers: `unit`, `property`, `differential`.
- **Differential / oracle tests:** move-gen vs pydraughts (test-only).
- **Property tests (hypothesis):** apply/undo round-trips; PDN-FEN
  round-trips; legal moves are a subset of pseudo moves; mandatory-capture
  invariant (if a capture exists, every legal move is a capture).
- **Tactical corpus:** known stroke puzzles -> engine must find the shot.
- **Forced-loss corpus:** positions where one move loses on the spot -> engine
  must avoid it.
- Establish the clean-baseline suite run before each phase (CLAUDE.md rule).

---

## 10. Risks & open decisions for Q

1. **Rule precision — RESOLVED.** The 5.1 rule set is verified against the
   WCDF official rules (2026-05-20). No design-breaking surprises; three
   refinements folded in (captured-pieces-removed-at-end, crowning-ends-turn,
   terminal=loss-not-draw). Phase 1's pydraughts differential gate remains the
   implementation-level net.
2. **Oracle/endgame-DB stance.** Recommend pydraughts strictly test-only, no
   endgame DB in the decision path. Confirm.
3. **Protocol/GUI.** Recommend text/JSON + PDN first; defer CheckerBoard DLL
   integration. Confirm — if Q wants CheckerBoard compatibility early, that is
   a meaningful extra scope item (C ABI).
4. **Third game** for core extraction: recommend Othello. Q's call.
5. **SMT.** Recommend dropping z3 entirely. Confirm.
6. **Weighting.** Recommend hard defeaters + categoriser, not copy-counts.
   This diverges from dialectical-chess deliberately and is an improvement the
   domain enables.

---

## 11. Toward the generalized core (kept deliberately light)

Do NOT design this now. After checkers, the likely seam — to be *confirmed* by
diffing, not assumed — is roughly: a `Game` protocol (legal moves / apply /
terminal / position I/O), a `WitnessGenerator` protocol, an
`ArgumentGraphBuilder` over witness bundles, selector strategies, and the
search skeleton. The part that will *not* generalize cleanly is the witness
vocabulary and its weighting — which is the whole reason for building 2-3
games first. Let the third game settle whether "hard defeater vs soft ranked
argument" is the right core distinction (this plan predicts it is, from the
chess-vs-checkers contrast, but one more data point should confirm it).

---

## Status / notes

- Codebase fully read: engine, arguments, evidence, probe, search, board, smt,
  optimizer, adapters, loss_mining, engine-API tests. Not read (low value for
  planning): uci.py/bench.py/CLI internals — pure I/O.
- Rules: VERIFIED against WCDF official rules (see 5.1).
- Papers: the full formal-argumentation corpus (64) was triaged, then
  `dialectical-chess/papers/` trimmed to the 10 the design actually uses
  (7 load-bearing + Prakken/Potyka/Rago for the named v1.5 deferred work).
  `.gitignore` excludes `*.pdf`/`*.png` so only the text notes are committed.
- Corpus triaged → `checkers-papers-findings.md` (7 load-bearing papers).
- Detailed design written → `checkers-design.md`. It supersedes 5.4 and
  upgrades the architecture: two layers (crisp Dung grounded for fact-tier
  defeaters + Categoriser for ranking survivors), no doubt node, no
  copy-counting, witness vocabulary derived from Atkinson's AS2 scheme +
  critical questions, fact/heuristic tiering from Bench-Capon.
- Planning deliverable COMPLETE. Next would be implementation (Phase 0+),
  pending Q's go-ahead.
</content>
