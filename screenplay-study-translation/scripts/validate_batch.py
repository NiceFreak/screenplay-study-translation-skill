#!/usr/bin/env python3
"""Validate translation batch JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ENTRY_TYPES = {
    "page_heading",
    "scene_heading",
    "action",
    "character",
    "parenthetical",
    "dialogue",
    "transition",
    "format_marker",
    "note",
}
MARKER_TYPES = {
    "scene_no",
    "omitted",
    "contd",
    "more",
    "split_scene",
    "voice_or_position",
    "transition",
    "unknown_uppercase",
}
SUBTITLE_LABELS = {"字幕匹配", "字幕差异", "字幕未见"}
DRAFT_PREFIXES = (
    "待译场景标题：",
    "待译动作描写：",
    "待译角色提示：",
    "待译括号说明：",
    "待译对白：",
    "待译转场：",
    "待译格式标记：",
    "待处理页码：",
)
RAW_FORMAT_MARKER_RE = r"\((?:CONT'D|MORE|O\.S\.|O\.C\.|V\.O\.)\)|\b(?:OMITTED|CONT'D|MORE|V\.O\.|O\.S\.|O\.C\.)\b"
INLINE_MARKUP_RE = re.compile(
    r"__(.+?)__|\*\*(.+?)\*\*|(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)"
)


@dataclass
class Finding:
    level: str
    code: str
    message: str

    def render(self) -> str:
        return f"{self.level} {self.code} {self.message}"


def fail(findings: list[Finding], code: str, message: str) -> None:
    findings.append(Finding("FAIL", code, message))


def warn(findings: list[Finding], code: str, message: str) -> None:
    findings.append(Finding("WARN", code, message))


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_entry(
    entry: Any,
    index: int,
    has_subtitles: bool,
    seen_ids: set[str],
    findings: list[Finding],
) -> None:
    path = f"entries[{index}]"
    if not isinstance(entry, dict):
        fail(findings, "batch.entry_type", f"{path} must be object")
        return

    entry_id = entry.get("id")
    if not is_non_empty_string(entry_id):
        fail(findings, "batch.entry_id", f"{path}.id missing")
    elif entry_id in seen_ids:
        fail(findings, "batch.entry_id_duplicate", f"{path}.id={entry_id}")
    else:
        seen_ids.add(entry_id)

    entry_type = entry.get("type")
    if entry_type not in ENTRY_TYPES:
        fail(findings, "batch.entry_kind", f"{path}.type={entry_type}")

    for page_key in ("pdf_page", "display_page"):
        if not isinstance(entry.get(page_key), int):
            fail(findings, "batch.page", f"{path}.{page_key} must be int")

    if not is_non_empty_string(entry.get("source")):
        fail(findings, "batch.source", f"{path}.source missing")
    if not is_non_empty_string(entry.get("translation")):
        fail(findings, "batch.translation", f"{path}.translation missing")

    label = entry.get("subtitle_label")
    if label is not None:
        if label not in SUBTITLE_LABELS:
            fail(findings, "batch.subtitle_label", f"{path}.subtitle_label={label}")
        if not has_subtitles:
            fail(
                findings,
                "batch.subtitle_without_source",
                f"{path}.subtitle_label={label}",
            )

    markers = entry.get("markers", [])
    if markers is None:
        return
    if not isinstance(markers, list):
        fail(findings, "batch.markers", f"{path}.markers must be list")
        return
    for marker_index, marker in enumerate(markers):
        marker_path = f"{path}.markers[{marker_index}]"
        if not isinstance(marker, dict):
            fail(findings, "batch.marker", f"{marker_path} must be object")
            continue
        marker_type = marker.get("type")
        if marker_type not in MARKER_TYPES:
            fail(findings, "batch.marker_type", f"{marker_path}.type={marker_type}")


def validate_final_entry(
    entry: dict[str, Any], index: int, findings: list[Finding]
) -> None:
    path = f"entries[{index}]"
    entry_id = entry.get("id") if is_non_empty_string(entry.get("id")) else path
    translation = entry.get("translation")
    if not isinstance(translation, str):
        return
    stripped = translation.strip()
    if stripped.startswith(DRAFT_PREFIXES):
        fail(findings, "batch.final.placeholder_translation", f"{entry_id}")
    if re.search(RAW_FORMAT_MARKER_RE, stripped):
        fail(
            findings,
            "batch.final.raw_format_marker",
            f"{entry_id} translation={stripped}",
        )


def validate_batch(batch: dict[str, Any], final: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    if batch.get("version") != 1:
        fail(findings, "batch.version", "version must be 1")
    if not is_non_empty_string(batch.get("batch_id")):
        fail(findings, "batch.batch_id", "batch_id missing")

    source_pages = batch.get("source_pages")
    if not isinstance(source_pages, dict):
        fail(findings, "batch.source_pages", "source_pages must be object")
    else:
        start = source_pages.get("start")
        end = source_pages.get("end")
        if not isinstance(start, int) or not isinstance(end, int) or start > end:
            fail(findings, "batch.source_pages_range", f"start={start} end={end}")

    has_subtitles = bool(batch.get("has_subtitles", False))
    entries = batch.get("entries")
    if not isinstance(entries, list) or not entries:
        fail(findings, "batch.entries", "entries must be a non-empty list")
        return findings

    seen_ids: set[str] = set()
    inline_markup_count = 0
    front_matter = batch.get("front_matter", [])
    if front_matter is not None:
        if not isinstance(front_matter, list):
            fail(findings, "batch.front_matter", "front_matter must be list")
        else:
            for index, entry in enumerate(front_matter):
                validate_entry(entry, index, has_subtitles, seen_ids, findings)
                if final and isinstance(entry, dict):
                    validate_final_entry(entry, index, findings)
                    translation = entry.get("translation")
                    if isinstance(translation, str):
                        inline_markup_count += len(
                            INLINE_MARKUP_RE.findall(translation)
                        )
    for index, entry in enumerate(entries):
        validate_entry(entry, index, has_subtitles, seen_ids, findings)
        if final and isinstance(entry, dict):
            validate_final_entry(entry, index, findings)
            translation = entry.get("translation")
            if isinstance(translation, str):
                inline_markup_count += len(INLINE_MARKUP_RE.findall(translation))
    if final and inline_markup_count == 0:
        warn(
            findings,
            "batch.final.no_inline_reader_markup",
            "no __proper name__, **emphasis**, or *term* markup found",
        )
    if not findings:
        findings.append(Finding("INFO", "batch.valid", f"entries={len(entries)}"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate translation batch JSON.")
    parser.add_argument("batch", type=Path)
    parser.add_argument(
        "--final",
        action="store_true",
        help="Require final translation text, not draft placeholders.",
    )
    args = parser.parse_args()

    data = json.loads(args.batch.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        print("FAIL batch.root root must be object")
        return 1
    findings = validate_batch(data, final=args.final)
    for finding in findings:
        print(finding.render())
    return 1 if any(finding.level == "FAIL" for finding in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
