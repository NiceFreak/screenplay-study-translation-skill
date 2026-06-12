#!/usr/bin/env python3
"""Shared paths, types, and synthetic-fixture helpers for smoke checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT
SCRIPTS_DIR = SKILL_DIR / "scripts"
FIXTURES_DIR = SKILL_DIR / "assets" / "fixtures"
SUBTITLE_FIXTURE_DIR = FIXTURES_DIR / "subtitles"
HTML_FIXTURE_DIR = FIXTURES_DIR / "html"
VALID_BATCH = FIXTURES_DIR / "batches" / "valid" / "batch.json"
VALID_NO_SCENE_NUMBERS_BATCH = (
    FIXTURES_DIR / "batches" / "valid-no-scene-numbers" / "batch.json"
)


class Check(TypedDict):
    name: str
    command: list[str]


class SmokeCheck(Check, total=False):
    expect_failure: bool
    skip: bool
    skip_reason: str


def json_fixture(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def minimal_text_pdf(page_texts: list[str | None]) -> bytes:
    page_ids: list[int] = []
    content_ids: list[int] = []
    next_id = 4
    for _text in page_texts:
        page_ids.append(next_id)
        content_ids.append(next_id + 1)
        next_id += 2

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids).encode("ascii")
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids ["
        + kids
        + b"] /Count "
        + str(len(page_ids)).encode("ascii")
        + b" >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    }
    for page_id, content_id, text in zip(page_ids, content_ids, page_texts):
        page_obj = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >>"
        )
        if text is not None:
            page_obj += b" /Contents " + f"{content_id} 0 R".encode("ascii")
        objects[page_id] = page_obj + b" >>"
        if text is None:
            continue
        stream = (
            f"BT 1 0 0 1 72 720 Tm /F1 12 Tf ({pdf_escape(text)}) Tj ET\n"
        ).encode("latin1")
        objects[content_id] = (
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"endstream"
        )

    output = bytearray(b"%PDF-1.4\n")
    offsets = {0: 0}
    for obj_id in sorted(objects):
        offsets[obj_id] = len(output)
        output.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        output.extend(objects[obj_id])
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    max_id = max(objects)
    output.extend(f"xref\n0 {max_id + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for obj_id in range(1, max_id + 1):
        output.extend(f"{offsets.get(obj_id, 0):010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)
