# Phase 3a — FACT-tier witness layer (Coder notes)

## 2026-05-20

### Task
Implement FACT-tier witness layer only: `scheme.py`, `evidence.py`,
`witnesses.py` (FACT producers). TDD. Commit to master.

### Observations (verified by reading source)
- `scheme.py` already complete: `Value`, `Tier`, `CriticalQuestion` enums
  match design §4 exactly. NOTE: `Tier` also defined in `captures.py` —
  two `Tier` enums exist. `captures.Tier` and `scheme.Tier` have identical
  members. Witnesses must compare resolver `ResolvedLine.tier` (captures.Tier)
  and emit scheme.Tier.
- `evidence.py`: `ArgumentEvidence` dataclass exists; `to_argument_evidence`
  raises NotImplementedError. Must implement.
- `witnesses.py`: `probe_moves` raises NotImplementedError. Must implement.
- `arguments.py`: `MoveProbe` has `pdn, score, reasons, objections,
  reply_attacks, defenses, search_score, search_line`. Phase 3a uses
  reasons/objections/reply_attacks/defenses. No new field needed so far.
- `captures.py` API: `resolve(board) -> ResolvedLine`,
  `opponent_shot(board, move) -> ShotResult|None`,
  `own_shot(board, move) -> ShotResult|None`. ShotResult has
  `material_net, forced, truncated, terminal, tier`.
- `board.py`: `legal_moves()`, `apply(move)`, `is_terminal()`, `winner()`,
  `CheckersMove.pdn()`, `.is_jump`, `.captured`, `.path`. Crowning detected
  in apply; a man landing on king-row crowns.

### Design §5 FACT rows to implement
PRO: `pro:terminal_win`, `pro:material:{n}`, `pro:crown`, `pro:shot_setup:{n}`
OBJ: `obj:terminal_loss`, `obj:allows_shot:{n}`, `obj:loses_exchange:{n}`
REPLY: `reply:{...}` FACT iff proven forced win/gain
DEFENSE: `defense:{...}` FACT iff resolver proves objection's line refuted

### Curated positions (verified by scripts/phase3a_verify_positions*.py)
- free winning shot: `B:W18,26:B15` -> only move 15x22x31, own_shot net 250
  terminal=r, crowns. -> pro:terminal_win, pro:material:2, pro:crown,
  pro:shot_setup:2 (terminal+gain).
- win material 2: `B:W16,24:B11` -> 11x20x27, own_shot net 200 terminal=r.
- crowning non-terminal: `B:W21:B27` -> 27-31/27-32 crown, no shots,
  non-terminal -> pro:crown only.
- allows_shot + quiet: `B:W22,30:B6,9,13,14` -> 6-10/14-17 quiet (no FACT
  witnesses); 13-17/14-18 quiet moves, opponent_shot net 100 terminal=None
  -> obj:allows_shot:1.
- terminal loss: `B:W22,30:B9,13` -> 13-17 quiet, opponent_shot net 200
  terminal=w -> obj:terminal_loss.
- loses_exchange: capture move, mover swing across line < 0. Need a probe.

### Under-specification resolved: allows_shot vs loses_exchange
Design §5 gives both as resolver-sourced FACT, with overlapping conditions.
Resolution: partition by move.is_jump.
- quiet move + opponent forced material gain -> obj:allows_shot:{n}
- capture move + mover forced NET loss across the line -> obj:loses_exchange:{n}
mover_swing = (move's immediate capture gain) - resolve(child).material_swing.
A 1-for-1 even trade is swing 0 -> no loses_exchange. terminal=opponent on
either -> obj:terminal_loss instead.

### loses_exchange position (verified phase3a_verify_loses_exchange2.py)
`B:W10,17,18:B6,13,14` (Red): `13x22` mover_swing -150 (loses_exchange:150),
`14x21` mover_swing -50 (loses_exchange:50), `6x15x22` mover_swing +100,
`14x23` mover_swing +50. Rich multi-move position.

### Final witness semantics (all FACT, weighted material units man=100/king=150)
- pro:terminal_win  : child.is_terminal() and child.winner()==mover
- pro:material:{n}  : move.is_jump and immediate weighted capture gain n>0
- pro:crown         : a man (not king) lands on its king-row this move
- pro:shot_setup:{n}: own_shot(board,move) returns FACT ShotResult, n=material_net
- obj:terminal_loss : opponent_shot FACT with terminal==opponent
- obj:allows_shot:{n}: quiet move (not jump), opponent_shot FACT, terminal None
- obj:loses_exchange:{n}: capture move, mover_swing<0 by force, terminal None
- reply:terminal_loss / reply:material:{n}: opponent_shot FACT (reply_attacks ch.)
- defense:holds_exchange: child has opponent captures but opponent_shot is None
  (resolver refutes the apparent reply)
All {n} magnitudes are weighted material (resolver native units). HEURISTIC /
truncated resolver results are NOT emitted as FACT witnesses.

### CORRECTED semantics (verified phase3a_verify_test_values.py)
- reply:material:{n}  n = opponent_shot.material_net (opponent's gain)
- reply:terminal_loss : opponent_shot FACT terminal==opponent
- obj:loses_exchange:{n}: capture move, opponent_shot FACT material shot,
  mover_swing = immediate_gain - opponent_shot.material_net < 0, n=abs(mover_swing)
- defense:holds_exchange: capture move, opponent_shot FACT material shot,
  mover_swing >= 0 (exchange held even/favorable; reply refuted)
- 13x22: opp_shot 250 -> loses_exchange:150, reply:material:250
- 2x11 : opp_shot 100, immediate 100 -> mover_swing 0 -> defense:holds_exchange,
  reply:material:100, pro:material:100

### Implementation complete
- scheme.py: UNCHANGED — already matched design §4 exactly.
- evidence.py: implemented to_argument_evidence; added `magnitude: int|None`
  field to ArgumentEvidence (directive: evidence carries "any parsed
  magnitude"). FACT-tier label taxonomy via two dict lookups.
- witnesses.py: implemented probe_moves. No MoveProbe field added.
- Found: TWO Tier enums (scheme.Tier, captures.Tier) — identical members,
  distinct classes. witnesses.py bridges: reads captures.Tier from resolver
  results, emits scheme.Tier-typed labels via evidence.py. Test file aliases
  captures.Tier as ResolverTier for ShotResult inspection. captures.py NOT
  modified (out of scope, verified Phase 2).

### Gate results (final, on committed state)
- uv sync: ok (16 packages)
- uv run pyright: 0 errors, 0 warnings, 0 informations
- uv run pytest: 179 passed (99 baseline + 80 new) — 108 unit, 5 property,
  66 differential.

### Status
DONE. Committing.
