#!/usr/bin/env python3
"""Build a compact context package for writing a project reading guide."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import audit


BATCH_RE = re.compile(r"^translated-p(?P<start>\d+)(?:-(?P<end>\d+))?\.json$")
TERM_ROW_RE = re.compile(r"^\|\s*(?P<english>[^|]+?)\s*\|\s*(?P<chinese>[^|]+?)\s*\|")
MAX_SCENES = 80
MAX_TERMS = 40
MAX_SAMPLES_PER_LABEL = 6
MAX_TEXT_CHARS = 160


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def batch_key(path: Path) -> tuple[int, int, str]:
    match = BATCH_RE.fullmatch(path.name)
    if match is None:
        return (-1, -1, path.name)
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    return (end - start + 1, end, path.name)


def default_batch_path(project_file: Path) -> Path:
    batch_dir = project_file.parent / "work" / "batches"
    candidates = [
        path
        for path in batch_dir.glob("translated-p*.json")
        if path.is_file() and BATCH_RE.fullmatch(path.name)
    ]
    if not candidates:
        raise FileNotFoundError(f"no translated-p*.json batch found in {batch_dir}")
    return max(candidates, key=batch_key)


def output_path(project_file: Path, override: Path | None) -> Path:
    if override is not None:
        path = override.expanduser()
        return path if path.is_absolute() else project_file.parent / path
    return project_file.parent / "work" / "context" / "reading-guide-context.json"


def compact_text(value: Any, limit: int = MAX_TEXT_CHARS) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def entries_from_batch(batch: dict[str, Any]) -> list[dict[str, Any]]:
    entries = batch.get("entries")
    if not isinstance(entries, list):
        raise ValueError("batch.entries must be list")
    return [entry for entry in entries if isinstance(entry, dict)]


def scene_outline(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scenes: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for entry in entries:
        entry_type = entry.get("type")
        if entry_type == "scene_heading":
            current = {
                "display_page": entry.get("display_page"),
                "heading": compact_text(entry.get("translation") or entry.get("source")),
                "source_heading": compact_text(entry.get("source")),
                "dialogue_count": 0,
                "action_count": 0,
                "subtitle_labels": Counter(),
                "speakers": Counter(),
            }
            scenes.append(current)
            continue
        if current is None:
            continue
        if entry_type == "dialogue":
            current["dialogue_count"] += 1
            label = entry.get("subtitle_label")
            if isinstance(label, str) and label:
                current["subtitle_labels"][label] += 1
        elif entry_type == "action":
            current["action_count"] += 1
        elif entry_type == "character":
            speaker = str(entry.get("translation") or entry.get("source") or "").strip()
            if speaker:
                current["speakers"][speaker] += 1

    compact_scenes: list[dict[str, Any]] = []
    for scene in scenes[:MAX_SCENES]:
        compact_scenes.append(
            {
                "display_page": scene["display_page"],
                "heading": scene["heading"],
                "source_heading": scene["source_heading"],
                "dialogue_count": scene["dialogue_count"],
                "action_count": scene["action_count"],
                "subtitle_labels": dict(scene["subtitle_labels"]),
                "major_speakers": [
                    speaker for speaker, _count in scene["speakers"].most_common(4)
                ],
            }
        )
    return compact_scenes


def subtitle_label_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    samples: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        label = entry.get("subtitle_label")
        if not isinstance(label, str) or not label:
            continue
        counts[label] += 1
        bucket = samples.setdefault(label, [])
        if len(bucket) >= MAX_SAMPLES_PER_LABEL:
            continue
        bucket.append(
            {
                "display_page": entry.get("display_page"),
                "source": compact_text(entry.get("source")),
                "translation": compact_text(entry.get("translation")),
            }
        )
    return {"counts": dict(counts), "samples": samples}


def screenplay_arc(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pages = [
        entry.get("display_page")
        for entry in entries
        if isinstance(entry.get("display_page"), int) and entry.get("display_page") > 0
    ]
    if not pages:
        return []
    start, end = min(pages), max(pages)
    if start > end:
        return []
    span = max(1, end - start + 1)
    segment_count = 5
    segments: list[dict[str, Any]] = []
    for index in range(segment_count):
        seg_start = start + (span * index) // segment_count
        seg_end = start + (span * (index + 1)) // segment_count - 1
        if index == segment_count - 1:
            seg_end = end
        subset = [
            entry
            for entry in entries
            if isinstance(entry.get("display_page"), int)
            and seg_start <= entry["display_page"] <= seg_end
        ]
        scenes = [
            compact_text(entry.get("translation") or entry.get("source"), 80)
            for entry in subset
            if entry.get("type") == "scene_heading"
        ][:8]
        characters = Counter(
            compact_text(entry.get("translation") or entry.get("source"), 60)
            for entry in subset
            if entry.get("type") == "character"
        )
        labels = Counter(
            str(entry.get("subtitle_label"))
            for entry in subset
            if isinstance(entry.get("subtitle_label"), str)
            and entry.get("subtitle_label")
        )
        segments.append(
            {
                "display_pages": {"start": seg_start, "end": seg_end},
                "scene_headings": scenes,
                "major_characters": [
                    character
                    for character, _count in characters.most_common(8)
                    if character
                ],
                "subtitle_labels": dict(labels),
            }
        )
    return segments


def parse_terminology(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    terms: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = TERM_ROW_RE.match(line)
        if not match:
            continue
        english = match.group("english").strip()
        chinese = match.group("chinese").strip()
        if english.lower() == "english" or set(english) <= {"-"}:
            continue
        if chinese.lower() == "chinese" or set(chinese) <= {"-"}:
            continue
        terms.append({"english": english, "chinese": chinese})
    return terms[:MAX_TERMS]


def source_stats(entries: list[dict[str, Any]]) -> dict[str, Any]:
    pages = sorted(
        {
            entry.get("display_page")
            for entry in entries
            if isinstance(entry.get("display_page"), int)
            and entry.get("display_page") > 0
        }
    )
    return {
        "entry_count": len(entries),
        "display_pages": {"start": pages[0], "end": pages[-1], "count": len(pages)}
        if pages
        else None,
        "entry_types": dict(Counter(str(entry.get("type") or "") for entry in entries)),
    }


def build_context(project_file: Path, batch_path: Path) -> dict[str, Any]:
    config = audit.load_simple_yaml(project_file)
    batch = load_json(batch_path)
    if not isinstance(batch, dict):
        raise ValueError("batch root must be object")
    entries = entries_from_batch(batch)
    terminology = parse_terminology(project_file.parent / "references" / "terminology.md")
    return {
        "version": 1,
        "kind": "reading_guide_context",
        "project": {
            "project_file": str(project_file),
            "title": audit.section(config, "project").get("title"),
            "chinese_title": audit.section(config, "project").get("chinese_title"),
            "has_subtitles": bool(batch.get("has_subtitles")),
        },
        "sources": {
            "batch": str(batch_path),
            "terminology": str(project_file.parent / "references" / "terminology.md"),
            "reading_guide": str(project_file.parent / "references" / "reading_guide.md"),
        },
        "stats": source_stats(entries),
        "arc_segments": screenplay_arc(entries),
        "scene_outline": scene_outline(entries),
        "subtitle_alignment": subtitle_label_summary(entries),
        "terminology": terminology,
        "guide_brief": {
            "target_path": "references/reading_guide.md",
            "recommended_length": "1-2 printed pages",
            "write_in": "Chinese",
            "include": [
                "how to read this screenplay edition",
                "story/scene-section reading path",
                "screenplay-vs-subtitle expression differences",
                "character relationship and information setup observations",
                "adaptation, compression, omission, or reordering tendencies",
            ],
            "avoid": [
                "subtitle label statistics as the main content",
                "mechanical per-line comparison",
                "claims not supported by the translated batch/context",
                "workflow/debug notes",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a compact context package for AI-authored reading guides."
    )
    parser.add_argument("project", type=Path, help="Path to project.yaml.")
    parser.add_argument(
        "--batch",
        type=Path,
        help="Merged translated batch JSON. Defaults to the largest translated batch.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    project_file = args.project.expanduser().resolve()
    batch_path = (
        args.batch.expanduser().resolve()
        if args.batch is not None
        else default_batch_path(project_file)
    )
    context = build_context(project_file, batch_path)
    out_path = output_path(project_file, args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"INFO reading_guide_context {out_path}")
    print(f"INFO scenes {len(context['scene_outline'])}")
    print(f"INFO arc_segments {len(context['arc_segments'])}")
    labels = context["subtitle_alignment"].get("counts", {})
    print(f"INFO subtitle_labels {labels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
