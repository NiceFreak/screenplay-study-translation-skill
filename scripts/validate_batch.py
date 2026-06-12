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
}
SUBTITLE_LABELS = {"字幕匹配", "字幕差异", "字幕未见"}
LAYOUT_TYPES = {"parallel_dialogue"}
SUBTITLE_TIMESTAMP_FIELDS = {
    "subtitle_event_index",
    "subtitle_start",
    "subtitle_end",
    "subtitle_match_confidence",
}
SUBTITLE_MATCH_CONFIDENCE = {"high", "low"}
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
RAW_FORMAT_MARKER_RE = (
    r"(?<![A-Za-z])(?:\((?:CONT['’]D|MORE|O\.S\.|O\.C\.|V\.O\.)\)|"
    r"OMITTED|CONT['’]D|MORE|V\.O\.|O\.S\.|O\.C\.|INT\.|EXT\.|"
    r"CUT TO:?|FADE IN:?|FADE OUT:?|DISSOLVE TO:?|SMASH CUT:?|MATCH CUT:?)"
    r"(?![A-Za-z])"
)
INLINE_MARKUP_RE = re.compile(
    r"\[\[(.+?)\]\]|__(.+?)__|\*\*(.+?)\*\*|(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)"
)
CJK_RE = re.compile(r"[\u3400-\u9fff]")
SOURCE_REVISION_ASTERISK_RE = re.compile(r"(?:^|(?<=\s))\*(?!\*)\s*$")
RENDERED_REVISION_ASTERISK_RE = re.compile(r"\[\[\*\]\]\s*$")
REVISED_DRAFT_CONTEXT_RE = re.compile(r"\b(?:rev\.?|revised|revision)\b", re.I)
TERMINOLOGY_TABLE_HEADER = re.compile(r"^\|\s*English\s*\|\s*Chinese\s*\|", re.I)
ANNOTATION_EVENT_TYPES = {"annotation", "comment", "note"}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def load_project_terms(terminology_path: Path) -> dict[str, str]:
    if not terminology_path.exists():
        return {}

    lines = terminology_path.read_text(encoding="utf-8").splitlines()
    start_index = None
    for index, line in enumerate(lines):
        if TERMINOLOGY_TABLE_HEADER.match(line):
            start_index = index
            break
    if start_index is None or start_index + 1 >= len(lines):
        return {}

    terms: dict[str, str] = {}
    for line in lines[start_index + 2 :]:
        if not line.strip().startswith("|"):
            break
        columns = [col.strip() for col in line.strip().strip("|").split("|")]
        if len(columns) < 2:
            continue
        english, chinese = columns[0], columns[1]
        if english and chinese:
            terms[english] = chinese
    return terms


def subtitles_path_for_batch(batch_path: Path) -> Path | None:
    if not batch_path:
        return None
    batch_dir = batch_path.parent
    if batch_dir.name == "batches" and batch_dir.parent:
        candidate = batch_dir.parent / "subtitles.json"
        if candidate.exists():
            return candidate
    candidate = batch_dir / "subtitles.json"
    return candidate if candidate.exists() else None


def project_file_for_batch(batch_path: Path | None) -> Path | None:
    if batch_path is None:
        return None
    for parent in batch_path.resolve().parents:
        candidate = parent / "project.yaml"
        if candidate.exists():
            return candidate
    return None


def has_revised_draft_context(batch_path: Path | None) -> bool:
    project_file = project_file_for_batch(batch_path)
    if project_file is None:
        return False
    text = project_file.read_text(encoding="utf-8")
    return REVISED_DRAFT_CONTEXT_RE.search(text) is not None


def load_subtitle_annotations(subtitles_path: Path) -> list[str]:
    if not subtitles_path.exists():
        return []
    payload = json.loads(subtitles_path.read_text(encoding="utf-8"))
    events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        return []

    annotations: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("type") or "").strip().lower()
        if event_type in ANNOTATION_EVENT_TYPES:
            text = str(event.get("text") or "").strip()
            if text:
                annotations.append(text)
            continue
        if "annotation" in event and isinstance(event.get("annotation"), str):
            text = event.get("annotation").strip()
            if text:
                annotations.append(text)
    return annotations


def find_terminology_inconsistencies(
    entries: list[Any], terms: dict[str, str], findings: list["Finding"]
) -> None:
    if not terms:
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        source = str(entry.get("source") or "")
        translation = str(entry.get("translation") or "")
        for english, chinese in terms.items():
            if not english or not re.search(
                rf"(?<!\w){re.escape(english)}(?!\w)", source, re.I
            ):
                continue
            if chinese not in translation:
                entry_id = entry.get("id") or f"entries[{index}]"
                warn(
                    findings,
                    "batch.terminology_inconsistency",
                    f"{entry_id} term={english} expected={chinese}",
                )


def find_subtitle_annotation_coverage(
    entries: list[Any],
    front_matter: list[Any],
    subtitles_path: Path,
    findings: list["Finding"],
) -> None:
    annotations = load_subtitle_annotations(subtitles_path)
    if not annotations:
        return

    translations: list[str] = []
    for item in (front_matter or []) + (entries or []):
        if not isinstance(item, dict):
            continue
        translation = str(item.get("translation") or "").strip()
        if translation:
            translations.append(normalize_text(translation))

    for annotation in annotations:
        normalized_annotation = normalize_text(annotation)
        if any(normalized_annotation in normalize_text(text) for text in translations):
            continue
        warn(
            findings,
            "batch.subtitle_annotation_missing",
            f"annotation={normalized_annotation}",
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


def has_source_revision_asterisk(source: Any) -> bool:
    return (
        isinstance(source, str)
        and SOURCE_REVISION_ASTERISK_RE.search(source) is not None
    )


def has_rendered_revision_asterisk(text: Any) -> bool:
    return (
        isinstance(text, str) and RENDERED_REVISION_ASTERISK_RE.search(text) is not None
    )


def count_source_revision_asterisk_candidates(entries: list[Any]) -> int:
    return sum(
        1
        for entry in entries
        if isinstance(entry, dict) and has_source_revision_asterisk(entry.get("source"))
    )


def should_require_revision_asterisk(
    entries: list[Any], batch_path: Path | None
) -> bool:
    candidate_count = count_source_revision_asterisk_candidates(entries)
    if candidate_count == 0:
        return False
    return has_revised_draft_context(batch_path) or candidate_count >= 3


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

    validate_subtitle_timestamps(entry, path, has_subtitles, findings)

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
        if not is_non_empty_string(marker.get("text")):
            fail(findings, "batch.marker_text", f"{marker_path}.text missing")
        if marker_type in {"scene_no", "split_scene"}:
            scene_text = marker.get("scene_no", marker.get("text"))
            if not is_non_empty_string(scene_text):
                fail(
                    findings, "batch.marker_scene_no", f"{marker_path}.scene_no missing"
                )

    layout_hidden = entry.get("layout_hidden")
    if layout_hidden is not None and not isinstance(layout_hidden, bool):
        fail(findings, "batch.layout_hidden", f"{path}.layout_hidden must be bool")

    layout = entry.get("layout")
    if layout is not None:
        validate_entry_layout(layout, path, findings)


def validate_subtitle_timestamps(
    entry: dict[str, Any], path: str, has_subtitles: bool, findings: list[Finding]
) -> None:
    present = SUBTITLE_TIMESTAMP_FIELDS & entry.keys()
    if not present:
        return
    if not has_subtitles:
        fail(
            findings,
            "batch.subtitle_timestamp_without_source",
            f"{path} timestamp fields require subtitles",
        )
    if entry.get("type") != "dialogue":
        fail(
            findings,
            "batch.subtitle_timestamp_entry_type",
            f"{path} timestamp fields require dialogue entry",
        )
    if entry.get("subtitle_label") == "字幕未见":
        fail(
            findings,
            "batch.subtitle_timestamp_unseen",
            f"{path} timestamp fields cannot accompany 字幕未见",
        )
    event_index = entry.get("subtitle_event_index")
    if not isinstance(event_index, int) or event_index < 0:
        fail(
            findings,
            "batch.subtitle_event_index",
            f"{path}.subtitle_event_index={event_index}",
        )
    start = entry.get("subtitle_start")
    end = entry.get("subtitle_end")
    if not isinstance(start, (int, float)):
        fail(findings, "batch.subtitle_start", f"{path}.subtitle_start={start}")
    if not isinstance(end, (int, float)):
        fail(findings, "batch.subtitle_end", f"{path}.subtitle_end={end}")
    if (
        isinstance(start, (int, float))
        and isinstance(end, (int, float))
        and start > end
    ):
        fail(
            findings,
            "batch.subtitle_time_range",
            f"{path}.subtitle_start={start} subtitle_end={end}",
        )
    confidence = entry.get("subtitle_match_confidence")
    if confidence is not None and confidence not in SUBTITLE_MATCH_CONFIDENCE:
        fail(
            findings,
            "batch.subtitle_match_confidence",
            f"{path}.subtitle_match_confidence={confidence}",
        )


def validate_entry_layout(layout: Any, path: str, findings: list[Finding]) -> None:
    if not isinstance(layout, dict):
        fail(findings, "batch.layout", f"{path}.layout must be object")
        return

    layout_type = layout.get("type")
    if layout_type not in LAYOUT_TYPES:
        fail(findings, "batch.layout_type", f"{path}.layout.type={layout_type}")
        return

    source_entry_ids = layout.get("source_entry_ids")
    if source_entry_ids is not None:
        if not isinstance(source_entry_ids, list):
            fail(
                findings,
                "batch.layout_source_entry_ids",
                f"{path}.layout.source_entry_ids must be list",
            )
        else:
            for source_index, source_entry_id in enumerate(source_entry_ids):
                if not is_non_empty_string(source_entry_id):
                    fail(
                        findings,
                        "batch.layout_source_entry_id",
                        f"{path}.layout.source_entry_ids[{source_index}] missing",
                    )

    if layout_type == "parallel_dialogue":
        columns = layout.get("columns")
        if not isinstance(columns, list) or len(columns) < 2:
            fail(
                findings,
                "batch.layout_parallel_columns",
                f"{path}.layout.columns must contain at least two columns",
            )
            return
        for column_index, column in enumerate(columns):
            column_path = f"{path}.layout.columns[{column_index}]"
            if not isinstance(column, dict):
                fail(
                    findings,
                    "batch.layout_parallel_column",
                    f"{column_path} must be object",
                )
                continue
            speaker = column.get("speaker")
            if speaker is not None and not is_non_empty_string(speaker):
                fail(
                    findings,
                    "batch.layout_parallel_speaker",
                    f"{column_path}.speaker must be non-empty string",
                )
            lines = column.get("lines")
            if not isinstance(lines, list) or not lines:
                fail(
                    findings,
                    "batch.layout_parallel_lines",
                    f"{column_path}.lines must be non-empty list",
                )
                continue
            for line_index, line in enumerate(lines):
                if not is_non_empty_string(line):
                    fail(
                        findings,
                        "batch.layout_parallel_line",
                        f"{column_path}.lines[{line_index}] missing",
                    )


def validate_final_entry(
    entry: dict[str, Any],
    index: int,
    findings: list[Finding],
    revision_asterisk_required: bool,
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
    source = entry.get("source")
    if has_source_revision_asterisk(source):
        if has_rendered_revision_asterisk(stripped):
            return
        if revision_asterisk_required:
            fail(findings, "batch.final.revision_asterisk_missing", f"{entry_id}")


def validate_batch(
    batch: dict[str, Any],
    final: bool = False,
    batch_path: Path | None = None,
    terminology_path: Path | None = None,
) -> list[Finding]:
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
    subtitle_label_counts: dict[str, int] = {}
    missing_subtitle_label_ids: list[str] = []
    previous_translation: str | None = None
    previous_entry_id: str | None = None
    front_matter = batch.get("front_matter", [])
    front_matter_entries = front_matter if isinstance(front_matter, list) else []
    revision_asterisk_is_required = should_require_revision_asterisk(
        front_matter_entries + entries, batch_path
    )
    if front_matter is not None:
        if not isinstance(front_matter, list):
            fail(findings, "batch.front_matter", "front_matter must be list")
        else:
            for index, entry in enumerate(front_matter):
                validate_entry(entry, index, has_subtitles, seen_ids, findings)
                if final and isinstance(entry, dict):
                    validate_final_entry(
                        entry, index, findings, revision_asterisk_is_required
                    )
                    translation = entry.get("translation")
                    if isinstance(translation, str):
                        inline_markup_count += len(
                            INLINE_MARKUP_RE.findall(translation)
                        )
    for index, entry in enumerate(entries):
        validate_entry(entry, index, has_subtitles, seen_ids, findings)
        if isinstance(entry, dict):
            label = entry.get("subtitle_label")
            if isinstance(label, str):
                subtitle_label_counts[label] = subtitle_label_counts.get(label, 0) + 1
            elif has_subtitles and entry.get("type") == "dialogue":
                entry_id = (
                    str(entry.get("id"))
                    if is_non_empty_string(entry.get("id"))
                    else f"entries[{index}]"
                )
                missing_subtitle_label_ids.append(entry_id)
        if final and isinstance(entry, dict):
            validate_final_entry(entry, index, findings, revision_asterisk_is_required)
            translation = entry.get("translation")
            if isinstance(translation, str):
                inline_markup_count += len(INLINE_MARKUP_RE.findall(translation))
                normalized_translation = re.sub(r"\s+", "", translation)
                entry_id = (
                    str(entry.get("id"))
                    if is_non_empty_string(entry.get("id"))
                    else f"entries[{index}]"
                )
                if (
                    previous_translation
                    and normalized_translation
                    and normalized_translation == previous_translation
                    and len(normalized_translation) >= 6
                ):
                    warn(
                        findings,
                        "batch.final.adjacent_duplicate_translation",
                        f"{previous_entry_id},{entry_id}",
                    )
                previous_translation = normalized_translation
                previous_entry_id = entry_id
                source = entry.get("source")
                if (
                    entry.get("type") == "action"
                    and isinstance(source, str)
                    and len(source) >= 80
                    and len(CJK_RE.findall(translation)) < 8
                ):
                    warn(
                        findings,
                        "batch.final.short_action_translation",
                        f"{entry_id}",
                    )
    if final and inline_markup_count == 0:
        warn(
            findings,
            "batch.final.no_inline_reader_markup",
            "no __proper name__, **source emphasis**, *source italic*, or [[reader annotation]] markup found",
        )
    if final and subtitle_label_counts:
        label_summary = " ".join(
            f"{label}={subtitle_label_counts[label]}"
            for label in sorted(subtitle_label_counts)
        )
        findings.append(Finding("INFO", "batch.final.subtitle_labels", label_summary))
    if final and missing_subtitle_label_ids:
        preview = ",".join(missing_subtitle_label_ids[:12])
        suffix = (
            f" total={len(missing_subtitle_label_ids)}"
            if len(missing_subtitle_label_ids) > 12
            else ""
        )
        fail(
            findings,
            "batch.final.missing_subtitle_labels",
            f"{preview}{suffix}",
        )

    terminology_path = (
        terminology_path
        or Path(__file__).resolve().parents[1] / "references" / "terminology.md"
    )
    terms = load_project_terms(terminology_path)
    if terms:
        find_terminology_inconsistencies(entries, terms, findings)

    subtitles_path = subtitles_path_for_batch(batch_path) if batch_path else None
    if subtitles_path is not None:
        find_subtitle_annotation_coverage(
            entries, front_matter, subtitles_path, findings
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
    parser.add_argument(
        "--terminology",
        type=Path,
        help="Path to terminology markdown file for project-specific term consistency checks.",
    )
    args = parser.parse_args()

    data = json.loads(args.batch.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        print("FAIL batch.root root must be object")
        return 1
    findings = validate_batch(
        data,
        final=args.final,
        batch_path=args.batch,
        terminology_path=args.terminology,
    )
    for finding in findings:
        print(finding.render())
    return 1 if any(finding.level == "FAIL" for finding in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
