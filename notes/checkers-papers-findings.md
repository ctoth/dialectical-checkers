# Checkers-engine design: findings from the formal-argumentation corpus

## 2026-05-20 — corpus triage for dialectical-checkers

Triage of the ~64-paper corpus in `dialectical-chess/papers/` to extract what
should inform the dialectical-checkers design. Read in full: Dunne 2011,
Baroni 2019, Amgoud 2013, Bonzon 2016, Prakken 2019, Atkinson 2007,
Bench-Capon 2003, Cayrol 2005, Amgoud 2008, Brewka 2010, Potyka 2018, Matt 2008
(notes.md each), plus all 64 description.md files. Cross-checked against
`notes/architecture-review.md` and `notes/checkers-port-plan.md`.

Note on corpus completeness: the `Baroni_2005_SCC-recursivenessGeneralSchema-
Argumentation/` directory has no notes.md/abstract.md/description.md — only a
gitignored PDF (now absent). SCC-recursiveness content below is reconstructed
from cross-references in other papers' notes, not from a primary read. Flagged
where it matters.

---

## 1. One-line map of the full corpus, grouped by theme

### Foundational abstract argumentation (Dung semantics)
- **Dung_1995_AcceptabilityArguments** — the AF = (arguments, attacks);
  admissible/preferred/stable/grounded/complete semantics. Bedrock.
- **Caminada_2006_IssueReinstatementArgumentation** — 3-valued in/out/undec
  labellings correspond to Dung semantics; introduces semi-stable.
- **Caminada_2007_EvaluationArgumentationFormalisms** — closure / direct &
  indirect consistency rationality postulates for rule-based systems.
- **Coste-Marquis_2005_PrudentSemantics** — cautious semantics: no co-accepted
  pair on an odd-length indirect attack path.
- **Baroni_2005_SCC-recursivenessGeneralSchemaArgumentation** — SCC-recursive
  schema: decompose AF into strongly-connected components, evaluate bottom-up;
  also defines cf2. (No notes.md in corpus.)
- **Gaggl_2013_CF2ArgumentationSemanticsRevisited** — simpler cf2
  characterisation; SCC-based.
- **Oikarinen_2010_CharacterizingStrongEquivalenceArgumentation** — kernels;
  when two AFs are substitutable without changing extensions.

### Weighted / quantitative / gradual / ranking semantics (Question A & E core)
- **Dunne_2011_WeightedArgumentSystemsBasic** — weights on *attacks* +
  inconsistency budget β; weighted grounded/preferred semantics.
- **Bistarelli_2012_ConArgToolSolveWeighted** — ConArg: CP/semiring-SCSP
  encodings of classical and weighted AF extensions; a solver.
- **Baroni_2019_GradualArgumentationPrinciples** — unifies 29 gradual-semantics
  properties into 11 principle groups; balance + monotonicity meta-principles;
  classifies 15+ semantics over QBAF/aQBAF/sQBAF.
- **Amgoud_2013_Ranking-BasedSemanticsArgumentationFrameworks** — axiomatic
  ranking-based semantics; 8 postulates; Discussion-based and Burden-based.
- **Bonzon_2016_ComparativeStudyRanking-basedSemantics** — property matrix for
  5 ranking semantics incl. the Categoriser; no semantics satisfies all 16.
- **Matt_2008_Game-TheoreticMeasureArgumentStrength** — argument strength as
  value of a 2-player zero-sum game, computed by LP.
- **Gabbay_2012_EquationalApproachArgumentationNetworks** — equational
  semantics: each node a value in [0,1] from equations over attackers.
- **Potyka_2018_ContinuousDynamicalSystemsWeighted** — quadratic-energy model
  for weighted bipolar AFs; provable convergence (acyclic), strong empirical
  convergence (cyclic).
- **Rago_2016_DiscontinuityFreeQuAD** — QuAD frameworks + DF-QuAD aggregation.
- **Rago_2016_AdaptingDFQuADBipolarArgumentation** — DF-QuAD ported to BAFs.
- **Delobelle_2019_InterpretabilityGradualSemanticsAbstract** — deletion-based
  impact measure; Counting Semantics has Balanced Impact, h-categorizer not.
- **Kampik_2024_ContributionFunctionsQuantitativeBipolar** — 4 contribution
  functions (Removal/Shapley/Gradient) for QBAGs; no function satisfies all
  principles.
- **AlAnaissy_2024_ImpactMeasuresGradualArgumentation** — revised removal and
  Shapley impact measures; counting semantics best behaved.
- **Yin_2023_ArgumentAttributionExplanationsQuantitative** — gradient-based
  attribution over acyclic QBAFs under DF-QuAD; O(n) closed forms.

### Bipolar argumentation / support (Question B core)
- **Amgoud_2004_BipolarityArgumentationFrameworks** — origin of BAF =
  (A, R_def, R_sup); three layers where bipolarity matters.
- **Amgoud_2008_BipolarityArgumentationFrameworks** — comprehensive bipolarity
  survey; BAF formal definition; supported defeat; gradual valuation.
- **Cayrol_2005_AcceptabilityArgumentsBipolarArgumentation** — BAF semantics:
  d-/s-/c-admissibility; supported & indirect defeat; safe sets.
- **Cayrol_2014_ChangeAbstractArgumentationFrameworks** — taxonomy of how
  adding an argument changes the extension set.

### Abstract Dialectical Frameworks (Question B & E)
- **Brewka_2010_AbstractDialecticalFrameworks** — ADFs: per-node Boolean
  acceptance conditions over parents; unify attack+support+thresholds.
- **Brewka_2013_AbstractDialecticalFrameworksRevisited** — preferred/stable
  ADF semantics for arbitrary (not just bipolar) ADFs; preferences; DIAMOND.
- **Polberg_2017_DevelopingAbstractDialecticalFramework** — ADFs as unifying
  substrate; ~90 inter-formalism translations; impossibility theorems.
- **Strass_2013_ApproximatingOperatorsSemanticsAbstract** — ADFs in
  approximation-fixpoint theory; one operator yields all ADF semantics.

### Structured argumentation (ASPIC / ABA) and accrual (Question C & D)
- **Prakken_2010_AbstractFrameworkArgumentationStructured** — ASPIC: strict/
  defeasible rules, undermining/rebutting/undercutting attacks.
- **Modgil_2018_GeneralAccountArgumentationPreferences** — ASPIC+ with
  preferences; attack-based conflict-free; rationality postulates.
- **Prakken_2019_ModellingAccrualArgumentsASPIC** — accrual model: multiple
  reasons for one conclusion via accrual sets + labelling-relative defeat.
- **Caminada_2007** (above) — postulates ASPIC+ must satisfy.
- **Besnard_2001_Logic-basedTheoryDeductiveArguments** — logic-based arguments;
  **origin of the categoriser/accumulator** for aggregating competing args.
- **Bondarenko_1997_AbstractArgumentation-TheoreticApproachDefault** — ABA
  foundations (no notes.md).
- **Toni_2013_GeneralisedFrameworkDisputeDerivations**,
  **Toni_2014_TutorialAssumption-basedArgumentation**,
  **Dimopoulos_2002_ComputationalComplexityAssumption-basedArgumentation**,
  **Lehtonen_2021_DeclarativeAlgorithmsComplexityResults**,
  **Lehtonen_2024_PreferentialASPIC**, **Popescu_2023_...TreeDecompositions**,
  **Čyras_2016_ABA...Preferences**, **Odekerken_2023_ASPICIncomplete...**,
  **Diller_2025_GroundingRule-BasedArgumentationDatalog**,
  **Wallner_2024_ValueBasedReasoningInASPIC** — ABA/ASPIC+ algorithms,
  complexity, preferences, grounding. Mostly out of scope for checkers.

### Practical reasoning / value-based / decision (Question D core)
- **Atkinson_2007_PracticalReasoningPresumptiveArgumentation** — practical-
  reasoning argument scheme AS1/AS2 + 17 critical questions over an AATS.
- **Bench-Capon_2003_PersuasionPracticalArgumentValue-based** — Value-based
  AFs: arguments carry values, defeat is audience-relative.

### Solvers / SAT / ASP / complexity (implementation infrastructure)
- **Egly_2010_Answer-setProgrammingEncodingsArgumentation** — ASPARTIX ASP
  encodings of all Dung semantics.
- **Cerutti_2013_ComputingPreferredExtensionsAbstract**,
  **Cerutti_2015_ArgSemSAT-1.0...**, **Pu_2017_ArgmatSat...**,
  **Dvorak_2014_ComplexitySensitive...**, **Thimm_2021_Fudge...**,
  **Thimm_2021_SkepticalReasoning...** — SAT-based AF solvers.
- **Egly/Cerutti/Pu/Dvorak** above — preferred/semi-stable/stage encodings.

### Probabilistic argumentation (out of scope for checkers)
- **Li_2011_ProbabilisticArgumentationFrameworks**, **Hunter_2017_...**,
  **Riveret_2017_...**, **Popescu_2024_×3 (Probabilistic Constellation)** —
  probabilities on arguments/attacks. Not relevant to a deterministic game.

### Belief revision / dynamics (out of scope for checkers)
- **Baumann_2015_AGMMeets...**, **Baumann_2019_AGMContractionDung**,
  **Diller_2015_ExtensionBasedBeliefRevision**,
  **Coste-Marquis_2007_MergingDung's...** — AGM revision/contraction/merging.

### Defeasible reasoning / TMS (background)
- **Pollock_1987_DefeasibleReasoning** — prima facie vs conclusive reasons;
  rebutting vs undercutting defeaters; collective defeat.
- **deKleer_1986_AssumptionBasedTMS**, **deKleer_1986_ProblemSolvingATMS** —
  ATMS; assumption/environment tracking.

### LLM / mining (out of scope)
- **Freedman_2025_ArgumentativeLLMsClaimVerification** — LLM-generated QBAFs
  scored by DF-QuAD. (Relevant only as a worked QBAF-construction example.)

---

## 2. Findings per question

### A. WEIGHTING — what replaces copy-count multiplication

**The defect, restated from the corpus's vocabulary.** The current engine
duplicates an argument N times to give it weight N. `architecture-review.md`
already proved this is inert under grounded semantics. In corpus terms: copy-
counting is a *broken, non-axiomatic encoding of cardinality* — and
`Bonzon_2016` shows that cardinality (the Cardinality-Precedence postulate) is
exactly one axis a *principled* ranking semantics already accounts for, with no
duplication. Copy-counting reinvents weighted argumentation badly.

There are three distinct principled families in the corpus. They are not
interchangeable:

**(1) Weighted argument systems — `Dunne_2011`.** Weights go on *attacks*, not
arguments, and are consumed by an *inconsistency budget* β: you may delete any
set of attacks whose total weight ≤ β, then take ordinary Dung semantics of the
reduced framework. β = 0 recovers plain Dung. Dunne explicitly argues
(pp.3-4) for weighting attacks not arguments, because one global argument-
strength number cannot be locally adjusted per attack. Cost: weighted
credulous/skeptical grounded acceptance is NP/coNP-complete (p.8-13); minimal-
budget is FP^NP-complete. This buys *graded relaxation of acceptance* — useful
when the crisp grounded extension would be empty. **Verdict for checkers:**
not the primary tool. Checkers' hard tactical defeaters should NOT be
budget-deletable — a proven forced loss is not "tolerable inconsistency." A
budget would let the engine ignore a real refutation. Keep β = 0 on the crisp
layer.

**(2) Gradual / quantitative semantics — `Baroni_2019`, `Potyka_2018`,
`Rago_2016`, `Gabbay_2012`.** Every argument gets a base score τ ∈ [0,1];
final strength σ is a fixpoint propagating attack (and support) influence. The
Quantitative Bipolar AF (QBAF) of `Baroni_2019` = (X, R-, R+, τ) *generalises
both* Dunne-style weighting and bipolar AFs. `Baroni_2019` reduces 29 scattered
properties to two meta-principles — **balance** (no attackers/supporters ⇒
σ = τ; an attacker pulls σ below τ; a supporter pulls it above) and
**monotonicity** (more/stronger attackers ⇒ lower σ; more/stronger supporters
⇒ higher σ). Any semantics with both satisfies all 11 principle groups. This is
the principled replacement for "argument worth 5": instead of 5 copies, give
the argument base score and let a balanced+monotonic semantics aggregate.

**(3) Ranking-based semantics — `Amgoud_2013`, `Bonzon_2016`, `Matt_2008`.**
Output a total preorder over arguments instead of numeric strengths.
`Amgoud_2013`'s 8 postulates and `Bonzon_2016`'s 16-property matrix are the
correctness checklist. Crucially, the **Categoriser** (Besnard & Hunter 2001,
`Besnard_2001`; analysed in `Bonzon_2016` p.3) is:

    Cat(a) = 1 / (1 + Σ_{b ∈ Att(a)} Cat(b)),  Cat(a) = 1 if no attackers.

`Bonzon_2016` Table 2: the Categoriser satisfies Abstraction, Void Precedence,
Defense Precedence, (Strict) Counter-Transitivity, **Cardinality Precedence**,
Distributed Defense Precedence, and more — failing only Quality Precedence and
Non-attacked Equivalence. `Baroni_2019` Table 5: the h-categorizer is *strictly
balanced and strictly monotonic*. So the Categoriser is a vetted, well-behaved
ranking semantics that already encodes cardinality and quality-of-attacker.

**Recommendation for A.** For "rank candidate moves, each carrying accepted/
defeated pro and con arguments," the corpus most supports a **gradual /
ranking-based semantics on the soft layer, with no copy-counting at all**, and
specifically the **Categoriser** — for three concrete reasons:

1. The `formal-argumentation` library *already implements it*
   (`categoriser_scores`, per the import-site facts in the mission and named
   "categoriser" in `architecture-review.md`). It is `Besnard_2001` /
   `Bonzon_2016`'s Cat function. Zero new code.
2. `Bonzon_2016` proves the Categoriser already satisfies Cardinality
   Precedence — the exact property copy-counting was trying (and failing) to
   buy. N independent reasons make Cat go up monotonically by construction.
3. `Baroni_2019` certifies it as balanced + monotonic, so it satisfies all 11
   gradual principle groups. It is the *axiomatically justified* version of
   "more reasons = stronger move."

For per-argument base-score weighting (a `material:capture:king` reason
mattering more than a `tempo` reason), move to a **QBAF with base scores τ**
(`Baroni_2019`) evaluated by **DF-QuAD** (`Rago_2016`) or **Potyka's quadratic-
energy model** (`Potyka_2018`). Potyka is the better cyclic-graph choice
(proven convergence acyclic, ~99% empirical cyclic; DF-QuAD provably oscillates
on some cycles — `Potyka_2018` p.5). Checkers soft-argument graphs are likely
acyclic or near-acyclic, so DF-QuAD is acceptable, but Potyka is the safer
default. Either way: **base scores replace copy counts.**

Do **not** adopt Dunne's budget for the soft layer — budget semantics relax
*acceptance*, while what's wanted is a *ranking* of already-surviving moves.

### B. SUPPORT / BIPOLARITY — replacing the "defeat the doubt" trick

Current encoding: a per-move `doubt:{uci}` argument attacks every move; each
pro-reason attacks (defeats) the doubt. So "reason supports move" is encoded as
"reason attacks a thing that attacks the move" — support faked through a double
attack. The corpus says this is a known anti-pattern and gives cleaner options.

**`Cayrol_2005` / `Amgoud_2008` (BAFs).** Add an explicit, first-class support
relation: BAF = (A, R_def, R_sup), R_sup independent of R_def. `Amgoud_2008`
identifies three positive-interaction types — confirms-premise, confirms-
conclusion (same conclusion / different reasons — *this is exactly multiple
pro-reasons for a move*), and brought-by. BAFs also formalise **supported
defeat** (a support chain ending in a defeat counts as a defeat) and require
admissible sets to be **closed for R_sup**. Caveat from `Polberg_2017`: the BAF
"Fundamental Lemma" fails, so BAF admissibility semantics are partly
problematic; Polberg restricts BAFs to d-complete/d-grounded. So BAFs give a
clean *modelling vocabulary* but a semantically awkward extension theory.

**`Brewka_2010` / `Brewka_2013` (ADFs).** The strongest answer. An ADF puts a
Boolean (or weighted-threshold) **acceptance condition** on each node over its
parents — attack, support, joint attack, "defeated only if BOTH counter-args
hold," and thresholds are all just formulas. A move-node's acceptance condition
becomes, directly: "this move is acceptable iff no hard objection holds AND
(enough pro-reasons hold)." The `doubt` argument disappears entirely — its job
(force reasons to matter) is the move-node's acceptance condition. `Brewka_2010`
also gives **weighted ADFs**: `C_s` accepted iff Σ weights of true parents ≥ α
— a principled threshold that directly models "the move is good iff its reasons
outweigh its objections," and `Brewka_2010` uses exactly this for legal proof
standards (preponderance / clear-and-convincing / beyond-reasonable-doubt).
Dung AFs are the special case where every condition is a conjunction of negated
attackers; grounded and complete semantics generalise cleanly to all ADFs
(stable/preferred need bipolar ADFs).

**Recommendation for B.** The cleanest *principled* encoding is an **ADF-style
per-move acceptance condition**, not the doubt trick and not raw BAF support
edges. Concretely: a move's acceptance condition = (∧ ¬hard-objection) ∧
(pro-reason threshold). This is `Brewka_2010` directly.

But pragmatically: `formal-argumentation` exposes a Dung `Argumentation-
Framework` + grounded extension + categoriser, *not* an ADF engine. Two-tier
recommendation:

- **Crisp layer:** keep a plain Dung AF for hard defeaters (Question E). Drop
  the `doubt` argument. A move is in the grounded extension iff no hard
  objection is undefeated — that is already what Dung grounded semantics does
  without any doubt node. The doubt node only existed to inject soft pro-
  reasons into a crisp framework; once soft reasoning moves to its own layer
  (E), the doubt node has no purpose.
- **Soft layer:** model pro-reasons as genuine **support** in a QBAF
  (`Baroni_2019`) / BAF (`Rago_2016` DF-QuAD handles BAF support natively).
  Support raises the move's strength directly — no attack-on-an-attacker
  indirection. If/when an ADF engine is available, collapse both layers into
  one ADF with weighted acceptance conditions (`Brewka_2010`).

### C. ACCRUAL — multiple independent reasons for one move

`Prakken_2019_ModellingAccrualArgumentsASPIC` is directly on point and **does
supersede copy-counting**, though it solves a subtler problem than the checkers
engine currently has.

The accrual problem: several arguments support the same conclusion; together
they should matter more than any one alone, and the linked/convergent/
cumulative distinction must be preserved. Prakken's model: an **accrual set** is
a set of same-conclusion arguments; **defeat is labelling-relative** (`l-defeat`)
and depends on a preference order over *sets* of arguments, not individual
arguments; a monotone characteristic function `F` over labellings gives a
well-behaved grounded semantics. Key results: it reduces to ordinary ASPIC+
when each conclusion has ≤ 1 argument, and it *avoids the exponential blow-up*
of the 2005 accrual model (which generated one argument per subset of reasons —
the closest formal analogue of, and an indictment of, copy-counting).

Prakken's explicit framing: copy/subset enumeration is the wrong way to do
accrual. The right way is to treat accrual as a property of *sets* of arguments
and let defeat depend on set preferences.

**Recommendation for C.** Adopt the *principle* — "multiple reasons for a move
accrue as a set, not as duplicated arguments" — but **not the full ASPIC+
l-defeat machinery**. The full machinery (labelling-relative defeat, set-
preference orders, the monotone `F`) is built for structured ASPIC+ with strict/
defeasible rules and is heavier than a game engine needs. For checkers, the
gradual-semantics layer from Question A already delivers accrual correctly and
cheaply: a move-node supported by N pro-reasons gets a Categoriser/DF-QuAD/QBAF
strength that *monotonically* increases with the number and base-score of those
reasons (`Baroni_2019` GP8 Strengthening Soundness; `Bonzon_2016` Cardinality
Precedence). That IS accrual, axiomatically, with no subset enumeration and no
copies. Reserve Prakken's set-preference model only if checkers later needs the
cumulative-vs-convergent distinction (e.g. two positional reasons that are
*the same idea counted twice* must not double-count) — that is the one thing a
plain sum-based gradual semantics gets wrong, and Prakken's set preferences fix
it. Note it as a known future refinement, not a v1 requirement.

### D. PRACTICAL REASONING — an argument scheme for move selection

Yes — the corpus contains a concrete, directly applicable argument scheme for
action choice, and the checkers engine's reasoning *should* be structured
around it.

**`Atkinson_2007` — the AS1/AS2 practical-reasoning scheme.** AS1:

    In current circumstances R, we should perform action A,
    which results in new circumstances S, which realises goal G,
    which promotes value V.

AS2 restates this over an Action-Based Alternating Transition System (AATS):
states Q, joint actions, a transition function τ, propositions, and a value-
valuation δ labelling each transition as promoting (+), demoting (−), or neutral
(=) w.r.t. a value. Critically, the scheme comes with **17 critical questions
(CQs)** that *generate the attacks* on a proposed action — a presumptive
argument for an action is defeated by a successful CQ. The CQs relevant to a
game engine:

- CQ2: does the action actually have the stated consequences? (move doesn't do
  what we claim)
- CQ3: does it actually bring about the goal?
- CQ5: is there an alternative action reaching the same resulting state?
- CQ6: is there an alternative action realising the same goal?
- CQ8/CQ9: does the action have a side effect that demotes this/another value?
  (the move has a tactical downside)
- CQ11: does the action preclude another action that would promote another
  value? (taking this move forfeits a better one)
- CQ17 (added for multi-agent AATS): is the *other agent* guaranteed to play
  its part of the joint action? (the opponent's reply — directly the
  `reply_attack` family)

`Atkinson_2007` states explicitly (p.859) that negative answers to CQ5-CQ11
are themselves AS1-style arguments — i.e. objections are first-class arguments
in the same scheme, exactly the move/reason/objection structure the engine
already has.

**`Bench-Capon_2003` — Value-based AFs (VAFs).** VAF = (args, attacks, V, val,
P): each argument promotes a value; **defeat is audience-relative** — A defeats
B iff A attacks B and the audience does not prefer B's value to A's. Distinguish
*attack* (structural) from *defeat* (successful for an audience). Key device
for checkers: **facts as a highest-priority value** — a factual argument always
defeats a merely-evaluative one. This is the principled version of the
hard/soft split (Question E): a *proven* tactical refutation promotes the
"fact" value and beats any positional argument regardless of the audience's
value ordering.

**Recommendation for D.** Structure the engine's reasoning explicitly as the
**AS2 practical-reasoning scheme over a game-AATS**, with checkers states as Q,
moves as actions, and the forced-capture resolver computing τ. This is not a
cosmetic relabelling — it gives a *principled, closed taxonomy of why a move
can be objected to* (the CQs), replacing the current ad-hoc stringly-typed
witness vocabulary with a checklist:

- Map each witness producer to a CQ. `tactical:allows_shot` = CQ8/CQ9 (side
  effect demotes the material value). `reply_attack` = CQ17 (opponent's joint-
  action part). A move that wins material but a better move wins more = CQ6/
  CQ11. `terminal:loss` = CQ8 with the "winning" value maximally demoted.
- Adopt `Bench-Capon_2003`'s **attack-vs-defeat split and "fact" value**: a
  CQ backed by a *proven* forced sequence promotes the fact value and is a hard
  defeater (E); a CQ backed by a heuristic positional judgement promotes an
  ordinary value and is resolved by ranking.
- "Values" in checkers terms: a small fixed set — `winning`, `material`,
  `king-count`, `tempo/opposition`, `mobility`, `structure`. CQ8/CQ9 attacks
  carry the value they demote; this tells the soft layer how to weigh them.

This makes the witness vocabulary *derivable from the scheme* rather than
invented per producer — the `checkers-port-plan.md` §5.4 vocabulary should be
re-grouped under AS2 + the CQs.

### E. SEMANTICS FIT — crisp Dung layer + graded layer for soft arguments

The checkers domain (mandatory captures ⇒ tactical objections are *provable
forced sequences*; positional arguments stay *soft*) is, per the corpus, an
almost textbook case for a **two-layer architecture**. No single semantics in
the corpus does both well, and the corpus is explicit that they are different
mechanisms:

- **Crisp layer = Dung grounded semantics** (`Dung_1995`). Hard tactical
  defeaters (proven forced loss of material / loss of game) are ordinary
  attacks in a plain Dung AF. A move is *eliminated* iff an undefeated hard
  objection attacks it — that is exactly grounded-extension membership. This
  layer is decidable, cheap (grounded is polynomial), and `formal-
  argumentation` already computes it (`grounded_extension`). No weights, no
  budget, no doubt node. Because checkers tactics are forced and exact, this
  layer carries most of the engine's correctness — the soft layer never gets to
  override a proven refutation.

- **Graded layer = a gradual/ranking semantics over the surviving moves**
  (Question A). Among the moves that survive the crisp layer, positional/quiet-
  move arguments are soft. Rank them with the **Categoriser** (already in
  `formal-argumentation`) or a QBAF/DF-QuAD base-score model. This layer only
  *orders* survivors; it can never resurrect a crisply-defeated move.

This is precisely what `checkers-port-plan.md` §4 already predicts ("hard
defeaters for provable refutations AND ranking-based weighting for soft
arguments — two mechanisms the chess project conflated"). The corpus confirms
the prediction and names the mechanisms.

**Bridge between the layers — corpus options:**

- `Bench-Capon_2003`'s **fact-as-highest-value** is the cleanest conceptual
  bridge: proven objections promote the fact value (hard, audience-independent);
  positional objections promote ordinary values (soft, ranked). One VAF, two
  tiers of value, defeat audience-relative for the soft tier and forced for the
  fact tier.
- `Brewka_2010` **weighted ADFs** unify both in one framework if an ADF engine
  is available: hard objections are conjuncts of the acceptance condition,
  soft arguments are weighted-threshold terms. Single framework, single
  evaluation. This is the long-term target; it needs an ADF solver
  `formal-argumentation` does not currently expose.

**SCC-recursiveness (`Baroni_2005`).** No notes.md in the corpus — the
following is from cross-references only and should be verified before relying
on it. SCC-recursiveness is a *general schema*: decompose the AF into strongly
connected components, topologically order them, and evaluate component by
component, each SCC's result feeding the next. Relevance to checkers: the
crisp tactical layer of a checkers position is **largely acyclic** — a forced
capture sequence is a DAG of positions, "this move allows that shot" rarely
forms cycles. On an acyclic AF, grounded = preferred = stable = the unique
extension (noted in `Cayrol_2005` p.380 and `Bench-Capon_2003`), and SCC-
recursive evaluation degenerates to a single bottom-up sweep. Practical
consequence: the crisp layer needs no expensive semantics — a topological
sweep over the defeat DAG suffices, and the same acyclicity is why
`Potyka_2018`'s quadratic-energy model has *proven* convergence and DF-QuAD's
cyclic oscillation problem mostly does not arise. If positional arguments do
introduce cycles (mutual `tempo` objections), confine the gradual semantics to
those SCCs and keep the acyclic remainder on the cheap sweep.

**Gradual-semantics caveat for the soft layer.** `Potyka_2018` proves DF-QuAD
can oscillate on cyclic graphs; `Baroni_2019` Table 5 and `Bonzon_2016` show no
gradual/ranking semantics satisfies every property. Pick deliberately: the
Categoriser (balanced + monotonic per `Baroni_2019`; satisfies cardinality &
defense precedence per `Bonzon_2016`) is the safe default and is free in the
library. Move to a QBAF + Potyka model only when per-argument base scores are
genuinely needed.

---

## 3. Load-bearing papers — build the checkers design against these

In priority order. These 7 are the ones the design actually rests on; the rest
of the corpus is context, infrastructure, or out of scope.

1. **Dung_1995_AcceptabilityArguments** — the crisp layer. Grounded semantics
   over a plain Dung AF of hard tactical defeaters. Already in
   `formal-argumentation` (`grounded_extension`).

2. **Besnard_2001_Logic-basedTheoryDeductiveArguments** — defines the
   **Categoriser** that `formal-argumentation` ships as `categoriser_scores`.
   This is the soft-layer ranking semantics; it already encodes "more reasons =
   stronger" (cardinality precedence) with no copy-counting. The single most
   important paper for fixing the weighting defect.

3. **Bonzon_2016_ComparativeStudyRanking-basedSemantics** — the property matrix
   that *justifies* picking the Categoriser and tells you exactly what it does
   and does not guarantee. The correctness checklist for the soft layer.

4. **Baroni_2019_GradualArgumentationPrinciples** — balance + monotonicity meta-
   principles; certifies the Categoriser and defines the QBAF (base-score)
   generalisation to graduate to if per-argument weighting is needed. The
   axiomatic backbone of the soft layer.

5. **Atkinson_2007_PracticalReasoningPresumptiveArgumentation** — the AS1/AS2
   action-choice argument scheme + 17 critical questions. The engine's
   reasoning should be *structured as this scheme*; the witness vocabulary
   should be derived from the CQs, not invented per producer.

6. **Bench-Capon_2003_PersuasionPracticalArgumentValue-based** — Value-based
   AFs; the attack-vs-defeat distinction and **fact-as-highest-value**. The
   principled bridge between the crisp (proven) and soft (positional) layers.

7. **Brewka_2010_AbstractDialecticalFrameworks** — ADFs with per-node /
   weighted-threshold acceptance conditions. The clean replacement for the
   "defeat the doubt" support trick, and the long-term target for unifying both
   layers in one framework. Adopt the *modelling idea* now (acceptance
   condition per move); adopt the *engine* later if an ADF solver is added.

Secondary (adopt the principle, not the full machinery):
- **Prakken_2019_ModellingAccrualArgumentsASPIC** — accrual as sets, not
  copies; supersedes copy-counting in principle. Full l-defeat machinery is
  heavier than v1 needs; revisit only for cumulative-vs-convergent dedup.
- **Potyka_2018_ContinuousDynamicalSystemsWeighted** — better-converging
  gradual semantics if the soft layer ever needs base scores and has cycles.
- **Dunne_2011_WeightedArgumentSystemsBasic** — explicitly *not* recommended
  for checkers' hard layer (budget would let the engine ignore proven
  refutations); listed so the decision to reject it is on record.

### Library capability map (what already exists vs must be built)

Already implemented in `formal-argumentation` (per mission's verified import
facts):
- Grounded extension — `Dung_1995`. **Reuse for the crisp layer.**
- Categoriser ranking (`categoriser_scores`) — `Besnard_2001` /
  `Bonzon_2016`. **Reuse for the soft layer. This is the copy-count
  replacement.**
- `optimize_framework` — likely an ILP/CSP optimiser in the
  `Bistarelli_2012`/`Dunne_2011` family; optional.

Must be built (not in the library):
- A QBAF / DF-QuAD / quadratic-energy base-score evaluator (`Baroni_2019`,
  `Rago_2016`, `Potyka_2018`) — only if per-argument base scores beyond the
  Categoriser's structural cardinality are needed.
- An ADF engine with weighted acceptance conditions (`Brewka_2010`/
  `Brewka_2013`) — only for the long-term unified-framework target.
- The AS2 practical-reasoning scheme + critical-question taxonomy
  (`Atkinson_2007`) — this is a *modelling discipline* layered on top of the
  witness producers, not a library feature.
- Value tagging + fact-as-highest-value defeat tiering (`Bench-Capon_2003`) —
  a thin layer over the witness vocabulary.

The accrual set machinery (`Prakken_2019`), weighted attack budgets
(`Dunne_2011`), probabilistic and belief-revision papers — not needed for the
checkers engine.
