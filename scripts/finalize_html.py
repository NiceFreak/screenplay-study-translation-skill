#!/usr/bin/env python3
"""Validate, build, audit, and optionally clean final HTML output."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import audit


SCRIPTS_DIR = Path(__file__).resolve().parent
TRANSLATED_BATCH_RE = re.compile(
    r"^translated-p(?P<start>\d+)(?:-(?P<end>\d+))?\.json$"
)


def translated_batch_key(path: Path) -> tuple[int, int, int, str]:
    match = TRANSLATED_BATCH_RE.fullmatch(path.name)
    if match is None:
        return (-1, -1, -1, path.name)
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    if end < start:
        return (-1, end, start, path.name)
    return (end - start + 1, end, start, path.name)


def translated_batch_range(path: Path) -> tuple[int, int] | None:
    match = TRANSLATED_BATCH_RE.fullmatch(path.name)
    if match is None:
        return None
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    if end < start:
        return None
    return (start, end)


def select_default_batch(project: Path) -> Path:
    batch_dir = project.parent / "work" / "batches"
    candidates = [
        path
        for path in batch_dir.glob("translated-*.json")
        if path.is_file() and translated_batch_key(path)[0] > 0
    ]
    if not candidates:
        raise FileNotFoundError(f"no translated-*.json batch found in {batch_dir}")
    selected = max(candidates, key=translated_batch_key)
    ranges = [
        batch_range
        for path in candidates
        if (batch_range := translated_batch_range(path)) is not None
    ]
    selected_range = translated_batch_range(selected)
    if len(ranges) > 1 and selected_range is not None:
        total_range = (min(start for start, _ in ranges), max(end for _, end in ranges))
        if selected_range != total_range:
            raise ValueError(
                "multiple translated batches found; merge them with "
                "scripts/merge_batches.py or pass a specific batch for a range preview"
            )
    return selected


def run_step(name: str, command: list[str]) -> int:
    print(f"== {name}", flush=True)
    result = subprocess.run(command, text=True, check=False)
    if result.returncode == 0:
        print(f"PASS {name}", flush=True)
    else:
        print(f"FAIL {name} exit={result.returncode}", flush=True)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize screenplay study HTML from a translated batch."
    )
    parser.add_argument("project", type=Path, help="Path to project.yaml.")
    parser.add_argument(
        "batch",
        nargs="?",
        type=Path,
        help="Final translation batch JSON. Defaults to the largest translated-*.json in work/batches.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="HTML output path. Defaults to the project configured path.",
    )
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
        "--clean",
        action="store_true",
        help="Clean transient project files after HTML audit passes.",
    )
    parser.add_argument(
        "--allow-missing-inputs",
        action="store_true",
        help="Downgrade missing source inputs to WARN for template smoke tests.",
    )
    args = parser.parse_args()

    if (
        args.display_page_start is not None
        and args.display_page_end is not None
        and args.display_page_start > args.display_page_end
    ):
        parser.error(
            "--display-page-start must be less than or equal to --display-page-end"
        )

    project = args.project.expanduser().resolve()
    if args.batch is None:
        try:
            batch = select_default_batch(project)
        except (FileNotFoundError, ValueError) as exc:
            print(f"FAIL batch.auto_select {exc}", file=sys.stderr)
            return 1
        print(f"INFO batch.auto_selected {batch}")
    else:
        batch = args.batch.expanduser().resolve()
    if args.output is not None:
        output = args.output.expanduser().resolve()
    else:
        config = audit.load_simple_yaml(project)
        outputs = audit.section(config, "outputs")
        configured_output = audit.resolve_path(project, outputs.get("html"))
        output = configured_output or project.parent / "dist" / "screenplay-study.html"

    steps = [
        (
            "validate_final_batch",
            [
                sys.executable,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(batch),
                "--final",
            ],
        ),
        (
            "build_html",
            [
                sys.executable,
                str(SCRIPTS_DIR / "build_html.py"),
                str(batch),
                "--output",
                str(output),
                "--project",
                str(project),
            ],
        ),
    ]

    audit_command = [
        sys.executable,
        str(SCRIPTS_DIR / "audit.py"),
        str(project),
        "--html",
        str(output),
    ]
    if args.allow_missing_inputs:
        audit_command.append("--allow-missing-inputs")
    if args.display_page_start is not None:
        audit_command.extend(["--display-page-start", str(args.display_page_start)])
    if args.display_page_end is not None:
        audit_command.extend(["--display-page-end", str(args.display_page_end)])
    steps.append(("audit_html", audit_command))

    if args.clean:
        steps.append(
            (
                "clean_project",
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "clean_project.py"),
                    str(project.parent),
                    "--apply",
                ],
            )
        )

    for name, command in steps:
        code = run_step(name, command)
        if code != 0:
            return code

    cost_report_code = run_step(
        "cost_report",
        [
            sys.executable,
            str(SCRIPTS_DIR / "cost_report.py"),
            str(project),
        ],
    )
    if cost_report_code != 0:
        return cost_report_code
    print(f"INFO final_html {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
