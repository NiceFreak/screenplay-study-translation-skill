#!/usr/bin/env python3
"""Parse ASS/SRT/VTT subtitles into normalized JSON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TIME_RE = re.compile(r"(?P<h>\d+):(?P<m>\d{2}):(?P<s>\d{2})(?P<f>[.,:]\d+)?")


def parse_time(value: str) -> float:
    match = TIME_RE.search(value.strip())
    if not match:
        raise ValueError(f"invalid subtitle time: {value}")
    hours = int(match.group("h"))
    minutes = int(match.group("m"))
    seconds = int(match.group("s"))
    fraction = match.group("f") or ""
    fraction_value = float(f"0.{fraction[1:]}") if fraction else 0.0
    return hours * 3600 + minutes * 60 + seconds + fraction_value


def clean_subtitle_text(text: str) -> str:
    text = text.replace("\\N", "\n").replace("\\n", "\n")
    text = re.sub(r"\{[^}]*\}", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_ass(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    format_fields: list[str] = []
    for raw_line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw_line.strip()
        if line.startswith("Format:"):
            format_fields = [
                field.strip().lower() for field in line.split(":", 1)[1].split(",")
            ]
            continue
        if not line.startswith("Dialogue:"):
            continue
        body = line.split(":", 1)[1].lstrip()
        parts = (
            body.split(",", max(len(format_fields) - 1, 0))
            if format_fields
            else body.split(",", 9)
        )
        if format_fields and len(parts) == len(format_fields):
            item = dict(zip(format_fields, parts))
            start = item.get("start", "")
            end = item.get("end", "")
            text = item.get("text", "")
        elif len(parts) >= 10:
            start, end, text = parts[1], parts[2], parts[9]
        else:
            continue
        events.append(
            {
                "start": parse_time(start),
                "end": parse_time(end),
                "text": clean_subtitle_text(text),
            }
        )
    return events


def parse_srt_or_vtt(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line or line.upper() == "WEBVTT" or line.isdigit():
            index += 1
            continue
        if "-->" not in line:
            index += 1
            continue
        start_text, end_text = [
            part.strip().split()[0] for part in line.split("-->", 1)
        ]
        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index])
            index += 1
        events.append(
            {
                "start": parse_time(start_text),
                "end": parse_time(end_text),
                "text": clean_subtitle_text("\n".join(text_lines)),
            }
        )
    return events


def parse_subtitles(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".ass":
        return parse_ass(path)
    if suffix in {".srt", ".vtt"}:
        return parse_srt_or_vtt(path)
    raise ValueError(f"unsupported subtitle format: {suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse subtitles into normalized JSON."
    )
    parser.add_argument("subtitles", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    events = parse_subtitles(args.subtitles)
    payload = {"version": 1, "source": str(args.subtitles), "events": events}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    print(f"INFO subtitle_events count={len(events)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
