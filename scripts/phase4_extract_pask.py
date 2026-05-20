"""Phase 4 — extract the 'the move' / opposition section from Pask's primer.

Reads the downloaded 'Checkers for the Novice' PDF, finds the pages mentioning
'the move' / 'opposition', and prints their text so the standard opposition
rule can be transcribed precisely into the witness docstring.
"""

from __future__ import annotations

import pdfplumber

PDF = (
    r"C:\Users\Q\.claude\projects\C--Users-Q-code-dialectical-chess"
    r"\cf936cca-c237-483d-94e8-80b8f8c621ff\tool-results"
    r"\webfetch-1779312783978-8c4fvl.pdf"
)


def main() -> None:
    with pdfplumber.open(PDF) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            low = text.lower()
            if "the move" in low and (
                "opposition" in low
                or "count" in low
                or "system" in low
                or "tempo" in low
            ):
                print(f"===== PAGE {i + 1} =====")
                print(text)
                print()


if __name__ == "__main__":
    main()
