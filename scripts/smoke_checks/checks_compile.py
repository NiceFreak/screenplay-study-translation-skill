#!/usr/bin/env python3
"""Byte-compile checks for all pipeline scripts."""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SmokeCheck


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    return [
        {
            "name": "py_compile",
            "command": [
                python,
                "-m",
                "compileall",
                "-q",
                str(SCRIPTS_DIR),
                "-x",
                r"export_pdf\.py",
            ],
        },
        {
            "name": "py_compile_export_pdf",
            "command": [
                python,
                "-m",
                "py_compile",
                str(SCRIPTS_DIR / "export_pdf.py"),
            ],
            # SKIP: PDF output deprecated in v0.3. See references/decisions.md.
            "skip": True,
            "skip_reason": "PDF output deprecated in v0.3. See references/decisions.md.",
        },
    ]
