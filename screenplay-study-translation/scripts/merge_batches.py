#!/usr/bin/env python3
"""Merge translated screenplay batches into one final batch."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


BATCH_RE = re.compile(r"^translated-p(?P<start>\d+)(?:-(?P<end>\d+))?\.json$")


def batch_key(path: Path) -> tuple[int, int, str]:
    match = BATCH_RE.fullmatch(path.name)
    if match is None:
        return (sys.maxsize, sys.maxsize, path.name)
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    return (start, end, path.name)


def load_batch(path: Path) -> dict[str, Any]:
    batch = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(batch, dict):
        raise ValueError(f"{path}: batch must be object")
    entries = batch.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"{path}: entries must be list")
    return batch


def merge_batches(paths: list[Path]) -> dict[str, Any]:
    if not paths:
        raise ValueError("no batches provided")

    loaded = [(path, load_batch(path)) for path in sorted(paths, key=batch_key)]
    first = loaded[0][1]
    seen_ids: set[str] = set()
    entries: list[dict[str, Any]] = []
    pages: list[int] = []

    for path, batch in loaded:
        source_pages = batch.get("source_pages")
        if not isinstance(source_pages, dict):
            raise ValueError(f"{path}: source_pages must be object")
        start = source_pages.get("start")
        end = source_pages.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError(f"{path}: source_pages start/end must be int")
        pages.extend([start, end])

        for entry in batch["entries"]:
            if not isinstance(entry, dict):
                raise ValueError(f"{path}: entry must be object")
            entry_id = entry.get("id")
            if not isinstance(entry_id, str) or not entry_id.strip():
                raise ValueError(f"{path}: entry id missing")
            if entry_id in seen_ids:
                raise ValueError(f"{path}: duplicate entry id {entry_id}")
            seen_ids.add(entry_id)
            entries.append(entry)

    result: dict[str, Any] = {
        "version": 1,
        "batch_id": f"translated-p{min(pages):03d}-{max(pages):03d}",
        "source_pages": {"start": min(pages), "end": max(pages)},
        "has_subtitles": any(bool(batch.get("has_subtitles")) for _, batch in loaded),
        "entries": entries,
    }
    if "title" in first:
        result["title"] = first["title"]
    front_matter = first.get("front_matter")
    if isinstance(front_matter, list) and front_matter:
        result["front_matter"] = front_matter
    return result


def discover_batches(batch_dir: Path) -> list[Path]:
    return [
        path
        for path in batch_dir.glob("translated-p*.json")
        if path.is_file() and BATCH_RE.fullmatch(path.name)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge translated-p*.json batches into one translated batch."
    )
    parser.add_argument("batches", nargs="*", type=Path)
    parser.add_argument(
        "--batch-dir",
        type=Path,
        help="Directory to auto-discover translated-p*.json when no batches are listed.",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if args.batches:
        paths = [path.expanduser().resolve() for path in args.batches]
    elif args.batch_dir is not None:
        paths = discover_batches(args.batch_dir.expanduser().resolve())
    else:
        parser.error("provide batches or --batch-dir")

    try:
        merged = merge_batches(paths)
    except ValueError as exc:
        print(f"FAIL merge_batches {exc}", file=sys.stderr)
        return 1

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"INFO merged_batch {output}")
    print(f"INFO merged_entries {len(merged['entries'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
