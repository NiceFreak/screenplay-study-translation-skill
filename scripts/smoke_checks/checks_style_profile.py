#!/usr/bin/env python3
"""Style profile generation checks with and without subtitles."""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SmokeCheck, json_fixture


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    style_profile_project_dir = tmp_dir / "style-profile-project"
    style_profile_work = style_profile_project_dir / "work"
    style_profile_work.mkdir(parents=True)
    (style_profile_project_dir / "work" / "source-lines.json").write_text(
        json_fixture(
            {
                "version": 1,
                "source": {"screenplay_pdf": "source.pdf"},
                "rows": [
                    {
                        "pdf_page": 1,
                        "display_page": 1,
                        "text": "INT. TEST LOCATION - DAY",
                        "zone": "body",
                    },
                    {
                        "pdf_page": 1,
                        "display_page": 1,
                        "text": "Character Alpha says a synthetic line.",
                        "zone": "body",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (style_profile_project_dir / "work" / "subtitles.json").write_text(
        json_fixture(
            {
                "version": 1,
                "source": "generated",
                "events": [
                    {"start": 0.0, "end": 1.0, "text": "角色甲，执行测试指令！"},
                    {"start": 1.1, "end": 2.0, "text": "这是一个合成测试时刻。"},
                ],
            }
        ),
        encoding="utf-8",
    )

    style_profile_no_subtitles_project_dir = (
        tmp_dir / "style-profile-no-subtitles-project"
    )
    style_profile_no_subtitles_work = style_profile_no_subtitles_project_dir / "work"
    style_profile_no_subtitles_work.mkdir(parents=True)
    (style_profile_no_subtitles_work / "source-lines.json").write_text(
        json_fixture(
            {
                "version": 1,
                "source": {"screenplay_pdf": "source.pdf"},
                "rows": [
                    {
                        "pdf_page": 1,
                        "display_page": 1,
                        "text": "EXT. TEST AREA - NIGHT",
                        "zone": "body",
                    },
                    {
                        "pdf_page": 1,
                        "display_page": 1,
                        "text": "A synthetic figure crosses the test area.",
                        "zone": "body",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    return [
        {
            "name": "build_style_profile_with_subtitles",
            "command": [
                python,
                str(SCRIPTS_DIR / "build_style_profile.py"),
                str(style_profile_project_dir / "work" / "source-lines.json"),
            ],
        },
        {
            "name": "assert_style_profile_contains_evidence",
            "command": [
                python,
                "-c",
                (
                    "import json; from pathlib import Path; "
                    f"path=Path({str(style_profile_project_dir / 'work' / 'style-profile.json')!r}); "
                    "data=json.loads(path.read_text(encoding='utf-8')); "
                    "missing=[]; "
                    "missing += ['subtitle_style_notes'] if 'subtitle_style_notes' not in data else []; "
                    "missing += ['profile_hints.dialogue_tone.evidence'] if 'evidence' not in data.get('profile_hints', {}).get('dialogue_tone', {}) else []; "
                    "missing += ['profile_semantics'] if data.get('profile_semantics') != 'heuristic_hints_pending_first_batch_confirmation' else []; "
                    "missing += ['style_basis'] if data.get('style_basis') != 'subtitles' else []; "
                    "raise SystemExit('style profile evidence missing: '+','.join(missing) if missing else 0)"
                ),
            ],
        },
        {
            "name": "build_style_profile_without_subtitles",
            "command": [
                python,
                str(SCRIPTS_DIR / "build_style_profile.py"),
                str(style_profile_no_subtitles_work / "source-lines.json"),
            ],
        },
        {
            "name": "assert_style_profile_no_subtitle_notes",
            "command": [
                python,
                "-c",
                (
                    "import json; from pathlib import Path; "
                    f"path=Path({str(style_profile_no_subtitles_work / 'style-profile.json')!r}); "
                    "data=json.loads(path.read_text(encoding='utf-8')); "
                    "bad='subtitle_style_notes' in data; "
                    "missing='profile_hints' not in data or 'evidence' not in data or data.get('style_basis') != 'source_lines'; "
                    "raise SystemExit('style profile no-subtitle contract failed' if bad or missing else 0)"
                ),
            ],
        },
    ]
