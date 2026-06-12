#!/usr/bin/env python3
"""clean_project.py dry-run candidate selection checks."""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SmokeCheck


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    clean_project_dir = tmp_dir / "clean-project"
    (clean_project_dir / "work" / "batches").mkdir(parents=True)
    (clean_project_dir / "work" / "reports").mkdir(parents=True)
    (clean_project_dir / "dist").mkdir(parents=True)
    for relative in [
        "work/batches/draft.json",
        "work/batches/translated-p001-002.json",
        "work/batches/translated-p001-004.json",
        "work/reports/cost-report.json",
        "work/reports/sample-validation.txt",
        "work/reports/temp.txt",
        "dist/screenplay-study.html",
        "dist/preview.html",
    ]:
        (clean_project_dir / relative).write_text("fixture\n", encoding="utf-8")

    return [
        {
            "name": "clean_project_fixture_dry_run",
            "command": [
                python,
                str(SCRIPTS_DIR / "clean_project.py"),
                str(clean_project_dir),
            ],
        },
        {
            "name": "assert_clean_project_fixture_candidates",
            "command": [
                python,
                "-c",
                (
                    "import subprocess, sys; "
                    f"cmd=[sys.executable, {str(SCRIPTS_DIR / 'clean_project.py')!r}, {str(clean_project_dir)!r}]; "
                    "out=subprocess.check_output(cmd, text=True); "
                    "required=['draft.json', 'translated-p001-002.json', 'temp.txt', 'preview.html']; "
                    "forbidden=['translated-p001-004.json', 'cost-report.json', 'sample-validation.txt', 'screenplay-study.html']; "
                    "missing=[item for item in required if item not in out]; "
                    "bad=[item for item in forbidden if item in out]; "
                    "raise SystemExit(f'clean candidates missing={missing} bad={bad}' if missing or bad else 0)"
                ),
            ],
        },
    ]
