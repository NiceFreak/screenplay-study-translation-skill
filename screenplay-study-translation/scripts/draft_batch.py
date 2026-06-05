#!/usr/bin/env python3
"""Create a draft translation batch skeleton from extracted source lines."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import audit
import make_sample_batch


SCENE_HEADING_RE = re.compile(r"^(INT|EXT|INT/EXT|I/E)[. ]")
TRANSITION_RE = re.compile(
    r"^(CUT TO|FADE|DISSOLVE|SMASH CUT|MATCH CUT|BACK TO|JUMP CUT)\b|:$"
)


def is_upperish(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    return (
        bool(letters) and sum(char.isupper() for char in letters) / len(letters) > 0.8
    )


def classify_line(
    row: dict[str, Any], previous_type: str | None, in_parenthetical: bool
) -> str:
    text = str(row.get("text", "")).strip()
    x = float(row.get("x", 0))
    if row.get("zone") == "page_number":
        return "page_heading"
    if in_parenthetical:
        return "parenthetical"
    if SCENE_HEADING_RE.match(text):
        return "scene_heading"
    if text.startswith("("):
        return "parenthetical"
    if TRANSITION_RE.match(text) and is_upperish(text):
        return "transition"
    if is_upperish(text) and len(text) <= 40 and x >= 220:
        return "character"
    if previous_type in {"character", "parenthetical", "dialogue"} and x >= 160:
        return "dialogue"
    if is_upperish(text) and len(text) <= 40:
        return "format_marker"
    return "action"


def marker_y(marker: dict[str, Any]) -> float:
    value = marker.get("y")
    return float(value) if isinstance(value, (int, float)) else 0.0


def row_y(row: dict[str, Any]) -> float:
    value = row.get("y")
    return float(value) if isinstance(value, (int, float)) else 0.0


def markers_for_row(
    row: dict[str, Any], markers: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    row_page = row.get("pdf_page")
    y = row_y(row)
    return [
        marker
        for marker in markers
        if marker.get("pdf_page") == row_page and abs(marker_y(marker) - y) <= 3
    ]


def marker_key(marker: dict[str, Any]) -> tuple[object, object, object, object, int]:
    return (
        marker.get("pdf_page"),
        marker.get("display_page"),
        marker.get("type"),
        marker.get("scene_key") or marker.get("text"),
        round(marker_y(marker) / 3) * 3,
    )


def synthetic_marker_entries(
    markers: list[dict[str, Any]], used_marker_ids: set[int], start_index: int
) -> list[dict[str, Any]]:
    groups: dict[tuple[object, object, object, object, int], list[dict[str, Any]]] = {}
    for marker in markers:
        if id(marker) in used_marker_ids:
            continue
        groups.setdefault(marker_key(marker), []).append(marker)

    entries: list[dict[str, Any]] = []
    for offset, group in enumerate(
        make_sample_batch.group_markers(
            [marker for group in groups.values() for marker in group]
        )
    ):
        first = group[0]
        display_page = int(first.get("display_page") or 0)
        marker_type = str(first.get("type", "unknown"))
        source = " / ".join(
            str(marker.get("text", ""))
            for marker in make_sample_batch.sorted_markers(group)
        )
        entry_type = (
            "scene_heading"
            if marker_type in make_sample_batch.SCENE_TYPES
            else "format_marker"
        )
        entries.append(
            {
                "id": f"p{display_page:03d}-m{start_index + offset:03d}",
                "type": entry_type,
                "pdf_page": int(first.get("pdf_page") or 0),
                "display_page": display_page,
                "source": f"STRUCTURE MARKER: {source}",
                "translation": translation_placeholder(entry_type, source),
                "markers": make_sample_batch.sorted_markers(group),
            }
        )
    return entries


def translation_placeholder(entry_type: str, source: str) -> str:
    labels = {
        "scene_heading": "待译场景标题",
        "action": "待译动作描写",
        "character": "待译角色提示",
        "parenthetical": "待译括号说明",
        "dialogue": "待译对白",
        "transition": "待译转场",
        "format_marker": "待译格式标记",
        "page_heading": "待处理页码",
    }
    return f"{labels.get(entry_type, '待译文本')}：{source}"


def source_pages(rows: list[dict[str, Any]]) -> dict[str, int]:
    pages = [
        row.get("display_page")
        for row in rows
        if isinstance(row.get("display_page"), int)
    ]
    return {"start": min(pages), "end": max(pages)} if pages else {"start": 0, "end": 0}


def page_in_range(value: Any, start: int | None, end: int | None) -> bool:
    if not isinstance(value, int):
        return False
    if start is not None and value < start:
        return False
    return not (end is not None and value > end)


def filter_by_display_page(
    rows: list[dict[str, Any]],
    markers: list[dict[str, Any]],
    start: int | None,
    end: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if start is None and end is None:
        return rows, markers
    filtered_rows = [
        row for row in rows if page_in_range(row.get("display_page"), start, end)
    ]
    filtered_markers = [
        marker
        for marker in markers
        if page_in_range(marker.get("display_page"), start, end)
    ]
    return filtered_rows, filtered_markers


def batch_from_lines(
    project_file: Path,
    config: dict[str, Any],
    rows: list[dict[str, Any]],
    markers: list[dict[str, Any]],
    display_page_start: int | None = None,
    display_page_end: int | None = None,
) -> dict[str, Any]:
    inputs = audit.section(config, "inputs")
    entries: list[dict[str, Any]] = []
    previous_type: str | None = None
    in_parenthetical = False
    used_marker_ids: set[int] = set()
    rows, markers = filter_by_display_page(
        rows, markers, display_page_start, display_page_end
    )
    body_rows = [row for row in rows if row.get("zone") != "page_number"]
    for index, row in enumerate(body_rows, start=1):
        entry_type = classify_line(row, previous_type, in_parenthetical)
        source = str(row.get("text", ""))
        display_page = int(row.get("display_page") or 0)
        entry = {
            "id": f"p{display_page:03d}-e{index:03d}",
            "type": entry_type,
            "pdf_page": int(row.get("pdf_page") or 0),
            "display_page": display_page,
            "source": source,
            "translation": translation_placeholder(entry_type, source),
        }
        row_markers = markers_for_row(row, markers)
        if row_markers:
            entry["markers"] = make_sample_batch.sorted_markers(row_markers)
            used_marker_ids.update(id(marker) for marker in row_markers)
        entries.append(entry)
        if entry_type == "parenthetical":
            stripped = source.strip()
            in_parenthetical = stripped.startswith("(") and not stripped.endswith(")")
            if in_parenthetical and stripped.endswith(")"):
                in_parenthetical = False
        else:
            in_parenthetical = False
        previous_type = entry_type
    entries.extend(synthetic_marker_entries(markers, used_marker_ids, len(entries) + 1))
    entries.sort(key=lambda entry: (entry["pdf_page"], entry["id"]))
    pages = source_pages(body_rows)
    return {
        "version": 1,
        "batch_id": f"draft-p{pages['start']:03d}-{pages['end']:03d}",
        "source_pages": pages,
        "has_subtitles": inputs.get("subtitles") not in {None, ""},
        "entries": entries,
        "note": f"Draft skeleton generated from {project_file.name}; translations are placeholders.",
    }


def load_source_lines(
    project_file: Path, config: dict[str, Any]
) -> list[dict[str, Any]]:
    outputs = audit.section(config, "outputs")
    source_lines_path = audit.resolve_path(
        project_file, outputs.get("source_lines") or "work/source-lines.json"
    )
    if source_lines_path is None or not source_lines_path.exists():
        raise FileNotFoundError(f"source_lines={source_lines_path}")
    payload = json.loads(source_lines_path.read_text(encoding="utf-8"))
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("source lines rows must be a list")
    return rows


def output_path(
    project_file: Path, config: dict[str, Any], override: Path | None
) -> Path:
    if override is not None:
        return override.expanduser().resolve()
    outputs = audit.section(config, "outputs")
    work_dir = audit.resolve_path(project_file, outputs.get("work_dir") or "work")
    if work_dir is None:
        work_dir = project_file.parent / "work"
    return work_dir / "batches" / "draft.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a draft translation batch skeleton from source lines."
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--display-page-start", type=int)
    parser.add_argument("--display-page-end", type=int)
    args = parser.parse_args()
    if (
        args.display_page_start is not None
        and args.display_page_end is not None
        and args.display_page_start > args.display_page_end
    ):
        parser.error(
            "--display-page-start must be less than or equal to --display-page-end"
        )

    project_file = args.project.expanduser().resolve()
    config = audit.load_simple_yaml(project_file)
    rows = load_source_lines(project_file, config)
    inventory_path, inventory = audit.load_marker_inventory(project_file, config)
    if inventory is None:
        raise FileNotFoundError(f"marker_inventory={inventory_path}")
    markers = inventory.get("markers")
    if not isinstance(markers, list):
        raise ValueError("marker inventory markers must be a list")
    batch = batch_from_lines(
        project_file,
        config,
        rows,
        markers,
        args.display_page_start,
        args.display_page_end,
    )
    out_path = output_path(project_file, config, args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"INFO batch {out_path}")
    print(f"INFO batch_entries {len(batch['entries'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
