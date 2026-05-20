"""Phase 2 — tests for ``dialectical_checkers.captures``.

The forced-capture resolver (design ``notes/checkers-design.md`` §3) is the
exact tactical spine: because captures are mandatory, a capture sequence is a
*bounded, exact* minimax over capture-only moves down to a quiet position.

Three test families, mirroring the project markers:

* ``unit`` — focused contract tests, curated hand-built shot positions, and
  the budget/truncation behaviour.
* ``property`` — the differential test: a seeded set of >=200 reachable
  positions, every non-truncated resolver result checked against an
  INDEPENDENT brute-force reference defined in this file.
* ``differential`` — the pydraughts cross-check: the resolver's claimed forced
  sequence is replayed move-by-move in pydraughts and the material outcome
  confirmed.

The brute-force reference (`brute_force_resolve`) is deliberately naive — a
plain recursive capture-only minimax with no budget and no optimisation — so it
cannot share a bug with the real resolver. pydraughts is imported ONLY in this
file, never by ``dialectical_checkers`` itself (the non-oracle-strength stance).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import pytest

from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.captures import (
    KING_VALUE,
    MAN_VALUE,
    ResolvedLine,
    ShotResult,
    Tier,
    opponent_shot,
    own_shot,
    resolve,
)

# ---------------------------------------------------------------------------
# Independent brute-force reference (TDD directive)
# ---------------------------------------------------------------------------
#
# A deliberately naive, obviously-correct recursive capture-only minimax. It
# computes the exact forced material outcome of a position from the perspective
# of the side to move at the ROOT. No budget, no optimisation, no caching — so
# it cannot share an implementation bug with the real resolver in captures.py.
#
# Because captures are mandatory (board.legal_moves() returns the jump set when
# any jump exists), the capture tree is small and this recursion always
# terminates: every capture strictly reduces the opponent's piece count, so the
# depth of any capture line is bounded by the total number of pieces.


def _material(board: CheckersBoard, side: str) -> int:
    """Weighted material for ``side`` on ``board`` — man=100, king=150."""
    total = 0
    for cell in board.cells:
        if cell is None or cell[0] != side:
            continue
        total += KING_VALUE if cell[1] else MAN_VALUE
    return total


def _net_material(board: CheckersBoard, root_side: str) -> int:
    """Material balance on ``board`` from ``root_side``'s perspective."""
    other = "w" if root_side == "r" else "r"
    return _material(board, root_side) - _material(board, other)


def _outcome_rank(
    balance: int, terminal: str | None, root_side: str
) -> tuple[int, int]:
    """Total-order key for a capture-line outcome, from ``root_side``'s view.

    Mirrors ``captures._outcome_rank`` deliberately — the reference must rank
    outcomes the SAME way the resolver should: a forced terminal game-win
    outranks any material outcome and a forced terminal game-loss is outranked
    by any material outcome (the analyst's CRITICAL finding). Without this band
    the reference would make the identical material-only mistake and so could
    not catch the bug. The band (``+1`` root wins / ``0`` non-terminal / ``-1``
    root loses) is the primary key; weighted material breaks ties only inside
    the non-terminal band.
    """
    if terminal is None:
        band = 0
    elif terminal == root_side:
        band = 1
    else:
        band = -1
    return (band, balance)


def brute_force_resolve(board: CheckersBoard) -> tuple[int, bool, str | None]:
    """Exact forced material outcome of ``board`` — the reference oracle.

    Returns ``(net_swing, forced, terminal)`` where:

    * ``net_swing`` is the change in material balance, from the perspective of
      the side to move at the ROOT, between ``board`` and the quiet (no-capture)
      position the mandatory-capture sequence resolves to.
    * ``forced`` is True iff the realised principal line passed only through
      capture nodes — vacuously True for a quiet root.
    * ``terminal`` is the winning side ("r"/"w") if the resolved line ends a
      game, else None.

    Naive recursion: at a node with captures the side to move picks the capture
    that is best *for it* under :func:`_outcome_rank` (minimax — the root side
    maximises that key, the opponent minimises it). Terminal game-wins/losses
    are banded above/below all material outcomes, so the reference, like the
    resolver, never trades a forced win for a larger material swing. At a node
    with no captures the line is quiet and stops.
    """
    root_side = board.turn
    start_balance = _net_material(board, root_side)

    def best_balance(node: CheckersBoard) -> tuple[int, bool, str | None]:
        """Best reachable end-balance (root perspective) by capture-only play."""
        moves = node.legal_moves()
        captures = [m for m in moves if m.is_jump]
        if not captures:
            # Quiet node — the capture sequence has resolved here.
            terminal = node.winner() if not moves else None
            return _net_material(node, root_side), True, terminal
        node_side = node.turn
        results: list[tuple[int, bool, str | None]] = []
        for mv in captures:
            results.append(best_balance(node.apply(mv)))
        if node_side == root_side:
            # Root side moves: maximise the banded outcome rank — a terminal
            # win beats any material gain, a material gain beats any loss.
            chosen = max(
                results, key=lambda r: _outcome_rank(r[0], r[2], root_side)
            )
        else:
            # Opponent moves: minimise the same banded outcome rank.
            chosen = min(
                results, key=lambda r: _outcome_rank(r[0], r[2], root_side)
            )
        # forced stays True: every node visited here had only captures.
        return chosen[0], True, chosen[2]

    end_balance, forced, terminal = best_balance(board)
    return end_balance - start_balance, forced, terminal


# ---------------------------------------------------------------------------
# Position generation for the differential test
# ---------------------------------------------------------------------------


def _reachable_boards(seed: int, max_plies: int) -> list[CheckersBoard]:
    """A deterministic random walk from the start; every visited board."""
    rng = random.Random(seed)
    board = CheckersBoard.initial()
    visited = [board]
    for _ in range(max_plies):
        moves = board.legal_moves()
        if not moves:
            break
        board = board.apply(rng.choice(moves))
        visited.append(board)
        if board.is_draw():
            break
    return visited


def differential_positions(target: int) -> list[CheckersBoard]:
    """At least ``target`` distinct positions from varied seeded walks.

    Walks start from the standard opening with many different seeds and varied
    depths, so the sample spans openings, midgames reached after exchanges, and
    capture-rich tactical positions.
    """
    seen: set[str] = set()
    out: list[CheckersBoard] = []
    seed = 0
    while len(out) < target:
        for depth in (8, 16, 24, 32, 44):
            for board in _reachable_boards(seed, depth):
                fen = board.to_fen()
                if fen in seen:
                    continue
                seen.add(fen)
                out.append(board)
        seed += 1
        if seed > 5_000:  # safety — should never be hit
            break
    return out


# ---------------------------------------------------------------------------
# pydraughts cross-check helpers (test-only — directive)
# ---------------------------------------------------------------------------


def _oracle_material(fen: str, side: str) -> int:
    """Weighted material for ``side`` from a PDN-FEN, via pydraughts' parse.

    Recomputed from the FEN that pydraughts produced after replaying a move —
    this confirms the engine's resolved sequence yields the same board the
    oracle reaches.
    """
    parts = fen.strip().split(":")
    field_for = {"W": "w", "B": "r"}
    total = 0
    for field_text in parts[1:]:
        tag, body = field_text[0], field_text[1:]
        colour = field_for[tag]
        if colour != side or not body:
            continue
        for token in body.split(","):
            token = token.strip()
            if not token:
                continue
            total += KING_VALUE if token.startswith("K") else MAN_VALUE
    return total


def _oracle_net(fen: str, root_side: str) -> int:
    """Material balance from a PDN-FEN, from ``root_side``'s perspective."""
    other = "w" if root_side == "r" else "r"
    return _oracle_material(fen, root_side) - _oracle_material(fen, other)


#: pydraughts ``Board.winner()`` codes -> the engine's side letters. pydraughts
#: BLACK (== engine Red, moves first) wins as ``1``; pydraughts WHITE (== engine
#: white) wins as ``2``. Confirmed by scripts/probe_oracle_winner.py.
_ORACLE_WINNER_TO_SIDE: dict[int, str] = {1: "r", 2: "w"}


@dataclass(frozen=True)
class OracleReplay:
    """The independent pydraughts verdict on a resolver's claimed line.

    ``final_fen`` — pydraughts' FEN after replaying the claimed line.
    ``net_swing`` — the material swing pydraughts reaches, root-side perspective.
    ``terminal`` — the winner pydraughts reports at the final position (engine
    side letter), or ``None`` if pydraughts says the game is not over there.
    ``replayed`` — the PDN strings of every claimed move, all asserted legal.
    """

    final_fen: str
    net_swing: int
    terminal: str | None
    replayed: tuple[str, ...]


def _replay_claimed_line_in_oracle(
    board: CheckersBoard, line: ResolvedLine
) -> OracleReplay:
    """Replay the resolver's CLAIMED principal line in pydraughts.

    This is an INDEPENDENT cross-check (analyst MAJOR finding): it never calls
    ``resolve`` to decide what to replay. The resolver hands over its claimed
    ``line.principal_line``; this helper replays exactly those moves in
    pydraughts, asserts each is legal there, and reports pydraughts' own
    material swing and terminal verdict at the quiet position. The caller then
    checks that verdict against the resolver's ``material_swing`` / ``terminal``
    — pydraughts, not the resolver, decides whether the claim holds.

    A claimed line is only meaningful if the result is not truncated; the
    caller guards on that. Returns an :class:`OracleReplay`.
    """
    from draughts import Board as OracleBoard

    root_side = board.turn
    start_fen = board.to_fen()
    start_balance = _oracle_net(start_fen, root_side)

    oracle = OracleBoard(variant="english", fen=start_fen)
    replayed: list[str] = []
    for move in line.principal_line:
        oracle_pdns = {
            ("x" if m.has_captures else "-").join(
                str(s) for s in m.steps_move
            ): m
            for m in oracle.legal_moves()
        }
        assert move.pdn() in oracle_pdns, (
            f"resolver's claimed move {move.pdn()} not legal in pydraughts "
            f"(oracle moves {sorted(oracle_pdns)}, start {start_fen})"
        )
        oracle.push(oracle_pdns[move.pdn()])
        replayed.append(move.pdn())

    final_fen = oracle.fen
    # pydraughts decides terminality independently: a side with no legal move
    # has lost. ``winner()`` is only meaningful once the game is over, and may
    # itself return ``None`` (a drawn or undecided game) — guard for it.
    oracle_terminal: str | None = None
    if oracle.is_over():
        oracle_winner = oracle.winner()
        if oracle_winner is not None:
            oracle_terminal = _ORACLE_WINNER_TO_SIDE.get(oracle_winner)
    return OracleReplay(
        final_fen=final_fen,
        net_swing=_oracle_net(final_fen, root_side) - start_balance,
        terminal=oracle_terminal,
        replayed=tuple(replayed),
    )


# ---------------------------------------------------------------------------
# unit — core contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_quiet_root_resolves_to_zero_swing() -> None:
    """A position with no captures resolves to zero swing, forced, FACT tier."""
    board = CheckersBoard.initial()
    line = resolve(board)
    assert isinstance(line, ResolvedLine)
    assert line.material_swing == 0
    assert line.forced is True
    assert line.truncated is False
    assert line.terminal is None
    assert line.tier is Tier.FACT


@pytest.mark.unit
def test_single_capture_nets_one_man() -> None:
    """A forced single capture nets the root side exactly one man (100)."""
    # Red man on 15, lone White man on 18: forced 15x22, White then has no
    # piece and no move -> terminal loss for White.
    board = CheckersBoard.from_fen("B:W18:B15")
    line = resolve(board)
    assert line.material_swing == MAN_VALUE
    assert line.forced is True
    assert line.truncated is False
    assert line.terminal == "r"
    assert line.tier is Tier.FACT


@pytest.mark.unit
def test_double_jump_nets_two_men() -> None:
    """A forced double jump nets the root side two men (200)."""
    board = CheckersBoard.from_fen("B:W16,24:B11")
    line = resolve(board)
    assert line.material_swing == 2 * MAN_VALUE
    assert line.forced is True
    assert line.truncated is False


@pytest.mark.unit
def test_resolve_matches_reference_on_quiet_and_capture() -> None:
    """The resolver agrees with the brute-force reference on simple cases."""
    for fen in ("B:W18:B15", "B:W16,24:B11", "B:W25,26:B21"):
        board = CheckersBoard.from_fen(fen)
        swing, forced, terminal = brute_force_resolve(board)
        line = resolve(board)
        assert line.material_swing == swing, fen
        assert line.forced == forced, fen
        assert line.terminal == terminal, fen


# ---------------------------------------------------------------------------
# unit — curated hand-built shot positions (directive: >=4)
# ---------------------------------------------------------------------------
#
# Each entry: (label, FEN, expected net swing from root side's perspective).
# All are verified against the brute-force reference AND pydraughts below.

CURATED_SHOTS: list[tuple[str, str, int]] = [
    # All expected swings are from the ROOT side's perspective and were
    # independently confirmed by scripts/verify_curated_shots.py — a standalone
    # capture-only minimax whose principal line is replayed in pydraughts. The
    # swing is the change in WEIGHTED material (man=100, king=150), so a man
    # that crowns inside the forced line contributes its +50 king bonus.
    #
    # 1. Plain single capture: Red 15 takes White 18 (15x22). White has no
    #    piece left -> terminal loss for White. Nets one man.
    ("single_man_capture", "B:W18:B15", MAN_VALUE),
    # 2. Double jump: Red 11 takes White 16 then 24 (11x20x27). Nets two men.
    ("double_jump", "B:W16,24:B11", 2 * MAN_VALUE),
    # 3. Two-for-zero crowning shot: Red 15 is forced into 15x22, which
    #    continues 22x31 capturing White 26 as well, and 31 is Red's king-row
    #    so the man crowns. Net = two men captured (200) + the crown bonus
    #    (50) = 250.
    ("double_capture_with_crown", "B:W18,26:B15", 2 * MAN_VALUE + 50),
    # 4. A genuine 2-for-1: Red has men on 14 and 15, White a lone man on 18.
    #    Red 15 is forced to take 18 (15x22). After 15x22 White has no piece
    #    -> terminal. Red kept the man on 14 and gained one -> net +100.
    ("two_men_one_capture", "B:W18:B14,15", MAN_VALUE),
    # 5. White-to-move forced double: White man on 22 must take Red 18
    #    (22x15), then continues 15x8 capturing Red 11. White nets two Red
    #    men (200) and Red is left with no piece -> terminal win for White.
    ("white_double_capture", "W:W22:B11,18", 2 * MAN_VALUE),
    # 6. Crowning shot: Red man on 21 takes White 25, landing on king-row 30
    #    and crowning; the crown ends the turn. Net = one man captured (100) +
    #    the crown bonus (50) = 150.
    ("crowning_capture", "B:W25:B21", MAN_VALUE + 50),
    # --- king / deep coverage (analyst MINOR finding) -----------------------
    # The six shots above are all man-captures with max forced depth 1 ply.
    # The four below cover king captures, king multi-jumps, and a genuine 3-ply
    # forced reply sequence. Each was hand-pinned and oracle-verified by
    # scripts/verify_king_deep_shots.py (and scripts/search_deep_forced.py for
    # the deep one) — a standalone banded minimax whose principal line is
    # replayed in pydraughts.
    #
    # 7. King single capture: a lone Red KING on 15 takes White man 18
    #    (15x22) — a king capture (kings move/capture any diagonal). White is
    #    then out of pieces -> terminal Red win. Nets one man (100).
    ("king_single_capture", "B:W18:BK15", MAN_VALUE),
    # 8. King multi-jump: a Red KING on 2 chains 2x11x18, capturing White men
    #    on 7 and 15 in one king multi-jump. Nets two men (200).
    ("king_double_jump", "B:W7,15:BK2", 2 * MAN_VALUE),
    # 9. King triple multi-jump: a Red KING on 14 chains 14x23x30x21, capturing
    #    White men on 18, 25 and 26. Nets three men (300).
    ("king_triple_jump", "B:W18,25,26:BK14", 3 * MAN_VALUE),
    # 10. A genuine 3-PLY forced reply sequence (not one chained multi-jump):
    #     Red 18x25, White forced 15x24 (a White-king recapture), Red forced
    #     27x20 (a Red-king capture). Three separate forced plies; White ends
    #     out of pieces -> terminal Red win. Net: Red captures White 22 and the
    #     White king on 15/24 (man 100 + king 150 = 250) and loses its own man
    #     on 18/25 (-100) -> +150.
    ("deep_three_ply_king_finish", "B:WK15,22:B18,19,K27,31", MAN_VALUE + 50),
]


@pytest.mark.unit
@pytest.mark.parametrize(
    "label,fen,expected",
    CURATED_SHOTS,
    ids=[c[0] for c in CURATED_SHOTS],
)
def test_curated_shot_outcomes(label: str, fen: str, expected: int) -> None:
    """Each curated shot resolves to its hand-computed forced net outcome."""
    board = CheckersBoard.from_fen(fen)
    line = resolve(board)
    assert line.truncated is False, f"{label} should resolve within budget"
    assert line.material_swing == expected, label
    # The brute-force reference must agree — independent confirmation.
    ref_swing, ref_forced, ref_terminal = brute_force_resolve(board)
    assert ref_swing == expected, f"reference disagrees on {label}"
    assert line.forced == ref_forced, label
    assert line.terminal == ref_terminal, label


# ---------------------------------------------------------------------------
# unit — terminal-vs-material conflict (analyst CRITICAL — direct tests)
# ---------------------------------------------------------------------------
#
# The CRITICAL finding: a material-only minimax can choose a non-terminal
# material gain over a forced terminal game-win (or, symmetrically at an
# opponent node, miss a forced terminal loss). These tests are DIRECT — they
# assert the resolver's outcome against hand/oracle-computed values, NOT against
# the in-file brute-force reference. The reference shares the resolver's banded
# ordering, so a differential test alone cannot prove the bug is fixed; a
# material-only resolver would fail every assertion below. Each position was
# independently verified in pydraughts by scripts/verify_terminal_conflict.py
# and scripts/search_minimising_conflict.py.


@pytest.mark.unit
def test_terminal_win_outranks_larger_material_gain() -> None:
    """A forced terminal game-win is chosen over a bigger material swing.

    ``W:W13,14,21:B1,9`` — the analyst's oracle. White to move (the ROOT side, a
    MAXIMISING node) has exactly two captures:

    * ``13x6`` — initiates the forced line ``13x6``, ``1x10x17``, ``21x14``;
      Red is then out of pieces, so White wins the GAME. Net material swing 0.
    * ``14x5`` — captures one Red man, leaving ``B:W5,13,21:B1``, non-terminal,
      material swing +100.

    A material-only ``max`` would pick ``14x5`` (+100 > 0) and discard the win.
    The fixed resolver bands any terminal win above any material outcome, so it
    must report the forced terminal White win — ``terminal == "w"`` — and the
    principal line must be the winning line, not the +100 grab.
    """
    board = CheckersBoard.from_fen("W:W13,14,21:B1,9")
    line = resolve(board)
    assert line.terminal == "w", "the forced terminal White win must be reported"
    assert line.truncated is False
    assert line.tier is Tier.FACT
    assert line.material_swing == 0, "the winning line nets zero material"
    assert [m.pdn() for m in line.principal_line] == ["13x6", "1x10x17", "21x14"]
    # An independent pydraughts replay of the resolver's CLAIMED line confirms
    # the terminal verdict — White wins, Red has no piece left.
    replay = _replay_claimed_line_in_oracle(board, line)
    assert replay.terminal == "w", replay.final_fen
    assert replay.net_swing == 0, replay.final_fen


@pytest.mark.unit
def test_terminal_win_outranks_material_gain_red_to_move() -> None:
    """The same conflict with Red as the root side — colour-symmetric.

    ``B:W32,24:B20,19,12`` — Red to move (ROOT, MAXIMISING node). ``19x28``
    grabs one White man non-terminally (+100); ``20x27`` initiates the forced
    line ``20x27``, ``32x23x16``, ``12x19`` that leaves White with no piece —
    a terminal RED win, material swing 0. A material-only ``max`` would take
    the +100 grab; the resolver must report the terminal Red win.
    """
    board = CheckersBoard.from_fen("B:W32,24:B20,19,12")
    line = resolve(board)
    assert line.terminal == "r", "the forced terminal Red win must be reported"
    assert line.truncated is False
    assert line.tier is Tier.FACT
    assert line.material_swing == 0
    assert [m.pdn() for m in line.principal_line] == [
        "20x27",
        "32x23x16",
        "12x19",
    ]
    replay = _replay_claimed_line_in_oracle(board, line)
    assert replay.terminal == "r", replay.final_fen
    assert replay.net_swing == 0, replay.final_fen


@pytest.mark.unit
def test_opponent_terminal_win_outranks_its_material_gain() -> None:
    """A MINIMISING (opponent) node picks its terminal win over a bigger grab.

    The CRITICAL defect is symmetric — it must be fixed at opponent nodes too.

    ``B:W15,K17,23,K24:B11,27`` — Red to move (ROOT). Red is forced into the
    single capture ``11x18``. After it White — the opponent, a MINIMISING node
    for the root Red balance — has a choice of captures:

    * ``23x14`` merely nets White material, non-terminal;
    * ``24x31`` initiates the forced line ``24x31``, ``18x27``, ``31x24`` that
      leaves Red with no piece — a terminal WHITE win, i.e. a root (Red) LOSS.

    A material-only ``min`` minimises the root balance and would pick ``23x14``,
    missing White's forced win. The fixed resolver bands a root loss below every
    material outcome, so the minimising node selects ``24x31`` and the result
    reports ``terminal == "w"`` — the forced game loss for the root side. Found
    and oracle-verified by scripts/search_minimising_conflict.py.
    """
    board = CheckersBoard.from_fen("B:W15,K17,23,K24:B11,27")
    line = resolve(board)
    assert line.terminal == "w", (
        "the opponent's forced terminal win (a root loss) must be reported"
    )
    assert line.truncated is False
    assert line.tier is Tier.FACT
    assert [m.pdn() for m in line.principal_line] == [
        "11x18",
        "24x31",
        "18x27",
        "31x24",
    ]
    replay = _replay_claimed_line_in_oracle(board, line)
    assert replay.terminal == "w", replay.final_fen
    assert replay.net_swing == line.material_swing, replay.final_fen


# ---------------------------------------------------------------------------
# differential — pydraughts cross-check of the principal line (directive)
# ---------------------------------------------------------------------------


@pytest.mark.differential
@pytest.mark.parametrize(
    "label,fen,expected",
    CURATED_SHOTS,
    ids=[c[0] for c in CURATED_SHOTS],
)
def test_curated_shots_match_pydraughts(label: str, fen: str, expected: int) -> None:
    """Replay the resolver's CLAIMED line in pydraughts; outcome must match.

    The resolver's own ``principal_line`` is replayed move-by-move in
    pydraughts (the helper never re-runs ``resolve`` to choose moves — analyst
    MAJOR finding). Every claimed move must be legal in pydraughts, the final
    material swing pydraughts reaches must equal the resolver's
    ``material_swing``, and pydraughts' terminal verdict must equal the
    resolver's ``terminal``.
    """
    board = CheckersBoard.from_fen(fen)
    line = resolve(board)
    replay = _replay_claimed_line_in_oracle(board, line)
    assert replay.net_swing == expected, (
        f"{label}: oracle swing {replay.net_swing} (final {replay.final_fen})"
    )
    assert replay.net_swing == line.material_swing, (
        f"{label}: resolver {line.material_swing} != oracle {replay.net_swing} "
        f"(final {replay.final_fen})"
    )
    assert replay.terminal == line.terminal, (
        f"{label}: resolver terminal {line.terminal!r} != oracle "
        f"{replay.terminal!r} (final {replay.final_fen})"
    )


@pytest.mark.differential
def test_multi_capture_positions_match_pydraughts() -> None:
    """Resolver's CLAIMED line is legal & outcome-correct in pydraughts.

    A set of capture-rich positions: the resolver's own ``principal_line`` is
    replayed move-by-move in pydraughts; each step must be legal, the final
    material swing must equal the resolver's claim, and pydraughts' terminal
    verdict must equal the resolver's ``terminal``.
    """
    multi_capture_fens = [
        "B:W16,24:B11",  # double jump
        "B:W18,26:B15",  # even exchange chain
        "B:W7,15,23,24:BK2",  # king multi-jump
        "B:W18,25,26:BK14",  # king triple jump
        "B:W17,18,25,26:BK14",  # king loop capture
        "B:W22:B11,18",  # white-to-move forced exchange
    ]
    for fen in multi_capture_fens:
        board = CheckersBoard.from_fen(fen)
        line = resolve(board)
        if line.truncated:
            continue  # truncated lines make no exact claim
        replay = _replay_claimed_line_in_oracle(board, line)
        assert replay.net_swing == line.material_swing, (
            f"{fen}: resolver {line.material_swing} != oracle "
            f"{replay.net_swing} (final {replay.final_fen})"
        )
        assert replay.terminal == line.terminal, (
            f"{fen}: resolver terminal {line.terminal!r} != oracle "
            f"{replay.terminal!r} (final {replay.final_fen})"
        )


# ---------------------------------------------------------------------------
# property — the brute-force differential over >=200 positions (directive)
# ---------------------------------------------------------------------------


@pytest.mark.property
def test_differential_resolve_vs_brute_force() -> None:
    """Every non-truncated resolver result equals the brute-force reference.

    On a deterministic seeded set of >=200 reachable positions, the resolver's
    ``(material_swing, forced, terminal)`` must equal the independent
    brute-force capture-only minimax for every position whose result is not
    truncated (a truncated result makes no exact claim — design §3/§4).
    """
    positions = differential_positions(target=260)
    assert len(positions) >= 200, len(positions)
    checked = 0
    truncated = 0
    for board in positions:
        line = resolve(board)
        if line.truncated:
            truncated += 1
            continue
        ref_swing, ref_forced, ref_terminal = brute_force_resolve(board)
        fen = board.to_fen()
        assert line.material_swing == ref_swing, (
            f"swing mismatch at {fen}: resolver {line.material_swing} "
            f"!= reference {ref_swing}"
        )
        assert line.forced == ref_forced, f"forced mismatch at {fen}"
        assert line.terminal == ref_terminal, f"terminal mismatch at {fen}"
        assert line.tier is Tier.FACT, f"non-truncated must be FACT at {fen}"
        checked += 1
    # The vast majority of reachable positions resolve fully within budget.
    assert checked >= 200, f"only {checked} non-truncated positions checked"


@pytest.mark.property
def test_capture_positions_are_exercised() -> None:
    """The differential sample actually contains capture positions.

    A differential test over only quiet positions would be vacuous. Confirm the
    seeded sample includes positions where the side to move has a forced
    capture, so the resolver's recursion is genuinely exercised.
    """
    positions = differential_positions(target=260)
    with_captures = sum(
        1
        for b in positions
        if any(m.is_jump for m in b.legal_moves())
    )
    assert with_captures >= 20, with_captures


# ---------------------------------------------------------------------------
# unit — budget / truncation (directive)
# ---------------------------------------------------------------------------


# A position with a genuinely multi-PLY capture tree: captures by both sides
# spread across several plies, so the resolver's minimax descends through many
# nodes (48 — see scripts/find_truncation_position.py). A lone multi-jump is a
# single CheckersMove (board.py expands the whole chain) and would give a
# one-node tree that no budget could truncate; this position does not.
TRUNCATION_FEN = "W:W18,22,23,24,26,27,28,30,32:B1,3,4,5,7,11,12,14,19"


@pytest.mark.unit
def test_budget_truncation_yields_heuristic_tier() -> None:
    """A position exceeding the node budget yields a truncated HEURISTIC line.

    Passing a deliberately tiny budget forces truncation on a position whose
    capture tree is larger than the budget. A truncated line must be marked
    ``truncated`` and ``Tier.HEURISTIC`` — never a confident FACT-tier claim.
    """
    board = CheckersBoard.from_fen(TRUNCATION_FEN)
    line = resolve(board, max_depth=1, max_nodes=1)
    assert line.truncated is True
    assert line.tier is Tier.HEURISTIC


@pytest.mark.unit
def test_truncated_result_is_not_a_false_fact() -> None:
    """A truncated result never claims FACT tier even when its swing is wrong.

    With a tiny budget the resolver computes an incomplete swing. The contract
    is: it must NOT label that incomplete result FACT. For this position the
    truncated swing (200) genuinely differs from the true forced swing (100) —
    so a FACT label would be an outright false claim; the resolver marks it
    HEURISTIC instead. The full (un-budgeted) resolve is exact and equals the
    brute-force reference.
    """
    board = CheckersBoard.from_fen(TRUNCATION_FEN)
    truncated = resolve(board, max_depth=1, max_nodes=1)
    full = resolve(board)
    ref_swing, _, _ = brute_force_resolve(board)
    # The full resolve is exact and matches the reference.
    assert full.truncated is False
    assert full.tier is Tier.FACT
    assert full.material_swing == ref_swing
    # The truncated resolve disagrees with the truth here — and is honestly
    # marked HEURISTIC, never FACT, precisely because of that.
    assert truncated.truncated is True
    assert truncated.tier is Tier.HEURISTIC
    assert truncated.material_swing != full.material_swing


@pytest.mark.unit
def test_generous_budget_does_not_truncate_normal_positions() -> None:
    """Reachable positions resolve fully under the default budget."""
    for board in _reachable_boards(seed=7, max_plies=40):
        line = resolve(board)
        # Default budget is sized so ordinary capture trees fully resolve.
        assert line.truncated is False, board.to_fen()


# ---------------------------------------------------------------------------
# unit — opponent_shot / own_shot (design §3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_opponent_shot_detects_forced_loss() -> None:
    """``opponent_shot`` flags a move that hands the opponent a forced capture.

    Red king on 23, Red also has a man on 7; White man on 18. If Red plays the
    quiet king move 23-18? not possible (18 occupied). Construct directly: Red
    to move plays a quiet move that exposes a man to a forced White capture.

    Position: Red men on 9 and 14, White man on 22. Red plays 9-13 (quiet).
    After 9-13 it is White's move; White man 22 has no capture. So instead use:
    Red man on 15, White man on 24. Red plays 15-19; now White 24x15 captures
    -> opponent_shot must report a forced material gain for White.
    """
    board = CheckersBoard.from_fen("B:W24:B15")
    # Red's quiet move 15-19 places the Red man where White 24 can jump it.
    move = CheckersMove(path=(15, 19), captured=())
    assert move in board.legal_moves()
    shot = opponent_shot(board, move)
    assert shot is not None
    assert isinstance(shot, ShotResult)
    # White nets one Red man: from White's perspective +100.
    assert shot.material_net == MAN_VALUE
    assert shot.forced is True


@pytest.mark.unit
def test_opponent_shot_returns_none_for_safe_move() -> None:
    """``opponent_shot`` returns None when the move concedes nothing."""
    board = CheckersBoard.from_fen("B:W24:B15")
    # Red's other quiet move 15-18 does not expose the man to White 24.
    move = CheckersMove(path=(15, 18), captured=())
    assert move in board.legal_moves()
    assert opponent_shot(board, move) is None


@pytest.mark.unit
def test_own_shot_detects_initiating_a_winning_capture() -> None:
    """``own_shot`` flags a move that itself initiates a forced winning gain.

    Red man on 11 to move: the only legal move is the forced double jump
    11x20x27 (captures White 16 and 24). That move IS a forced winning
    sequence — ``own_shot`` must report a net gain of two men.
    """
    board = CheckersBoard.from_fen("B:W16,24:B11")
    move = board.legal_moves()[0]
    assert move.is_jump
    shot = own_shot(board, move)
    assert shot is not None
    assert shot.material_net == 2 * MAN_VALUE
    assert shot.forced is True


@pytest.mark.unit
def test_own_shot_returns_none_for_even_or_losing_move() -> None:
    """``own_shot`` returns None when the move wins no material.

    A quiet move from a quiet position initiates no forced gain.
    """
    board = CheckersBoard.initial()
    move = board.legal_moves()[0]
    assert not move.is_jump
    assert own_shot(board, move) is None
