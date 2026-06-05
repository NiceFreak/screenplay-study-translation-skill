#!/usr/bin/env python3
"""Create a tiny PDF fixture for marker scanning tests."""

from __future__ import annotations

import argparse
from pathlib import Path


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_op(text: str, x: int, y: int, size: int = 12) -> str:
    return f"BT 1 0 0 1 {x} {y} Tm /F1 {size} Tf ({pdf_escape(text)}) Tj ET\n"


def title_text_op(text: str, x: int, y: int, size: int = 12) -> str:
    return (
        f"BT -0.0167 Tc {size} 0 0 {size} {x} {y} Tm "
        f"/F1 1 Tf ({pdf_escape(text)}) Tj 0 Tc ET\n"
    )


def build_pdf() -> bytes:
    stream = "".join(
        [
            title_text_op("SAMPLE TITLE", 240, 760),
            text_op("73", 36, 740),
            text_op("73", 560, 740),
            text_op("IV", 36, 720),
            text_op("IV", 560, 720),
            text_op("73 pt2", 36, 700),
            text_op("73 pt2", 560, 700),
            text_op("1999", 220, 680),
            text_op("A", 560, 680),
            text_op("MADDY (CONT'D)", 220, 650),
            text_op("(MORE)", 290, 80),
            text_op("OMITTED", 260, 520),
            text_op("OWEN (V.O.)", 220, 600),
            text_op("MADDY (O.S.)", 220, 580),
        ]
    ).encode("latin1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"endstream",
    ]

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
    parser = argparse.ArgumentParser(description="Create the PDF scan fixture.")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(build_pdf())
    print(f"INFO pdf_fixture {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
