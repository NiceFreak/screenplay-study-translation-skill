#!/usr/bin/env python3
"""Suggest deterministic translation batch ranges without modifying project state."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import audit
import draft_batch


DEFAULT_MIN_PAGES = 5
DEFAULT_MAX_PAGES = 10
MAX_ENTRIES_PER_BATCH = 110
MAX_DIALOGUE_PER_BATCH = 65
MAX_MARKERS_PER_BATCH = 18


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_source_lines(
    project_file: Path, config: dict[str, Any]
) -> list[dict[str, Any]]:
    outputs = audit.section(config, "outputs")
    source_lines_path = audit.resolve_path(
        project_file, outputs.get("source_lines") or "work/source-lines.json"
    )
    if source_lines_path is None or not source_lines_path.exists():
        raise FileNotFoundError(f"source_lines={source_lines_path}")
    payload = load_json(source_lines_path)
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("source-lines.json must contain rows list")
    return [row for row in rows if isinstance(row, dict)]


def load_markers(project_file: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    inventory_path, inventory = audit.load_marker_inventory(project_file, config)
    if inventory is None:
        raise FileNotFoundError(f"marker_inventory={inventory_path}")
    markers = inventory.get("markers")
    if not isinstance(markers, list):
        markers = inventory.get("known_markers")
    if not isinstance(markers, list):
        return []
    return [marker for marker in markers if isinstance(marker, dict)]


def display_pages(rows: list[dict[str, Any]]) -> list[int]:
    pages = {
        row.get("display_page")
        for row in rows
        if isinstance(row.get("display_page"), int)
        and row.get("display_page", 0) > 0
        and row.get("zone") != "page_number"
    }
    return sorted(pages)


def page_counts(entries: list[dict[str, Any]]) -> dict[int, Counter[str]]:
    counts: dict[int, Counter[str]] = {}
    for entry in entries:
        page = entry.get("display_page")
        if not isinstance(page, int) or page <= 0:
            continue
        page_counter = counts.setdefault(page, Counter())
        page_counter["entries"] += 1
        entry_type = str(entry.get("type") or "")
        if entry_type:
            page_counter[entry_type] += 1
    return counts


def marker_counts(markers: list[dict[str, Any]]) -> Counter[int]:
    counts: Counter[int] = Counter()
    for marker in markers:
        page = marker.get("display_page")
        if isinstance(page, int) and page > 0:
            counts[page] += 1
    return counts


def range_stats(
    pages: list[int],
    counts: dict[int, Counter[str]],
    markers_by_page: Counter[int],
) -> dict[str, int]:
    stats = Counter()
    for page in pages:
        stats.update(counts.get(page, Counter()))
        stats["markers"] += markers_by_page.get(page, 0)
    return dict(stats)


def exceeds_safe_limits(stats: dict[str, int]) -> bool:
    return (
        stats.get("entries", 0) > MAX_ENTRIES_PER_BATCH
        or stats.get("dialogue", 0) > MAX_DIALOGUE_PER_BATCH
        or stats.get("markers", 0) > MAX_MARKERS_PER_BATCH
    )


def plan_ranges(
    pages: list[int],
    counts: dict[int, Counter[str]],
    markers_by_page: Counter[int],
    min_pages: int,
    max_pages: int,
) -> list[dict[str, Any]]:
    ranges: list[dict[str, Any]] = []
    index = 0
    while index < len(pages):
        start_index = index
        end_index = min(len(pages), start_index + min_pages) - 1
        if end_index < start_index:
            break
        while end_index + 1 < len(pages) and (end_index - start_index + 1) < max_pages:
            candidate_pages = pages[start_index : end_index + 2]
            if exceeds_safe_limits(
                range_stats(candidate_pages, counts, markers_by_page)
            ):
                break
            end_index += 1
        selected_pages = pages[start_index : end_index + 1]
        stats = range_stats(selected_pages, counts, markers_by_page)
        ranges.append(
            {
                "display_page_start": selected_pages[0],
                "display_page_end": selected_pages[-1],
                "page_count": len(selected_pages),
                "stats": stats,
                "risk": "standard"
                if len(selected_pages) <= min_pages
                else "low_density",
            }
        )
        index = end_index + 1
    return ranges


def output_path(
    project_file: Path, config: dict[str, Any], override: Path | None
) -> Path:
    if override is not None:
        path = override.expanduser()
        return path if path.is_absolute() else project_file.parent / path
    outputs = audit.section(config, "outputs")
    work_dir = audit.resolve_path(project_file, outputs.get("work_dir") or "work")
    if work_dir is None:
        work_dir = project_file.parent / "work"
    return work_dir / "reports" / "batch-plan.json"


def build_plan(project_file: Path, min_pages: int, max_pages: int) -> dict[str, Any]:
    config = audit.load_simple_yaml(project_file)
    rows = load_source_lines(project_file, config)
    markers = load_markers(project_file, config)
    entries = draft_batch.batch_from_lines(project_file, config, rows, markers).get(
        "entries"
    )
    if not isinstance(entries, list):
        entries = []
    pages = display_pages(rows)
    counts = page_counts([entry for entry in entries if isinstance(entry, dict)])
    markers_by_page = marker_counts(markers)
    ranges = plan_ranges(pages, counts, markers_by_page, min_pages, max_pages)
    return {
        "version": 1,
        "kind": "batch_plan",
        "project": {
            "project_file": str(project_file),
            "title": audit.section(config, "project").get("title"),
            "chinese_title": audit.section(config, "project").get("chinese_title"),
        },
        "policy": {
            "min_pages": min_pages,
            "max_pages": max_pages,
            "max_entries_per_batch": MAX_ENTRIES_PER_BATCH,
            "max_dialogue_per_batch": MAX_DIALOGUE_PER_BATCH,
            "max_markers_per_batch": MAX_MARKERS_PER_BATCH,
            "effect": "advisory only; does not modify batches or pipeline state",
        },
        "ranges": ranges,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Suggest deterministic displayed-page batch ranges."
    )
    parser.add_argument("project", type=Path, help="Path to project.yaml.")
    parser.add_argument("--min-pages", type=int, default=DEFAULT_MIN_PAGES)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.min_pages < 1:
        parser.error("--min-pages must be positive")
    if args.max_pages < args.min_pages:
        parser.error("--max-pages must be greater than or equal to --min-pages")

    project_file = args.project.expanduser().resolve()
    config = audit.load_simple_yaml(project_file)
    plan = build_plan(project_file, args.min_pages, args.max_pages)
    out_path = output_path(project_file, config, args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"INFO batch_plan {out_path}")
    print(f"INFO batch_ranges {len(plan['ranges'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
