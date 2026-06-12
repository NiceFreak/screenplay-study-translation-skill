#!/usr/bin/env python3
"""Checks against the repository's static synthetic fixtures."""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import (
    FIXTURES_DIR,
    SCRIPTS_DIR,
    VALID_BATCH,
    SmokeCheck,
    json_fixture,
)


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    valid_batch = VALID_BATCH
    invalid_subtitle_timestamp_batch = tmp_dir / "invalid-subtitle-timestamp.json"
    invalid_subtitle_timestamp_batch.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "invalid-subtitle-timestamp",
                "source_pages": {"start": 1, "end": 1},
                "has_subtitles": True,
                "entries": [
                    {
                        "id": "p001-e001",
                        "type": "dialogue",
                        "pdf_page": 2,
                        "display_page": 1,
                        "source": "Unseen line.",
                        "translation": "未见对白。",
                        "subtitle_label": "字幕未见",
                        "subtitle_event_index": 0,
                        "subtitle_start": 1.0,
                        "subtitle_end": 2.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    return [
        {
            "name": "valid_batch_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(valid_batch),
            ],
        },
        {
            "name": "valid_batch_fixture_final",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(valid_batch),
                "--final",
            ],
        },
        {
            "name": "invalid_batch_subtitle_label",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(FIXTURES_DIR / "batches" / "invalid-subtitle-label" / "batch.json"),
            ],
            "expect_failure": True,
        },
        {
            "name": "invalid_batch_subtitle_timestamp",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(invalid_subtitle_timestamp_batch),
            ],
            "expect_failure": True,
        },
        {
            "name": "invalid_batch_final_placeholder",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(
                    FIXTURES_DIR
                    / "batches"
                    / "invalid-final-placeholder"
                    / "batch.json"
                ),
                "--final",
            ],
            "expect_failure": True,
        },
        {
            "name": "minimal_fixture_audit",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(FIXTURES_DIR / "minimal" / "project.yaml"),
                "--allow-missing-inputs",
            ],
        },
        {
            "name": "broken_links_fixture_audit",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(FIXTURES_DIR / "broken-links" / "project.yaml"),
                "--allow-missing-inputs",
            ],
            "expect_failure": True,
        },
        {
            "name": "unstructured_fixture_audit",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(FIXTURES_DIR / "unstructured" / "project.yaml"),
                "--allow-missing-inputs",
            ],
            "expect_failure": True,
        },
    ]
