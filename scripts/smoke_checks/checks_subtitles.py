#!/usr/bin/env python3
"""Subtitle parsing and subtitle report checks."""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SUBTITLE_FIXTURE_DIR, SmokeCheck


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    subtitle_fixture_dir = SUBTITLE_FIXTURE_DIR
    subtitle_report = tmp_dir / "subtitle-report.txt"
    assert_ass_annotation_script = tmp_dir / "assert_ass_annotation_type.py"
    assert_ass_annotation_script.write_text(
        "\n".join(
            [
                "import json",
                "from pathlib import Path",
                f"payload = Path({str(tmp_dir / 'sample.ass.json')!r}).read_text(encoding='utf-8')",
                "data = json.loads(payload)",
                "events = data.get('events') if isinstance(data, dict) else data",
                "annotations = [e for e in events if isinstance(e, dict) and e.get('type') == 'annotation']",
                "dialogues = [e for e in events if isinstance(e, dict) and e.get('type') != 'annotation']",
                "if len(annotations) != 1: raise SystemExit('annotation event count=' + str(len(annotations)))",
                "if annotations[0].get('text', '') != '这是一个顶部注释': raise SystemExit('annotation text mismatch')",
                "if any(e.get('text', '').startswith('这是一个顶部注释') for e in dialogues): raise SystemExit('comment misclassified as dialogue')",
                "raise SystemExit(0)",
            ]
        ),
        encoding="utf-8",
    )

    return [
        {
            "name": "parse_ass_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "parse_subtitles.py"),
                str(subtitle_fixture_dir / "sample.ass"),
                "--output",
                str(tmp_dir / "sample.ass.json"),
            ],
        },
        {
            "name": "assert_ass_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "assert_marker_counts.py"),
                str(tmp_dir / "sample.ass.json"),
                str(subtitle_fixture_dir / "expected-counts.json"),
            ],
        },
        {
            "name": "assert_ass_annotation_type",
            "command": [
                python,
                str(assert_ass_annotation_script),
            ],
        },
        {
            "name": "parse_srt_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "parse_subtitles.py"),
                str(subtitle_fixture_dir / "sample.srt"),
                "--output",
                str(tmp_dir / "sample.srt.json"),
            ],
        },
        {
            "name": "assert_srt_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "assert_marker_counts.py"),
                str(tmp_dir / "sample.srt.json"),
                str(subtitle_fixture_dir / "expected-counts-srt-vtt.json"),
            ],
        },
        {
            "name": "parse_vtt_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "parse_subtitles.py"),
                str(subtitle_fixture_dir / "sample.vtt"),
                "--output",
                str(tmp_dir / "sample.vtt.json"),
            ],
        },
        {
            "name": "assert_vtt_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "assert_marker_counts.py"),
                str(tmp_dir / "sample.vtt.json"),
                str(subtitle_fixture_dir / "expected-counts-srt-vtt.json"),
            ],
        },
        {
            "name": "subtitle_report_fixture",
            "command": [
                "sh",
                "-c",
                " ".join(
                    [
                        python,
                        str(SCRIPTS_DIR / "subtitle_report.py"),
                        str(subtitle_fixture_dir / "sample.ass"),
                        "--output",
                        str(subtitle_report),
                        "&&",
                        "grep",
                        "-q",
                        "'INFO subtitle.events count=5'",
                        str(subtitle_report),
                        "&&",
                        "grep",
                        "-q",
                        "'INFO subtitle.term_candidate count=2 text=术语甲'",
                        str(subtitle_report),
                    ]
                ),
            ],
        },
    ]
