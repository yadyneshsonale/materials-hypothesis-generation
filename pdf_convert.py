"""Column-aware PDF-to-text conversion using PyMuPDF block coordinates.

pdftotext -layout occasionally interleaves two-column PDFs (left/right column
text mashed onto the same line) because it doesn't reliably detect column
boundaries. This reads text as positioned blocks and sorts them by column
(x-position bucketed into left/right half of the page) then reading order
(top-to-bottom within a column), which is far more robust for 2-column
scientific paper layouts.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf


def convert(pdf_path: Path) -> str:
    doc = pymupdf.open(pdf_path)
    pages_text = []
    for page in doc:
        blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
        page_width = page.rect.width
        mid_x = page_width / 2

        def sort_key(b):
            x0, y0 = b[0], b[1]
            column = 0 if x0 < mid_x else 1
            return (column, y0, x0)

        blocks_sorted = sorted(blocks, key=sort_key)
        page_text = "\n".join(b[4].strip() for b in blocks_sorted if b[4].strip())
        pages_text.append(page_text)
    return "\n\n".join(pages_text)


def main() -> None:
    pdf_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    out_path.write_text(convert(pdf_path))
    print(f"[pdf_convert] {pdf_path} -> {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
