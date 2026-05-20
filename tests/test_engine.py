"""Phase 3b — tests for ``dialectical_checkers.engine`` (the engine that PLAYS).

The engine orchestration (design ``notes/checkers-design.md`` §6-7):
``probe_moves`` -> ``build_root_argument_graph`` (crisp Dung layer) -> the
FACT-tier selector -> an ``EngineDecision``.

Four test families, mirroring the directive:

* ``unit`` — contract tests on ``analyze`` / ``choose_move``: a terminal
  position yields a null decision; a chosen move is always one of the probed
  moves; the analysis carries the crisp graph.
* ``property`` — LEGALITY: across >=300 deterministic-seeded reached positions
  with legal moves, ``choose_move`` returns a move in ``legal_moves()``.
* ``property`` — NO AVOIDABLE FORCED LOSS: across >=200 seeded positions, if
  some legal move avoids giving the opponent a forced material/game win, the
  engine must pick such a move. The "forced loss" classifier is the verified
  Phase-2 forced-capture resolver (``captures.opponent_shot``) — an INDEPENDENT
  oracle of the loss, not the engine's own selection.
* ``differential`` — the curated tactical corpus: >=8 positions with a free
  winning shot/capture (the engine must take it) and >=6 positions where some
  moves lose and others are safe (the engine must pick a safe one). Every
  curated position's classification was verified against the resolver and
  pydraughts by ``scripts/phase3b_confirm_corpus.py``.

The resolver is the verified tactical spine; pydraughts is not imported here —
the curated corpus's independence comes from ``phase3b_confirm_corpus.py``,
which cross-checked every curated FEN against pydraughts' own move generator.
"""

from __future__ import annotations

import random

import pytest

from dialectical_checkers import (
    DialecticalCheckersEngine,
    EngineAnalysis,
    EngineDecision,
)
from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.captures import Tier, opponent_shot


# ---------------------------------------------------------------------------
# helpers
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


def _seeded_positions(target: int) -> list[CheckersBoard]:
    """At least ``target`` distinct non-terminal positions, deterministically.

    Walks deterministic random games from the standard opening with many seeds
    and varied depths, so the sample spans openings, post-exchange midgames and
    capture-rich tactical positions. Terminal positions (no legal move) are
    excluded — the property tests are about *choosing* a move.
    """
    seen: set[str] = set()
    out: list[CheckersBoard] = []
    seed = 0
    while len(out) < target:
        for depth in (8, 16, 24, 32, 44):
            for board in _reachable_boards(seed, depth):
                if not board.legal_moves():
                    continue
                fen = board.to_fen()
                if fen in seen:
                    continue
                seen.add(fen)
                out.append(board)
        seed += 1
        if seed > 5_000:  # safety — should never be hit
            break
    return out


def _gives_opponent_forced_win(board: CheckersBoard, move: CheckersMove) -> bool:
    """True iff ``move`` hands the opponent a forced material/game win.

    The classifier is INDEPENDENT of the engine's selection: it applies
    ``move`` and asks the verified Phase-2 forced-capture resolver
    (``captures.opponent_shot``) whether the opponent then has a *proven*
    (``Tier.FACT``) forced sequence netting material or winning the game.

    A truncated (``Tier.HEURISTIC``) resolver result is NOT treated as a
    forced loss — it was not proven, and the engine is judged only on proven
    losses (honest about what the resolver established).
    """
    shot = opponent_shot(board, move)
    if shot is None or shot.tier is not Tier.FACT:
        return False
    mover = board.turn
    wins_game = shot.terminal is not None and shot.terminal != mover
    wins_material = shot.terminal is None and shot.material_net > 0
    return wins_game or wins_material


# ---------------------------------------------------------------------------
# unit — engine contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_terminal_position_yields_null_decision() -> None:
    """A position with no legal move yields a null decision — the game is over.

    ``B:W18:B`` — Red to move with no Red piece: no legal move, the game is
    over. ``choose_move`` returns an empty ``move_pdn`` and ``selected`` is
    ``None``.
    """
    board = CheckersBoard.from_fen("B:W18:B")
    assert board.is_terminal()
    engine = DialecticalCheckersEngine()
    decision: EngineDecision = engine.choose_move(board)
    assert decision.move_pdn == ""
    assert decision.selected is None
    assert decision.score is None


@pytest.mark.unit
def test_analyze_returns_graph_and_decision() -> None:
    """``analyze`` returns the probes, the crisp graph, and a decision."""
    engine = DialecticalCheckersEngine()
    board = CheckersBoard.initial()
    analysis: EngineAnalysis = engine.analyze(board)
    assert len(analysis.probes) == len(board.legal_moves())
    # The crisp graph has one move: argument per probed move.
    assert len(analysis.graph.move_arguments) == len(analysis.probes)
    assert analysis.decision.move_pdn in {m.pdn() for m in board.legal_moves()}


@pytest.mark.unit
def test_chosen_move_is_one_of_the_probed_moves() -> None:
    """The chosen move is always one of the probed legal moves."""
    engine = DialecticalCheckersEngine()
    for fen in (
        "B:W18,26:B15",
        "B:W22,30:B9,13",
        "B:W21:B27",
        "W:WK10:B5",
    ):
        board = CheckersBoard.from_fen(fen)
        analysis = engine.analyze(board)
        probed = {p.pdn for p in analysis.probes}
        assert analysis.decision.move_pdn in probed, fen


@pytest.mark.unit
def test_choose_move_is_deterministic() -> None:
    """Repeated ``choose_move`` on the same position returns the same move."""
    engine = DialecticalCheckersEngine()
    board = CheckersBoard.from_fen("B:W18,21,22,25,26,29,31,32:B1,2,3,4,5,6,7,9,19,28")
    first = engine.choose_move(board).move_pdn
    for _ in range(5):
        assert engine.choose_move(board).move_pdn == first


# ---------------------------------------------------------------------------
# property — LEGALITY
# ---------------------------------------------------------------------------


@pytest.mark.property
def test_engine_never_plays_an_illegal_move() -> None:
    """For >=300 seeded reached positions the chosen move is legal.

    The single most basic gate (design §10 / port-plan §8): the engine never
    plays an illegal move.
    """
    engine = DialecticalCheckersEngine()
    positions = _seeded_positions(300)
    assert len(positions) >= 300
    for board in positions:
        legal = {m.pdn() for m in board.legal_moves()}
        chosen = engine.choose_move(board).move_pdn
        assert chosen in legal, (board.to_fen(), chosen, sorted(legal))


# ---------------------------------------------------------------------------
# property — NO AVOIDABLE FORCED LOSS
# ---------------------------------------------------------------------------


@pytest.mark.property
def test_engine_never_plays_an_avoidable_forced_loss() -> None:
    """For >=200 seeded positions the engine never plays an avoidable loss.

    For each position: classify every legal move with the INDEPENDENT verified
    resolver (``_gives_opponent_forced_win``). If at least one legal move does
    NOT give the opponent a forced material/game win, the engine's chosen move
    must be one of those safe moves. The engine may pick a losing move only
    when *every* legal move loses (design §10 gate).
    """
    engine = DialecticalCheckersEngine()
    positions = _seeded_positions(200)
    assert len(positions) >= 200
    checked_with_safe_option = 0
    for board in positions:
        moves = board.legal_moves()
        losing = {
            m.pdn(): _gives_opponent_forced_win(board, m) for m in moves
        }
        safe = [pdn for pdn, lost in losing.items() if not lost]
        if not safe:
            # Every move loses by force — the engine cannot avoid it.
            continue
        checked_with_safe_option += 1
        chosen = engine.choose_move(board).move_pdn
        assert not losing[chosen], (
            board.to_fen(),
            chosen,
            "engine played an avoidable forced loss; safe moves were",
            sorted(safe),
        )
    # The seeded sample must actually contain positions with a safe option,
    # else the assertion above is vacuous.
    assert checked_with_safe_option >= 50, checked_with_safe_option


# ---------------------------------------------------------------------------
# differential — curated tactical corpus
# ---------------------------------------------------------------------------
#
# Every curated position below was classified against the verified
# forced-capture resolver AND cross-checked against pydraughts' own
# legal-move generator by ``scripts/phase3b_confirm_corpus.py`` — the engine's
# chosen move was confirmed correct and legal on every one.

# >=8 positions with a free winning shot / winning capture — the side to move
# can win the game or win material by force, and the engine must take it. The
# value is the PDN of the winning move (for the single-legal-move positions it
# is the only move; for the multi-move positions it is the proven winner).
WINNING_SHOT_CORPUS: list[tuple[str, str]] = [
    ("B:W18,26:B15", "15x22x31"),
    ("B:W16,24:B11", "11x20x27"),
    ("B:W18:BK15", "15x22"),
    ("B:W7,15:BK2", "2x11x18"),
    ("B:W18,25,26:BK14", "14x23x30x21"),
    ("B:W14:B10", "10x17"),
    ("B:W16,21,22,24,25,27,28,29,30,31,32:B1,2,3,4,5,7,8,11,12,14", "11x20"),
    ("B:W11,19,21,22,25,26,29,30,31,32:B1,2,3,4,5,6,7,8,12", "8x15x24"),
    (
        "B:W10,19,21,23,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,12,15,16",
        "7x14",
    ),
    ("W:W21,22,23,24,25,27,28,29,30,31,32:B1,2,3,4,5,7,8,11,12,14,19", "24x15"),
]

# >=6 positions where some legal moves lose (by force, proven) and others are
# safe — the engine must pick a safe one. The value is the set of LOSING move
# PDNs; the engine's chosen move must NOT be in it.
SAFE_VS_LOSING_CORPUS: list[tuple[str, frozenset[str]]] = [
    ("B:W22,30:B9,13", frozenset({"13-17"})),
    (
        "W:W18,21,22,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,11,19",
        frozenset({"18-14", "28-24"}),
    ),
    (
        "B:W18,21,22,25,26,29,31,32:B1,2,3,4,5,6,7,9,19,28",
        frozenset({"19-23"}),
    ),
    (
        "W:W18,21,22,25,26,29,31,32:B1,2,3,4,5,7,9,10,19,28",
        frozenset({"26-23"}),
    ),
    (
        "B:W18,21,22,23,25,29,31:B1,3,4,5,6,7,9,10,26,28",
        frozenset({"9-14", "10-15"}),
    ),
    (
        "W:W17,18,22,23,25,29,31:B1,4,5,6,8,9,10,11,26,28",
        frozenset({"18-14", "18-15"}),
    ),
]


@pytest.mark.differential
@pytest.mark.parametrize(
    ("fen", "winning_move"), WINNING_SHOT_CORPUS, ids=lambda v: str(v)
)
def test_engine_takes_the_free_winning_shot(fen: str, winning_move: str) -> None:
    """On a free-winning-shot position the engine takes the winning move."""
    engine = DialecticalCheckersEngine()
    board = CheckersBoard.from_fen(fen)
    legal = {m.pdn() for m in board.legal_moves()}
    assert winning_move in legal, (fen, winning_move, sorted(legal))
    chosen = engine.choose_move(board).move_pdn
    assert chosen == winning_move, (fen, chosen, winning_move)


@pytest.mark.differential
def test_winning_shot_corpus_has_at_least_eight_positions() -> None:
    """The directive requires >=8 free-winning-shot positions."""
    assert len(WINNING_SHOT_CORPUS) >= 8


@pytest.mark.differential
@pytest.mark.parametrize(
    ("fen", "losing_moves"), SAFE_VS_LOSING_CORPUS, ids=lambda v: str(v)
)
def test_engine_picks_a_safe_move(fen: str, losing_moves: frozenset[str]) -> None:
    """On a safe-vs-losing position the engine picks a move that is not losing.

    The losing moves were proven losing by the verified resolver; the position
    has at least one safe move (confirmed by ``phase3b_confirm_corpus.py``).
    The engine's chosen move must not be one of the proven losers.
    """
    engine = DialecticalCheckersEngine()
    board = CheckersBoard.from_fen(fen)
    legal = {m.pdn() for m in board.legal_moves()}
    # Sanity: the named losing moves are genuinely legal, and a safe move exists.
    assert losing_moves <= legal, (fen, losing_moves, sorted(legal))
    assert legal - losing_moves, (fen, "no safe move in corpus position")
    chosen = engine.choose_move(board).move_pdn
    assert chosen not in losing_moves, (fen, chosen, sorted(losing_moves))


@pytest.mark.differential
def test_safe_vs_losing_corpus_has_at_least_six_positions() -> None:
    """The directive requires >=6 safe-vs-losing positions."""
    assert len(SAFE_VS_LOSING_CORPUS) >= 6
