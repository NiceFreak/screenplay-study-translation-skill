#!/usr/bin/env python3
"""Project template audit and project initialization checks."""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SKILL_DIR, SmokeCheck


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    initialized_project_dir = tmp_dir / "initialized-project"
    initialized_project = initialized_project_dir / "project.yaml"

    return [
        {
            "name": "project_template_audit",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(SKILL_DIR / "assets" / "project.example.yaml"),
                "--allow-missing-inputs",
            ],
        },
        {
            "name": "init_project_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "init_project.py"),
                str(initialized_project_dir),
                "--title",
                "Initialized Fixture",
                "--chinese-title",
                "初始化样例",
            ],
        },
        {
            "name": "audit_initialized_project",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(initialized_project),
                "--allow-missing-inputs",
            ],
        },
        {
            "name": "init_project_signal_lifecycle",
            "command": [
                python,
                "-c",
                (
                    "import json, pathlib, sys; "
                    f"path=pathlib.Path({str(initialized_project_dir)!r}) / "
                    "'work' / 'signal' / 'signal_lifecycle.json'; "
                    "payload=json.loads(path.read_text(encoding='utf-8')); "
                    "bad=(payload.get('records') != [] or "
                    "payload.get('status_values') != ['open', 'reviewed', 'ignored']); "
                    "sys.exit(1 if bad else 0)"
                ),
            ],
        },
    ]
