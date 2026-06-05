#!/usr/bin/env python3
"""Export a minimal A4 PDF from study HTML.

This is a deterministic smoke/export interface, not the final typography engine.
"""

from __future__ import annotations

import argparse
import html
import re
import textwrap
from pathlib import Path


A4_WIDTH = 595
A4_HEIGHT = 842


def html_to_text(html_text: str) -> list[str]:
    text = re.sub(r"<br\s*/?>", "\n", html_text, flags=re.I)
    text = re.sub(r"</(?:p|div|section|main|h1|h2|h3)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        lines.extend(textwrap.wrap(line, width=82) or [""])
    return lines or ["screenplay-study"]


def pdf_escape(text: str) -> str:
    # The smoke PDF uses WinAnsi-safe replacement; final exports should use a
    # real font-capable renderer.
    safe = text.encode("latin1", errors="replace").decode("latin1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def page_stream(lines: list[str]) -> bytes:
    y = A4_HEIGHT - 56
    ops: list[str] = []
    for line in lines:
        ops.append(f"BT /F1 10 Tf 50 {y} Td ({pdf_escape(line)}) Tj ET\n")
        y -= 14
    return "".join(ops).encode("latin1")


def paginate(lines: list[str]) -> list[list[str]]:
    per_page = 52
    return [lines[index : index + per_page] for index in range(0, len(lines), per_page)]


def build_pdf(lines: list[str]) -> bytes:
    pages = paginate(lines)
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    ]
    page_refs: list[str] = []
    for page_index, page_lines in enumerate(pages):
        page_obj_id = 4 + page_index * 2
        content_obj_id = page_obj_id + 1
        page_refs.append(f"{page_obj_id} 0 R")
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {A4_WIDTH} {A4_HEIGHT}] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj_id} 0 R >>"
            ).encode("ascii")
        )
        stream = page_stream(page_lines)
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"endstream"
        )
    objects[1] = (
        f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(pages)} >>".encode(
            "ascii"
        )
    )

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
    parser = argparse.ArgumentParser(description="Export a minimal A4 PDF from HTML.")
    parser.add_argument("html", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    lines = html_to_text(args.html.read_text(encoding="utf-8", errors="replace"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(build_pdf(lines))
    print(f"INFO pdf {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
