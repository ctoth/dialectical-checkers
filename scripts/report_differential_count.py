"""Report how many positions the resolver was differential-checked against.

Run: ``uv run python scripts/report_differential_count.py``

Reproduces the sample used by ``test_differential_resolve_vs_brute_force`` and
prints: total positions, how many had captures, how many resolved within budget
(FACT-tier, checked against the brute-force reference), and how many truncated.
Used to fill in the Phase 2 report's coverage numbers with an exact figure.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "tests")

from test_captures import brute_force_resolve, differential_positions  # noqa: E402

from dialectical_checkers.captures import resolve  # noqa: E402


def main() -> None:
    positions = differential_positions(target=260)
    total = len(positions)
    with_captures = 0
    checked = 0
    truncated = 0
    mismatches = 0
    for board in positions:
        if any(m.is_jump for m in board.legal_moves()):
            with_captures += 1
        line = resolve(board)
        if line.truncated:
            truncated += 1
            continue
        ref_swing, ref_forced, ref_terminal = brute_force_resolve(board)
        if (
            line.material_swing != ref_swing
            or line.forced != ref_forced
            or line.terminal != ref_terminal
        ):
            mismatches += 1
        checked += 1
    print(f"total positions in differential sample: {total}")
    print(f"  with a forced capture at the root:    {with_captures}")
    print(f"  resolved within budget (FACT, checked): {checked}")
    print(f"  truncated (HEURISTIC, no exact claim):  {truncated}")
    print(f"  mismatches vs brute-force reference:    {mismatches}")
    print("ALL MATCH" if mismatches == 0 else "MISMATCHES FOUND")


if __name__ == "__main__":
    main()
