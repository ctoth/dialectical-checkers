"""Phase 4 — extract Pask Lesson 21 'The Opposition' verbatim.

Book page 82 maps to a PDF page near 90. Print pages 88-96 so the whole lesson
is captured.
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
        for i in range(87, 100):
            text = pdf.pages[i].extract_text() or ""
            if "Opposition" in text or "opposition" in text or "Lesson 2" in text:
                print(f"===== PDF PAGE {i + 1} =====")
                print(text)
                print()


if __name__ == "__main__":
    main()
