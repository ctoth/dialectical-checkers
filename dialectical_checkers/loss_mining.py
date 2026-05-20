"""Loss turning-point mining — the Phase 7 diagnostic.

Ported in shape from ``dialectical_chess/loss_mining.py`` and rebuilt for
checkers (port-plan §6 — "rewrite ``loss_mining.py`` ``has_forced_mate`` as a
forced-win search"; §8 Phase 7). Given a game the engine **lost**, it finds the
*turning point* — the ply at which the engine played a move that turned a
non-losing position into a losing one.

In chess, "losing" was characterised as "the opponent can force mate". In
checkers the analog is sharper and *provable*: captures are mandatory, so
:func:`dialectical_checkers.captures.opponent_shot` resolves — exactly, within
the recursion budget — whether a move hands the opponent a forced sequence that
nets material or the game. That fact-tier (``Tier.FACT``) resolver IS the
classifier the Phase 7 directive calls for; this module does not re-implement
search, it consumes the verified one.

The turning point of a lost game is the **first** engine ply whose move
:func:`move_allows_shot` flags — the engine had a quiet position, played a move,
and after it the opponent has a proven forced shot. That is the move that "made
a non-losing move a losing one". If no such ply exists (the engine was already
losing from the start position, or the loss came only from slow positional
attrition the resolver cannot see), the turning point is ``None`` and the
diagnostic reports that honestly rather than inventing one.

This module is **evaluation tooling**; it imports only ``dialectical_checkers``
+ the stdlib and changes no verified Phase 0-6 behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass

from dialectical_checkers.board import CheckersBoard, CheckersMove
from dialectical_checkers.captures import ShotResult, opponent_shot
from dialectical_checkers.match import DRAW, RED_WIN, GameResult


@dataclass(frozen=True)
class LossTurningPoint:
    """The ply at which the engine's game turned from non-losing to losing.

    ``game_index`` identifies the game within a batch (1-based; ``1`` for a
    single game). ``ply`` is the 1-based half-move number of the blunder.
    ``fen_before`` is the position *before* the blunder move, ``played_move``
    the blunder in PDN notation, ``side`` the engine's colour (``"r"`` / ``"w"``)
    on that ply. ``shot_material_net`` is the weighted material the opponent's
    forced reply nets (the proven cost of the blunder); ``shot_wins_game`` is
    True iff that forced sequence wins the game outright. ``safe_alternatives``
    lists the PDN moves that were legal in ``fen_before`` and did *not* concede
    a shot — moves the engine could have played instead.

    ``was_avoidable`` is the load-bearing honesty field. It is True iff, at
    ``ply``, the engine had at least one legal move that conceded NO shot — so
    the loss at this ply was a genuine choice. It is False iff every legal move
    at ``ply`` conceded a shot (typically because all legal moves were
    mandatory captures): the position was *already* lost before this ply, and
    this is merely the first ply where the loss became resolvable — the true
    blunder happened earlier, on a quiet move the resolver cannot see. The
    diagnostic reports this distinction rather than blaming a forced move.
    """

    game_index: int
    ply: int
    fen_before: str
    played_move: str
    side: str
    shot_material_net: int
    shot_wins_game: bool
    safe_alternatives: tuple[str, ...]
    was_avoidable: bool

    def describe(self) -> str:
        """A one-line human-readable description of the turning point."""
        kind = "loses the game" if self.shot_wins_game else (
            f"loses {self.shot_material_net} material"
        )
        if self.was_avoidable:
            safe = ", ".join(self.safe_alternatives)
            tail = f"avoidable; safe alternatives: {safe}"
        else:
            tail = (
                "unavoidable at this ply (every legal move concedes — the "
                "loss was locked in by an earlier quiet move)"
            )
        return (
            f"game {self.game_index} ply {self.ply} ({self.side}): "
            f"{self.played_move} {kind}; {tail}"
        )


def move_allows_shot(
    board: CheckersBoard, move: CheckersMove
) -> ShotResult | None:
    """Return the opponent's forced shot after ``move``, or ``None`` if none.

    A thin, named wrapper over :func:`dialectical_checkers.captures.opponent_shot`
    so the loss-mining intent reads clearly: "does playing ``move`` here hand
    the opponent a proven forced capture sequence?" The returned
    :class:`ShotResult` carries the net material, whether it wins the game and
    the evidence tier (``Tier.FACT`` for a fully resolved line).
    """
    return opponent_shot(board, move)


def _engine_lost(result: GameResult, engine_is_red: bool) -> bool:
    """True iff ``result`` is a game the engine (``engine_is_red``) lost."""
    if result.outcome == DRAW:
        return False
    engine_won = (result.outcome == RED_WIN) == engine_is_red
    return not engine_won


def _turning_point_at(
    result: GameResult,
    ply: int,
    engine_side: str,
    game_index: int,
    shot: ShotResult,
) -> LossTurningPoint:
    """Build a :class:`LossTurningPoint` for a known conceding engine ``ply``.

    Classifies the ply: ``was_avoidable`` is True iff some legal move at the
    position before ``ply`` conceded no shot — a genuine choice — and the safe
    moves are recorded.
    """
    board = result.positions[ply - 1]
    safe = [
        candidate.pdn()
        for candidate in board.legal_moves()
        if move_allows_shot(board, candidate) is None
    ]
    return LossTurningPoint(
        game_index=game_index,
        ply=ply,
        fen_before=board.to_fen(),
        played_move=result.moves[ply - 1].pdn(),
        side=engine_side,
        shot_material_net=shot.material_net,
        shot_wins_game=shot.terminal is not None,
        safe_alternatives=tuple(safe),
        was_avoidable=bool(safe),
    )


def mine_turning_point(
    result: GameResult,
    *,
    engine_is_red: bool,
    game_index: int = 1,
) -> LossTurningPoint | None:
    """Find the turning point of a game the engine lost.

    Walks the engine's plies of ``result`` in order, asking
    :func:`move_allows_shot` whether — in the position *before* each engine
    move — the move handed the opponent a proven forced shot. Two kinds of
    conceding ply are distinguished, to point at the *cause* not the *symptom*:

    * an **avoidable** turning point — the engine conceded a shot but a legal
      move that conceded nothing was available. This is a genuine blunder: a
      non-losing move was there and the engine did not play it. The **first**
      avoidable conceding ply is preferred as the turning point.
    * an **unavoidable** conceding ply — every legal move conceded a shot
      (typically all legal moves were mandatory captures). The position was
      already lost; the real blunder was an earlier quiet move the capture
      resolver cannot see. This is reported, with ``was_avoidable=False``, only
      when *no* avoidable turning point exists in the game.

    Returns ``None`` when the engine did not lose, or when no engine ply
    conceded a resolvable shot at all (a loss from slow attrition) — the
    diagnostic never invents a turning point it did not measure.
    """
    if not _engine_lost(result, engine_is_red):
        return None

    engine_side = "r" if engine_is_red else "w"
    first_unavoidable: LossTurningPoint | None = None
    for ply, move in enumerate(result.moves, start=1):
        board = result.positions[ply - 1]
        if board.turn != engine_side:
            continue
        shot = move_allows_shot(board, move)
        if shot is None:
            continue
        point = _turning_point_at(result, ply, engine_side, game_index, shot)
        if point.was_avoidable:
            # A genuine, avoidable blunder — the turning point we want.
            return point
        if first_unavoidable is None:
            first_unavoidable = point
    # No avoidable blunder: report the first unavoidable conceding ply (if any),
    # honestly flagged as already-lost.
    return first_unavoidable


def mine_losses(
    results: list[tuple[GameResult, bool]],
) -> list[LossTurningPoint]:
    """Mine turning points across a batch of (game, engine_is_red) pairs.

    ``results`` is a list of ``(GameResult, engine_is_red)`` tuples — typically
    every game of a matchup, with the colour the engine played. Returns one
    :class:`LossTurningPoint` per lost game in which a turning point was found,
    in game order, each tagged with its 1-based ``game_index``. Lost games with
    no resolvable turning point, and non-lost games, contribute nothing.
    """
    points: list[LossTurningPoint] = []
    for index, (result, engine_is_red) in enumerate(results, start=1):
        point = mine_turning_point(
            result, engine_is_red=engine_is_red, game_index=index
        )
        if point is not None:
            points.append(point)
    return points
