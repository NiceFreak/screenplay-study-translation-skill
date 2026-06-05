#!/usr/bin/env python3
"""Audit screenplay study project outputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    level: str
    code: str
    message: str

    def render(self) -> str:
        return f"{self.level} {self.code} {self.message}"


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def load_simple_yaml(path: Path) -> dict[str, Any]:
    """Load the small project.yaml subset used by this skill.

    Supports top-level mappings and one nested mapping level. This avoids a
    mandatory PyYAML dependency for the audit skeleton.
    """
    data: dict[str, Any] = {}
    current: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not raw_line.startswith(" "):
            if ":" not in line:
                raise ValueError(f"invalid YAML line: {raw_line}")
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = parse_scalar(value)
                current = None
            else:
                data[key] = {}
                current = key
            continue
        if current is None or not isinstance(data.get(current), dict):
            raise ValueError(f"nested value without parent: {raw_line}")
        if ":" not in line:
            raise ValueError(f"invalid YAML line: {raw_line}")
        key, value = line.split(":", 1)
        data[current][key.strip()] = parse_scalar(value)
    return data


def resolve_path(project_file: Path, value: Any) -> Path | None:
    if value in {None, ""}:
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = project_file.parent / path
    return path


def section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name)
    return value if isinstance(value, dict) else {}


def check_required_files(
    project_file: Path, config: dict[str, Any], allow_missing_inputs: bool
) -> list[Finding]:
    findings: list[Finding] = []
    inputs = section(config, "inputs")
    audit = section(config, "audit")
    require_subtitles = bool(audit.get("require_subtitles", False))

    screenplay = resolve_path(project_file, inputs.get("screenplay_pdf"))
    if screenplay is None:
        findings.append(
            Finding(
                "FAIL", "config.screenplay_pdf", "inputs.screenplay_pdf is required"
            )
        )
    elif not screenplay.exists():
        level = "WARN" if allow_missing_inputs else "FAIL"
        findings.append(Finding(level, "file.missing", f"screenplay_pdf={screenplay}"))
    else:
        findings.append(Finding("INFO", "file.screenplay_pdf", str(screenplay)))

    subtitles = resolve_path(project_file, inputs.get("subtitles"))
    if subtitles is None:
        level = "FAIL" if require_subtitles else "INFO"
        findings.append(Finding(level, "file.subtitles", "not configured"))
    elif not subtitles.exists():
        level = "FAIL" if require_subtitles else "WARN"
        findings.append(Finding(level, "file.subtitles_missing", str(subtitles)))
    else:
        findings.append(Finding("INFO", "file.subtitles", str(subtitles)))

    return findings


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


def explicit_marker_count(html: str, marker_type: str) -> int:
    data_attr = rf"\bdata-marker-type=[\"']{re.escape(marker_type)}[\"']"
    class_attr = rf"\bclass=[\"'][^\"']*\bmarker-{re.escape(marker_type)}\b[^\"']*[\"']"
    return sum(
        1
        for tag in re.findall(r"<[^>]+>", html)
        if re.search(data_attr, tag) or re.search(class_attr, tag)
    )


def explicit_marker_counts(html: str, marker_types: set[str]) -> dict[str, int]:
    return {
        marker_type: explicit_marker_count(html, marker_type)
        for marker_type in marker_types
    }


def page_in_range(value: Any, start: int | None, end: int | None) -> bool:
    if not isinstance(value, int):
        return False
    if start is not None and value < start:
        return False
    return not (end is not None and value > end)


def html_marker_counts(html: str) -> dict[str, int]:
    plain = strip_tags(html)
    scene_no_spans = re.findall(
        r'<span class="[^"]*\bscene-no\b[^"]*">([^<]+)</span>', html
    )
    scene_no = explicit_marker_count(html, "scene_no")
    contd = explicit_marker_count(html, "contd")
    more = explicit_marker_count(html, "more")
    omitted = explicit_marker_count(html, "omitted")
    return {
        "contd": contd if contd else len(re.findall(r"[（(]续[）)]", plain)),
        "more": more
        if more
        else len(re.findall(r"[（(]?下页续[）)]?|[（(]?MORE[）)]?", plain)),
        "omitted": omitted
        if omitted
        else len(re.findall(r"本场删去|删去场次|删场|OMITTED", plain)),
        "scene_no": scene_no if scene_no else len(scene_no_spans),
        "split_scene": explicit_marker_count(html, "split_scene"),
        "voice_or_position": explicit_marker_count(html, "voice_or_position"),
    }


def check_internal_links(html: str) -> list[Finding]:
    findings: list[Finding] = []
    ids = set(re.findall(r"\bid=[\"']([^\"']+)[\"']", html))
    targets = re.findall(r"\bhref=[\"']#([^\"']+)[\"']", html)
    missing = sorted({target for target in targets if target not in ids})
    if missing:
        findings.append(
            Finding("FAIL", "html.internal_links", f"missing={','.join(missing[:10])}")
        )
    elif targets:
        findings.append(
            Finding("INFO", "html.internal_links", f"checked={len(targets)}")
        )
    return findings


def check_html(
    project_file: Path, config: dict[str, Any], html_override: str | None
) -> list[Finding]:
    findings: list[Finding] = []
    outputs = section(config, "outputs")
    inputs = section(config, "inputs")
    html_path = resolve_path(project_file, html_override or outputs.get("html"))
    if html_path is None:
        findings.append(Finding("INFO", "html.skip", "no HTML path configured"))
        return findings
    if not html_path.exists():
        findings.append(Finding("WARN", "html.missing", str(html_path)))
        return findings

    text = html_path.read_text(encoding="utf-8", errors="replace")
    plain = strip_tags(text)
    findings.append(Finding("INFO", "html.file", str(html_path)))

    forbidden_patterns = {
        "html.task_label": r"任务\s*\d+|task-\d+",
        "html.debug": r"DEBUG|debug|TODO",
        "html.generic_action": r"剧本在这一动作段落推进场面、人物位置和情绪状态",
    }
    for code, pattern in forbidden_patterns.items():
        hits = len(re.findall(pattern, plain, flags=re.I))
        if hits:
            findings.append(Finding("FAIL", code, f"hits={hits}"))

    subtitle_labels = len(re.findall(r"字幕匹配|字幕差异|字幕未见", plain))
    subtitles_configured = inputs.get("subtitles") not in {None, ""}
    if subtitle_labels and not subtitles_configured:
        findings.append(
            Finding(
                "FAIL",
                "html.subtitle_labels_without_subtitles",
                f"hits={subtitle_labels}",
            )
        )
    elif subtitle_labels:
        findings.append(
            Finding("INFO", "html.subtitle_labels", f"hits={subtitle_labels}")
        )

    duplicate_index_titles = len(re.findall(r"场次索引", plain))
    if duplicate_index_titles > 1:
        findings.append(
            Finding("WARN", "html.scene_index_titles", f"hits={duplicate_index_titles}")
        )

    raw_markers = re.findall(r"\((?:CONT'D|MORE|O\.S\.|O\.C\.|V\.O\.)\)", plain)
    if raw_markers:
        findings.append(
            Finding(
                "WARN", "html.raw_parenthetical_markers", f"hits={len(raw_markers)}"
            )
        )

    findings.extend(check_internal_links(text))
    return findings


def check_pdf(
    project_file: Path, config: dict[str, Any], pdf_override: str | None
) -> list[Finding]:
    findings: list[Finding] = []
    outputs = section(config, "outputs")
    audit = section(config, "audit")
    pdf_path = resolve_path(project_file, pdf_override or outputs.get("pdf"))
    if pdf_path is None:
        findings.append(Finding("INFO", "pdf.skip", "no PDF path configured"))
        return findings
    if not pdf_path.exists():
        findings.append(Finding("WARN", "pdf.missing", str(pdf_path)))
        return findings

    data = pdf_path.read_bytes().decode("latin1", errors="ignore")
    counts = [int(value) for value in re.findall(r"/Count\s+(\d+)", data)]
    boxes = re.findall(r"/MediaBox\s*\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]", data)
    findings.append(Finding("INFO", "pdf.file", str(pdf_path)))
    if counts:
        findings.append(Finding("INFO", "pdf.pages", str(max(counts))))
    if boxes:
        width, height = map(float, boxes[0])
        width_mm = round(width * 25.4 / 72, 1)
        height_mm = round(height * 25.4 / 72, 1)
        findings.append(Finding("INFO", "pdf.size_mm", f"{width_mm}x{height_mm}"))
        if audit.get("paper_size") == "A4" and (
            abs(width_mm - 210.0) > 1 or abs(height_mm - 297.0) > 1
        ):
            findings.append(
                Finding(
                    "FAIL",
                    "pdf.paper_size",
                    f"expected=A4 actual={width_mm}x{height_mm}",
                )
            )

    return findings


def load_marker_inventory(
    project_file: Path, config: dict[str, Any]
) -> tuple[Path | None, dict[str, Any] | None]:
    outputs = section(config, "outputs")
    inventory_path = resolve_path(
        project_file, outputs.get("marker_inventory") or "work/source-markers.json"
    )
    if inventory_path is None or not inventory_path.exists():
        return inventory_path, None
    return inventory_path, json.loads(inventory_path.read_text(encoding="utf-8"))


def check_marker_inventory(
    project_file: Path,
    config: dict[str, Any],
    html_override: str | None,
    display_page_start: int | None,
    display_page_end: int | None,
) -> list[Finding]:
    findings: list[Finding] = []
    audit = section(config, "audit")
    inventory_path, inventory = load_marker_inventory(project_file, config)
    if inventory is None:
        findings.append(
            Finding("WARN", "marker_inventory.missing", str(inventory_path))
        )
        return findings

    markers = inventory.get("markers", [])
    if not isinstance(markers, list):
        findings.append(
            Finding("FAIL", "marker_inventory.invalid", "markers must be a list")
        )
        return findings
    if display_page_start is not None or display_page_end is not None:
        markers = [
            marker
            for marker in markers
            if isinstance(marker, dict)
            and page_in_range(
                marker.get("display_page"), display_page_start, display_page_end
            )
        ]
        findings.append(
            Finding(
                "INFO",
                "marker_inventory.page_range",
                f"start={display_page_start} end={display_page_end}",
            )
        )

    source_counts: dict[str, int] = {}
    for marker in markers:
        if isinstance(marker, dict) and isinstance(marker.get("type"), str):
            marker_type = marker["type"]
            source_counts[marker_type] = source_counts.get(marker_type, 0) + 1
    findings.append(Finding("INFO", "marker_inventory.file", str(inventory_path)))
    for marker_type in sorted(source_counts):
        findings.append(
            Finding(
                "INFO",
                "marker_inventory.count",
                f"{marker_type}={source_counts[marker_type]}",
            )
        )

    outputs = section(config, "outputs")
    html_path = resolve_path(project_file, html_override or outputs.get("html"))
    if html_path is None or not html_path.exists():
        findings.append(Finding("INFO", "marker_inventory.html_compare", "skipped"))
        return findings

    html = html_path.read_text(encoding="utf-8", errors="replace")
    html_counts = html_marker_counts(html)
    explicit_counts = explicit_marker_counts(html, set(source_counts))
    require_structured = bool(audit.get("require_structured_markers", False))
    for marker_type in (
        "contd",
        "more",
        "omitted",
        "scene_no",
        "split_scene",
        "voice_or_position",
    ):
        source_count = source_counts.get(marker_type, 0)
        html_count = html_counts.get(marker_type, 0)
        if source_count == 0:
            continue
        explicit_count = explicit_counts.get(marker_type, 0)
        if require_structured and explicit_count != source_count:
            findings.append(
                Finding(
                    "FAIL",
                    f"marker_structured.{marker_type}",
                    f"source={source_count} structured_html={explicit_count}",
                )
            )
            continue
        if source_count != html_count:
            findings.append(
                Finding(
                    "FAIL",
                    f"marker_count.{marker_type}",
                    f"source={source_count} html={html_count}",
                )
            )
        else:
            findings.append(
                Finding(
                    "INFO",
                    f"marker_count.{marker_type}",
                    f"source={source_count} html={html_count}",
                )
            )
    return findings


def run(
    project_file: Path,
    html: str | None,
    pdf: str | None,
    allow_missing_inputs: bool,
    display_page_start: int | None = None,
    display_page_end: int | None = None,
) -> list[Finding]:
    config = load_simple_yaml(project_file)
    findings: list[Finding] = []
    findings.extend(check_required_files(project_file, config, allow_missing_inputs))
    findings.extend(check_html(project_file, config, html))
    findings.extend(check_pdf(project_file, config, pdf))
    findings.extend(
        check_marker_inventory(
            project_file, config, html, display_page_start, display_page_end
        )
    )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit screenplay study project outputs."
    )
    parser.add_argument("project", type=Path, help="Path to project.yaml")
    parser.add_argument("--html", help="Override HTML output path")
    parser.add_argument("--pdf", help="Override PDF output path")
    parser.add_argument(
        "--display-page-start",
        type=int,
        help="Audit source markers from this displayed page onward.",
    )
    parser.add_argument(
        "--display-page-end",
        type=int,
        help="Audit source markers through this displayed page.",
    )
    parser.add_argument(
        "--allow-missing-inputs",
        action="store_true",
        help="Downgrade missing source input files to WARN for template smoke tests.",
    )
    args = parser.parse_args(argv)
    if (
        args.display_page_start is not None
        and args.display_page_end is not None
        and args.display_page_start > args.display_page_end
    ):
        parser.error(
            "--display-page-start must be less than or equal to --display-page-end"
        )

    findings = run(
        args.project.expanduser().resolve(),
        args.html,
        args.pdf,
        args.allow_missing_inputs,
        args.display_page_start,
        args.display_page_end,
    )
    for finding in findings:
        print(finding.render())
    return 1 if any(finding.level == "FAIL" for finding in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
