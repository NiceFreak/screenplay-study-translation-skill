#!/usr/bin/env python3
"""Audit draft batch structure before translation work."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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


@dataclass
class Finding:
    level: str
    code: str
    message: str

    def render(self) -> str:
        return f"{self.level} {self.code} {self.message}"


def text(entry: dict[str, Any], key: str) -> str:
    value = entry.get(key)
    return value if isinstance(value, str) else ""


def has_marker(entry: dict[str, Any], marker_type: str) -> bool:
    markers = entry.get("markers")
    return isinstance(markers, list) and any(
        isinstance(marker, dict) and marker.get("type") == marker_type
        for marker in markers
    )


def audit_entries(entries: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    counts = Counter(str(entry.get("type")) for entry in entries)
    for entry_type, count in sorted(counts.items()):
        findings.append(Finding("INFO", "draft.entry_count", f"{entry_type}={count}"))
    placeholder_count = 0

    previous_type: str | None = None
    open_parenthetical: str | None = None
    for index, entry in enumerate(entries):
        entry_id = text(entry, "id") or f"entries[{index}]"
        entry_type = str(entry.get("type", ""))
        source = text(entry, "source").strip()
        translation = text(entry, "translation").strip()

        if translation.startswith(DRAFT_PREFIXES):
            placeholder_count += 1

        if entry_type == "dialogue" and previous_type not in {
            "character",
            "dialogue",
            "parenthetical",
        }:
            findings.append(
                Finding(
                    "WARN",
                    "draft.dialogue_without_character",
                    f"{entry_id} source={source}",
                )
            )

        if entry_type == "parenthetical":
            if source.startswith("(") and not source.endswith(")"):
                open_parenthetical = entry_id
            elif open_parenthetical and source.endswith(")"):
                open_parenthetical = None
        elif open_parenthetical:
            findings.append(
                Finding("WARN", "draft.parenthetical_unclosed", open_parenthetical)
            )
            open_parenthetical = None

        if (
            entry_type == "scene_heading"
            and source.startswith(("INT", "EXT", "I/E"))
            and not has_marker(entry, "scene_no")
        ):
            findings.append(
                Finding(
                    "WARN",
                    "draft.scene_heading_without_scene_no",
                    f"{entry_id} source={source}",
                )
            )

        if (
            entry_type == "character"
            and source.endswith("(CONT'D)")
            and not has_marker(entry, "contd")
        ):
            findings.append(
                Finding(
                    "WARN",
                    "draft.contd_text_without_marker",
                    f"{entry_id} source={source}",
                )
            )

        previous_type = entry_type

    if open_parenthetical:
        findings.append(
            Finding("WARN", "draft.parenthetical_unclosed", open_parenthetical)
        )
    if placeholder_count:
        findings.append(
            Finding(
                "INFO", "draft.placeholder_translations", f"count={placeholder_count}"
            )
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit draft batch structure before translation."
    )
    parser.add_argument("batch", type=Path)
    args = parser.parse_args()

    data = json.loads(args.batch.read_text(encoding="utf-8"))
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        print("FAIL draft.entries entries must be a list")
        return 1
    findings = audit_entries([entry for entry in entries if isinstance(entry, dict)])
    for finding in findings:
        print(finding.render())
    return 1 if any(finding.level == "FAIL" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
