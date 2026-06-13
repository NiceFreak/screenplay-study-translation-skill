#!/usr/bin/env python3
"""Generate an original SYNTHETIC screenplay PDF for the skill demo.

Content is entirely invented for demonstration. It contains no real film,
screenplay, or subtitle text. The text-operator layout matches the parser in
scripts/scan_markers.py so extraction and marker scanning work end to end.
"""

from __future__ import annotations

import sys
from pathlib import Path


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def op(text: str, x: float, y: float, size: int = 12) -> str:
    return f"BT 1 0 0 1 {x} {y} Tm /F1 {size} Tf ({esc(text)}) Tj ET\n"


# Each page is a list of (text, x, y) rows.
PAGES: list[list[tuple[str, float, float]]] = [
    # Page 1 - title page (display_page 0)
    [
        ("THE TIDE CLERK", 220, 560, 16),
        ("Written by", 270, 520),
        ("A. SYNTHETIC", 262, 500),
        ("Demonstration Draft", 250, 120),
    ],
    # Page 2 - screenplay display_page 1
    [
        ("2.", 300, 752),
        ("1", 70, 700),  # left scene number
        ("1", 540, 700),  # right scene number
        ("INT. TIDE STATION - NIGHT", 90, 700),
        ("Rain hammers the windows. MARA, 30s, logs the", 90, 672),
        ("water level by lamplight.", 90, 656),
        ("MARA", 250, 624),
        ("(not looking up)", 210, 606),
        ("The tide came early again.", 170, 588),
        ("MARA (CONT'D)", 250, 552),
        ("Three nights running. Same hour.", 170, 534),
        ("CUT TO:", 440, 498),
    ],
    # Page 3 - screenplay display_page 2
    [
        ("3.", 300, 752),
        ("2", 70, 700),
        ("2", 540, 700),
        ("EXT. PIER - DAWN", 90, 700),
        ("Grey light. The flat water looks wrong.", 90, 672),
        ("ELIAS (V.O.)", 250, 640),
        ("You wrote it down. Good girl.", 170, 622),
        ("3", 70, 520),
        ("3", 540, 520),
        ("OMITTED", 260, 520),
        ("(MORE)", 250, 110),
    ],
]


def build_pdf() -> bytes:
    objects: list[bytes] = []
    # Reserve: 1 Catalog, 2 Pages, then per page: Page obj + Content obj, then Font.
    page_count = len(PAGES)
    font_obj_id = 3 + page_count * 2

    page_obj_ids = [3 + i * 2 for i in range(page_count)]
    content_obj_ids = [4 + i * 2 for i in range(page_count)]
    kids = " ".join(f"{pid} 0 R" for pid in page_obj_ids)

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(
        f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii")
    )

    page_streams: list[bytes] = []
    for rows in PAGES:
        stream = "".join(op(*row) for row in rows).encode("latin1")
        page_streams.append(stream)

    for i in range(page_count):
        page_obj = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> "
            f"/Contents {content_obj_ids[i]} 0 R >>"
        ).encode("ascii")
        content_obj = (
            b"<< /Length "
            + str(len(page_streams[i])).encode("ascii")
            + b" >>\nstream\n"
            + page_streams[i]
            + b"endstream"
        )
        objects.append(page_obj)
        objects.append(content_obj)

    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source/tide-clerk.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(build_pdf())
    print(f"INFO demo_pdf {out} pages={len(PAGES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
