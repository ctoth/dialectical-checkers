# Dialectical Checkers — build log (foreman coordination)

## Setup

Foreman coordinating the build of `dialectical-checkers` per:
- `notes/checkers-port-plan.md` — 8 phases + hard gates
- `notes/checkers-design.md` — concrete module design
- `notes/checkers-papers-findings.md` — corpus triage / theory

Build target repo: `C:\Users\Q\code\dialectical-checkers` (created in Phase 0).
Coordination artifacts (`prompts/`, `reports/`, this log) live in
`dialectical-chess`.

## Cycle structure

- Phase 0 (scaffold): single coder, low-risk, dispatched directly.
- Phases 1-7: gauntlet per phase — Coder (claude general-purpose, TDD) →
  Analyst (Codex, external independent review) → Verifier (claude
  general-purpose, gate decision). Scout role pre-satisfied by
  `checkers-design.md`.
- Gate per phase = the gate named in `checkers-port-plan.md §8`.

## Progress

- [ ] Phase 0 — scaffold the repo. DISPATCHED 2026-05-20.
- [ ] Phase 1 — board.py (move-gen, mandatory capture, multi-jump, crowning,
      PDN-FEN, perft, pydraughts differential).
- [ ] Phase 2 — captures.py (forced-capture resolver).
- [ ] Phase 3 — FACT-tier witnesses + crisp Dung layer.
- [ ] Phase 4 — graded layer + selection.
- [ ] Phase 5 — heuristic witnesses; v1.5 QBAF if measured worthwhile.
- [ ] Phase 6 — PDN I/O, harness, benchmark corpus.
- [ ] Phase 7 — strength evaluation.

## Log

### 2026-05-20 — Phase 0 dispatched
Prompt: `prompts/phase0-scaffold.md`. Coder agent (general-purpose) dispatched
to scaffold the repo. Awaiting `reports/phase0-scaffold.md`.
