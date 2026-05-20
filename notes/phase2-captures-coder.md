# Phase 2 — captures.py forced-capture resolver (Coder notes)

## 2026-05-20

### Step 0 — DONE
- `git checkout master`, `git merge --ff-only phase1-board-fix`, `git branch -d phase1-board-fix`.
- master HEAD = `2da1a24f` "Phase 1 fix: circular king multi-jump generation + test hardening". Confirmed.

### State / observations
- `dialectical_checkers/captures.py` is a Phase-0 skeleton: `ResolvedLine`,
  `ShotResult` dataclasses + `resolve`/`opponent_shot`/`own_shot` raising
  NotImplementedError.
- `board.py` (verified Phase 1): `CheckersBoard` frozen dataclass, `legal_moves`,
  `apply`, `is_terminal`, `winner`, `is_draw`, `is_loss_for`. PDN squares 1-32.
  `CheckersMove(path, captured)`, `is_jump = bool(captured)`.
- Mandatory capture: `legal_moves()` returns capture set if any jump exists.
- Terminal = LOSS for side-to-move (no stalemate). `winner()` returns side or None.

### Design §3 contract (captures.py)
- `resolve(board) -> ResolvedLine`: minimax over capture-only moves until a quiet
  (no-capture) position. Returns net material swing (man/king weighted), `forced`
  flag (losing side had no non-capturing alternative at each of its turns),
  `truncated`, terminal status.
- `opponent_shot(board, move)`: apply move, resolve; if opponent has forced
  sequence netting material/game return ShotResult else None.
- `own_shot(board, move)`: does move initiate forced winning sequence -> ShotResult.
- Budget: bound depth AND node count; budget hit -> truncated -> HEURISTIC tier;
  fully resolved -> FACT tier.
- captures.py imports only from within dialectical_checkers + stdlib. pydraughts
  only in tests/.

### Material weights
Design §8: man = 100, king = 150. Swing computed from side-to-move-at-resolve
perspective (need to decide sign convention — see below).

### Open design questions to resolve
1. Sign convention of material_swing: from whose perspective? Design says "net
   material swing" — resolve from the perspective of the side to move at the
   ROOT board. Brute-force reference will pin this down.
2. What counts as "quiet": a position with no captures for the side to move.
3. `forced` flag semantics: a line is forced if at every node the side to move
   had ONLY capture moves available (mandatory). The root may itself be quiet.

### Plan
- Write tests first (TDD): brute-force reference minimax + differential.
- Implement resolver: recursive capture-only minimax with depth+node budget.
- Gate: uv sync, pytest, pyright, brute-force differential.

### Verified observations (2026-05-20, second pass)
- master HEAD == 2da1a24f. `phase1-board-fix` branch does not exist; Step 0
  merge already effected on master (master already contains 2da1a24f). No
  branch to delete. Step 0 is satisfied.
- Baseline suite: `uv sync` ok, `uv run pytest -q` = 62 passed.
- test_board.py shows pydraughts pattern: `from draughts import Board as
  OracleBoard`, `OracleBoard(variant="english", fen=fen)`, `.legal_moves()`,
  move has `.steps_move` (list of squares) + `.has_captures`. PDN-FEN turn
  token B = Red, W = White; same square numbering as engine.
- captures.py skeleton: ResolvedLine(material_swing, forced, truncated,
  terminal), ShotResult(material_net, forced, truncated, terminal),
  resolve/opponent_shot/own_shot raising NotImplementedError. I will keep
  these dataclass field names and add a Tier field.

### Design decisions (resolved, no architectural discretion needed)
- material_swing sign: from the perspective of the side to move at the ROOT
  board (the side whose `resolve` is being called). Positive = root side
  gains. Brute-force reference pins this.
- Quiet = side to move has no capture moves.
- forced flag: True iff at every node on the realised principal line, the
  side to move had ONLY capture moves (i.e. the move set was forced). Root
  quiet position -> forced=True vacuously (empty line, swing 0).
- Budget: depth cap + node cap. Hit -> truncated=True -> HEURISTIC tier.
- Tier added to dataclasses: FACT if not truncated, HEURISTIC if truncated.

### Blockers
None.

## 2026-05-20 — Phase 2 execution pass

### Step 0 verified
- master HEAD == 2da1a24f. No phase1-board-fix branch (already merged). Tree
  has only untracked notes/phase2-captures-coder.md + pyghidra_mcp_projects/.
  Step 0 end state satisfied.
- Baseline: `uv sync` ok, `uv run pytest -q` = 62 passed in 2.47s.

### Board API confirmed (board.py read in full)
- `CheckersBoard.from_fen`, `.legal_moves() -> tuple[CheckersMove,...]`,
  `.apply(move) -> CheckersBoard`, `.is_terminal()`, `.winner()`, `.is_draw()`,
  `.turn` ("r"/"w"). `CheckersMove.is_jump`, `.captured`, `.path`, `.pdn()`.
- Mandatory capture: legal_moves returns jump set if any jump exists.
- Terminal = side-to-move has no legal move -> LOSS for that side.

### Design decisions (no discretion needed — pinned by design + brute-force ref)
- Material weights: man=100, king=150 (design §8 / §5.6).
- material_swing sign: from ROOT side-to-move perspective. Positive = root
  side nets material.
- Quiet = side to move has no capture move. resolve recurses ONLY through
  capture moves (legal_moves() restricted to is_jump). If side to move has no
  jump -> quiet, swing 0 contribution, recursion stops.
- A quiet root (no captures) -> ResolvedLine(swing=0, forced=True vacuously,
  truncated=False, terminal=None unless board terminal).
- forced flag: True iff at every node on the realised principal line the side
  to move had ONLY capture moves (mandatory). Since resolve only walks capture
  nodes and captures are always mandatory when present, every node resolve
  visits is forced -> forced is effectively always True for the line resolve
  produces. Kept as a field for honesty/API; computed as "no node was quiet
  -with-a-choice". Actually: resolve only ever recurses on capture positions,
  so forced=True for any non-trivial line.
- Budget: depth cap + node cap. Hit -> truncated=True -> Tier.HEURISTIC.
- Tier enum added (FACT/HEURISTIC); ResolvedLine/ShotResult gain `.tier`.
- terminal: if a resolved line ends on a board with no legal moves, terminal
  = winner side ("r"/"w"); else None.

### Plan
1. Write tests/test_captures.py with brute-force reference first (TDD).
2. Implement captures.py.
3. Gate: uv sync, pytest, pyright, brute-force differential >=200 positions.
4. Commit on master, write report.

### Progress (execution)
- captures.py implemented: Tier enum, ResolvedLine/ShotResult dataclasses with
  .tier, resolve() capture-only minimax w/ _Budget (depth+node caps),
  opponent_shot, own_shot. MAN_VALUE=100 KING_VALUE=150.
- verify_curated_shots.py CAUGHT 3 wrong hand-computed expected values before
  they became fake test assertions:
  * B:W18,26:B15 is a 2-for-0 crowning shot -> +250 (not even exchange).
  * W:W22:B11,18 is a white double -> +200 (not even exchange).
  * B:W25:B21 crowning capture -> +150 (man +crown bonus, not +100).
  Curated FENs/expected fixed to verified values.
- test_captures.py first run: 23 passed, 3 failed.
  * own_shot bug: resolved AFTER the move so it missed the material the move
    itself captured. FIXED: now resolves from mover's perspective spanning the
    move (before = net at root, end = _resolve_balance(after, mover)).
  * budget truncation tests: my chosen position B:W17,18,25,26:BK14 has only
    ONE legal move (board.py expands the whole king loop into a single
    CheckersMove) -> only 1 node, budget never hit. NEED a multi-PLY capture
    tree (both sides recapture across separate plies) to exercise truncation.

### Current blocker / next step
Need a position whose capture MINIMAX TREE is genuinely multi-node so a tiny
budget truncates it. Multi-jumps are single moves; need cross-ply recapture
chains. Writing scripts/find_truncation_position.py to search seeded walks for
a position whose resolve() node count > N, then use it in the truncation test.
