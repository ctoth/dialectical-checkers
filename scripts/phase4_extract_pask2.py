"""Phase 4 — search Pask's primer for the formal 'opposition' / counting rule."""

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
            if "opposition" in low:
                print(f"===== PAGE {i + 1} (opposition) =====")
                print(text)
                print()


if __name__ == "__main__":
    main()
