"""Check str.isdigit() behaviour for the magnitude-validation edge cases.

Run: ``uv run python scripts/phase3a_check_isdigit.py``

Confirms ``str.isdigit()`` rejects signed/empty/non-numeric magnitudes and
accepts plain ASCII digit runs, and flags whether any unicode-digit string
slips through (a superscript such as ``²``).
"""

from __future__ import annotations

CASES = [
    "100",
    "0",
    "00",
    "-100",
    "+100",
    "",
    "abc",
    " 100",
    "100 ",
    "²",  # superscript two — isdigit True, int() raises
    "٠",  # arabic-indic digit zero
]


def main() -> None:
    for s in CASES:
        is_digit = s.isdigit()
        is_ascii_decimal = s.isascii() and s.isdecimal()
        try:
            parsed: object = int(s)
        except ValueError:
            parsed = "ValueError"
        print(
            f"{s!r:14} isdigit={is_digit!s:5} "
            f"ascii_decimal={is_ascii_decimal!s:5} int()={parsed!r}"
        )


if __name__ == "__main__":
    main()
