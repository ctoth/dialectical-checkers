"""Phase 3a — tests for ``dialectical_checkers.witnesses``.

``probe_moves(board)`` produces one :class:`MoveProbe` per legal move, carrying
the FACT-tier witnesses of design ``notes/checkers-design.md`` §5: the AS1
pro-reasons (``pro:terminal_win``, ``pro:material:{n}``, ``pro:crown``,
``pro:shot_setup:{n}``) and the CQ-derived objections / replies / defenses
(``obj:terminal_loss``, ``obj:allows_shot:{n}``, ``obj:loses_exchange:{n}``,
``reply:{...}``, ``defense:{...}``).

Two test families:

* ``unit`` — curated, hand-verified positions: a free winning shot, a move
  winning material, a move that allows the opponent a shot, a move that loses
  the game on the spot, a crowning move, and a quiet move with NO FACT
  witnesses. Each asserts the exact FACT witness set for the relevant move.
* ``differential`` — consistency tests tying the witness layer to the verified
  forced-capture resolver: ``obj:allows_shot`` appears iff
  ``captures.opponent_shot`` returns a shot; ``pro:shot_setup`` iff
  ``captures.own_shot``; ``pro:terminal_win`` iff the move's child is terminal
  for the mover.

Every FACT-tier witness is checked against the resolver, never asserted on
faith. The curated positions were independently hand-verified by
``scripts/phase3a_verify_positions*.py``.
"""

from __future__ import annotations

import pytest

from dialectical_checkers import witnesses
from dialectical_checkers.arguments import MoveProbe
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import ShotResult
from dialectical_checkers.captures import Tier as ResolverTier
from dialectical_checkers.captures import opponent_shot, own_shot
from dialectical_checkers.evidence import to_argument_evidence
from dialectical_checkers.scheme import Tier
from dialectical_checkers.witnesses import probe_moves

# Two ``Tier`` enums exist in the codebase: ``scheme.Tier`` — the public AS2
# taxonomy a witness label is typed by (design §4) — and ``captures.Tier`` (here
# ``ResolverTier``), an implementation detail of the forced-capture resolver
# tagging a ``ShotResult`` FACT vs truncated. They have identical members but
# are distinct classes; ``witnesses.py`` bridges them. Inspecting a resolver
# ``ShotResult`` therefore compares against ``ResolverTier``; inspecting a
# parsed witness label compares against ``Tier``.


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _probe_for(board: CheckersBoard, pdn: str) -> MoveProbe:
    """Return the :class:`MoveProbe` for the move with PDN string ``pdn``."""
    probes = {p.pdn: p for p in probe_moves(board)}
    assert pdn in probes, f"no probe for move {pdn!r}; have {sorted(probes)}"
    return probes[pdn]


def _all_labels(probe: MoveProbe) -> list[str]:
    """Every witness label on ``probe`` across all channels."""
    return [
        *probe.reasons,
        *probe.objections,
        *probe.reply_attacks,
        *probe.defenses,
    ]


def _fact_labels(probe: MoveProbe) -> set[str]:
    """The set of FACT-tier witness labels on ``probe``.

    Phase 3a emits only FACT witnesses, but this filters by the evidence tier
    so the assertion is honest about what it checks.
    """
    return {
        label
        for label in _all_labels(probe)
        if to_argument_evidence(label).tier is Tier.FACT
    }


# ---------------------------------------------------------------------------
# unit — probe_moves shape
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_probe_moves_one_probe_per_legal_move() -> None:
    """``probe_moves`` returns exactly one probe per legal move, by PDN."""
    board = CheckersBoard.initial()
    moves = board.legal_moves()
    probes = probe_moves(board)
    assert len(probes) == len(moves)
    assert {p.pdn for p in probes} == {m.pdn() for m in moves}


@pytest.mark.unit
def test_every_emitted_label_is_typed() -> None:
    """Every label any probe emits is parseable typed evidence (design §5).

    Phase 4 adds the HEURISTIC-tier rows, so an emitted label may be FACT or
    HEURISTIC — but it must always be a *known, typed* label: ``evidence.py``
    must parse it without raising. No untyped / unknown label may ever leak
    out of the witness layer.
    """
    for fen in (
        "B:W18,26:B15",
        "B:W22,30:B6,9,13,14",
        "B:W10,17,18:B6,13,14",
        "B:W21:B27",
        "B:WK4:BK15",
        "B:W13,16:B8,9",
    ):
        board = CheckersBoard.from_fen(fen)
        for probe in probe_moves(board):
            for label in _all_labels(probe):
                evidence = to_argument_evidence(label)
                assert evidence.tier in (Tier.FACT, Tier.HEURISTIC), (
                    fen,
                    probe.pdn,
                    label,
                )


# ---------------------------------------------------------------------------
# unit — curated, hand-verified positions (directive's required six)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_free_winning_shot() -> None:
    """A free winning shot: the one forced move ends the game by force.

    ``B:W18,26:B15`` (Red) — Red's only legal move is the forced multi-jump
    ``15x22x31``: it captures White's men on 18 and 26 (weighted 200), the man
    crowns on king-row square 31 (+50), and White is left with no piece —
    terminal Red win. The move must carry every FACT pro-reason: terminal win,
    material gained, the crown, and the proven shot setup.
    """
    board = CheckersBoard.from_fen("B:W18,26:B15")
    probe = _probe_for(board, "15x22x31")
    assert _fact_labels(probe) == {
        "pro:terminal_win",
        "pro:material:250",
        "pro:crown",
        "pro:shot_setup:250",
    }


@pytest.mark.unit
def test_move_winning_material() -> None:
    """A move winning material N: a forced double jump nets two men.

    ``B:W16,24:B11`` (Red) — the only legal move ``11x20x27`` captures White's
    men on 16 and 24 (weighted 200) and leaves White with no piece (terminal
    Red win). It is not a crowning move (27 is not Red's king-row).
    """
    board = CheckersBoard.from_fen("B:W16,24:B11")
    probe = _probe_for(board, "11x20x27")
    assert _fact_labels(probe) == {
        "pro:terminal_win",
        "pro:material:200",
        "pro:shot_setup:200",
    }


@pytest.mark.unit
def test_move_allows_opponent_a_shot() -> None:
    """A quiet move that allows the opponent a forced material shot.

    ``B:W22,30:B6,9,13,14`` (Red) — the quiet move ``13-17`` exposes a Red man:
    White then has a forced capture netting one man (weighted 100), Red
    surviving (non-terminal). The move must carry ``obj:allows_shot:100`` and
    the matching ``reply:material:100`` — and no pro-reason.
    """
    board = CheckersBoard.from_fen("B:W22,30:B6,9,13,14")
    probe = _probe_for(board, "13-17")
    assert _fact_labels(probe) == {
        "obj:allows_shot:100",
        "reply:material:100",
    }


@pytest.mark.unit
def test_move_loses_game_on_the_spot() -> None:
    """A move that loses the game by force.

    ``B:W22,30:B9,13`` (Red) — the quiet move ``13-17`` lets White force a
    double capture that removes both Red men: Red ends with no piece, a
    terminal White win. The move must carry ``obj:terminal_loss`` and the
    matching ``reply:terminal_loss``.
    """
    board = CheckersBoard.from_fen("B:W22,30:B9,13")
    probe = _probe_for(board, "13-17")
    assert _fact_labels(probe) == {
        "obj:terminal_loss",
        "reply:terminal_loss",
    }


@pytest.mark.unit
def test_crowning_move() -> None:
    """A crowning move: a man steps onto its king-row.

    ``B:W21:B27`` (Red) — the quiet move ``27-31`` advances a Red man onto
    king-row square 31, crowning it. White still has a piece, so the position
    is not terminal and there is no shot either way: the move carries exactly
    ``pro:crown``.
    """
    board = CheckersBoard.from_fen("B:W21:B27")
    probe = _probe_for(board, "27-31")
    assert _fact_labels(probe) == {"pro:crown"}


@pytest.mark.unit
def test_quiet_move_has_no_fact_witnesses() -> None:
    """A quiet move with NO FACT witnesses.

    ``B:W22,30:B6,9,13,14`` (Red) — the quiet move ``6-10`` does not capture,
    does not crown, ends no game and the resolver proves no forced shot for
    either side. It must carry an empty FACT witness set.
    """
    board = CheckersBoard.from_fen("B:W22,30:B6,9,13,14")
    probe = _probe_for(board, "6-10")
    assert _fact_labels(probe) == set()


@pytest.mark.unit
def test_quiet_opening_move_has_no_fact_witnesses() -> None:
    """Every opening move is quiet — no FACT witness in the start position."""
    board = CheckersBoard.initial()
    for probe in probe_moves(board):
        assert _fact_labels(probe) == set(), probe.pdn


# ---------------------------------------------------------------------------
# unit — loses_exchange (a capture that loses material by force)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_capture_that_loses_the_exchange() -> None:
    """A capture move forced into a net material loss.

    ``B:W10,17,18:B6,13,14`` (Red) — the capture ``13x22`` takes one White man
    (weighted 100) but White then force-captures back more: the opponent's
    forced reply nets White 250, so the mover's net swing across the whole
    forced line is 100 - 250 = -150. The move carries ``obj:loses_exchange:150``
    (a capture move, distinguished from ``allows_shot`` which is for quiet
    moves) and ``pro:material:100`` for the man the capture itself took, plus
    the opponent's forcing ``reply:material:250``.
    """
    board = CheckersBoard.from_fen("B:W10,17,18:B6,13,14")
    probe = _probe_for(board, "13x22")
    facts = _fact_labels(probe)
    assert "obj:loses_exchange:150" in facts
    assert "pro:material:100" in facts
    # The opponent's recapture is a proven forcing reply netting material.
    assert "reply:material:250" in facts
    # A capture move that loses the exchange is never tagged allows_shot.
    assert not any(lbl.startswith("obj:allows_shot") for lbl in facts)


@pytest.mark.unit
def test_even_capture_trade_is_not_loses_exchange() -> None:
    """A 1-for-1 even capture trade carries no ``loses_exchange`` objection.

    ``B:W7,23:B2,18`` (Red) — ``2x11`` captures White's man on 7 (weighted
    100); White's forced recapture nets White 100 back, so the mover's net
    swing across the line is 0 — an even trade, not a loss. The move keeps
    ``pro:material:100`` for the man it took but carries no ``loses_exchange``.
    """
    board = CheckersBoard.from_fen("B:W7,23:B2,18")
    probe = _probe_for(board, "2x11")
    facts = _fact_labels(probe)
    assert "pro:material:100" in facts
    assert not any(lbl.startswith("obj:loses_exchange") for lbl in facts)
    assert not any(lbl.startswith("obj:allows_shot") for lbl in facts)


@pytest.mark.unit
def test_defense_when_resolver_refutes_apparent_reply() -> None:
    """A ``defense`` when the resolver refutes an apparent opponent reply.

    ``B:W7,23:B2,18`` (Red) — after the capture ``2x11`` White has a forced
    recapture (a proven forcing ``reply`` netting White 100), but the resolver
    proves the mover's net swing across the whole line is 0 — the exchange is
    held even. The opponent's reply is therefore refuted, so the move carries
    a ``defense:holds_exchange@{answered}`` defense **keyed** to that exact
    reply (design §6 — a defense answers "the objection/reply it answers, and
    only that one").
    """
    board = CheckersBoard.from_fen("B:W7,23:B2,18")
    probe = _probe_for(board, "2x11")
    facts = _fact_labels(probe)
    # The defense is keyed to the reply it answers.
    assert "defense:holds_exchange@reply:material:100" in facts
    # The defense answers a genuine, proven forcing reply.
    assert "reply:material:100" in facts
    # The keyed defense names exactly the reply on the same probe.
    from dialectical_checkers.evidence import to_argument_evidence

    defense = next(d for d in probe.defenses if d.startswith("defense:"))
    assert to_argument_evidence(defense).answered == "reply:material:100"


# ---------------------------------------------------------------------------
# unit — curated king-capture and deep (3+ ply) forced-line witnesses
# ---------------------------------------------------------------------------
#
# The positions below are the king/deep shots independently hand-verified by
# ``scripts/verify_king_deep_shots.py`` (engine banded capture-minimax replayed
# move-by-move in pydraughts, terminal verdicts agreeing). Each test asserts
# the exact FACT witness set ``probe_moves()`` emits, so a witness-layer
# regression on king material, king multi-jumps, or deep forced lines is
# caught. The asserted labels were confirmed by
# ``scripts/phase3a_verify_king_witness_labels.py``.


@pytest.mark.unit
def test_king_single_capture_witnesses() -> None:
    """A lone Red KING captures a White man, ending the game.

    ``B:W18:BK15`` (Red) — Red's only legal move is the king capture
    ``15x22``: it takes White's last man (weighted 100), the king cannot be
    crowned again, and White is left with no piece — a terminal Red win. The
    move carries the terminal win, the captured material, and the proven shot
    setup.
    """
    board = CheckersBoard.from_fen("B:W18:BK15")
    probe = _probe_for(board, "15x22")
    assert _fact_labels(probe) == {
        "pro:terminal_win",
        "pro:material:100",
        "pro:shot_setup:100",
    }


@pytest.mark.unit
def test_king_double_jump_witnesses() -> None:
    """A Red KING multi-jump takes two White men in one chained capture.

    ``B:W7,15:BK2`` (Red) — the king's only move is the double jump
    ``2x11x18`` capturing both White men (weighted 200), leaving White with no
    piece — a terminal Red win. The move carries the terminal win, the 200 of
    captured material, and the proven shot setup of 200.
    """
    board = CheckersBoard.from_fen("B:W7,15:BK2")
    probe = _probe_for(board, "2x11x18")
    assert _fact_labels(probe) == {
        "pro:terminal_win",
        "pro:material:200",
        "pro:shot_setup:200",
    }


@pytest.mark.unit
def test_king_triple_jump_witnesses() -> None:
    """A Red KING triple jump takes three White men in one chained capture.

    ``B:W18,25,26:BK14`` (Red) — the king's only move is the triple jump
    ``14x23x30x21`` capturing all three White men (weighted 300), a terminal
    Red win. The move carries the terminal win, 300 of captured material, and
    the proven shot setup of 300.
    """
    board = CheckersBoard.from_fen("B:W18,25,26:BK14")
    probe = _probe_for(board, "14x23x30x21")
    assert _fact_labels(probe) == {
        "pro:terminal_win",
        "pro:material:300",
        "pro:shot_setup:300",
    }


@pytest.mark.unit
def test_deep_three_ply_forced_line_witnesses() -> None:
    """A genuine 3-ply forced line: capture, forced recapture, forced finish.

    ``B:WK15,22:B18,19,K27,31`` (Red) — Red plays the capture ``18x25``
    (weighted gain 100). The whole forced line is three plies: ``18x25``, then
    White's only move ``15x24`` (a forced king recapture), then Red's forced
    finish ``27x20`` (a king capture) leaving White with no piece — a terminal
    Red win, net swing 150 over the line.

    The opening move ``18x25`` carries ``pro:material:100`` for the man it
    itself takes and ``pro:shot_setup:150`` — the resolver proves the whole
    3-ply line nets the mover 150. It is not yet terminal, so no
    ``pro:terminal_win`` on this move.
    """
    board = CheckersBoard.from_fen("B:WK15,22:B18,19,K27,31")
    probe = _probe_for(board, "18x25")
    assert _fact_labels(probe) == {
        "pro:material:100",
        "pro:shot_setup:150",
    }
    # Walk the forced line: after 18x25 White's only move is the forced
    # recapture 15x24, after which Red's forced finish 27x20 wins the game.
    after_first = board.apply(
        {m.pdn(): m for m in board.legal_moves()}["18x25"]
    )
    white_moves = after_first.legal_moves()
    assert [m.pdn() for m in white_moves] == ["15x24"], [
        m.pdn() for m in white_moves
    ]
    # White's forced recapture loses the game by force: it carries the
    # terminal-loss objection and the matching terminal-loss reply attack.
    white_probe = _probe_for(after_first, "15x24")
    assert "obj:terminal_loss" in white_probe.objections
    assert "reply:terminal_loss" in white_probe.reply_attacks
    # Red's forced finish 27x20 is a king capture that ends the game.
    after_second = after_first.apply(white_moves[0])
    finish = _probe_for(after_second, "27x20")
    assert _fact_labels(finish) == {
        "pro:terminal_win",
        "pro:material:150",
        "pro:shot_setup:150",
    }


# ---------------------------------------------------------------------------
# differential — consistency with the verified forced-capture resolver
# ---------------------------------------------------------------------------
#
# A spread of positions: opening, forced single/double captures, quiet moves
# allowing shots, crowning, and the loses-exchange position. Every assertion
# below ties a witness to what the verified resolver actually returns.

CONSISTENCY_FENS: list[str] = [
    "B:W18,26:B15",
    "B:W16,24:B11",
    "B:W22,30:B6,9,13,14",
    "B:W22,30:B9,13",
    "B:W21:B27",
    "B:W7,23:B2,18",
    "B:W10,17,18:B6,13,14",
    "B:W18,22:B9,13,25,29",
    "W:W23:B18,27",
    # King-capture and deep (3+ ply) forced lines — verified by
    # scripts/verify_king_deep_shots.py; the curated assertions for these are
    # the king/deep witness tests above.
    "B:W18:BK15",
    "B:W7,15:BK2",
    "B:W18,25,26:BK14",
    "B:WK15,22:B18,19,K27,31",
]


@pytest.mark.differential
@pytest.mark.parametrize("fen", CONSISTENCY_FENS, ids=lambda v: v)
def test_allows_shot_iff_opponent_shot_on_quiet_move(fen: str) -> None:
    """``obj:allows_shot`` on a quiet move iff ``opponent_shot`` returns a shot.

    Restricted to quiet (non-capture) moves: a capture that loses material is
    a ``loses_exchange`` objection, not ``allows_shot`` — the two FACT
    objections partition the resolver-proven losing moves by ``move.is_jump``.
    """
    board = CheckersBoard.from_fen(fen)
    move_by_pdn = {m.pdn(): m for m in board.legal_moves()}
    for probe in probe_moves(board):
        move = move_by_pdn[probe.pdn]
        if move.is_jump:
            continue
        shot = opponent_shot(board, move)
        is_fact_material_shot = (
            shot is not None
            and shot.tier is ResolverTier.FACT
            and shot.terminal is None
        )
        has_allows_shot = any(
            lbl.startswith("obj:allows_shot") for lbl in probe.objections
        )
        assert has_allows_shot == is_fact_material_shot, (fen, probe.pdn)


@pytest.mark.differential
@pytest.mark.parametrize("fen", CONSISTENCY_FENS, ids=lambda v: v)
def test_shot_setup_iff_own_shot(fen: str) -> None:
    """``pro:shot_setup`` appears for a move iff ``own_shot`` returns a shot."""
    board = CheckersBoard.from_fen(fen)
    move_by_pdn = {m.pdn(): m for m in board.legal_moves()}
    for probe in probe_moves(board):
        move = move_by_pdn[probe.pdn]
        shot = own_shot(board, move)
        is_fact_shot = shot is not None and shot.tier is ResolverTier.FACT
        has_shot_setup = any(
            lbl.startswith("pro:shot_setup") for lbl in probe.reasons
        )
        assert has_shot_setup == is_fact_shot, (fen, probe.pdn)


@pytest.mark.differential
@pytest.mark.parametrize("fen", CONSISTENCY_FENS, ids=lambda v: v)
def test_terminal_win_iff_child_terminal_for_mover(fen: str) -> None:
    """``pro:terminal_win`` appears iff the move's child is terminal, mover wins.

    ``obj:terminal_loss`` correspondingly appears iff the resolver proves the
    move leads, by force, to a terminal position the opponent wins.
    """
    board = CheckersBoard.from_fen(fen)
    mover = board.turn
    move_by_pdn = {m.pdn(): m for m in board.legal_moves()}
    for probe in probe_moves(board):
        move = move_by_pdn[probe.pdn]
        child = board.apply(move)
        child_wins_for_mover = child.is_terminal() and child.winner() == mover
        has_terminal_win = "pro:terminal_win" in probe.reasons
        assert has_terminal_win == child_wins_for_mover, (fen, probe.pdn)

        shot = opponent_shot(board, move)
        proven_terminal_loss = (
            shot is not None
            and shot.tier is ResolverTier.FACT
            and shot.terminal is not None
            and shot.terminal != mover
        )
        has_terminal_loss = "obj:terminal_loss" in probe.objections
        assert has_terminal_loss == proven_terminal_loss, (fen, probe.pdn)


@pytest.mark.differential
@pytest.mark.parametrize("fen", CONSISTENCY_FENS, ids=lambda v: v)
def test_every_emitted_consistency_label_is_typed(fen: str) -> None:
    """Across the consistency sample every emitted witness is typed (design §5).

    Phase 4 emits HEURISTIC witnesses alongside FACT ones, so a label may be of
    either tier — this sanity-checks that every emitted label across the
    differential sample is *parseable typed evidence* (FACT or HEURISTIC),
    never an untyped/unknown string. The resolver-FACT tier discipline (no
    FACT witness from a truncated resolver) is proven separately by the
    monkeypatched truncation tests below.
    """
    board = CheckersBoard.from_fen(fen)
    for probe in probe_moves(board):
        for label in (
            *probe.reasons,
            *probe.objections,
            *probe.reply_attacks,
            *probe.defenses,
        ):
            assert to_argument_evidence(label).tier in (
                Tier.FACT,
                Tier.HEURISTIC,
            ), (fen, probe.pdn, label)


# ---------------------------------------------------------------------------
# unit — tier discipline: a truncated (HEURISTIC) resolver result never
# becomes a FACT witness. These DRIVE a ``Tier.HEURISTIC`` ``ShotResult``
# through ``probe_moves()`` by monkeypatching the resolver entry points
# ``witnesses.own_shot`` / ``witnesses.opponent_shot`` — so they exercise the
# tier guards at ``witnesses.py`` directly, and FAIL if either guard is
# removed. (The differential test above would still pass with the guards gone,
# because the sampled positions resolve within budget; that is the coverage
# gap these tests close.)
# ---------------------------------------------------------------------------
#
# ``witnesses.py`` imports ``own_shot`` / ``opponent_shot`` into its own module
# namespace, so the monkeypatch target is ``witnesses.own_shot`` /
# ``witnesses.opponent_shot`` — patching the names ``_probe_move`` actually
# calls.

# A capture move that, with a real resolver, loses the exchange (see
# ``test_capture_that_loses_the_exchange``) — used to drive ``own_shot``.
_CAPTURE_FEN = "B:W10,17,18:B6,13,14"
_CAPTURE_PDN = "13x22"
# A quiet move that, with a real resolver, allows a shot (see
# ``test_move_allows_opponent_a_shot``) — used to drive ``opponent_shot``.
_QUIET_FEN = "B:W22,30:B6,9,13,14"
_QUIET_PDN = "13-17"


def _shot(tier: ResolverTier, *, terminal: str | None = None) -> ShotResult:
    """A synthetic ``ShotResult`` with the given resolver ``tier``.

    ``material_net`` is a large, recognisably-synthetic positive value so any
    leaked witness derived from it is unmistakable in an assertion message.
    """
    return ShotResult(
        material_net=300,
        forced=True,
        truncated=tier is ResolverTier.HEURISTIC,
        terminal=terminal,
        tier=tier,
    )


@pytest.mark.unit
def test_heuristic_own_shot_yields_no_fact_shot_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A HEURISTIC ``own_shot`` result must NOT produce a ``pro:shot_setup``.

    Drives a truncated (``Tier.HEURISTIC``) resolver result through
    ``probe_moves()``: ``witnesses.own_shot`` is monkeypatched to return a
    HEURISTIC ``ShotResult``. The ``setup.tier is Tier.FACT`` guard in
    ``witnesses.py`` must suppress the ``pro:shot_setup`` reason — removing
    that guard makes this test fail.
    """
    monkeypatch.setattr(
        witnesses, "own_shot", lambda *a, **k: _shot(ResolverTier.HEURISTIC)
    )
    probe = _probe_for(CheckersBoard.from_fen(_CAPTURE_FEN), _CAPTURE_PDN)
    setups = [r for r in probe.reasons if r.startswith("pro:shot_setup")]
    assert setups == [], setups


@pytest.mark.unit
def test_fact_own_shot_does_produce_shot_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FACT control: a FACT ``own_shot`` DOES produce ``pro:shot_setup``.

    Confirms it is the *tier guard* — not merely the absence of any shot at
    that boundary — that suppresses the HEURISTIC case above. With an
    otherwise-identical FACT ``ShotResult`` the reason IS emitted.
    """
    monkeypatch.setattr(
        witnesses, "own_shot", lambda *a, **k: _shot(ResolverTier.FACT)
    )
    probe = _probe_for(CheckersBoard.from_fen(_CAPTURE_FEN), _CAPTURE_PDN)
    setups = [r for r in probe.reasons if r.startswith("pro:shot_setup")]
    assert setups == ["pro:shot_setup:300"], setups


@pytest.mark.unit
def test_heuristic_opponent_shot_yields_no_fact_objection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A HEURISTIC ``opponent_shot`` must NOT produce any FACT objection.

    Drives a truncated (``Tier.HEURISTIC``) resolver result through
    ``probe_moves()``: ``witnesses.opponent_shot`` is monkeypatched to return a
    HEURISTIC ``ShotResult``. The ``shot.tier is Tier.FACT`` guard in
    ``witnesses.py`` must suppress every **FACT** objection, reply attack, and
    defense derived from the resolver — removing that guard makes this test
    fail.

    The assertion is on the FACT-tier witnesses only: a HEURISTIC
    ``opponent_shot`` may still leave HEURISTIC objections standing (notably
    ``obj:exposes_man``, which fires precisely *because* the resolver did not
    prove a FACT shot — design §5). Phase 4 added those; the resolver-FACT
    discipline this test guards is unchanged.
    """
    monkeypatch.setattr(
        witnesses,
        "opponent_shot",
        lambda *a, **k: _shot(ResolverTier.HEURISTIC),
    )
    probe = _probe_for(CheckersBoard.from_fen(_QUIET_FEN), _QUIET_PDN)
    derived = [*probe.objections, *probe.reply_attacks, *probe.defenses]
    fact_derived = [
        label
        for label in derived
        if to_argument_evidence(label).tier is Tier.FACT
    ]
    assert fact_derived == [], fact_derived


@pytest.mark.unit
def test_fact_opponent_shot_does_produce_objection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FACT control: a FACT ``opponent_shot`` DOES produce a FACT objection.

    Confirms it is the *tier guard* — not the absence of any shot at that
    boundary — that suppresses the HEURISTIC case above. With an
    otherwise-identical FACT ``ShotResult`` the quiet move carries
    ``obj:allows_shot`` and the matching ``reply:material``.
    """
    monkeypatch.setattr(
        witnesses,
        "opponent_shot",
        lambda *a, **k: _shot(ResolverTier.FACT),
    )
    probe = _probe_for(CheckersBoard.from_fen(_QUIET_FEN), _QUIET_PDN)
    derived = [*probe.objections, *probe.reply_attacks, *probe.defenses]
    assert "obj:allows_shot:300" in derived, derived
    assert "reply:material:300" in derived, derived


@pytest.mark.unit
def test_heuristic_resolver_result_emits_no_fact_witness_anywhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With BOTH resolver entry points HEURISTIC, no FACT witness leaks.

    Both ``witnesses.own_shot`` and ``witnesses.opponent_shot`` are
    monkeypatched to return HEURISTIC ``ShotResult`` objects. No
    resolver-derived FACT witness (``pro:shot_setup``, ``obj:allows_shot``,
    ``obj:loses_exchange``, ``obj:terminal_loss``, ``reply:...``,
    ``defense:...``) may appear on ANY probe — only the non-resolver reasons
    (``pro:material``, ``pro:crown``, ``pro:terminal_win``) survive.
    """
    monkeypatch.setattr(
        witnesses, "own_shot", lambda *a, **k: _shot(ResolverTier.HEURISTIC)
    )
    monkeypatch.setattr(
        witnesses,
        "opponent_shot",
        lambda *a, **k: _shot(ResolverTier.HEURISTIC),
    )
    resolver_prefixes = (
        "pro:shot_setup",
        "obj:allows_shot",
        "obj:loses_exchange",
        "obj:terminal_loss",
        "reply:",
        "defense:",
    )
    for fen in (_CAPTURE_FEN, _QUIET_FEN):
        for probe in probe_moves(CheckersBoard.from_fen(fen)):
            for label in _all_labels(probe):
                assert not label.startswith(resolver_prefixes), (
                    fen,
                    probe.pdn,
                    label,
                )


# ---------------------------------------------------------------------------
# unit — HEURISTIC-tier witnesses (design §5, Phase 4)
# ---------------------------------------------------------------------------
#
# Each test below is a curated, hand-verified position exercising one HEURISTIC
# witness against its precise definition (see the ``witnesses.py`` module
# docstring). The positions were independently hand-verified by the
# ``scripts/phase4_*`` smoke / search scripts. A HEURISTIC witness is a
# positional judgement — it carries no oracle proof — but its firing condition
# is deterministic, and these tests pin that exact condition.


def _heuristic_labels(probe: MoveProbe) -> set[str]:
    """The set of HEURISTIC-tier witness labels on ``probe``."""
    return {
        label
        for label in _all_labels(probe)
        if to_argument_evidence(label).tier is Tier.HEURISTIC
    }


# --- pro:opposition / obj:loses_opposition (TEMPO) -------------------------


@pytest.mark.unit
def test_opposition_held_by_side_to_move() -> None:
    """``pro:opposition`` fires when the mover holds the opposition.

    ``B:WK4:BK15`` (Red) — a 1-king-v-1-king equal-force ending, the only case
    the pairing-off opposition is unambiguous. The kings' Chebyshev separation
    is 3 (odd), so the side to move (Red) holds the opposition; every Red move
    reaches a position whose opposition Red still holds. ``pro:opposition``
    must appear on every Red move.
    """
    board = CheckersBoard.from_fen("B:WK4:BK15")
    probes = probe_moves(board)
    assert probes, "expected legal moves"
    for probe in probes:
        assert "pro:opposition" in probe.reasons, probe.pdn


@pytest.mark.unit
def test_opposition_not_held_by_side_to_move() -> None:
    """``pro:opposition`` is silent when the opponent holds the opposition.

    ``B:WK8:BK15`` (Red) — the kings' Chebyshev separation is 2 (even), so the
    side NOT to move (White) holds the opposition; Red cannot seize it. No Red
    move may carry ``pro:opposition``.
    """
    board = CheckersBoard.from_fen("B:WK8:BK15")
    for probe in probe_moves(board):
        assert "pro:opposition" not in probe.reasons, probe.pdn


@pytest.mark.unit
def test_opposition_silent_when_more_than_one_piece_a_side() -> None:
    """The opposition witnesses are silent outside the 1-v-1 equal-force case.

    With more than one piece per side the pairing-off method is ambiguous
    (Pask), so neither ``pro:opposition`` nor ``obj:loses_opposition`` may
    fire — the witness makes no claim rather than an arbitrary one.
    ``B:W22,30:B6,9,13,14`` (Red) has many pieces a side.
    """
    board = CheckersBoard.from_fen("B:W22,30:B6,9,13,14")
    for probe in probe_moves(board):
        assert "pro:opposition" not in probe.reasons, probe.pdn
        assert "obj:loses_opposition" not in probe.objections, probe.pdn


@pytest.mark.unit
def test_opposition_silent_on_unequal_force_one_piece_a_side() -> None:
    """The opposition witnesses are silent for a 1-piece-per-side unequal force.

    One piece per side is necessary but NOT sufficient — the pairing-off method
    is unambiguous only when the forces are *equal* (Pask: "in any position
    where the forces are equal"), i.e. the two lone pieces are the same type.
    ``B:WK10:B15`` (Red) is one piece each but a *man vs a king* — unequal
    force. Neither ``pro:opposition`` nor ``obj:loses_opposition`` may fire;
    the witness makes no claim rather than apply a parity rule outside its
    defined case.
    """
    board = CheckersBoard.from_fen("B:WK10:B15")
    probes = probe_moves(board)
    assert probes, "expected legal moves"
    for probe in probes:
        assert "pro:opposition" not in probe.reasons, probe.pdn
        assert "obj:loses_opposition" not in probe.objections, probe.pdn


@pytest.mark.unit
def test_loses_opposition_fires_when_move_lands_in_lost_ending() -> None:
    """``obj:loses_opposition`` fires — the mirror of ``pro:opposition``.

    ``B:WK8:BK15`` (Red) — a 1-king-v-1-king equal-force ending; the kings'
    Chebyshev separation is 2 (even), so the side NOT to move (White) holds the
    opposition. Every Red move reaches a 1-king-v-1-king ending whose
    opposition White still holds — Red is the side in zugzwang — so every Red
    move carries ``obj:loses_opposition`` and none carries ``pro:opposition``.
    The move ``15-18`` is a quiet, non-terminal move: a genuine, reachable
    firing case (the witness is not dead).
    """
    board = CheckersBoard.from_fen("B:WK8:BK15")
    probes = probe_moves(board)
    assert probes, "expected legal moves"
    for probe in probes:
        assert "obj:loses_opposition" in probe.objections, probe.pdn
        assert "pro:opposition" not in probe.reasons, probe.pdn
    # the firing move 15-18 is a quiet (non-capture), non-terminal move.
    quiet = _probe_for(board, "15-18")
    assert "obj:loses_opposition" in quiet.objections
    move = next(m for m in board.legal_moves() if m.pdn() == "15-18")
    assert not move.is_jump
    assert not board.apply(move).is_terminal()


# --- pro:back_rank_hold / obj:back_rank_break (STRUCTURE) -------------------


@pytest.mark.unit
def test_back_rank_hold_and_break() -> None:
    """``pro:back_rank_hold`` / ``obj:back_rank_break`` on the home rank.

    ``W:W29,32,18:B6`` (White) — White's home rank is row 7 (squares 29-32);
    it starts with two men there (29 and 32). A move of the spare man
    (``18-14``) keeps both home-rank men: ``pro:back_rank_hold`` fires. A move
    of a home-rank man (``29-25``) drops the home-rank count from 2 to 1:
    ``obj:back_rank_break`` fires and ``pro:back_rank_hold`` does not.
    """
    board = CheckersBoard.from_fen("W:W29,32,18:B6")
    hold = _probe_for(board, "18-14")
    assert "pro:back_rank_hold" in hold.reasons
    assert "obj:back_rank_break" not in hold.objections

    brk = _probe_for(board, "29-25")
    assert "obj:back_rank_break" in brk.objections
    assert "pro:back_rank_hold" not in brk.reasons


@pytest.mark.unit
def test_back_rank_witnesses_ignore_kings_on_home_rank() -> None:
    """The back-rank witnesses count only MEN — kings on the home rank are not
    guards.

    ``W:WK29,K32,18:B6`` (White) — White's home rank is row 7 (squares 29-32);
    here both home-rank pieces (29 and 32) are *kings*, not men. A king on the
    home rank is a mobile crowned piece, not an unmoved back-rank guard, so:

    * moving the spare man ``18-14`` leaves zero home-rank *men* —
      ``pro:back_rank_hold`` must NOT fire (it would, wrongly, if kings were
      counted);
    * moving a home-rank *king* ``29-25`` is not a man leaving the home rank —
      ``obj:back_rank_break`` must NOT fire.
    """
    board = CheckersBoard.from_fen("W:WK29,K32,18:B6")
    hold = _probe_for(board, "18-14")
    assert "pro:back_rank_hold" not in hold.reasons

    king_move = _probe_for(board, "29-25")
    assert "obj:back_rank_break" not in king_move.objections


# --- pro:center:{n} (STRUCTURE) --------------------------------------------


@pytest.mark.unit
def test_center_occupation_gained() -> None:
    """``pro:center:{n}`` fires when a move increases central-square occupation.

    ``B:W30:B10`` (Red) — the central squares are {14, 15, 18, 19}. The move
    ``10-14`` puts a Red man on central square 14; Red's central count rises
    from 0 to 1, so the move carries ``pro:center:1``.
    """
    board = CheckersBoard.from_fen("B:W30:B10")
    probe = _probe_for(board, "10-14")
    assert "pro:center:1" in probe.reasons


@pytest.mark.unit
def test_center_silent_when_occupation_not_increased() -> None:
    """``pro:center`` is silent when a move does not gain a central square.

    ``B:W30:B14`` (Red) — the Red man is already on central square 14; moving
    it OFF the centre (``14-17``) does not increase central occupation, so no
    ``pro:center`` label is emitted.
    """
    board = CheckersBoard.from_fen("B:W30:B14")
    probe = _probe_for(board, "14-17")
    assert not any(r.startswith("pro:center") for r in probe.reasons)


# --- pro:mobility:{n} (MOBILITY) -------------------------------------------


@pytest.mark.unit
def test_mobility_gain_is_emitted_with_count() -> None:
    """``pro:mobility:{n}`` carries the move's relative mobility gain.

    The witness fires iff the opponent's legal-move count after the move is
    strictly below the mover's legal-move count at the root; ``{n}`` is that
    positive difference. Checked directly against ``board.legal_moves()``.
    """
    board = CheckersBoard.from_fen("B:W22,30:B6,9,13,14")
    mover_root_moves = len(board.legal_moves())
    move_by = {m.pdn(): m for m in board.legal_moves()}
    for probe in probe_moves(board):
        opponent_moves = len(board.apply(move_by[probe.pdn]).legal_moves())
        gain = mover_root_moves - opponent_moves
        mobility = [r for r in probe.reasons if r.startswith("pro:mobility:")]
        if gain > 0:
            assert mobility == [f"pro:mobility:{gain}"], probe.pdn
        else:
            assert mobility == [], probe.pdn


# --- pro:formation:{kind} (STRUCTURE) --------------------------------------


@pytest.mark.unit
def test_formation_phalanx() -> None:
    """``pro:formation:phalanx`` — the moved piece gains a same-rank neighbour.

    ``B:W22,30:B6,9,13,14`` (Red) — the move ``6-10`` lands a Red man on
    square 10 (row 2); Red already has a man on square 9 (row 2, the adjacent
    dark square). The two men stand side by side on the same rank — a phalanx.
    """
    board = CheckersBoard.from_fen("B:W22,30:B6,9,13,14")
    probe = _probe_for(board, "6-10")
    assert "pro:formation:phalanx" in probe.reasons


@pytest.mark.unit
def test_formation_echelon() -> None:
    """``pro:formation:echelon`` — the moved piece joins a 3-piece diagonal.

    ``B:W30:B1,10,15`` (Red) — the move ``1-6`` places a Red man on square 6;
    Red then has men on 6, 10, 15 — a run of three on one diagonal (each one
    king-step from the next). The move carries ``pro:formation:echelon``.
    """
    board = CheckersBoard.from_fen("B:W30:B1,10,15")
    probe = _probe_for(board, "1-6")
    assert "pro:formation:echelon" in probe.reasons


@pytest.mark.unit
def test_formation_bridge_maintained() -> None:
    """``pro:formation:bridge`` — a move that keeps both home-rank bridge squares.

    ``W:W29,31,18:B6`` (White) — White occupies both of its home-rank bridge
    squares (29 and 31). Moving the spare man (``18-14``) keeps the bridge
    intact: ``pro:formation:bridge`` fires. Moving a bridge man (``29-25``)
    breaks the bridge: no ``pro:formation:bridge``.
    """
    board = CheckersBoard.from_fen("W:W29,31,18:B6")
    kept = _probe_for(board, "18-14")
    assert "pro:formation:bridge" in kept.reasons

    broken = _probe_for(board, "29-25")
    assert "pro:formation:bridge" not in broken.reasons


# --- obj:single_corner_drift (STRUCTURE) -----------------------------------


@pytest.mark.unit
def test_single_corner_drift() -> None:
    """``obj:single_corner_drift`` — a man driven into the single corner.

    ``B:W21:B3`` (Red) — Red's single-corner squares are {4, 8} (the cramped
    true-grid-corner region near square 4). The move ``3-8`` steps a Red man
    into the single corner: ``obj:single_corner_drift`` fires. The move
    ``3-7`` (destination 7, not a single-corner square) does not.
    """
    board = CheckersBoard.from_fen("B:W21:B3")
    drift = _probe_for(board, "3-8")
    assert "obj:single_corner_drift" in drift.objections

    no_drift = _probe_for(board, "3-7")
    assert "obj:single_corner_drift" not in no_drift.objections


# --- obj:exposes_man (MATERIAL, HEURISTIC) ---------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "fen,pdn",
    [
        ("B:W13,16:B8,9", "8-12"),
        ("B:W14,18:B9,11", "11-15"),
        ("B:W15,18:B9,11", "9-14"),
    ],
)
def test_exposes_man_when_loss_not_proven(fen: str, pdn: str) -> None:
    """``obj:exposes_man`` — a piece left en prise with the loss not proven.

    Each curated position: a quiet move after which the opponent has a legal
    capture (a mover piece is capturable) but the forced-capture resolver
    proves no fact-tier shot — the mover recaptures, so the man only *looks*
    loose. The move carries ``obj:exposes_man`` and no FACT objection.
    """
    board = CheckersBoard.from_fen(fen)
    probe = _probe_for(board, pdn)
    assert "obj:exposes_man" in probe.objections
    # The HEURISTIC objection is only emitted when no FACT objection covers
    # the move — the FACT objection would supersede it (design §5).
    fact_objs = [
        o for o in probe.objections if to_argument_evidence(o).tier is Tier.FACT
    ]
    assert fact_objs == [], fact_objs


@pytest.mark.unit
def test_exposes_man_suppressed_by_fact_objection() -> None:
    """``obj:exposes_man`` is suppressed when a FACT objection already covers it.

    ``B:W22,30:B6,9,13,14`` (Red) — the quiet move ``13-17`` lets White force a
    proven material shot: the move carries the FACT ``obj:allows_shot:100``.
    The FACT objection supersedes the HEURISTIC one, so ``obj:exposes_man``
    must NOT also appear (design §5 — the tier is decided by what the resolver
    proved).
    """
    board = CheckersBoard.from_fen("B:W22,30:B6,9,13,14")
    probe = _probe_for(board, "13-17")
    assert "obj:allows_shot:100" in probe.objections
    assert "obj:exposes_man" not in probe.objections


@pytest.mark.unit
def test_exposes_man_silent_when_exposed_piece_is_a_king() -> None:
    """``obj:exposes_man`` does not fire when the en-prise piece is a KING.

    ``B:WK18,19:B3,8,K13,K17,K20,K30`` (Red) — the move ``17-14`` walks the
    Red KING on 17 to square 14, where White's king on 18 can capture it
    (``18x9``). The piece left capturable is a *king*, not a man — the label
    and design §5 row are "man capturable", so ``obj:exposes_man`` must NOT
    fire (an exposed king is a materially different fact).
    """
    board = CheckersBoard.from_fen("B:WK18,19:B3,8,K13,K17,K20,K30")
    probe = _probe_for(board, "17-14")
    assert "obj:exposes_man" not in probe.objections
    # the opponent does have a capture after the move — it is the king-vs-man
    # distinction, not the absence of a capture, that keeps the witness silent.
    child = board.apply(
        next(m for m in board.legal_moves() if m.pdn() == "17-14")
    )
    assert any(m.is_jump for m in child.legal_moves())


# --- differential — every emitted HEURISTIC label is HEURISTIC-tier --------


@pytest.mark.differential
@pytest.mark.parametrize(
    "fen",
    [
        "B:WK4:BK15",
        "B:WK8:BK15",
        "W:W29,32,18:B6",
        "B:W30:B10",
        "B:W22,30:B6,9,13,14",
        "B:W13,16:B8,9",
        "B:W30:B1,10,15",
        "W:W29,31,18:B6",
        "B:W21:B3",
    ],
    ids=lambda v: v,
)
def test_heuristic_witnesses_are_typed_heuristic(fen: str) -> None:
    """Every HEURISTIC label a probe emits parses to ``Tier.HEURISTIC``.

    The mirror of the FACT-tier consistency check: a HEURISTIC witness must
    always be typed HEURISTIC by ``evidence.py`` — never silently mistyped as
    FACT (which would let it leak into the crisp argument layer).
    """
    board = CheckersBoard.from_fen(fen)
    for probe in probe_moves(board):
        for label in _heuristic_labels(probe):
            assert to_argument_evidence(label).tier is Tier.HEURISTIC, (
                fen,
                probe.pdn,
                label,
            )
