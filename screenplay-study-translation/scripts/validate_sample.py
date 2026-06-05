#!/usr/bin/env python3
"""Run a compact structure validation pass for a real sample project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import audit
import parse_subtitles
import scan_markers


def count_by_type(markers: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for marker in markers:
        marker_type = marker.get("type")
        if isinstance(marker_type, str):
            counts[marker_type] = counts.get(marker_type, 0) + 1
    return counts


def render_counts(prefix: str, counts: dict[str, int]) -> list[str]:
    if not counts:
        return [f"WARN {prefix}.empty no items found"]
    return [f"INFO {prefix}.{key} {counts[key]}" for key in sorted(counts)]


def render_scan_details(scan: scan_markers.ScanResult) -> list[str]:
    lines: list[str] = []
    for key in sorted(scan.assumptions):
        lines.append(f"INFO scan_assumption.{key} {scan.assumptions[key]}")
    for key in sorted(scan.stats):
        level = (
            "WARN"
            if key == "scene_candidates_unmatched" and scan.stats[key]
            else "INFO"
        )
        lines.append(f"{level} scan_stat.{key} {scan.stats[key]}")
    for index, candidate in enumerate(scan.unmatched_scene_candidates, start=1):
        parts = " ".join(f"{key}={candidate[key]}" for key in sorted(candidate))
        lines.append(f"WARN scan_unmatched_scene_candidate.{index} {parts}")
    return lines


def y_bucket(marker: dict[str, object]) -> int | None:
    value = marker.get("y")
    if isinstance(value, (int, float)):
        return round(float(value) / 3) * 3
    return None


def render_scene_pair_checks(markers: list[dict[str, object]]) -> list[str]:
    pairs: dict[tuple[object, object, str, str, int | None], set[str]] = {}
    for marker in markers:
        marker_type = marker.get("type")
        if marker_type not in {"scene_no", "split_scene"}:
            continue
        scene_no = str(marker.get("scene_no") or marker.get("text") or "")
        key = (
            marker.get("pdf_page"),
            marker.get("display_page"),
            str(marker_type),
            scene_no,
            y_bucket(marker),
        )
        position = marker.get("position")
        if isinstance(position, str):
            pairs.setdefault(key, set()).add(position)

    lines: list[str] = []
    for key, positions in sorted(pairs.items(), key=lambda item: str(item[0])):
        if positions == {"left", "right"}:
            continue
        pdf_page, display_page, marker_type, scene_no, y_pos = key
        found = ",".join(sorted(positions)) if positions else "none"
        lines.append(
            "WARN marker_pair."
            f"{marker_type} pdf_page={pdf_page} display_page={display_page} "
            f"scene_no={scene_no} y={y_pos} positions={found}"
        )
    if not lines and pairs:
        lines.append("INFO marker_pair.scene_no all paired")
    return lines


def write_marker_inventory(
    project_file: Path, config: dict[str, object]
) -> tuple[Path, list[dict[str, object]]]:
    inputs = audit.section(config, "inputs")
    page_mapping = audit.section(config, "page_mapping")
    pdf_path = audit.resolve_path(project_file, inputs.get("screenplay_pdf"))
    if pdf_path is None or not pdf_path.exists():
        raise FileNotFoundError(f"screenplay_pdf={pdf_path}")
    offset = int(page_mapping.get("displayed_page_offset", 0))
    scan = scan_markers.scan_pdf_detailed(pdf_path, offset)
    out_path = scan_markers.write_inventory(project_file, config, scan.markers)
    return out_path, scan.markers


def scan_and_write_inventory(
    project_file: Path, config: dict[str, object]
) -> tuple[Path, list[dict[str, object]], scan_markers.ScanResult]:
    inputs = audit.section(config, "inputs")
    page_mapping = audit.section(config, "page_mapping")
    pdf_path = audit.resolve_path(project_file, inputs.get("screenplay_pdf"))
    if pdf_path is None or not pdf_path.exists():
        raise FileNotFoundError(f"screenplay_pdf={pdf_path}")
    offset = int(page_mapping.get("displayed_page_offset", 0))
    scan = scan_markers.scan_pdf_detailed(pdf_path, offset)
    out_path = scan_markers.write_inventory(project_file, config, scan.markers)
    return out_path, scan.markers, scan


def write_subtitles(
    project_file: Path, config: dict[str, object]
) -> tuple[Path | None, int | None]:
    inputs = audit.section(config, "inputs")
    outputs = audit.section(config, "outputs")
    subtitles_path = audit.resolve_path(project_file, inputs.get("subtitles"))
    if subtitles_path is None:
        return None, None
    if not subtitles_path.exists():
        raise FileNotFoundError(f"subtitles={subtitles_path}")
    events = parse_subtitles.parse_subtitles(subtitles_path)
    out_path = audit.resolve_path(
        project_file, outputs.get("subtitles_json") or "work/subtitles.json"
    )
    if out_path is None:
        raise ValueError("outputs.subtitles_json is missing")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "source": str(subtitles_path), "events": events}
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out_path, len(events)


def report_path(
    project_file: Path, config: dict[str, object], override: str | None
) -> Path:
    if override:
        return audit.resolve_path(project_file, override) or Path(override)
    outputs = audit.section(config, "outputs")
    work_dir = audit.resolve_path(project_file, outputs.get("work_dir") or "work")
    if work_dir is None:
        work_dir = project_file.parent / "work"
    return work_dir / "reports" / "sample-validation.txt"


def validate_sample(
    project_file: Path, report_override: str | None = None
) -> tuple[Path, list[str], bool]:
    config = audit.load_simple_yaml(project_file)
    lines = [f"INFO project {project_file}"]
    ok = True

    try:
        marker_path, markers, scan = scan_and_write_inventory(project_file, config)
        lines.append(f"INFO marker_inventory {marker_path}")
        lines.extend(render_counts("marker_count", count_by_type(markers)))
        lines.extend(render_scene_pair_checks(markers))
        lines.extend(render_scan_details(scan))
        if not markers:
            ok = False
    except Exception as exc:  # noqa: BLE001 - report compact validation failure.
        lines.append(f"FAIL marker_scan {exc}")
        ok = False

    try:
        subtitles_path, event_count = write_subtitles(project_file, config)
        if subtitles_path is None:
            lines.append("INFO subtitles not configured")
        else:
            lines.append(f"INFO subtitles_json {subtitles_path}")
            lines.append(f"INFO subtitle_events {event_count}")
    except Exception as exc:  # noqa: BLE001 - report compact validation failure.
        lines.append(f"FAIL subtitles {exc}")
        ok = False

    findings = audit.run(project_file, html=None, pdf=None, allow_missing_inputs=True)
    lines.extend(finding.render() for finding in findings)
    if any(finding.level == "FAIL" for finding in findings):
        ok = False

    out_path = report_path(project_file, config, report_override)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path, lines, ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a real screenplay sample project before translation."
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--report")
    args = parser.parse_args()

    project_file = args.project.expanduser().resolve()
    out_path, lines, ok = validate_sample(project_file, args.report)
    for line in lines:
        print(line)
    print(f"INFO report {out_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
