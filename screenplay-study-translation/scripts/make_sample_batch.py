#!/usr/bin/env python3
"""Create a structural preview batch from a source marker inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import audit


SCENE_TYPES = {"scene_no", "split_scene"}


def marker_y(marker: dict[str, Any]) -> float:
    value = marker.get("y")
    return float(value) if isinstance(value, (int, float)) else 0.0


def marker_x(marker: dict[str, Any]) -> float:
    value = marker.get("x")
    return float(value) if isinstance(value, (int, float)) else 0.0


def scene_group_key(
    marker: dict[str, Any],
) -> tuple[object, object, object, object, int]:
    scene_key = marker.get("scene_key") or marker.get("scene_no") or marker.get("text")
    return (
        marker.get("pdf_page"),
        marker.get("display_page"),
        marker.get("type"),
        scene_key,
        round(marker_y(marker) / 3) * 3,
    )


def sorted_markers(markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        markers,
        key=lambda marker: (
            marker.get("pdf_page") or 0,
            -marker_y(marker),
            marker_x(marker),
        ),
    )


def group_markers(markers: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    scene_groups: dict[
        tuple[object, object, object, object, int], list[dict[str, Any]]
    ] = {}
    groups: list[list[dict[str, Any]]] = []
    for marker in markers:
        if marker.get("type") in SCENE_TYPES:
            scene_groups.setdefault(scene_group_key(marker), []).append(marker)
        else:
            groups.append([marker])
    groups.extend(scene_groups.values())
    return sorted(
        groups,
        key=lambda group: (
            group[0].get("pdf_page") or 0,
            -marker_y(group[0]),
            marker_x(group[0]),
        ),
    )


def entry_type(marker_type: str) -> str:
    if marker_type in SCENE_TYPES:
        return "scene_heading"
    if marker_type in {"contd", "voice_or_position"}:
        return "character"
    return "format_marker"


def source_text(group: list[dict[str, Any]]) -> str:
    marker_type = str(group[0].get("type", "marker"))
    texts = " / ".join(str(marker.get("text", "")) for marker in sorted_markers(group))
    return f"STRUCTURE PREVIEW {marker_type}: {texts}"


def translation_text(group: list[dict[str, Any]]) -> str:
    marker_type = str(group[0].get("type", "marker"))
    label = " / ".join(str(marker.get("text", "")) for marker in sorted_markers(group))
    translations = {
        "scene_no": "结构预览：场号",
        "split_scene": "结构预览：分段场号",
        "contd": "结构预览：续接标记",
        "more": "结构预览：下页续标记",
        "omitted": "结构预览：删去标记",
        "voice_or_position": "结构预览：声音/位置标记",
    }
    return f"{translations.get(marker_type, '结构预览：格式标记')} {label}"


def batch_from_markers(
    project_file: Path, config: dict[str, Any], markers: list[dict[str, Any]]
) -> dict[str, Any]:
    display_pages = [
        marker.get("display_page")
        for marker in markers
        if isinstance(marker.get("display_page"), int)
    ]
    start_page = min(display_pages) if display_pages else 0
    end_page = max(display_pages) if display_pages else 0
    inputs = audit.section(config, "inputs")
    entries: list[dict[str, Any]] = []
    for index, group in enumerate(group_markers(markers), start=1):
        first = group[0]
        display_page = int(first.get("display_page") or 0)
        entries.append(
            {
                "id": f"p{display_page:03d}-e{index:03d}",
                "type": entry_type(str(first.get("type", "marker"))),
                "pdf_page": int(first.get("pdf_page") or 0),
                "display_page": display_page,
                "source": source_text(group),
                "translation": translation_text(group),
                "markers": sorted_markers(group),
            }
        )
    return {
        "version": 1,
        "batch_id": f"structure-preview-p{start_page:03d}-{end_page:03d}",
        "source_pages": {"start": start_page, "end": end_page},
        "has_subtitles": inputs.get("subtitles") not in {None, ""},
        "entries": entries,
        "note": f"Structural preview generated from {project_file.name}; not a translation draft.",
    }


def output_path(
    project_file: Path, config: dict[str, Any], override: Path | None
) -> Path:
    if override is not None:
        return override.expanduser().resolve()
    outputs = audit.section(config, "outputs")
    work_dir = audit.resolve_path(project_file, outputs.get("work_dir") or "work")
    if work_dir is None:
        work_dir = project_file.parent / "work"
    return work_dir / "batches" / "structure-preview.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a structural preview batch from source markers."
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    project_file = args.project.expanduser().resolve()
    config = audit.load_simple_yaml(project_file)
    inventory_path, inventory = audit.load_marker_inventory(project_file, config)
    if inventory is None:
        raise FileNotFoundError(f"marker_inventory={inventory_path}")
    markers = inventory.get("markers")
    if not isinstance(markers, list):
        raise ValueError("marker inventory markers must be a list")
    batch = batch_from_markers(project_file, config, markers)
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
