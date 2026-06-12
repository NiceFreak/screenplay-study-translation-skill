#!/usr/bin/env python3
"""Merge translated screenplay batches into one final batch."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPTS_DIR = Path(__file__).resolve().parent
BATCH_RE = re.compile(r"^translated-p(?P<start>\d+)(?:-(?P<end>\d+))?\.json$")
TIMESTAMP_FIELDS = (
    "subtitle_event_index",
    "subtitle_start",
    "subtitle_end",
    "subtitle_match_confidence",
)


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


def context_dir_for_batches(paths: list[Path], batch_dir: Path | None) -> Path | None:
    if batch_dir is not None:
        return batch_dir.parent / "context"
    if paths and paths[0].parent.name == "batches":
        return paths[0].parent.parent / "context"
    return None


def load_timestamp_index(context_dir: Path | None) -> dict[str, dict[str, Any]]:
    if context_dir is None or not context_dir.exists():
        return {}

    timestamps: dict[str, dict[str, Any]] = {}
    for path in sorted(context_dir.glob("batch-context-p*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        candidates = payload.get("subtitle_candidates")
        if not isinstance(candidates, dict):
            continue
        source_items = (
            candidates.get("subtitle_timestamps")
            or candidates.get("unique_subtitle_timestamps")
            or []
        )
        for item in source_items:
            if not isinstance(item, dict):
                continue
            event_index = item.get("subtitle_event_index")
            start = item.get("subtitle_start")
            end = item.get("subtitle_end")
            entry_ids = item.get("entry_ids")
            if (
                not isinstance(event_index, int)
                or not isinstance(start, (int, float))
                or not isinstance(end, (int, float))
                or not isinstance(entry_ids, list)
            ):
                continue
            timestamp = {
                "subtitle_event_index": event_index,
                "subtitle_start": start,
                "subtitle_end": end,
            }
            confidence = item.get("subtitle_match_confidence")
            if isinstance(confidence, str) and confidence in {"high", "low"}:
                timestamp["subtitle_match_confidence"] = confidence
            for entry_id in entry_ids:
                if isinstance(entry_id, str) and entry_id not in timestamps:
                    timestamps[entry_id] = timestamp
    return timestamps


def apply_subtitle_timestamps(
    entry: dict[str, Any], timestamps: dict[str, dict[str, Any]]
) -> None:
    if not timestamps or entry.get("type") != "dialogue":
        return
    if entry.get("subtitle_label") not in {"字幕匹配", "字幕差异"}:
        return
    entry_id = entry.get("id")
    if not isinstance(entry_id, str):
        return
    timestamp = timestamps.get(entry_id)
    if timestamp is None:
        return
    timestamp_fields = TIMESTAMP_FIELDS[:3]
    present = [field for field in timestamp_fields if field in entry]
    if present and any(entry.get(field) != timestamp[field] for field in present):
        raise ValueError(f"timestamp mismatch for entry {entry_id}")
    entry.update(timestamp)


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
            entries.append(dict(entry))

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


def merge_batches_with_context(
    paths: list[Path], context_dir: Path | None
) -> dict[str, Any]:
    merged = merge_batches(paths)
    timestamps = load_timestamp_index(context_dir)
    for entry in merged["entries"]:
        apply_subtitle_timestamps(entry, timestamps)
    return merged


def discover_batches(batch_dir: Path) -> list[Path]:
    return [
        path
        for path in batch_dir.glob("translated-p*.json")
        if path.is_file() and BATCH_RE.fullmatch(path.name)
    ]


def parse_validation_line(line: str) -> dict[str, str]:
    parts = line.split(maxsplit=2)
    return {
        "level": parts[0] if parts else "",
        "code": parts[1] if len(parts) > 1 else "",
        "message": parts[2] if len(parts) > 2 else "",
        "raw": line,
    }


def validation_state(findings: list[dict[str, str]], returncode: int) -> str:
    levels = {finding["level"] for finding in findings}
    if returncode != 0 or "FAIL" in levels:
        return "FAIL"
    if "WARN" in levels:
        return "WARN"
    return "PASS"


def validate_batch_file(path: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(SCRIPTS_DIR / "validate_batch.py"),
        str(path),
        "--final",
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    lines = [
        line.strip()
        for line in (result.stdout + result.stderr).splitlines()
        if line.strip()
    ]
    findings = [parse_validation_line(line) for line in lines]
    return {
        "path": str(path),
        "command": command,
        "returncode": result.returncode,
        "state": validation_state(findings, result.returncode),
        "findings": findings,
    }


def validation_log_path(
    paths: list[Path], output: Path, batch_dir: Path | None
) -> Path:
    if batch_dir is not None:
        return batch_dir.parent / "logs" / "merge-validation.json"
    if output.parent.name == "batches":
        return output.parent.parent / "logs" / "merge-validation.json"
    if paths and paths[0].parent.name == "batches":
        return paths[0].parent.parent / "logs" / "merge-validation.json"
    return output.parent / "logs" / "merge-validation.json"


def write_validation_log(
    log_path: Path, paths: list[Path], results: list[dict[str, Any]]
) -> None:
    failed = [result["path"] for result in results if result["state"] == "FAIL"]
    warned = [result["path"] for result in results if result["state"] == "WARN"]
    payload = {
        "version": 1,
        "stage": "MERGE VALIDATION",
        "inputs": [str(path) for path in paths],
        "overall_state": "FAIL" if failed else "WARN" if warned else "PASS",
        "failed_batches": failed,
        "warned_batches": warned,
        "results": results,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def validate_before_merge(
    paths: list[Path], output: Path, batch_dir: Path | None
) -> tuple[bool, list[dict[str, Any]], Path]:
    results = [validate_batch_file(path) for path in sorted(paths, key=batch_key)]
    log_path = validation_log_path(paths, output, batch_dir)
    write_validation_log(log_path, paths, results)
    return not any(result["state"] == "FAIL" for result in results), results, log_path


def print_validation_summary(results: list[dict[str, Any]], log_path: Path) -> None:
    print(f"INFO merge_validation {log_path}")
    failed = [result for result in results if result["state"] == "FAIL"]
    warned = [result for result in results if result["state"] == "WARN"]
    if failed:
        print(
            "FAIL merge_validation.failed_batches "
            + " ".join(result["path"] for result in failed),
            file=sys.stderr,
        )
    for result in warned:
        print(f"WARN merge_validation.batch {result['path']}")
        for finding in result["findings"]:
            if finding["level"] == "WARN":
                print(
                    f"WARN merge_validation.finding {result['path']} {finding['raw']}"
                )


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

    output = args.output.expanduser().resolve()
    batch_dir = args.batch_dir.expanduser().resolve() if args.batch_dir else None

    if args.batches:
        paths = [path.expanduser().resolve() for path in args.batches]
    elif batch_dir is not None:
        paths = [
            path
            for path in discover_batches(batch_dir)
            if path.expanduser().resolve() != output
        ]
    else:
        parser.error("provide batches or --batch-dir")

    validation_ok, validation_results, log_path = validate_before_merge(
        paths, output, batch_dir
    )
    print_validation_summary(validation_results, log_path)
    if not validation_ok:
        return 1

    try:
        merged = merge_batches_with_context(
            paths, context_dir_for_batches(paths, batch_dir)
        )
    except ValueError as exc:
        print(f"FAIL merge_batches {exc}", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"INFO merged_batch {output}")
    print(f"INFO merged_entries {len(merged['entries'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
