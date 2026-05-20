"""Confirm a HEURISTIC ShotResult through probe_moves() yields NO FACT witness.

Run: ``uv run python scripts/phase3a_verify_heuristic_witness.py``

The analyst's MAJOR finding: the tier-discipline test never drives a
``Tier.HEURISTIC`` resolver result through ``probe_moves()``. This script does
exactly that — it monkeypatches ``witnesses.own_shot`` and
``witnesses.opponent_shot`` to return a HEURISTIC ``ShotResult`` and checks
that:

* a HEURISTIC own_shot produces NO ``pro:shot_setup`` reason;
* a HEURISTIC opponent_shot produces NO ``obj:`` objection, ``reply:`` attack,
  or ``defense:`` derived from it.

It also checks the FACT control: with a real FACT ShotResult the same boundary
DOES emit the witness — so the guard, not the absence of any shot, is what
suppresses the HEURISTIC case.
"""

from __future__ import annotations

from dialectical_checkers import witnesses
from dialectical_checkers.board import CheckersBoard
from dialectical_checkers.captures import ShotResult, Tier

# A capture position: Red 13x22 is a jump that loses the exchange (see the
# curated test test_capture_that_loses_the_exchange).
CAPTURE_FEN = "B:W10,17,18:B6,13,14"
CAPTURE_PDN = "13x22"
# A quiet-move position where 13-17 allows a shot.
QUIET_FEN = "B:W22,30:B6,9,13,14"
QUIET_PDN = "13-17"


def heuristic_shot(*_args: object, **_kwargs: object) -> ShotResult:
    return ShotResult(
        material_net=300,
        forced=True,
        truncated=True,
        terminal=None,
        tier=Tier.HEURISTIC,
    )


def fact_shot(*_args: object, **_kwargs: object) -> ShotResult:
    return ShotResult(
        material_net=300,
        forced=True,
        truncated=False,
        terminal=None,
        tier=Tier.FACT,
    )


def probe_for(board: CheckersBoard, pdn: str) -> object:
    probes = {p.pdn: p for p in witnesses.probe_moves(board)}
    assert pdn in probes, (pdn, sorted(probes))
    return probes[pdn]


def main() -> None:
    orig_own = witnesses.own_shot
    orig_opp = witnesses.opponent_shot

    # --- HEURISTIC own_shot: NO pro:shot_setup -----------------------------
    witnesses.own_shot = heuristic_shot  # type: ignore[assignment]
    try:
        probe = probe_for(CheckersBoard.from_fen(CAPTURE_FEN), CAPTURE_PDN)
        setups = [r for r in probe.reasons if r.startswith("pro:shot_setup")]
        print(f"HEURISTIC own_shot -> pro:shot_setup reasons: {setups}")
        assert setups == [], setups
    finally:
        witnesses.own_shot = orig_own  # type: ignore[assignment]

    # --- FACT own_shot control: pro:shot_setup IS emitted ------------------
    witnesses.own_shot = fact_shot  # type: ignore[assignment]
    try:
        probe = probe_for(CheckersBoard.from_fen(CAPTURE_FEN), CAPTURE_PDN)
        setups = [r for r in probe.reasons if r.startswith("pro:shot_setup")]
        print(f"FACT own_shot -> pro:shot_setup reasons: {setups}")
        assert setups == ["pro:shot_setup:300"], setups
    finally:
        witnesses.own_shot = orig_own  # type: ignore[assignment]

    # --- HEURISTIC opponent_shot: NO obj/reply/defense ---------------------
    witnesses.opponent_shot = heuristic_shot  # type: ignore[assignment]
    try:
        probe = probe_for(CheckersBoard.from_fen(QUIET_FEN), QUIET_PDN)
        derived = [
            *probe.objections,
            *probe.reply_attacks,
            *probe.defenses,
        ]
        print(f"HEURISTIC opponent_shot -> obj/reply/defense: {derived}")
        assert derived == [], derived
    finally:
        witnesses.opponent_shot = orig_opp  # type: ignore[assignment]

    # --- FACT opponent_shot control on a quiet move: obj:allows_shot -------
    witnesses.opponent_shot = fact_shot  # type: ignore[assignment]
    try:
        probe = probe_for(CheckersBoard.from_fen(QUIET_FEN), QUIET_PDN)
        derived = [
            *probe.objections,
            *probe.reply_attacks,
            *probe.defenses,
        ]
        print(f"FACT opponent_shot -> obj/reply/defense: {derived}")
        assert "obj:allows_shot:300" in derived, derived
        assert "reply:material:300" in derived, derived
    finally:
        witnesses.opponent_shot = orig_opp  # type: ignore[assignment]

    print("OK: HEURISTIC shots emit no FACT witness; FACT control emits them.")


if __name__ == "__main__":
    main()
