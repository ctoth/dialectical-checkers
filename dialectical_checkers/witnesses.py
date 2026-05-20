"""CQ-derived witness producers -> ``MoveProbe`` (design §5).

``probe_moves(board)`` produces one :class:`MoveProbe` per legal move, each
carrying the design ``notes/checkers-design.md`` §5 witnesses — both the
**FACT-tier** rows (Phase 3a) and the **HEURISTIC-tier** rows (Phase 4).

Phase 4 is ADDITIVE: the FACT-tier production below is unchanged, the crisp
argument layer (``arguments.py``) still admits only FACT-tier witnesses
(``build_root_argument_graph`` filters by ``evidence.to_argument_evidence``'s
tier), and the FACT-tier selector ignores HEURISTIC witnesses — so the engine's
chosen move does not change. The HEURISTIC witnesses are produced for the
graded layer that the next phase wires in.

----------------------------------------------------------------------------
HEURISTIC-tier witnesses (design §5, Phase 4)
----------------------------------------------------------------------------

A HEURISTIC witness is a *positional judgement* — it does not need an oracle
proof, but its firing condition is **deterministic and precisely defined**.
Each producer below states the exact condition under which it fires. Every
HEURISTIC witness is ``Tier.HEURISTIC`` (``evidence.py`` types it so).

``mover`` = the side to move at the root; ``M`` = the move; ``R`` = the root
board; ``S`` = the board ``M`` reaches (``R.apply(M)`` — ``mover``'s opponent
is to move on ``S``).

* ``pro:opposition`` / ``obj:loses_opposition`` — TEMPO. "The opposition" (also
  "the move") of English-draughts endgame theory, implemented as the
  deterministic closed form of Richard Pask's *pairing-off* definition
  (*Checkers for the Novice*, Lesson 21: a player holds the opposition iff,
  pairing each of his pieces with the opponent's and treating the board as
  empty, he has the last move).

  The pairing-off method is unambiguous **only** for an equal-force ending
  with exactly **one piece per side** — then there is a single pairing and the
  result is the parity of the two pieces' separation. With more pieces per
  side the pairing is genuinely ambiguous (Pask: "Countless rules have been
  formulated ... all of them are confusing and unnecessary"), so the
  opposition witnesses fire **only** in the one-piece-per-side equal-force
  case and make no claim otherwise — a HEURISTIC witness firing exactly when
  its precise definition holds, silent when it does not.

  Precise rule (the turn-independent position property ``holder``):

      separation = Chebyshev (king-step) distance between the two pieces
                 = max(|row_a - row_b|, |col_a - col_b|)
      holder(pos) = the side NOT to move   if separation is EVEN
                  = the side to move       if separation is ODD

  (An even separation with you to move forces you to give ground first, so the
  *waiter* holds the opposition; an odd separation flips it. Verified
  self-consistent: when a side holds the opposition every legal move passes it
  to the opponent, and a side that does not hold it cannot seize it — the
  alternating "the move" property.)

  ``pro:opposition`` fires on ``M`` iff ``holder(S) == mover`` — the move
  reaches a position whose opposition the mover holds. ``obj:loses_opposition``
  fires iff ``holder(R) == mover`` but ``holder(S) != mover`` *and* some other
  legal move keeps it — the mover held the opposition and ``M`` threw it away
  when a keeping alternative existed.

* ``pro:back_rank_hold`` / ``obj:back_rank_break`` — STRUCTURE. The
  "king-row" / back-rank guard of design-§5 / Pask Lesson 18: keeping pieces
  on the mover's **home rank** (the rank the *opponent* must reach to crown —
  row 0 for Red, row 7 for White) denies the opponent crowning squares.

  ``pro:back_rank_hold`` fires iff, after ``M``, the mover has **>= 2** of its
  own pieces on its home rank. ``obj:back_rank_break`` fires iff ``M`` moves a
  mover piece **off** the home rank and that drops the mover's home-rank piece
  count from **>= 2 at the root to < 2 after the move** — a premature break of
  a back-rank guard that was intact.

* ``pro:center:{n}`` — STRUCTURE. Central-square occupation (Pask Lesson 16
  "Centre and Side Moves"). The four central squares are ``{14, 15, 18, 19}``
  (the board's middle). Fires iff, after ``M``, the mover has **strictly more**
  of its own pieces on the central squares than at the root; ``{n}`` is the
  post-move count of mover pieces on the central squares.

* ``pro:mobility:{n}`` — MOBILITY. Relative mobility: a move that leaves the
  opponent with fewer choices than the mover had. Fires iff the **opponent's**
  legal-move count on ``S`` is **strictly less than** the mover's legal-move
  count on ``R``; ``{n}`` is that positive difference (the mover's mobility
  advantage the move secures).

* ``pro:formation:{kind}`` — STRUCTURE. A named formation present after the
  move (``kind`` in the closed set ``phalanx`` / ``bridge`` / ``echelon`` —
  design §5 "bridge / phalanx / echelon"). On ``S``, with ``d`` = ``M``'s
  destination square:

  - ``phalanx`` — ``d`` holds a mover piece (the moved piece) that has another
    mover piece beside it on the same rank (same row, adjacent dark square,
    columns differing by 2). The moved piece participates in the formation.
  - ``bridge`` — the mover occupies **both** of its home-rank bridge squares
    (Red ``{2, 4}``, White ``{29, 31}`` — the classic two-square bridge that
    holds a lone enemy king out of the home rank). The bridge is a *static
    maintained* formation: a man can never step **onto** its own home rank
    (men only ever move away from it), so this kind fires whenever the bridge
    is intact after ``M`` — the move kept (did not break) the bridge. It does
    not require the moved piece to land on a bridge square.
  - ``echelon`` — ``d`` is part of a run of **>= 3** mover pieces on a single
    diagonal (each one king-step from the next). The moved piece participates.

  A move carries every ``pro:formation`` label whose precise condition holds —
  it may carry more than one.

* ``obj:single_corner_drift`` — STRUCTURE. A man driven toward the **single
  corner** — the true 8x8 grid corner with only one playable neighbour (Red's
  is square 4, White's square 29; verified by board geometry). The mover's
  single-corner squares are Red ``{4, 8}`` / White ``{25, 29}``. Fires iff
  ``M`` moves a mover **man** (not a king) whose destination is a mover
  single-corner square and whose origin is **not** — the man is drifting *into*
  the cramped single corner.

* ``obj:exposes_man`` — MATERIAL, HEURISTIC. A mover piece becomes capturable
  but the loss is **not proven**. Fires iff, after ``M``, the opponent has at
  least one legal capture (so a mover piece is *en prise*) **and** the
  forced-capture resolver did **not** prove a fact-tier shot for the opponent
  (``opponent_shot`` returned ``None`` or a non-FACT result). Design §5: "if
  the resolver proves the man is lost it is ``allows_shot`` (FACT); if it only
  *looks* loose it is ``exposes_man`` (HEURISTIC)" — the tier is decided by
  what the resolver proved, never asserted. A move already carrying the FACT
  ``obj:allows_shot`` / ``obj:loses_exchange`` / ``obj:terminal_loss`` does
  not also carry ``obj:exposes_man`` — the FACT objection supersedes it.

----------------------------------------------------------------------------
FACT-tier witnesses (design §5, Phase 3a — unchanged)
----------------------------------------------------------------------------

A witness's tier is determined by what the forced-capture resolver
(``captures.py``) actually **proved** — never asserted. The resolver tags a
fully-resolved (in-budget) line ``Tier.FACT`` and a budget-truncated line
``Tier.HEURISTIC``; this module emits a witness only from a ``Tier.FACT``
resolver result, so a truncated line yields no FACT witness at all (design §5:
"never assert a tier the resolver did not earn").

FACT-tier witnesses produced, per legal move (``mover`` = the side to move):

AS1 pro-reasons (``MoveProbe.reasons``):

* ``pro:terminal_win`` — the move's child is terminal and ``mover`` wins.
* ``pro:material:{n}`` — the move is a capture; ``n`` is the weighted material
  the move's own capture immediately nets the mover.
* ``pro:crown`` — the move advances an uncrowned man onto its king-row.
* ``pro:shot_setup:{n}`` — ``captures.own_shot`` proves the move initiates a
  forced sequence netting the mover ``n`` (FACT only — not truncated).

CQ8_9 / CQ17 objections (``MoveProbe.objections``):

* ``obj:terminal_loss`` — ``captures.opponent_shot`` proves a forced line that
  ends the game with the **opponent** winning.
* ``obj:allows_shot:{n}`` — a **quiet** (non-capture) move that
  ``opponent_shot`` proves lets the opponent force a material gain of ``n``,
  the game not ending.
* ``obj:loses_exchange:{n}`` — a **capture** move whose forced continuation
  the resolver proves nets the mover a material loss of ``n`` (the capture's
  immediate gain minus the opponent's proven recapture).

CQ17 reply attacks (``MoveProbe.reply_attacks``):

* ``reply:terminal_loss`` / ``reply:material:{n}`` — the opponent's proven
  forcing reply after the move (the same ``opponent_shot`` fact, expressed in
  the reply channel; design §6 has both objections and reply attacks defeat a
  move in the crisp layer).

Proven defenses (``MoveProbe.defenses``):

* ``defense:holds_exchange@{answered}`` — a capture move for which the opponent
  has a proven forcing recapture, but the resolver proves the mover's net swing
  across the whole line is even or favourable: the apparent reply is refuted.
  The defense is **keyed** to the specific reply it answers (design §6 — "and
  only that one"): ``{answered}`` is the exact ``reply:material:{n}`` label the
  same probe emits, so the crisp layer can wire ``defense -> only that reply``
  instead of over-defeating every attacker on the move.

The ``allows_shot`` / ``loses_exchange`` split — both FACT, both
resolver-sourced, with overlapping conditions in design §5 — is partitioned by
``move.is_jump``: a quiet move that walks into a combination is ``allows_shot``;
a capture that comes out behind in the trade is ``loses_exchange``. This is the
one design under-specification resolved in Phase 3a; see the phase report.

This module imports only from within ``dialectical_checkers`` and the stdlib.
pydraughts is a *test* dependency only (the non-oracle-strength stance).
"""

from __future__ import annotations

from dialectical_checkers.arguments import MoveProbe
from dialectical_checkers.board import (
    RED_KING_ROW,
    WHITE_KING_ROW,
    CheckersBoard,
    CheckersMove,
    _coord,
)
from dialectical_checkers.captures import (
    KING_VALUE,
    MAN_VALUE,
    ShotResult,
    Tier,
    opponent_shot,
    own_shot,
)

_KING_ROW = {"r": RED_KING_ROW, "w": WHITE_KING_ROW}

# --- HEURISTIC-tier geometry (design §5, Phase 4) ---------------------------
#
# A side's **home rank** is the rank the *opponent* must reach to crown — the
# rank whose pieces guard the king-row. Red's home rank is row 0 (squares 1-4,
# White's king-row); White's home rank is row 7 (squares 29-32, Red's
# king-row). It is exactly the *other* side's king-row.
_HOME_RANK = {"r": WHITE_KING_ROW, "w": RED_KING_ROW}

#: The four central squares (design §5 / Pask "Centre and Side Moves") — the
#: board's middle, PDN 14, 15, 18, 19.
_CENTRAL_SQUARES = frozenset({14, 15, 18, 19})

#: A side's two home-rank **bridge squares** — the classic two-square bridge
#: that holds a lone enemy king out of the home rank (design §5 "bridge").
#: Red: PDN 2 and 4; White: PDN 29 and 31.
_BRIDGE_SQUARES = {"r": frozenset({2, 4}), "w": frozenset({29, 31})}

#: A side's **single-corner** squares — the cramped true-grid-corner region a
#: man is driven into. The single corner is the 8x8 grid corner with one
#: playable neighbour: Red's is PDN 4, White's PDN 29 (verified by board
#: geometry). The drift region is the corner square plus its inner neighbour:
#: Red {4, 8}, White {25, 29}.
_SINGLE_CORNER_SQUARES = {"r": frozenset({4, 8}), "w": frozenset({25, 29})}

#: The minimum run length on one diagonal for the ``echelon`` formation.
_ECHELON_MIN = 3


def _opponent(side: str) -> str:
    """The opposing side of ``side``."""
    return "w" if side == "r" else "r"


def _weighted_material(board: CheckersBoard, side: str) -> int:
    """Weighted material for ``side`` on ``board`` — man=100, king=150.

    The same weighting ``captures.py`` uses; counted here so ``witnesses.py``
    does not reach into ``captures``' private helpers.
    """
    total = 0
    for cell in board.cells:
        if cell is None or cell[0] != side:
            continue
        total += KING_VALUE if cell[1] else MAN_VALUE
    return total


def _net_material(board: CheckersBoard, side: str) -> int:
    """Weighted material balance on ``board`` from ``side``'s perspective."""
    other = "w" if side == "r" else "r"
    return _weighted_material(board, side) - _weighted_material(board, other)


def _crowns(board: CheckersBoard, move: CheckersMove) -> bool:
    """True iff ``move`` advances an uncrowned man onto its king-row.

    A move crowns when the moving piece is a *man* (not already a king) and its
    destination square lies on the mover's king-row — for a simple step or for
    a jump that lands on the king-row (which, per ``board.py``, ends the turn).
    """
    cell = board.cells[move.origin - 1]
    if cell is None or cell[1]:
        # Empty origin (should not happen for a legal move) or an already
        # crowned king — a king cannot be crowned again.
        return False
    return _coord(move.destination - 1)[0] == _KING_ROW[board.turn]


# --- HEURISTIC-tier witness producers (design §5, Phase 4) ------------------
#
# Each producer below is a deterministic, precisely-defined positional
# judgement (see the module docstring's HEURISTIC section). They never read the
# forced-capture resolver tier (a HEURISTIC witness is not a proof); the one
# exception is ``obj:exposes_man``, which *consults* the resolver only to
# confirm the loss is **not** proven (so the witness stays HEURISTIC and does
# not duplicate a FACT objection).


def _pieces_of(board: CheckersBoard, side: str) -> list[tuple[int, bool]]:
    """The ``(pdn, is_king)`` of every ``side`` piece on ``board``."""
    out: list[tuple[int, bool]] = []
    for idx in range(len(board.cells)):
        cell = board.cells[idx]
        if cell is not None and cell[0] == side:
            out.append((idx + 1, cell[1]))
    return out


def _opposition_holder(board: CheckersBoard) -> str | None:
    """The side holding the opposition on ``board``, or ``None`` (design §5).

    "The opposition" of English-draughts endgame theory, as the deterministic
    closed form of Pask's pairing-off definition. Defined **only** for an
    equal-force ending with exactly **one piece per side** — the single case
    the pairing-off method is unambiguous; ``None`` otherwise (the witness
    makes no claim rather than an arbitrary one).

    ``holder`` is turn-independent: with ``separation`` the Chebyshev
    (king-step) distance between the two pieces, the side **not** to move holds
    the opposition when ``separation`` is even, the side to move when it is odd
    (an even separation forces the side to move to give ground first, so the
    waiter holds it).
    """
    reds = _pieces_of(board, "r")
    whites = _pieces_of(board, "w")
    if len(reds) != 1 or len(whites) != 1:
        # The pairing-off method is ambiguous with more than one piece a side
        # (Pask) — and undefined with none; make no claim.
        return None
    # Equal force (one piece each) is required; a man vs a king is still one
    # piece each, and the parity argument is purely geometric, so the rule
    # applies. The Chebyshev distance is the king-step separation.
    r_row, r_col = _coord(reds[0][0] - 1)
    w_row, w_col = _coord(whites[0][0] - 1)
    separation = max(abs(r_row - w_row), abs(r_col - w_col))
    if separation % 2 == 0:
        return _opponent(board.turn)
    return board.turn


def _home_rank_count(board: CheckersBoard, side: str) -> int:
    """How many ``side`` pieces stand on ``side``'s home rank (design §5).

    ``side``'s home rank is the rank the opponent crowns on (row 0 for Red,
    row 7 for White) — pieces there guard the king-row.
    """
    home_row = _HOME_RANK[side]
    count = 0
    for pdn, _is_king in _pieces_of(board, side):
        if _coord(pdn - 1)[0] == home_row:
            count += 1
    return count


def _central_count(board: CheckersBoard, side: str) -> int:
    """How many ``side`` pieces stand on the four central squares (design §5)."""
    return sum(
        1 for pdn, _k in _pieces_of(board, side) if pdn in _CENTRAL_SQUARES
    )


def _has_rank_neighbour(board: CheckersBoard, side: str, pdn: int) -> bool:
    """True iff a ``side`` piece sits beside ``pdn`` on the same rank.

    "Beside" = same row, an adjacent dark square (columns differing by 2) —
    the phalanx adjacency of design §5.
    """
    row, col = _coord(pdn - 1)
    for other_pdn, _k in _pieces_of(board, side):
        if other_pdn == pdn:
            continue
        o_row, o_col = _coord(other_pdn - 1)
        if o_row == row and abs(o_col - col) == 2:
            return True
    return False


def _diagonal_run_length(board: CheckersBoard, side: str, pdn: int) -> int:
    """The longest run of ``side`` pieces on a diagonal through ``pdn``.

    Counts ``pdn`` itself plus the contiguous ``side`` pieces extending from it
    along each of the two diagonals (NE-SW and NW-SE), each piece one king-step
    from the next. Returns the longer of the two diagonal runs.
    """
    own = {p for p, _k in _pieces_of(board, side)}
    if pdn not in own:
        return 0
    row, col = _coord(pdn - 1)
    occupied = {(_coord(p - 1)) for p in own}

    def run(dr: int, dc: int) -> int:
        # Length of the run from (row,col) including (row,col), stepping
        # (dr,dc) and (-dr,-dc) — a full diagonal line through the square.
        length = 1
        for sign in (1, -1):
            r, c = row + sign * dr, col + sign * dc
            while (r, c) in occupied:
                length += 1
                r, c = r + sign * dr, c + sign * dc
        return length

    return max(run(1, 1), run(1, -1))


def _heuristic_reasons(
    board: CheckersBoard,
    move: CheckersMove,
    child: CheckersBoard,
    siblings: tuple[CheckersMove, ...],
) -> list[str]:
    """The HEURISTIC AS1 pro-reasons for ``move`` (design §5, Phase 4).

    ``board`` is the root ``R``, ``child`` the board ``move`` reaches ``S``,
    ``siblings`` every legal move from ``R`` (used by the opposition witness to
    decide whether a keeping alternative existed). See the module docstring for
    each witness's precise firing condition.
    """
    mover = board.turn
    reasons: list[str] = []

    # --- pro:opposition — the move secures the opposition for the mover -----
    holder_after = _opposition_holder(child)
    if holder_after == mover:
        reasons.append("pro:opposition")

    # --- pro:back_rank_hold — >= 2 mover pieces on the home rank after M ----
    if _home_rank_count(child, mover) >= 2:
        reasons.append("pro:back_rank_hold")

    # --- pro:center:{n} — central-square occupation increased --------------
    central_before = _central_count(board, mover)
    central_after = _central_count(child, mover)
    if central_after > central_before:
        reasons.append(f"pro:center:{central_after}")

    # --- pro:mobility:{n} — opponent left with fewer choices than the mover -
    mover_root_moves = len(siblings)
    opponent_after_moves = len(child.legal_moves())
    mobility_gain = mover_root_moves - opponent_after_moves
    if mobility_gain > 0:
        reasons.append(f"pro:mobility:{mobility_gain}")

    # --- pro:formation:{kind} — a named formation present after the move ----
    dest = move.destination
    dest_cell = child.cells[dest - 1]
    dest_is_mover = dest_cell is not None and dest_cell[0] == mover
    if dest_is_mover:
        # phalanx — the moved piece has a same-rank mover neighbour.
        if _has_rank_neighbour(child, mover, dest):
            reasons.append("pro:formation:phalanx")
        # echelon — the moved piece is in a run of >= 3 on a diagonal.
        if _diagonal_run_length(child, mover, dest) >= _ECHELON_MIN:
            reasons.append("pro:formation:echelon")
    # bridge — a static maintained formation: the mover occupies both of its
    # home-rank bridge squares after the move. A man cannot step onto its own
    # home rank, so this kind does not require the moved piece to land there.
    bridge = _BRIDGE_SQUARES[mover]
    own_pdns = {p for p, _k in _pieces_of(child, mover)}
    if bridge <= own_pdns:
        reasons.append("pro:formation:bridge")

    return reasons


def _heuristic_objections(
    board: CheckersBoard,
    move: CheckersMove,
    child: CheckersBoard,
    siblings: tuple[CheckersMove, ...],
    fact_objections: list[str],
    opponent_shot_result: ShotResult | None,
) -> list[str]:
    """The HEURISTIC CQ8_9 objections for ``move`` (design §5, Phase 4).

    ``fact_objections`` is the move's already-computed FACT objection list —
    ``obj:exposes_man`` is suppressed when a FACT objection already covers the
    move (the FACT objection supersedes the HEURISTIC one, design §5).

    ``opponent_shot_result`` is the ``ShotResult | None`` ``_probe_move``
    already computed from ``opponent_shot(board, move)`` — reused here so the
    resolver is not run twice. ``obj:exposes_man`` consults it only to confirm
    the loss is **not** a proven FACT shot.
    """
    mover = board.turn
    objections: list[str] = []

    # --- obj:loses_opposition — the move throws away a held opposition ------
    holder_root = _opposition_holder(board)
    holder_after = _opposition_holder(child)
    if holder_root == mover and holder_after != mover:
        # The mover held the opposition and this move surrendered it — only an
        # objection if a sibling move would have kept it.
        keeps_exist = False
        for sibling in siblings:
            if sibling == move:
                continue
            if _opposition_holder(board.apply(sibling)) == mover:
                keeps_exist = True
                break
        if keeps_exist:
            objections.append("obj:loses_opposition")

    # --- obj:back_rank_break — a move that prematurely breaks the back rank -
    origin_row = _coord(move.origin - 1)[0]
    if origin_row == _HOME_RANK[mover]:
        before = _home_rank_count(board, mover)
        after = _home_rank_count(child, mover)
        if before >= 2 and after < 2:
            objections.append("obj:back_rank_break")

    # --- obj:single_corner_drift — a man driven into the single corner -----
    origin_cell = board.cells[move.origin - 1]
    moving_is_man = origin_cell is not None and not origin_cell[1]
    single_corner = _SINGLE_CORNER_SQUARES[mover]
    if (
        moving_is_man
        and move.destination in single_corner
        and move.origin not in single_corner
    ):
        objections.append("obj:single_corner_drift")

    # --- obj:exposes_man — a piece is en prise, the loss not proven --------
    # The opponent has a capture available after the move (a mover piece is
    # capturable) but the resolver did not prove a fact-tier shot — it only
    # *looks* loose. A FACT objection already on the move supersedes this.
    opponent_has_capture = any(m.is_jump for m in child.legal_moves())
    if opponent_has_capture and not fact_objections:
        shot = opponent_shot_result
        proven_fact_shot = shot is not None and shot.tier is Tier.FACT
        if not proven_fact_shot:
            objections.append("obj:exposes_man")

    return objections


def _probe_move(
    board: CheckersBoard,
    move: CheckersMove,
    siblings: tuple[CheckersMove, ...],
) -> MoveProbe:
    """Build the :class:`MoveProbe` for one legal ``move`` (design §5).

    Emits the FACT-tier witnesses (Phase 3a) and the HEURISTIC-tier witnesses
    (Phase 4). ``siblings`` is every legal move from ``board`` — the opposition
    witness needs it to decide whether a sibling move would have kept the
    opposition.
    """
    mover = board.turn
    child = board.apply(move)

    reasons: list[str] = []
    objections: list[str] = []
    reply_attacks: list[str] = []
    defenses: list[str] = []

    # --- pro:terminal_win — the move ends the game in the mover's favour ----
    child_terminal_win = child.is_terminal() and child.winner() == mover
    if child_terminal_win:
        reasons.append("pro:terminal_win")

    # --- pro:material — the weighted material the move itself captures ------
    # A capture move's own immediate net gain is the change in the mover's
    # material balance between the root and the child (the move's captures,
    # plus a +50 swing if the moving man crowns on this move).
    if move.is_jump:
        immediate_gain = _net_material(child, mover) - _net_material(board, mover)
        if immediate_gain > 0:
            reasons.append(f"pro:material:{immediate_gain}")
    else:
        immediate_gain = 0

    # --- pro:crown — a man reaches its king-row ----------------------------
    if _crowns(board, move):
        reasons.append("pro:crown")

    # --- pro:shot_setup — own_shot proves a forced winning sequence ---------
    # Only a FACT (non-truncated) own_shot earns a fact-tier reason.
    setup = own_shot(board, move)
    if setup is not None and setup.tier is Tier.FACT:
        reasons.append(f"pro:shot_setup:{setup.material_net}")

    # --- the opponent's forced reply: opponent_shot ------------------------
    # opponent_shot applies the move and resolves; a FACT result is a proven
    # forced sequence the opponent can play. Its material_net is measured from
    # the opponent's perspective after the move.
    shot = opponent_shot(board, move)
    if shot is not None and shot.tier is Tier.FACT:
        if shot.terminal is not None and shot.terminal != mover:
            # The forced reply ends the game with the opponent winning.
            objections.append("obj:terminal_loss")
            reply_attacks.append("reply:terminal_loss")
        elif shot.terminal is None:
            # A forced material gain for the opponent (the game does not end).
            reply_label = f"reply:material:{shot.material_net}"
            reply_attacks.append(reply_label)
            if move.is_jump:
                # A capture move: the mover's net swing across the whole line
                # is its own immediate capture minus the opponent's proven
                # recapture. Negative -> the exchange is genuinely lost;
                # even/favourable -> the apparent reply is refuted.
                mover_swing = immediate_gain - shot.material_net
                if mover_swing < 0:
                    objections.append(f"obj:loses_exchange:{-mover_swing}")
                else:
                    # The defense answers exactly this reply — keyed to it so
                    # the crisp layer defeats only that attacker (design §6).
                    defenses.append(
                        f"defense:holds_exchange@{reply_label}"
                    )
            else:
                # A quiet move that walks into a forced combination.
                objections.append(f"obj:allows_shot:{shot.material_net}")

    # --- HEURISTIC-tier witnesses (design §5, Phase 4) ---------------------
    # ADDITIVE: appended after the FACT witnesses, never altering them. The
    # crisp argument layer filters by tier (HEURISTIC excluded) and the
    # FACT-tier selector ignores HEURISTIC witnesses, so the engine's PLAY is
    # unchanged. ``obj:exposes_man`` is suppressed when a FACT objection
    # already covers the move — the FACT objection supersedes it.
    reasons.extend(_heuristic_reasons(board, move, child, siblings))
    objections.extend(
        _heuristic_objections(board, move, child, siblings, objections, shot)
    )

    return MoveProbe(
        pdn=move.pdn(),
        reasons=tuple(reasons),
        objections=tuple(objections),
        reply_attacks=tuple(reply_attacks),
        defenses=tuple(defenses),
    )


def probe_moves(board: CheckersBoard) -> tuple[MoveProbe, ...]:
    """Produce one :class:`MoveProbe` per legal move (design §5).

    Each probe carries the FACT-tier witnesses (Phase 3a) and the
    HEURISTIC-tier witnesses (Phase 4). The probes are returned in
    ``board.legal_moves()`` order — already sorted, so the result is
    deterministic. A terminal position (no legal move) yields an empty tuple.
    """
    moves = board.legal_moves()
    return tuple(_probe_move(board, move, moves) for move in moves)
