#!/usr/bin/env python3
"""Build a style profile from source lines and optional subtitles."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

CJK_RE = re.compile(r"[\u3400-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-z]")
INFORMAL_MARKERS = [
    "don't",
    "can't",
    "won't",
    "I'm",
    "ain't",
    "gonna",
    "wanna",
    "yeah",
    "nah",
    "hey",
    "okay",
    "ok",
    "shit",
    "dude",
    "man",
    "guy",
    "right",
]
FORMAL_MARKERS = [
    "shall",
    "therefore",
    "hereby",
    "whereupon",
    "thus",
    "aforementioned",
    "whereas",
    "hence",
    "whom",
]
ACTION_STYLE_MARKERS = [
    "CUT TO",
    "PAN TO",
    "FADE IN",
    "FADE OUT",
    "DISSOLVE TO",
    "INT.",
    "EXT.",
    "SMASH CUT",
    "MATCH CUT",
    "ANGLE ON",
    "TIGHT ON",
    "WIDE ON",
    "CLOSE ON",
    "POV",
    "MONTAGE",
]
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*|[\u3400-\u9fff]{2,}")
STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "you",
    "that",
    "this",
    "with",
    "for",
    "are",
    "but",
    "not",
    "have",
    "your",
    "what",
    "they",
    "from",
    "will",
    "just",
    "like",
    "about",
    "there",
    "here",
    "all",
    "come",
    "he",
    "i'll",
    "ill",
    "it's",
    "its",
    "now",
    "oh",
    "well",
    "yeah",
    "y'all",
    "yall",
    "to",
    "me",
    "of",
    "it",
    "on",
    "in",
    "we",
    "right",
    "get",
    "go",
    "my",
    "no",
    "was",
    "be",
    "out",
    "i'm",
    "im",
    "don't",
    "dont",
    "ain't",
    "aint",
    "second",
    "line",
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def source_lines_texts(source_lines_path: Path) -> list[str]:
    payload = load_json(source_lines_path)
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("source_lines.json must contain rows list")
    return [str(row.get("text") or "") for row in rows if isinstance(row, dict)]


def confidence_from_hits(primary: int, secondary: int) -> str:
    if primary == 0 and secondary == 0:
        return "low"
    if primary >= secondary + 3:
        return "medium"
    return "low"


def infer_dialogue_tone(lines: list[str]) -> dict[str, Any]:
    informal = 0
    formal = 0
    for line in lines:
        text = line.lower()
        for marker in INFORMAL_MARKERS:
            if marker.lower() in text:
                informal += 1
        for marker in FORMAL_MARKERS:
            if marker.lower() in text:
                formal += 1
    value = "mixed"
    if informal >= formal + 2:
        value = "casual"
    elif formal >= informal + 2:
        value = "formal"
    return {
        "value": value,
        "basis": "source_text_heuristic",
        "confidence": confidence_from_hits(
            max(informal, formal), min(informal, formal)
        ),
        "evidence": {
            "source_line_count": len(lines),
            "informal_marker_hits": informal,
            "formal_marker_hits": formal,
        },
    }


def infer_action_style(lines: list[str]) -> dict[str, Any]:
    score = 0
    for line in lines:
        text = line.upper()
        if any(marker in text for marker in ACTION_STYLE_MARKERS):
            score += 1
    return {
        "value": "literal" if score >= 1 else "interpretive",
        "basis": "source_text_heuristic",
        "confidence": "medium" if score >= 3 else "low",
        "evidence": {
            "source_line_count": len(lines),
            "format_marker_hits": score,
        },
    }


def keep_candidate_term(text: str) -> bool:
    if len(text) < 2:
        return False
    if CJK_RE.search(text):
        return True
    if not TOKEN_RE.fullmatch(text):
        return False
    return text.lower() not in STOPWORDS and not text.islower()


def terminology_tendencies_from_subtitles(
    events: list[dict[str, Any]], limit: int
) -> tuple[list[str], dict[str, int]]:
    counts: dict[str, int] = {}
    for event in events:
        text = str(event.get("text") or "")
        for token in TOKEN_RE.findall(text):
            normalized = token.strip(" -_.,!?;:()[]{}\"'“”‘’")
            if not normalized or not keep_candidate_term(normalized):
                continue
            counts[normalized] = counts.get(normalized, 0) + 1
    terms = [
        term
        for term, _count in sorted(
            counts.items(), key=lambda item: (-item[1], item[0])
        )[:limit]
    ]
    return terms, {term: counts[term] for term in terms}


def build_subtitle_style_notes(
    events: list[dict[str, Any]],
) -> tuple[list[str], dict[str, Any]]:
    notes: list[str] = []
    texts = [
        str(event.get("text") or "") for event in events if isinstance(event, dict)
    ]
    chinese_punctuation_events = sum(
        1
        for text in texts
        if "。" in text or "，" in text or "？" in text or "！" in text or "；" in text
    )
    mixed_language_events = sum(
        1 for text in texts if CJK_RE.search(text) and LATIN_RE.search(text)
    )
    parenthetical_events = sum(
        1
        for text in texts
        if "（" in text or "）" in text or "(" in text or ")" in text
    )
    if chinese_punctuation_events:
        notes.append("uses Chinese subtitle punctuation")
    if mixed_language_events:
        notes.append("blends Chinese and English")
    if parenthetical_events:
        notes.append("includes parenthetical annotation style")
    average = sum(len(text) for text in texts) / max(1, len(texts))
    if average < 24:
        notes.append("concise subtitle phrasing")
    return notes, {
        "subtitle_event_count": len(texts),
        "average_text_length": round(average, 2),
        "chinese_punctuation_events": chinese_punctuation_events,
        "mixed_language_events": mixed_language_events,
        "parenthetical_events": parenthetical_events,
    }


def load_subtitles(subtitles_path: Path) -> list[dict[str, Any]]:
    payload = load_json(subtitles_path)
    events = payload.get("events")
    if not isinstance(events, list):
        raise ValueError("subtitles.json must contain events list")
    return [event for event in events if isinstance(event, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a style profile from source lines and subtitles."
    )
    parser.add_argument(
        "source_lines", type=Path, help="Path to work/source-lines.json"
    )
    parser.add_argument(
        "--subtitles",
        type=Path,
        help="Optional path to work/subtitles.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for the style profile JSON.",
    )
    args = parser.parse_args()

    source_lines_path = args.source_lines.expanduser()
    if not source_lines_path.exists():
        raise FileNotFoundError(f"source_lines={source_lines_path}")

    subtitles_path = None
    if args.subtitles:
        subtitles_path = args.subtitles.expanduser()
    else:
        candidate = source_lines_path.parent / "subtitles.json"
        if candidate.exists():
            subtitles_path = candidate

    lines = source_lines_texts(source_lines_path)
    dialogue_tone = infer_dialogue_tone(lines)
    action_style = infer_action_style(lines)
    profile: dict[str, Any] = {
        "version": 1,
        "dialogue_tone": dialogue_tone["value"],
        "action_style": action_style["value"],
        "profile_semantics": "heuristic_hints_pending_first_batch_confirmation",
        "style_basis": "source_lines",
        "profile_hints": {
            "dialogue_tone": dialogue_tone,
            "action_style": action_style,
        },
        "evidence": {
            "source_line_count": len(lines),
            "non_empty_source_line_count": sum(1 for line in lines if line.strip()),
        },
    }

    if subtitles_path is not None:
        events = load_subtitles(subtitles_path)
        terms, term_counts = terminology_tendencies_from_subtitles(events, 10)
        notes, subtitle_evidence = build_subtitle_style_notes(events)
        profile["style_basis"] = "subtitles"
        profile["terminology_tendencies"] = terms
        profile["terminology_tendency_counts"] = term_counts
        profile["subtitle_style_notes"] = notes
        profile["subtitle_style_evidence"] = subtitle_evidence
    else:
        profile["terminology_tendencies"] = []

    output_path = (
        args.output.expanduser()
        if args.output
        else source_lines_path.parent / "style-profile.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
