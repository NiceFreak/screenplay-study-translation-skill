#!/usr/bin/env python3
"""Report subtitle coverage and reusable translation hints."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import parse_subtitles


CJK_RE = re.compile(r"[\u3400-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-z]")
LATIN_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
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
    "hey",
    "i'll",
    "ill",
    "it's",
    "its",
    "now",
    "oh",
    "shit",
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


def load_events(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        events = data.get("events") if isinstance(data, dict) else None
        if isinstance(events, list):
            return [event for event in events if isinstance(event, dict)]
        raise ValueError("subtitle JSON must contain an events list")
    return parse_subtitles.parse_subtitles(path)


def line_kinds(text: str) -> tuple[int, int, int]:
    cjk = 0
    latin = 0
    mixed = 0
    for line in [part.strip() for part in re.split(r"[\n\r]+", text) if part.strip()]:
        has_cjk = bool(CJK_RE.search(line))
        has_latin = bool(LATIN_RE.search(line))
        if has_cjk and has_latin:
            mixed += 1
        elif has_cjk:
            cjk += 1
        elif has_latin:
            latin += 1
    return cjk, latin, mixed


def event_duration(event: dict[str, Any]) -> float:
    start = event.get("start")
    end = event.get("end")
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        return 0.0
    return max(0.0, float(end) - float(start))


def normalized_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def latin_stopword_key(text: str) -> str:
    return text.replace("’", "'").replace("‘", "'").lower()


def keep_candidate_term(text: str) -> bool:
    if len(text) < 2:
        return False
    if CJK_RE.search(text):
        return True
    if not LATIN_TOKEN_RE.fullmatch(text):
        return False
    key = latin_stopword_key(text)
    if key in STOPWORDS:
        return False
    return not text.islower()


def candidate_terms(events: list[dict[str, Any]], limit: int) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for event in events:
        text = str(event.get("text") or "")
        for token in TOKEN_RE.findall(text):
            normalized = token.strip(" -_.,!?;:()[]{}\"'“”‘’")
            if not keep_candidate_term(normalized):
                continue
            counter[normalized] += 1
    return counter.most_common(limit)


def build_report(events: list[dict[str, Any]], term_limit: int) -> list[str]:
    texts = [normalized_text(str(event.get("text") or "")) for event in events]
    non_empty = [text for text in texts if text]
    empty_count = len(texts) - len(non_empty)
    duplicate_count = sum(
        count - 1 for count in Counter(non_empty).values() if count > 1
    )
    durations = [event_duration(event) for event in events]
    total_duration = max(
        (
            float(event.get("end"))
            for event in events
            if isinstance(event.get("end"), (int, float))
        ),
        default=0.0,
    )
    cjk_lines = latin_lines = mixed_lines = 0
    for text in texts:
        cjk, latin, mixed = line_kinds(text)
        cjk_lines += cjk
        latin_lines += latin
        mixed_lines += mixed
    long_events = sum(1 for text in non_empty if len(text) >= 42)
    short_duration_events = sum(1 for duration in durations if 0 < duration < 0.5)
    zero_duration_events = sum(1 for duration in durations if duration == 0)

    lines = [
        f"INFO subtitle.events count={len(events)}",
        f"INFO subtitle.timeline seconds={total_duration:.2f}",
        f"INFO subtitle.text empty={empty_count} duplicates={duplicate_count}",
        f"INFO subtitle.lines cjk={cjk_lines} latin={latin_lines} mixed={mixed_lines}",
        f"INFO subtitle.anomalies long_text={long_events} short_duration={short_duration_events} zero_duration={zero_duration_events}",
    ]
    for term, count in candidate_terms(events, term_limit):
        lines.append(f"INFO subtitle.term_candidate count={count} text={term}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report subtitle coverage and translation hint candidates."
    )
    parser.add_argument(
        "subtitles", type=Path, help="Subtitle file or normalized subtitle JSON."
    )
    parser.add_argument("--output", type=Path, help="Write report to this path.")
    parser.add_argument("--term-limit", type=int, default=20)
    args = parser.parse_args()

    events = load_events(args.subtitles.expanduser())
    report = "\n".join(build_report(events, max(0, args.term_limit))) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
