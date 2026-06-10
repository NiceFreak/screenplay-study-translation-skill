#!/usr/bin/env python3
"""Clean transient screenplay study project outputs."""

from __future__ import annotations

import argparse
from pathlib import Path


KEEP_REPORTS = {"sample-validation.txt", "subtitle-report.txt"}
KEEP_DIST_NAMES = {"screenplay-study.html"}


def translated_range_key(path: Path) -> tuple[int, str]:
    stem = path.stem
    parts = stem.removeprefix("translated-p").split("-")
    try:
        start = int(parts[0])
        end = int(parts[-1])
    except ValueError:
        return (0, path.name)
    return (end - start, path.name)


def keep_translated_batches(paths: list[Path]) -> set[Path]:
    translated = [path for path in paths if path.name.startswith("translated-")]
    if not translated:
        return set()
    return {max(translated, key=translated_range_key)}


def candidate_files(project_dir: Path, keep_draft: bool = False) -> list[Path]:
    paths: list[Path] = []
    batches = project_dir / "work" / "batches"
    if batches.exists():
        batch_files = [path for path in batches.iterdir() if path.is_file()]
        keep_batches = keep_translated_batches(batch_files)
        for path in batch_files:
            if (keep_draft and path.name == "draft.json") or path in keep_batches:
                continue
            paths.append(path)

    reports = project_dir / "work" / "reports"
    if reports.exists():
        for path in reports.iterdir():
            if path.is_file() and path.name not in KEEP_REPORTS:
                paths.append(path)

    dist = project_dir / "dist"
    if dist.exists():
        for path in dist.iterdir():
            if not path.is_file():
                continue
            if path.name in KEEP_DIST_NAMES:
                continue
            paths.append(path)
    return sorted(paths)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean transient generated files from a screenplay study project."
    )
    parser.add_argument("project_dir", type=Path)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete files. Without this flag, only print candidates.",
    )
    parser.add_argument(
        "--keep-draft",
        action="store_true",
        help="Keep work/batches/draft.json for debugging.",
    )
    args = parser.parse_args()

    project_dir = args.project_dir.expanduser().resolve()
    paths = candidate_files(project_dir, keep_draft=args.keep_draft)
    action = "DELETE" if args.apply else "DRY-RUN"
    for path in paths:
        print(f"{action} {path}")
        if args.apply:
            path.unlink()
    print(f"INFO clean candidates={len(paths)} applied={args.apply}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
