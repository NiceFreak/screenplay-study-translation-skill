#!/usr/bin/env python3
"""Run a compact structure validation pass for a real sample project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import audit
import parse_subtitles
import scan_markers
import subtitle_report


ISSUE_LEVELS = {"FAIL", "WARN", "UNCERTAIN"}


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
        lines.append(f"INFO scan_stat.{key} {scan.stats[key]}")
    for index, marker in enumerate(scan.known_markers[:50], start=1):
        parts = " ".join(f"{key}={marker[key]}" for key in sorted(marker))
        lines.append(f"INFO structural_signal.known_marker.{index} {parts}")
    for index, candidate in enumerate(scan.unclassified_signals, start=1):
        parts = " ".join(f"{key}={candidate[key]}" for key in sorted(candidate))
        lines.append(f"WARN warning_signal.unclassified.{index} {parts}")
    for index, candidate in enumerate(scan.noise_candidates, start=1):
        parts = " ".join(f"{key}={candidate[key]}" for key in sorted(candidate))
        lines.append(f"INFO noise_signal.candidate.{index} {parts}")
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
    out_path = scan_markers.write_inventory(
        project_file, config, scan.known_markers, scan
    )
    return out_path, scan.known_markers


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
    out_path = scan_markers.write_inventory(
        project_file, config, scan.known_markers, scan
    )
    return out_path, scan.known_markers, scan


def write_subtitles(
    project_file: Path, config: dict[str, object]
) -> tuple[Path | None, list[dict[str, Any]] | None]:
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
    return out_path, events


def work_dir_path(project_file: Path, config: dict[str, object]) -> Path:
    outputs = audit.section(config, "outputs")
    work_dir = audit.resolve_path(project_file, outputs.get("work_dir") or "work")
    return work_dir if work_dir is not None else project_file.parent / "work"


def report_path(
    project_file: Path, config: dict[str, object], override: str | None
) -> Path:
    if override:
        return audit.resolve_path(project_file, override) or Path(override)
    return work_dir_path(project_file, config) / "reports" / "sample-validation.txt"


def subtitle_report_path(project_file: Path, config: dict[str, object]) -> Path:
    return work_dir_path(project_file, config) / "reports" / "subtitle-report.txt"


def source_lines_path(project_file: Path, config: dict[str, object]) -> Path:
    outputs = audit.section(config, "outputs")
    out_path = audit.resolve_path(
        project_file, outputs.get("source_lines") or "work/source-lines.json"
    )
    return (
        out_path
        if out_path is not None
        else project_file.parent / "work" / "source-lines.json"
    )


def finding_log_path(project_file: Path, config: dict[str, object]) -> Path:
    return work_dir_path(project_file, config) / "logs" / "stage-1-2-findings.json"


def write_subtitle_report(
    project_file: Path, config: dict[str, object], events: list[dict[str, Any]]
) -> tuple[Path, list[str]]:
    out_path = subtitle_report_path(project_file, config)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = subtitle_report.build_report(events, term_limit=20)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path, lines


def source_line_pages(
    project_file: Path, config: dict[str, object]
) -> tuple[Path, list[int], list[int] | None]:
    path = source_lines_path(project_file, config)
    if not path.exists():
        return path, [], None

    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return path, [], None

    display_pages = sorted(
        {
            row["display_page"]
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("display_page"), int)
        }
    )
    pdf_pages = sorted(
        {
            row["pdf_page"]
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("pdf_page"), int)
        }
    )
    return path, display_pages, pdf_pages


def render_source_line_checks(
    project_file: Path, config: dict[str, object]
) -> list[str]:
    path, pages, _pdf_pages = source_line_pages(project_file, config)
    if not path.exists():
        return [f"INFO source_lines not_available path={path}"]
    if not pages:
        return [f"WARN source_lines.display_pages_empty path={path}"]

    lines = [
        f"INFO source_lines {path}",
        "INFO source_lines.display_pages "
        f"count={len(pages)} pages={audit.compact_ranges(pages)}",
    ]
    missing = [page for page in range(pages[0], pages[-1] + 1) if page not in pages]
    if missing:
        lines.append(
            "WARN source_lines.display_pages_missing "
            f"pages={audit.compact_ranges(missing)}"
        )
    return lines


def extraction_completeness_gate(
    project_file: Path, config: dict[str, object]
) -> tuple[list[str], bool]:
    inputs = audit.section(config, "inputs")
    pdf_path = audit.resolve_path(project_file, inputs.get("screenplay_pdf"))
    if pdf_path is None or not pdf_path.exists():
        return [f"UNCERTAIN extraction.screenplay_pdf_missing path={pdf_path}"], False

    source_path, _display_pages, pdf_pages = source_line_pages(project_file, config)
    if not source_path.exists():
        return [
            f"UNCERTAIN extraction.source_lines_missing path={source_path}",
            "UNCERTAIN extraction.completeness_unverified missing=source-lines",
        ], False
    if pdf_pages is None:
        return [
            f"UNCERTAIN extraction.source_lines_invalid path={source_path}",
            "UNCERTAIN extraction.completeness_unverified invalid=source-lines",
        ], False

    objects = scan_markers.pdf_objects(pdf_path)
    total_pages = scan_markers.pdf_page_count(objects)
    extracted_count = len(pdf_pages)
    lines = [
        f"INFO extraction.pdf_pages_total {total_pages}",
        f"INFO extraction.source_lines_pdf_pages count={extracted_count} pages={audit.compact_ranges(pdf_pages)}",
    ]
    expected_pages = list(range(1, total_pages + 1))
    missing_pages = sorted(set(expected_pages) - set(pdf_pages))
    extra_pages = sorted(set(pdf_pages) - set(expected_pages))
    if total_pages != extracted_count or missing_pages or extra_pages:
        if missing_pages:
            lines.append(
                "UNCERTAIN extraction.pdf_pages_missing "
                f"pages={audit.compact_ranges(missing_pages)}"
            )
        if extra_pages:
            lines.append(
                "UNCERTAIN extraction.pdf_pages_extra "
                f"pages={audit.compact_ranges(extra_pages)}"
            )
        lines.append(
            "UNCERTAIN extraction.completeness_unverified "
            f"pdf_pages={total_pages} extracted_pages={extracted_count}"
        )
        return lines, False
    lines.append("INFO extraction.completeness_verified true")
    return lines, True


def contract_state(level: str) -> str:
    if level == "FAIL":
        return "ISSUE DETECTED"
    if level == "WARN":
        return "OUT OF SCOPE FINDING"
    if level == "UNCERTAIN":
        return "UNCERTAIN"
    return "NO ISSUE DETECTED"


def overall_state(lines: list[str]) -> str:
    levels = {line.split(maxsplit=1)[0] for line in lines if line}
    if "FAIL" in levels:
        return "ISSUE DETECTED"
    if "UNCERTAIN" in levels:
        return "UNCERTAIN"
    if "WARN" in levels:
        return "OUT OF SCOPE FINDING"
    return "NO ISSUE DETECTED"


def finding_records(lines: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    active_assigned = False
    for line in lines:
        parts = line.split(maxsplit=2)
        if len(parts) < 2 or parts[0] not in ISSUE_LEVELS:
            continue
        level = parts[0]
        state = contract_state(level)
        issue_state = "PARKED"
        active = False
        if state in {"ISSUE DETECTED", "UNCERTAIN"}:
            issue_state = "OPEN" if not active_assigned else "FROZEN"
            active = not active_assigned
            active_assigned = True
        records.append(
            {
                "level": level,
                "code": parts[1],
                "message": parts[2] if len(parts) > 2 else "",
                "contract_state": state,
                "issue_state": issue_state,
                "active": active,
            }
        )
    return records


def signal_counts(lines: list[str]) -> dict[str, int]:
    counts = {"structural_signal": 0, "warning_signal": 0, "noise_signal": 0}
    for line in lines:
        parts = line.split(maxsplit=2)
        if len(parts) < 2:
            continue
        code = parts[1]
        for signal_name in counts:
            if code.startswith(signal_name + "."):
                counts[signal_name] += 1
    return counts


def write_finding_log(
    project_file: Path, config: dict[str, object], report: Path, lines: list[str]
) -> Path:
    out_path = finding_log_path(project_file, config)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "stage": "STAGE 1-2: EXTRACTION + SOURCE SIGNAL SCAN",
        "project": str(project_file),
        "report": str(report),
        "overall_state": overall_state(lines),
        "stage_gate": {
            "requires_stage2_signal_record_before_stage_3": True,
            "reason": "Stage 2 records structural, warning, and noise signals before batch creation.",
        },
        "signal_counts": signal_counts(lines),
        "records": finding_records(lines),
    }
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out_path


def validate_sample(
    project_file: Path,
    report_override: str | None = None,
    include_output_audit: bool = False,
) -> tuple[Path, list[str], bool]:
    config = audit.load_simple_yaml(project_file)
    lines = [f"INFO project {project_file}"]
    ok = True

    try:
        gate_lines, gate_ok = extraction_completeness_gate(project_file, config)
        lines.extend(gate_lines)
        if not gate_ok:
            ok = False
            out_path = report_path(project_file, config, report_override)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            lines.append("INFO stage_gate.stage_2 extraction_completeness=false")
            out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            log_path = write_finding_log(project_file, config, out_path, lines)
            lines.append(f"INFO finding_log {log_path}")
            out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return out_path, lines, False
    except Exception as exc:  # noqa: BLE001 - report compact validation failure.
        lines.append(f"UNCERTAIN extraction.completeness_check_failed {exc}")
        ok = False
        out_path = report_path(project_file, config, report_override)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines.append("INFO stage_gate.stage_2 extraction_completeness=false")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log_path = write_finding_log(project_file, config, out_path, lines)
        lines.append(f"INFO finding_log {log_path}")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out_path, lines, False

    try:
        marker_path, markers, scan = scan_and_write_inventory(project_file, config)
        lines.append(f"INFO marker_inventory {marker_path}")
        lines.extend(render_counts("marker_count", count_by_type(markers)))
        lines.extend(render_scene_pair_checks(markers))
        lines.extend(render_scan_details(scan))
    except Exception as exc:  # noqa: BLE001 - report compact validation failure.
        lines.append(f"FAIL marker_scan {exc}")
        ok = False

    try:
        subtitles_path, events = write_subtitles(project_file, config)
        if subtitles_path is None:
            lines.append("INFO subtitles not configured")
        else:
            lines.append(f"INFO subtitles_json {subtitles_path}")
            lines.append(f"INFO subtitle_events {len(events or [])}")
            report, report_lines = write_subtitle_report(
                project_file, config, events or []
            )
            lines.append(f"INFO subtitle_report {report}")
            lines.extend(report_lines)
    except Exception as exc:  # noqa: BLE001 - report compact validation failure.
        lines.append(f"FAIL subtitles {exc}")
        ok = False

    try:
        lines.extend(render_source_line_checks(project_file, config))
    except Exception as exc:  # noqa: BLE001 - report compact validation failure.
        lines.append(f"WARN source_lines.check_failed {exc}")

    findings = (
        audit.run(project_file, html=None, pdf=None, allow_missing_inputs=True)
        if include_output_audit
        else audit.check_required_files(project_file, config, allow_missing_inputs=True)
    )
    lines.extend(finding.render() for finding in findings)
    if any(finding.level == "FAIL" for finding in findings):
        ok = False

    out_path = report_path(project_file, config, report_override)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines.append("INFO stage_gate.stage_3 requires_stage2_signal_record=true")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log_path = write_finding_log(project_file, config, out_path, lines)
    lines.append(f"INFO finding_log {log_path}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path, lines, ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a real screenplay sample project before translation."
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--report")
    parser.add_argument(
        "--include-output-audit",
        action="store_true",
        help="Also audit configured reader outputs. Default validates Stage 1-2 only.",
    )
    args = parser.parse_args()

    project_file = args.project.expanduser().resolve()
    out_path, lines, ok = validate_sample(
        project_file, args.report, include_output_audit=args.include_output_audit
    )
    for line in lines:
        print(line)
    print(f"INFO report {out_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
