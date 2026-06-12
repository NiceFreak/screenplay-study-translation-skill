#!/usr/bin/env python3
"""Build a compact translation context package for one displayed-page range."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import audit
import draft_batch
import make_sample_batch
import stage_gate


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*|[\u3400-\u9fff]{2,}")
LATIN_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
TERM_ROW_RE = re.compile(r"^\|\s*(?P<english>[^|]+?)\s*\|\s*(?P<chinese>[^|]+?)\s*\|")
TRANSLATED_BATCH_RE = re.compile(
    r"^translated-p(?P<start>\d+)(?:-(?P<end>\d+))?\.json$"
)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "can",
    "can't",
    "cant",
    "come",
    "could",
    "did",
    "do",
    "does",
    "don't",
    "dont",
    "for",
    "from",
    "get",
    "go",
    "good",
    "got",
    "had",
    "has",
    "have",
    "he",
    "her",
    "his",
    "how",
    "i",
    "in",
    "is",
    "it",
    "its",
    "me",
    "my",
    "not",
    "of",
    "on",
    "or",
    "our",
    "probably",
    "she",
    "should",
    "that",
    "the",
    "their",
    "this",
    "to",
    "we",
    "what",
    "when",
    "where",
    "who",
    "why",
    "will",
    "with",
    "would",
    "yes",
    "you",
    "your",
}
MAX_SOURCE_ROWS = 160
MAX_SUBTITLE_MATCHES = 60
MAX_SUBTITLE_CANDIDATES_PER_UNIT = 2
SUBTITLE_HIGH_CONFIDENCE_SCORE = 0.7
SUBTITLE_MID_CONFIDENCE_SCORE = 0.6
MAX_RELEVANT_TERMS = 80
MAX_STYLE_TERMS = 20
MAX_CONTINUITY_ENTRIES = 8
MAX_WARNING_SIGNALS = 40


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def output_path(
    project_file: Path,
    config: dict[str, Any],
    start: int,
    end: int,
    override: Path | None,
) -> Path:
    if override is not None:
        return override.expanduser().resolve()
    outputs = audit.section(config, "outputs")
    work_dir = audit.resolve_path(project_file, outputs.get("work_dir") or "work")
    if work_dir is None:
        work_dir = project_file.parent / "work"
    return work_dir / "context" / f"batch-context-p{start:03d}-{end:03d}.json"


def load_source_lines(
    project_file: Path, config: dict[str, Any]
) -> tuple[Path, list[dict[str, Any]]]:
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
    return source_lines_path, [row for row in rows if isinstance(row, dict)]


def load_markers(
    project_file: Path, config: dict[str, Any]
) -> tuple[Path, dict[str, Any], list[dict[str, Any]]]:
    inventory_path, inventory = audit.load_marker_inventory(project_file, config)
    if inventory is None:
        raise FileNotFoundError(f"marker_inventory={inventory_path}")
    markers = inventory.get("markers")
    if not isinstance(markers, list):
        markers = inventory.get("known_markers")
    if not isinstance(markers, list):
        raise ValueError("marker inventory markers must be a list")
    return (
        inventory_path,
        inventory,
        [marker for marker in markers if isinstance(marker, dict)],
    )


def load_subtitles(
    project_file: Path, config: dict[str, Any]
) -> tuple[Path | None, list[dict[str, Any]]]:
    outputs = audit.section(config, "outputs")
    subtitles_path = audit.resolve_path(
        project_file, outputs.get("subtitles_json") or "work/subtitles.json"
    )
    if subtitles_path is None or not subtitles_path.exists():
        return None, []
    payload = load_json(subtitles_path)
    events = payload.get("events")
    if not isinstance(events, list):
        raise ValueError("subtitles.json must contain events list")
    return subtitles_path, [event for event in events if isinstance(event, dict)]


def load_style_profile(
    project_file: Path, config: dict[str, Any]
) -> tuple[Path | None, dict[str, Any]]:
    outputs = audit.section(config, "outputs")
    work_dir = audit.resolve_path(project_file, outputs.get("work_dir") or "work")
    if work_dir is None:
        work_dir = project_file.parent / "work"
    style_path = work_dir / "style-profile.json"
    if not style_path.exists():
        return None, {}
    payload = load_json(style_path)
    if not isinstance(payload, dict):
        raise ValueError("style-profile.json must be an object")
    return style_path, payload


def page_in_window(value: Any, start: int, end: int, overlap: int = 0) -> bool:
    if not isinstance(value, int):
        return False
    return start - overlap <= value <= end + overlap


def row_sort_key(row: dict[str, Any]) -> tuple[int, float, float, str]:
    return (
        int(row.get("pdf_page") or 0),
        -float(row.get("y") or 0),
        float(row.get("x") or 0),
        str(row.get("text") or ""),
    )


def marker_sort_key(marker: dict[str, Any]) -> tuple[int, float, float, str]:
    return (
        int(marker.get("pdf_page") or 0),
        -float(marker.get("y") or 0),
        float(marker.get("x") or 0),
        str(marker.get("text") or ""),
    )


def compact_row(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "pdf_page",
        "display_page",
        "printed_page",
        "text",
        "x",
        "y",
        "zone",
        "source_layer",
    )
    return {key: row[key] for key in keys if key in row}


def compact_marker(marker: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "type",
        "pdf_page",
        "display_page",
        "text",
        "scene_no",
        "scene_key",
        "position",
        "source_layer",
        "x",
        "y",
    )
    return {key: marker[key] for key in keys if key in marker}


def source_excerpt(
    rows: list[dict[str, Any]], start: int, end: int, overlap: int
) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if page_in_window(row.get("display_page"), start, end, overlap)
    ]
    selected.sort(key=row_sort_key)
    return [compact_row(row) for row in selected[:MAX_SOURCE_ROWS]]


def markers_excerpt(
    markers: list[dict[str, Any]], start: int, end: int, overlap: int
) -> list[dict[str, Any]]:
    selected = [
        marker
        for marker in markers
        if page_in_window(marker.get("display_page"), start, end, overlap)
    ]
    selected.sort(key=marker_sort_key)
    return [compact_marker(marker) for marker in selected]


def signals_from_inventory(
    inventory: dict[str, Any], start: int, end: int, overlap: int
) -> dict[str, list[dict[str, Any]]]:
    signals: dict[str, list[dict[str, Any]]] = {}
    counts: dict[str, int] = {}
    for source_key, output_key in (
        ("warning_signal", "warning_signal"),
        ("noise_signal", "noise_signal"),
        ("unclassified_signals", "unclassified_signals"),
        ("noise_candidates", "noise_candidates"),
    ):
        value = inventory.get(source_key)
        if not isinstance(value, list):
            continue
        selected = [
            compact_marker(signal)
            for signal in value
            if isinstance(signal, dict)
            and page_in_window(signal.get("display_page"), start, end, overlap)
        ]
        if selected:
            counts[output_key] = len(selected)
            signals[output_key] = selected[:MAX_WARNING_SIGNALS]
    if counts:
        signals["summary"] = [
            {"type": key, "count": value, "included": min(value, MAX_WARNING_SIGNALS)}
            for key, value in sorted(counts.items())
        ]
    return signals


def build_draft_entries(
    project_file: Path,
    config: dict[str, Any],
    rows: list[dict[str, Any]],
    markers: list[dict[str, Any]],
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    batch = draft_batch.batch_from_lines(
        project_file, config, rows, markers, start, end
    )
    entries = batch.get("entries")
    if not isinstance(entries, list):
        return []
    compact_entries: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        compact = {
            "id": entry.get("id"),
            "type": entry.get("type"),
            "pdf_page": entry.get("pdf_page"),
            "display_page": entry.get("display_page"),
            "source": entry.get("source"),
        }
        if isinstance(entry.get("markers"), list):
            compact["markers"] = [
                compact_marker(marker)
                for marker in make_sample_batch.sorted_markers(entry["markers"])
                if isinstance(marker, dict)
            ]
        compact_entries.append(compact)
    return compact_entries


def subtitle_event_text(event: dict[str, Any]) -> str:
    return re.sub(r"\s+", " ", str(event.get("text") or "")).strip()


def subtitle_event_sort_key(event: dict[str, Any]) -> tuple[float, float, str]:
    start = float(event.get("start") or 0.0)
    end = float(event.get("end") or 0.0)
    return (start, end, subtitle_event_text(event))


def normalized_for_match(value: str) -> str:
    normalized = value.replace("’", "'").replace("‘", "'").lower()
    return re.sub(r"[^a-z0-9\u3400-\u9fff]+", " ", normalized).strip()


def normalized_compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.replace("’", "'").replace("‘", "'").lower())


def latin_terms(value: str) -> set[str]:
    terms: set[str] = set()
    for token in LATIN_TOKEN_RE.findall(value):
        key = token.replace("’", "'").replace("‘", "'").lower()
        if len(key) < 3 or key in STOPWORDS:
            continue
        terms.add(key)
    return terms


def source_dialogue_units(source_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    current_speaker: str | None = None
    current: dict[str, Any] | None = None
    previous_type: str | None = None
    for entry in source_entries:
        entry_type = entry.get("type")
        if entry_type == "character":
            current_speaker = str(entry.get("source") or "").strip() or None
            current = None
            previous_type = entry_type
            continue
        text = str(entry.get("source") or "").strip()
        dialogue_context = entry_type == "dialogue" or (
            entry_type in {"parenthetical", "action"}
            and current_speaker is not None
            and previous_type in {"character", "parenthetical"}
            and bool(text)
        )
        if not dialogue_context:
            current = None
            if entry_type in {
                "scene_heading",
                "transition",
                "format_marker",
                "page_heading",
            }:
                current_speaker = None
            previous_type = str(entry_type or "")
            continue
        if not text:
            previous_type = str(entry_type or "")
            continue
        if current is None:
            current = {
                "speaker": current_speaker,
                "entry_ids": [],
                "display_pages": [],
                "source": "",
            }
            units.append(current)
        current["entry_ids"].append(entry.get("id"))
        page = entry.get("display_page")
        if page not in current["display_pages"]:
            current["display_pages"].append(page)
        current["source"] = " ".join(
            part for part in (current.get("source"), text) if part
        )
        previous_type = str(entry_type or "")
    return units


def unit_event_score(
    unit: dict[str, Any], event: dict[str, Any], term_pairs: list[dict[str, str]]
) -> float:
    event_text = subtitle_event_text(event)
    if not event_text:
        return 0.0
    event_compact = normalized_compact(event_text)
    event_terms = latin_terms(event_text)
    source = str(unit.get("source") or "")
    source_key = normalized_for_match(source)
    source_compact = normalized_compact(source)
    if not source_key:
        return 0.0
    if len(source_compact) >= 16 and source_compact in event_compact:
        return 1.0

    term_hits = 0
    source_lower = source.lower()
    for term in term_pairs:
        english = term.get("english", "")
        chinese = term.get("chinese", "")
        if not english or not chinese:
            continue
        if normalize_token(english) in source_lower and chinese in event_text:
            term_hits += 1

    source_terms = latin_terms(source)
    if not source_terms or not event_terms:
        return 0.72 if term_hits else 0.0
    overlap = len(source_terms & event_terms)
    required_overlap = 2 if len(source_terms) <= 4 else 3
    if overlap < required_overlap:
        return 0.72 if term_hits and overlap else 0.0
    if len(source_terms) <= 4 and overlap < len(source_terms):
        return 0.0
    denominator = max(1, min(len(source_terms), len(event_terms)))
    score = overlap / denominator
    if overlap >= 3:
        score = max(score, 0.65)
    if term_hits:
        score = max(score, 0.72 + min(term_hits, 3) * 0.05)
    return score


def compact_subtitle_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        key: event[key]
        for key in ("start", "end", "text", "type", "speaker", "annotation")
        if key in event
    }


def subtitle_matches_for_units(
    events: list[dict[str, Any]],
    dialogue_units: list[dict[str, Any]],
    term_pairs: list[dict[str, str]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    emitted = 0
    for unit in dialogue_units:
        scored = [
            (unit_event_score(unit, event, term_pairs), index, event)
            for index, event in enumerate(events)
        ]
        candidates = [
            (score, index, event)
            for score, index, event in scored
            if score >= SUBTITLE_MID_CONFIDENCE_SCORE
        ]
        candidates.sort(key=lambda item: (-item[0], subtitle_event_sort_key(item[2])))
        compact_candidates = [
            {
                "score": round(score, 3),
                "match_confidence": (
                    "high" if score >= SUBTITLE_HIGH_CONFIDENCE_SCORE else "low"
                ),
                "event_index": index,
                "event": compact_subtitle_event(event),
            }
            for score, index, event in candidates[:MAX_SUBTITLE_CANDIDATES_PER_UNIT]
        ]
        emitted += len(compact_candidates)
        match = {
            "speaker": unit.get("speaker"),
            "entry_ids": unit.get("entry_ids"),
            "display_pages": unit.get("display_pages"),
            "source": unit.get("source"),
        }
        if compact_candidates:
            match["candidates"] = compact_candidates
        else:
            match["candidate_count"] = 0
        matches.append(match)
        if emitted >= MAX_SUBTITLE_MATCHES:
            break
    return matches


def unique_subtitle_timestamps(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deferred: list[tuple[dict[str, Any], dict[str, Any]]] = []
    event_counts: dict[int, int] = {}
    for match in matches:
        candidates = match.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != 1:
            continue
        candidate = candidates[0]
        if candidate.get("match_confidence") != "high":
            continue
        event_index = candidate.get("event_index")
        event = candidate.get("event")
        if not isinstance(event_index, int) or not isinstance(event, dict):
            continue
        start = event.get("start")
        end = event.get("end")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue
        deferred.append((match, candidate))
        event_counts[event_index] = event_counts.get(event_index, 0) + 1

    timestamps: list[dict[str, Any]] = []
    for match, candidate in deferred:
        event_index = candidate["event_index"]
        if event_counts[event_index] > 1:
            continue
        event = candidate["event"]
        timestamps.append(
            {
                "entry_ids": match.get("entry_ids") or [],
                "subtitle_event_index": event_index,
                "subtitle_start": event["start"],
                "subtitle_end": event["end"],
            }
        )
    return timestamps


def subtitle_timestamps(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique = {
        tuple(item.get("entry_ids") or []): item
        for item in unique_subtitle_timestamps(matches)
    }
    timestamps: list[dict[str, Any]] = []
    for match in matches:
        entry_ids = match.get("entry_ids") or []
        if not isinstance(entry_ids, list) or not entry_ids:
            continue
        unique_item = unique.get(tuple(entry_ids))
        if unique_item is not None:
            timestamps.append({**unique_item, "subtitle_match_confidence": "high"})
            continue
        candidates = match.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            continue
        candidate = candidates[0]
        event_index = candidate.get("event_index")
        event = candidate.get("event")
        if not isinstance(event_index, int) or not isinstance(event, dict):
            continue
        start = event.get("start")
        end = event.get("end")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue
        timestamps.append(
            {
                "entry_ids": entry_ids,
                "subtitle_event_index": event_index,
                "subtitle_start": start,
                "subtitle_end": end,
                "subtitle_match_confidence": "low",
            }
        )
    return timestamps


def subtitle_candidates(
    events: list[dict[str, Any]],
    dialogue_units: list[dict[str, Any]],
    term_pairs: list[dict[str, str]],
) -> dict[str, Any]:
    if not events:
        return {
            "available": False,
            "summary": {"dialogue_unit_count": len(dialogue_units)},
            "advisory_matches": [],
            "unique_subtitle_timestamps": [],
            "fallback_events": [],
            "selection_note": "subtitles not configured",
        }
    matches = subtitle_matches_for_units(events, dialogue_units, term_pairs)
    matched_count = sum(len(match.get("candidates") or []) for match in matches)
    timestamps = unique_subtitle_timestamps(matches)
    all_timestamps = subtitle_timestamps(matches)
    return {
        "available": True,
        "summary": {
            "dialogue_unit_count": len(dialogue_units),
            "advisory_match_units_included": len(matches),
            "matched_candidate_count": matched_count,
            "unique_timestamp_count": len(timestamps),
            "timestamp_count": len(all_timestamps),
            "candidate_limit_total": MAX_SUBTITLE_MATCHES,
            "candidate_limit_per_unit": MAX_SUBTITLE_CANDIDATES_PER_UNIT,
        },
        "selection": {
            "method": "global_source_text_and_terminology_search",
            "event_count_total": len(events),
            "matched_candidate_count": matched_count,
            "confidence": "advisory",
        },
        "advisory_matches": matches,
        "unique_subtitle_timestamps": timestamps,
        "subtitle_timestamps": all_timestamps,
        "fallback_events": [],
        "selection_note": (
            "Subtitle candidates are searched across the full subtitle file "
            "without assuming screenplay order matches subtitle order. They are "
            "compact advisory evidence; semantic expression-unit judgment "
            "remains required."
        ),
    }


def parse_terminology_rows(path: Path) -> list[dict[str, str]]:
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
        if not english or not chinese or set(chinese) <= {"-"}:
            continue
        notes = ""
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) >= 3:
            notes = parts[2]
        terms.append({"english": english, "chinese": chinese, "notes": notes})
    return terms


def terminology_path(project_file: Path) -> Path:
    return project_file.parent / "references" / "terminology.md"


def normalize_token(value: str) -> str:
    return value.replace("’", "'").replace("‘", "'").lower()


def text_blob(items: list[str]) -> str:
    return "\n".join(item for item in items if item)


def relevant_terms(
    project_file: Path,
    source_entries: list[dict[str, Any]],
    style_profile: dict[str, Any],
) -> list[dict[str, str]]:
    path = terminology_path(project_file)
    terms = parse_terminology_rows(path)
    if not terms:
        return []
    source_text = text_blob(
        [str(entry.get("source") or "") for entry in source_entries]
    )
    source_key = normalize_token(source_text)
    style_tendencies = style_profile.get("terminology_tendencies")
    tendency_set = {
        normalize_token(str(term))
        for term in style_tendencies
        if isinstance(term, (str, int, float))
    }
    selected: list[dict[str, str]] = []
    for term in terms:
        english = term["english"]
        chinese = term["chinese"]
        if normalize_token(english) in source_key or chinese in source_text:
            selected.append(term)
            continue
        english_tokens = {
            normalize_token(token)
            for token in TOKEN_RE.findall(english)
            if len(token) >= 3
        }
        if english_tokens & tendency_set:
            selected.append(term)
    return selected[:MAX_RELEVANT_TERMS]


def style_summary(style_profile: dict[str, Any]) -> dict[str, Any]:
    if not style_profile:
        return {"available": False}
    summary: dict[str, Any] = {
        "available": True,
        "style_basis": style_profile.get("style_basis"),
        "dialogue_tone": style_profile.get("dialogue_tone"),
        "action_style": style_profile.get("action_style"),
        "profile_semantics": style_profile.get("profile_semantics"),
    }
    notes = style_profile.get("subtitle_style_notes")
    if isinstance(notes, list):
        summary["subtitle_style_notes"] = notes
    tendencies = style_profile.get("terminology_tendencies")
    if isinstance(tendencies, list):
        summary["terminology_tendencies"] = tendencies[:MAX_STYLE_TERMS]
    evidence = style_profile.get("subtitle_style_evidence")
    if isinstance(evidence, dict):
        summary["subtitle_style_evidence"] = {
            key: evidence[key]
            for key in (
                "subtitle_event_count",
                "average_text_length",
                "mixed_language_events",
                "parenthetical_events",
            )
            if key in evidence
        }
    return summary


def translated_batch_pages(path: Path) -> tuple[int, int] | None:
    match = TRANSLATED_BATCH_RE.match(path.name)
    if not match:
        return None
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    return start, end


def continuity_context(project_file: Path, start: int) -> dict[str, Any]:
    batch_dir = project_file.parent / "work" / "batches"
    if not batch_dir.exists():
        return {"previous_batch": None, "entries": []}
    candidates: list[tuple[int, int, Path]] = []
    for path in batch_dir.glob("translated-p*.json"):
        pages = translated_batch_pages(path)
        if pages is None:
            continue
        batch_start, batch_end = pages
        if batch_end < start:
            candidates.append((batch_end, batch_start, path))
    if not candidates:
        return {"previous_batch": None, "entries": []}
    _batch_end, _batch_start, path = sorted(candidates)[-1]
    payload = load_json(path)
    entries = payload.get("entries")
    if not isinstance(entries, list):
        entries = []
    tail_entries = [
        entry for entry in entries[-MAX_CONTINUITY_ENTRIES:] if isinstance(entry, dict)
    ]
    tail_type_counts: dict[str, int] = {}
    tail_speakers: list[str] = []
    compact_entries: list[dict[str, Any]] = []
    for entry in tail_entries:
        entry_type = str(entry.get("type") or "")
        tail_type_counts[entry_type] = tail_type_counts.get(entry_type, 0) + 1
        if entry_type == "character":
            speaker = str(entry.get("translation") or entry.get("source") or "").strip()
            if speaker and speaker not in tail_speakers:
                tail_speakers.append(speaker)
        compact_entries.append(
            {
                "id": entry.get("id"),
                "type": entry.get("type"),
                "display_page": entry.get("display_page"),
                "source": entry.get("source"),
                "translation": entry.get("translation"),
                "subtitle_label": entry.get("subtitle_label"),
            }
        )
    return {
        "previous_batch": str(path),
        "previous_batch_id": payload.get("batch_id"),
        "summary": {
            "total_entries": len(entries),
            "tail_entries_included": len(compact_entries),
            "tail_entry_types": tail_type_counts,
            "tail_speakers": tail_speakers[:6],
        },
        "entries": compact_entries,
    }


def batch_notes() -> list[str]:
    return [
        "Use this package as the default translation context for the current batch.",
        "Do not read full source-lines.json, full subtitles.json, or full marker inventory unless this package is insufficient.",
        "Subtitle events are advisory candidates; use semantic expression-unit matching for dialogue labels.",
        "This package is not a validation gate and does not replace batch JSON validation.",
    ]


def build_package(
    project_file: Path,
    config: dict[str, Any],
    start: int,
    end: int,
    overlap: int,
    include_source_rows: bool,
) -> dict[str, Any]:
    confirmed, _confirmation_lines = stage_gate.check_stage2_confirmation(
        project_file, config
    )
    if not confirmed:
        raise RuntimeError(
            "Stage 2 signal confirmation is required before packaging batch context."
        )
    source_lines_path, rows = load_source_lines(project_file, config)
    marker_path, inventory, markers = load_markers(project_file, config)
    subtitles_path, subtitles = load_subtitles(project_file, config)
    style_path, style = load_style_profile(project_file, config)
    source_entries = build_draft_entries(
        project_file, config, rows, markers, start, end
    )
    dialogue_units = source_dialogue_units(source_entries)
    terminology_pairs = relevant_terms(project_file, source_entries, style)

    package = {
        "version": 1,
        "kind": "translation_batch_context",
        "project": {
            "project_file": str(project_file),
            "title": audit.section(config, "project").get("title"),
            "chinese_title": audit.section(config, "project").get("chinese_title"),
        },
        "batch": {
            "display_page_start": start,
            "display_page_end": end,
            "overlap_pages": overlap,
            "expected_batch_id": f"translated-p{start:03d}-{end:03d}",
        },
        "sources": {
            "source_lines": str(source_lines_path),
            "marker_inventory": str(marker_path),
            "subtitles": str(subtitles_path) if subtitles_path is not None else None,
            "style_profile": str(style_path) if style_path is not None else None,
            "terminology": str(terminology_path(project_file)),
        },
        "source_entries": source_entries,
        "markers": markers_excerpt(markers, start, end, overlap),
        "signals": signals_from_inventory(inventory, start, end, overlap),
        "subtitle_candidates": subtitle_candidates(
            subtitles, dialogue_units, terminology_pairs
        ),
        "terminology": {
            "relevant_terms": terminology_pairs,
            "selection_note": (
                "Subset selected from project-local terminology by current source range "
                "and style-profile tendencies."
            ),
        },
        "style_summary": style_summary(style),
        "continuity": continuity_context(project_file, start),
        "agent_notes": batch_notes(),
    }
    if include_source_rows:
        package["source_rows_excerpt"] = source_excerpt(rows, start, end, overlap)
    return package


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a compact context package for one translation batch."
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--display-page-start", type=int, required=True)
    parser.add_argument("--display-page-end", type=int, required=True)
    parser.add_argument(
        "--overlap-pages",
        type=int,
        default=1,
        help="Include nearby source rows and signals for page-boundary continuity.",
    )
    parser.add_argument(
        "--include-source-rows",
        action="store_true",
        help="Include compact raw source row excerpts for extraction debugging.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.display_page_start > args.display_page_end:
        parser.error(
            "--display-page-start must be less than or equal to --display-page-end"
        )
    if args.overlap_pages < 0:
        parser.error("--overlap-pages must be non-negative")

    project_file = args.project.expanduser().resolve()
    config = audit.load_simple_yaml(project_file)
    package = build_package(
        project_file,
        config,
        args.display_page_start,
        args.display_page_end,
        args.overlap_pages,
        args.include_source_rows,
    )
    out_path = output_path(
        project_file,
        config,
        args.display_page_start,
        args.display_page_end,
        args.output,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"INFO batch_context {out_path}")
    print(f"INFO source_entries {len(package['source_entries'])}")
    print(f"INFO source_rows_excerpt {len(package.get('source_rows_excerpt', []))}")
    print(f"INFO markers {len(package['markers'])}")
    subtitle_matches = sum(
        len(match.get("candidates") or [])
        for match in package["subtitle_candidates"].get("advisory_matches", [])
    )
    fallback_events = len(package["subtitle_candidates"].get("fallback_events", []))
    print(f"INFO subtitle_candidates {subtitle_matches + fallback_events}")
    print(f"INFO relevant_terms {len(package['terminology']['relevant_terms'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
