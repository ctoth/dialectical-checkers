# Phase 4 HEURISTIC Witness Layer - Independent Analyst Review

Workflow used: I followed `C:\Users\Q\code\dialectical-chess\prompts\phase4-heuristic-witnesses-analyst.md` as an independent code-review task. I did not modify code or tests under review.

## Gate Results

- `uv run pyright`: PASS, `0 errors, 0 warnings, 0 informations`.
- `uv run pytest`: PASS, `568 passed in 4.25s`.
- The harness-reported `witnesses.py` pyright errors around `ShotResult` and `_heuristic_objections(...)` are stale; I did not reproduce them on the current checkout.

## Findings

### MAJOR - Opposition fires outside the claimed equal-force case

- File and line: `dialectical_checkers/witnesses.py:309-323`, especially `315-317`.
- What is wrong: `_opposition_holder` checks only `len(reds) == 1 and len(whites) == 1`. It does not enforce equal force by piece type/material, and the comment explicitly says "a man vs a king is still one piece each" and applies the parity rule anyway.
- Constructed position: `B:WK10:B15`. Red has a man on 15; White has a king on 10. `probe_moves` emits `pro:opposition` for both `15-18` and `15-19`.
- Why it matters: the review prompt says the opposition implementation is restricted to the unambiguous "1-piece-per-side equal-force case." A man-vs-king ending is not equal force. This is a wrong firing condition, not just a silence/usability limitation. A wrong `pro:opposition` is worse than silence because future heuristic ranking will treat the move as tempo-positive in a position the documented rule did not cover.

### MAJOR - Back-rank hold/break counts kings as back-rank men

- File and line: `dialectical_checkers/witnesses.py:326-337`, `411-413`, `488-494`.
- What is wrong: `_home_rank_count` counts every side-owned piece on the home rank, including kings. `obj:back_rank_break` also does not require the moving home-rank piece to be a man. The design row describes "keeps king-row men" / "premature king-row man move", not kings wandering through the home rank later.
- Constructed positions:
  - `W:WK29,K32,18:B6`, move `18-14`: emits `pro:back_rank_hold` solely because two White kings occupy 29 and 32.
  - `W:WK29,K32,18:B6`, move `29-25`: emits `obj:back_rank_break` when a White king leaves 29.
- Why it matters: this gives structure credit or blame for positions that are not the back-rank-guard motif. A king on the home rank is a mobile crowned piece, not an unmoved guard man preserving the king row. The witness can therefore fire for the wrong strategic fact.

### MAJOR - `obj:exposes_man` can fire when the exposed capturable piece is a king

- File and line: `dialectical_checkers/witnesses.py:511-516`.
- What is wrong: the implementation checks only `any(m.is_jump for m in child.legal_moves())`, so any opponent capture after the move can trigger `obj:exposes_man`. It never verifies that the capturable mover piece is a man.
- Constructed position: `B:WK18,19:B3,8,K13,K17,K20,K30`, move `17-14`.
  - Probe: `MoveProbe(... reasons=('pro:center:1', 'pro:mobility:10', 'pro:formation:phalanx'), objections=('obj:exposes_man',) ...)`.
  - Child: `W:WK18,19:B3,8,K13,K14,K20,K30`.
  - White reply: `18x9`, captured square `(14,)`, and the captured cell is `('r', True)`.
- Why it matters: the documented label and design row are "man capturable". A capturable king is materially and strategically different. Treating it as the same heuristic objection loses information and gives a mislabeled witness to the future heuristic selector.

### MAJOR - `obj:loses_opposition` appears to be a dead witness under the implemented rule

- File and line: `dialectical_checkers/witnesses.py:472-486`.
- What is wrong or untested: I brute-force swept all one-piece-per-side positions over both turns and all man/king type combinations. No legal move emitted `obj:loses_opposition`. The curated tests also have no positive firing case for this witness.
- Evidence command shape used: a Python stdin script over `CheckersBoard.from_fen(...)` and `probe_moves(...)`, enumerating all `B/W:W[K?]1..32:B[K?]1..32` non-overlapping one-piece positions, searching for `obj:loses_opposition`; result was `none`.
- Why it matters: Phase 4 claims all nine HEURISTIC-tier witnesses are emitted with precise firing conditions. This row is present in `evidence.py`, but I found no reachable firing case in the only position class where `_opposition_holder` returns a holder. That makes the witness effectively unimplemented or at least unverified.

### MINOR - Coverage misses the edge cases above

- File and line: `tests/test_witnesses.py:747-789`, `795-812`, `937-978`; `tests/test_evidence.py:80-94`.
- What is wrong or untested: the tests cover basic positive/negative cases for most labels and evidence typing, but they do not test:
  - opposition silence for one-piece unequal-force endings such as man-vs-king;
  - a positive `obj:loses_opposition` firing case;
  - back-rank hold/break with kings on the home rank;
  - `obj:exposes_man` where the available capture is of a mover king.
- Why it matters: the current curated suite proves the happy-path definitions, not the boundary conditions that distinguish checkers-sound witnesses from shape-compatible labels.

## Soundness Checks That Passed

- Additive guarantee: PASS. `arguments.py` filters non-move arguments through `Tier.FACT` at `dialectical_checkers/arguments.py:131-141` and uses only FACT objections/replies/defenses in `build_root_argument_graph`. `selection.py` filters FACT evidence in the unavoidable-objection and pro-value terms at `dialectical_checkers/selection.py:113-129` and `217-229`.
- Independent additive positions: I compared full probes against FACT-stripped probes for `B:WK4:BK15`, `B:W30:B10`, `B:W21:B3`, `W:W29,31,18:B6`, `B:W13,16:B8,9`, and `B:W22,30:B6,9,13,14`. The selected move matched in every case, and HEURISTIC-only positions produced no non-move crisp graph arguments.
- `evidence.py`: PASS for the claimed HEURISTIC labels. The fixed labels, magnitude labels, and formation kinds map to the correct `Value` and `Tier.HEURISTIC`; malformed magnitude and formation suffixes are rejected.
- Witnesses that looked sound under the documented implementation definitions and constructed checks: `pro:center:{n}`, `pro:mobility:{n}`, `pro:formation:phalanx`, `pro:formation:echelon`, `pro:formation:bridge` as a static occupied-squares definition, and `obj:single_corner_drift` for men entering the documented single-corner region.

## Overall Verdict

The Phase 4 layer is additive with respect to current engine play, and the gate commands are clean. The implementation is not fully sound as a HEURISTIC witness layer: opposition is too broad in 1v1 unequal-force endings, back-rank witnesses count kings where the design says men, `obj:exposes_man` can label an exposed king as a man, and `obj:loses_opposition` appears dead/untested under the implemented opposition rule.
