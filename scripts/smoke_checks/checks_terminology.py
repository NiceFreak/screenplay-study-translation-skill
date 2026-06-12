#!/usr/bin/env python3
"""Batch validation checks: terminology, annotations, markers, asterisks."""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SmokeCheck, json_fixture


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    terminology_project_dir = tmp_dir / "terminology-project"
    terminology_batch_dir = terminology_project_dir / "work" / "batches"
    terminology_batch_dir.mkdir(parents=True)
    (terminology_project_dir / "references").mkdir(parents=True)
    terminology_file = terminology_project_dir / "references" / "terminology.md"
    terminology_file.write_text(
        """
| English | Chinese | Notes |
|---------|---------|-------|
| TERM_ALPHA | 术语甲 |
| PERSON_ALPHA | 角色甲 |
""",
        encoding="utf-8",
    )
    subtitles_json = terminology_project_dir / "work" / "subtitles.json"
    subtitles_json.write_text(
        json_fixture(
            {
                "version": 1,
                "source": "generated",
                "events": [
                    {
                        "start": 0.0,
                        "end": 1.0,
                        "type": "annotation",
                        "text": "这是注释说明",
                    },
                    {
                        "start": 1.0,
                        "end": 2.5,
                        "type": "dialogue",
                        "text": "角色甲，执行测试指令！",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    consistent_batch = terminology_batch_dir / "consistent-batch.json"
    inconsistent_batch = terminology_batch_dir / "inconsistent-batch.json"
    annotation_present_batch = terminology_batch_dir / "annotation-present-batch.json"
    annotation_missing_batch = terminology_batch_dir / "annotation-missing-batch.json"
    invalid_raw_format_batch = terminology_batch_dir / "invalid-raw-format-batch.json"
    invalid_marker_identity_batch = (
        terminology_batch_dir / "invalid-marker-identity-batch.json"
    )
    semantic_asterisk_batch = terminology_batch_dir / "semantic-asterisk-batch.json"
    revision_asterisk_project_dir = tmp_dir / "revision-asterisk-project"
    revision_asterisk_batch_dir = revision_asterisk_project_dir / "work" / "batches"
    revision_asterisk_project = revision_asterisk_project_dir / "project.yaml"
    revision_asterisk_missing_batch = (
        revision_asterisk_batch_dir / "revision-asterisk-missing-batch.json"
    )
    consistent_batch.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "consistent",
                "source_pages": {"start": 1, "end": 1},
                "has_subtitles": True,
                "entries": [
                    {
                        "id": "t001",
                        "type": "dialogue",
                        "pdf_page": 1,
                        "display_page": 1,
                        "source": "TERM_ALPHA is active.",
                        "translation": "术语甲已激活。",
                    },
                    {
                        "id": "t002",
                        "type": "note",
                        "pdf_page": 1,
                        "display_page": 1,
                        "source": "Subtitle annotation",
                        "translation": "这是注释说明",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    inconsistent_batch.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "inconsistent",
                "source_pages": {"start": 1, "end": 1},
                "has_subtitles": True,
                "entries": [
                    {
                        "id": "t003",
                        "type": "dialogue",
                        "pdf_page": 1,
                        "display_page": 1,
                        "source": "TERM_ALPHA is active.",
                        "translation": "术语乙已激活。",
                    },
                    {
                        "id": "t004",
                        "type": "note",
                        "pdf_page": 1,
                        "display_page": 1,
                        "source": "Subtitle annotation",
                        "translation": "这是注释说明",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    annotation_present_batch.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "annotation-present",
                "source_pages": {"start": 1, "end": 1},
                "has_subtitles": True,
                "entries": [
                    {
                        "id": "t005",
                        "type": "dialogue",
                        "pdf_page": 1,
                        "display_page": 1,
                        "source": "Hello.",
                        "translation": "你好。",
                    },
                    {
                        "id": "t006",
                        "type": "note",
                        "pdf_page": 1,
                        "display_page": 1,
                        "source": "Subtitle annotation",
                        "translation": "这是注释说明",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    annotation_missing_batch.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "annotation-missing",
                "source_pages": {"start": 1, "end": 1},
                "has_subtitles": True,
                "entries": [
                    {
                        "id": "t007",
                        "type": "dialogue",
                        "pdf_page": 1,
                        "display_page": 1,
                        "source": "Hello.",
                        "translation": "你好。",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    invalid_raw_format_batch.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "invalid-raw-format",
                "source_pages": {"start": 1, "end": 1},
                "has_subtitles": False,
                "entries": [
                    {
                        "id": "t008",
                        "type": "scene_heading",
                        "pdf_page": 1,
                        "display_page": 1,
                        "source": "INT. TEST LOCATION - NIGHT",
                        "translation": "INT. 测试地点 - 夜",
                    },
                    {
                        "id": "t009",
                        "type": "transition",
                        "pdf_page": 1,
                        "display_page": 1,
                        "source": "CUT TO:",
                        "translation": "CUT TO: 测试区域",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    invalid_marker_identity_batch.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "invalid-marker-identity",
                "source_pages": {"start": 1, "end": 1},
                "has_subtitles": False,
                "entries": [
                    {
                        "id": "t010",
                        "type": "scene_heading",
                        "pdf_page": 1,
                        "display_page": 1,
                        "source": "INT. TEST LOCATION - NIGHT",
                        "translation": "内景。__测试地点__ - 夜",
                        "markers": [{"type": "scene_no", "position": "left"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    semantic_asterisk_batch.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "semantic-asterisk",
                "source_pages": {"start": 1, "end": 1},
                "has_subtitles": False,
                "entries": [
                    {
                        "id": "t011",
                        "type": "dialogue",
                        "pdf_page": 1,
                        "display_page": 1,
                        "source": "The terminal prints: use the wildcard *",
                        "translation": "终端显示：使用通配符*",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    revision_asterisk_batch_dir.mkdir(parents=True)
    revision_asterisk_project.write_text(
        "\n".join(
            [
                "project:",
                "  title: Revised Draft Fixture",
                "  chinese_title: 修订稿样例",
                "  source_language: en",
                "  target_language: zh-CN",
                "",
                "inputs:",
                "  screenplay_pdf: fixture [Rev.].pdf",
                "  subtitles: null",
                "",
                "outputs:",
                "  html: null",
                "  epub: null",
                "  pdf: null",
                "",
            ]
        ),
        encoding="utf-8",
    )
    revision_asterisk_missing_batch.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "revision-asterisk-missing",
                "source_pages": {"start": 1, "end": 1},
                "has_subtitles": False,
                "entries": [
                    {
                        "id": "r001",
                        "type": "action",
                        "pdf_page": 1,
                        "display_page": 1,
                        "source": "Synthetic action fragment waits. *",
                        "translation": "合成动作片段等待。",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    return [
        {
            "name": "validate_batch_consistent_terminology",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(consistent_batch),
                "--terminology",
                str(terminology_file),
            ],
        },
        {
            "name": "validate_batch_inconsistent_terminology_warns",
            "command": [
                python,
                "-c",
                (
                    "import subprocess, sys; from pathlib import Path; "
                    f"cmd=[sys.executable, {str(SCRIPTS_DIR / 'validate_batch.py')!r}, {str(inconsistent_batch)!r}, '--terminology', {str(terminology_file)!r}]; "
                    "result=subprocess.run(cmd, text=True, capture_output=True, check=False); "
                    "text=result.stdout + result.stderr; "
                    "missing='WARN batch.terminology_inconsistency' not in text; "
                    "bad=result.returncode != 0; "
                    "raise SystemExit('terminology warn missing: '+text if missing or bad else 0)"
                ),
            ],
        },
        {
            "name": "validate_batch_annotation_present",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(annotation_present_batch),
                "--terminology",
                str(terminology_file),
            ],
        },
        {
            "name": "validate_batch_annotation_missing_warns",
            "command": [
                python,
                "-c",
                (
                    "import subprocess, sys; from pathlib import Path; "
                    f"cmd=[sys.executable, {str(SCRIPTS_DIR / 'validate_batch.py')!r}, {str(annotation_missing_batch)!r}, '--terminology', {str(terminology_file)!r}]; "
                    "result=subprocess.run(cmd, text=True, capture_output=True, check=False); "
                    "text=result.stdout + result.stderr; "
                    "missing='WARN batch.subtitle_annotation_missing' not in text; "
                    "bad=result.returncode != 0; "
                    "raise SystemExit('annotation warn missing: '+text if missing or bad else 0)"
                ),
            ],
        },
        {
            "name": "validate_batch_raw_format_markers_fail",
            "command": [
                python,
                "-c",
                (
                    "import subprocess, sys; "
                    f"cmd=[sys.executable, {str(SCRIPTS_DIR / 'validate_batch.py')!r}, {str(invalid_raw_format_batch)!r}, '--final']; "
                    "result=subprocess.run(cmd, text=True, capture_output=True, check=False); "
                    "text=result.stdout + result.stderr; "
                    "missing='FAIL batch.final.raw_format_marker' not in text; "
                    "bad=result.returncode == 0; "
                    "raise SystemExit('raw marker fail missing: '+text if missing or bad else 0)"
                ),
            ],
        },
        {
            "name": "validate_batch_marker_identity_fails",
            "command": [
                python,
                "-c",
                (
                    "import subprocess, sys; "
                    f"cmd=[sys.executable, {str(SCRIPTS_DIR / 'validate_batch.py')!r}, {str(invalid_marker_identity_batch)!r}]; "
                    "result=subprocess.run(cmd, text=True, capture_output=True, check=False); "
                    "text=result.stdout + result.stderr; "
                    "missing='FAIL batch.marker_text' not in text; "
                    "bad=result.returncode == 0; "
                    "raise SystemExit('marker identity fail missing: '+text if missing or bad else 0)"
                ),
            ],
        },
        {
            "name": "validate_batch_semantic_asterisk_not_revision",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(semantic_asterisk_batch),
                "--final",
            ],
        },
        {
            "name": "validate_batch_revision_asterisk_requires_markup",
            "command": [
                python,
                "-c",
                (
                    "import subprocess, sys; "
                    f"cmd=[sys.executable, {str(SCRIPTS_DIR / 'validate_batch.py')!r}, {str(revision_asterisk_missing_batch)!r}, '--final']; "
                    "result=subprocess.run(cmd, text=True, capture_output=True, check=False); "
                    "text=result.stdout + result.stderr; "
                    "missing='FAIL batch.final.revision_asterisk_missing' not in text; "
                    "bad=result.returncode == 0; "
                    "raise SystemExit('revision asterisk fail missing: '+text if missing or bad else 0)"
                ),
            ],
        },
    ]
