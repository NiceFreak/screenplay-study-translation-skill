#!/usr/bin/env python3
"""Extract simple PDF text rows with coordinates for screenplay study work."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import audit
import scan_markers


BODY_LEFT_X = 90.0
LINE_Y_TOLERANCE = 3
WORD_GAP = 10.0
PAGE_NUMBER_RE = re.compile(r"\d+\.?")


def text_rows(pdf_path: Path, displayed_page_offset: int) -> list[dict[str, Any]]:
    objects = scan_markers.pdf_objects(pdf_path)
    rows: list[dict[str, Any]] = []
    seen: set[tuple[int, str, int, int]] = set()
    for page_index, (_page_obj, content_id) in enumerate(
        scan_markers.page_content_ids(objects), start=1
    ):
        data = scan_markers.content_stream(objects, content_id)
        for op in scan_markers.iter_text_ops(data):
            raw_text = scan_markers.normalize_pdf_text(
                scan_markers.pdf_unescape(op["text"])
            )
            text = re.sub(r"\s+", " ", raw_text).strip()
            if not text:
                continue
            x = float(op["x"])
            y = float(op["y"])
            key = (page_index, text, round(x), round(y))
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "pdf_page": page_index,
                    "display_page": page_index + displayed_page_offset,
                    "text": text,
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "source_layer": str(op["source_layer"]),
                    "zone": "raw",
                }
            )
    return sorted(
        rows, key=lambda row: (row["pdf_page"], -float(row["y"]), float(row["x"]))
    )


def line_key(row: dict[str, Any]) -> tuple[object, object, str, int]:
    return (
        row.get("pdf_page"),
        row.get("display_page"),
        round(float(row.get("y", 0)) / LINE_Y_TOLERANCE) * LINE_Y_TOLERANCE,
    )


def row_key(row: dict[str, Any]) -> tuple[object, str, float, float]:
    return (
        row.get("pdf_page"),
        str(row.get("text")),
        round(float(row["x"]), 3),
        round(float(row["y"]), 3),
    )


def scene_marker_row_keys(
    markers: list[dict[str, Any]],
) -> set[tuple[object, str, float, float]]:
    keys: set[tuple[object, str, float, float]] = set()
    for marker in markers:
        if marker.get("type") not in scan_markers.SCENE_MARKER_TYPES:
            continue
        keys.add(
            (
                marker.get("pdf_page"),
                str(marker.get("text")),
                round(float(marker["x"]), 3),
                round(float(marker["y"]), 3),
            )
        )
    return keys


def line_zone(line: dict[str, Any]) -> str:
    text = str(line.get("text", "")).strip()
    if PAGE_NUMBER_RE.fullmatch(text) and float(line["y"]) >= 720:
        return "page_number"
    return "body" if float(line["x"]) >= BODY_LEFT_X else "margin"


def join_row_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: float(row["x"]))
    parts: list[str] = []
    previous_x: float | None = None
    for row in ordered:
        text = str(row["text"])
        x = float(row["x"])
        if previous_x is not None and x - previous_x > WORD_GAP:
            parts.append(" ")
        parts.append(text)
        previous_x = x
    line = {
        "pdf_page": ordered[0]["pdf_page"],
        "display_page": ordered[0]["display_page"],
        "text": "".join(parts),
        "x": ordered[0]["x"],
        "y": ordered[0]["y"],
        "source_layer": "merged",
        "parts": len(ordered),
    }
    line["zone"] = line_zone(line)
    return line


def merge_text_rows(
    rows: list[dict[str, Any]], markers: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scene_keys = scene_marker_row_keys(markers)
    groups: dict[tuple[object, object, str, int], list[dict[str, Any]]] = {}
    removed_scene_markers = 0
    for row in rows:
        if row_key(row) in scene_keys:
            removed_scene_markers += 1
            continue
        groups.setdefault(line_key(row), []).append(row)
    merged = [join_row_group(group) for group in groups.values()]
    corrections = [
        {
            "type": "remove_promoted_scene_markers",
            "original_count": removed_scene_markers,
            "corrected_count": 0,
            "reason": "Scene numbers are tracked in source-markers.json and removed from source text rows.",
            "confidence": "high",
        },
        {
            "type": "merge_character_rows",
            "original_count": len(rows) - removed_scene_markers,
            "corrected_count": len(merged),
            "reason": "PDF text layer emits character-level Tj operations; rows are merged by page and y coordinate.",
            "confidence": "high",
        },
    ]
    return sorted(
        merged, key=lambda row: (row["pdf_page"], -float(row["y"]), float(row["x"]))
    ), corrections


def printed_page_number(row: dict[str, Any]) -> int | None:
    if row.get("zone") != "page_number":
        return None
    text = str(row.get("text", "")).strip().rstrip(".")
    return int(text) if text.isdigit() else None


def infer_printed_pages(
    rows: list[dict[str, Any]],
) -> tuple[dict[int, int], list[dict[str, Any]]]:
    display_pages = sorted(
        {
            row["display_page"]
            for row in rows
            if isinstance(row.get("display_page"), int)
        }
    )
    explicit = {
        int(row["display_page"]): page_number
        for row in rows
        if isinstance(row.get("display_page"), int)
        and (page_number := printed_page_number(row)) is not None
    }
    if not explicit:
        return {}, []

    offsets: dict[int, int] = {}
    for display_page, printed_page in explicit.items():
        offset = printed_page - display_page
        offsets[offset] = offsets.get(offset, 0) + 1
    best_offset, support = max(offsets.items(), key=lambda item: item[1])
    inferred: dict[int, int] = {}
    missing: list[int] = []
    for display_page in display_pages:
        expected = display_page + best_offset
        if expected < 1:
            continue
        if explicit.get(display_page, expected) != expected:
            return explicit, [
                {
                    "type": "printed_page_sequence_ambiguous",
                    "original_count": len(explicit),
                    "corrected_count": len(explicit),
                    "reason": "Explicit printed page numbers do not form a stable offset sequence.",
                    "confidence": "low",
                }
            ]
        inferred[display_page] = expected
        if display_page not in explicit:
            missing.append(display_page)

    corrections: list[dict[str, Any]] = [
        {
            "type": "infer_printed_page_numbers",
            "original_count": len(explicit),
            "corrected_count": len(inferred),
            "reason": f"Printed page numbers follow display_page + {best_offset} with {support} explicit examples.",
            "confidence": "high" if support >= 2 else "medium",
        }
    ]
    if missing:
        corrections.append(
            {
                "type": "fill_missing_printed_page_numbers",
                "original_count": len(explicit),
                "corrected_count": len(inferred),
                "reason": f"Missing printed page numbers inferred for display pages: {missing}.",
                "confidence": "high" if support >= 2 else "medium",
            }
        )
    return inferred, corrections


def apply_printed_pages(
    rows: list[dict[str, Any]], printed_pages: dict[int, int]
) -> list[dict[str, Any]]:
    for row in rows:
        display_page = row.get("display_page")
        if isinstance(display_page, int) and display_page in printed_pages:
            row["printed_page"] = printed_pages[display_page]
            if row.get("zone") == "page_number":
                row["zone"] = "page_number"
    return rows


def write_lines(
    project_file: Path,
    config: dict[str, Any],
    rows: list[dict[str, Any]],
    corrections: list[dict[str, Any]],
) -> Path:
    inputs = audit.section(config, "inputs")
    outputs = audit.section(config, "outputs")
    pdf_path = audit.resolve_path(project_file, inputs.get("screenplay_pdf"))
    out_path = audit.resolve_path(
        project_file, outputs.get("source_lines") or "work/source-lines.json"
    )
    if out_path is None:
        raise ValueError("source lines output path is missing")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "source": {"screenplay_pdf": str(pdf_path) if pdf_path else None},
        "assumptions": {
            "text_operator": "Tj",
            "body_left_x": BODY_LEFT_X,
            "line_y_tolerance": LINE_Y_TOLERANCE,
            "word_gap": WORD_GAP,
            "promoted_scene_markers_removed": True,
            "displayed_page_offset": audit.section(config, "page_mapping").get(
                "displayed_page_offset", 0
            ),
        },
        "corrections": corrections,
        "rows": rows,
    }
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out_path


def count_zones(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        zone = str(row.get("zone", "unknown"))
        counts[zone] = counts.get(zone, 0) + 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract simple PDF text rows with coordinates."
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    project_file = args.project.expanduser().resolve()
    config = audit.load_simple_yaml(project_file)
    inputs = audit.section(config, "inputs")
    page_mapping = audit.section(config, "page_mapping")
    pdf_path = audit.resolve_path(project_file, inputs.get("screenplay_pdf"))
    if pdf_path is None or not pdf_path.exists():
        print(f"FAIL file.missing screenplay_pdf={pdf_path}", file=sys.stderr)
        return 1
    offset = int(page_mapping.get("displayed_page_offset", 0))
    scan = scan_markers.scan_pdf_detailed(pdf_path, offset)
    raw_rows = text_rows(pdf_path, offset)
    rows, corrections = merge_text_rows(raw_rows, scan.markers)
    printed_pages, page_corrections = infer_printed_pages(rows)
    rows = apply_printed_pages(rows, printed_pages)
    corrections.extend(page_corrections)
    if args.output is not None:
        outputs = audit.section(config, "outputs")
        outputs["source_lines"] = str(args.output)
    out_path = write_lines(project_file, config, rows, corrections)
    print(f"INFO source_lines {out_path}")
    print(f"INFO text_rows {len(rows)}")
    print(f"INFO text_rows.raw {len(raw_rows)}")
    for correction in corrections:
        print(
            "INFO correction."
            f"{correction['type']} original={correction['original_count']} corrected={correction['corrected_count']}"
        )
    for zone, count in sorted(count_zones(rows).items()):
        print(f"INFO text_rows.{zone} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
