#!/usr/bin/env python3
"""HTML rendering, navigation, marker, and finalize checks for valid batches."""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import (
    HTML_FIXTURE_DIR,
    SCRIPTS_DIR,
    VALID_BATCH,
    VALID_NO_SCENE_NUMBERS_BATCH,
    SmokeCheck,
)


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    html_fixture_dir = HTML_FIXTURE_DIR
    valid_batch = VALID_BATCH
    valid_no_scene_numbers_batch = VALID_NO_SCENE_NUMBERS_BATCH
    batch_html = tmp_dir / "batch.html"
    no_scene_numbers_html = tmp_dir / "no-scene-numbers.html"
    batch_pdf = tmp_dir / "batch.pdf"
    batch_markers = tmp_dir / "batch-source-markers.json"
    batch_project = tmp_dir / "batch-project.yaml"
    batch_project.write_text(
        "\n".join(
            [
                "project:",
                "  title: Batch HTML Fixture",
                "  chinese_title: 批次HTML样例",
                "  source_language: en",
                "  target_language: zh-CN",
                "",
                "inputs:",
                "  screenplay_pdf: missing-source.pdf",
                "  subtitles: null",
                "",
                "outputs:",
                f"  marker_inventory: {batch_markers}",
                f"  html: {batch_html}",
                "  epub: null",
                # SKIP: PDF output deprecated in v0.3. See references/decisions.md.
                "  pdf: null",
                "",
                "audit:",
                "  require_subtitles: false",
                "  require_structured_markers: true",
                "  paper_size: A4",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return [
        {
            "name": "build_valid_batch_html",
            "command": [
                python,
                str(SCRIPTS_DIR / "build_html.py"),
                str(valid_batch),
                "--output",
                str(batch_html),
            ],
        },
        {
            "name": "assert_valid_batch_html_layout",
            "command": [
                python,
                "-c",
                (
                    "import json; "
                    "from pathlib import Path; "
                    f"text=Path({str(batch_html)!r}).read_text(encoding='utf-8'); "
                    f"progress=json.loads(Path({str(html_fixture_dir / 'expected-progress-snippets.json')!r}).read_text(encoding='utf-8'))['snippets']; "
                    "required=['<style>', '原剧本第 1 页', 'scene-marker-left', 'scene-marker-right', "
                    "'position: fixed;', 'scroll-padding-top', 'document.addEventListener(\"pointerdown\"', "
                    "'const closeSceneIndex = () =>', 'closeSceneIndex();', "
                    "'font-weight: 700;', 'border-color: color-mix(in srgb, var(--accent) 45%, var(--rule));', "
                    "'.entry.note', '.reader-annotation', '.revision-asterisk', "
                    "'<details class=\"scene-index\"', '<summary id=\"scene-index-title\">场次索引</summary>', "
                    "'本中文剧本学习版仅供个人学习与研究使用，请勿商用或公开传播。', "
                    "'原剧本共 2 页', '未提供参考字幕，译文仅依据剧本正文生成。', "
                    "'<span class=\"proper-name\">下划线</span>用于人物、地点、片名等专名', "
                    "'<strong class=\"emphasis\">加粗</strong>用于音效、银幕重点或剧本强调', "
                    "'<em class=\"term\">斜体</em>用于英文剧本术语、缩写或格式说明', "
                    "'1 · 内景。<span class=\"proper-name\">测试地点</span> - 夜', "
                    '\'<span class="scene-marker-slot scene-marker-left"><span class="marker marker-scene_no scene-no" data-marker-type="scene_no" data-marker-position="left">1</span></span>\', '
                    '\'<span class="scene-marker-slot scene-marker-right"><span class="marker marker-scene_no scene-no" data-marker-type="scene_no" data-marker-position="right">1</span></span>\', '
                    "'<span class=\"proper-name\">角色甲</span>', "
                    "'<span class=\"reader-annotation\">提示音</span>', "
                    "'<span class=\"reader-annotation\">屏幕文字</span>', "
                    '\'<p class="entry-line-with-revision-asterisk"><span class="entry-line-text">合成动作片段等待。</span><span class="revision-asterisk" aria-label="源剧本修订星号">*</span></p>\']; '
                    "forbidden=[]; "
                    "missing=[item for item in required + progress if item not in text]; "
                    "bad=[item for item in forbidden if item in text]; "
                    "missing += ['forbidden present: '+repr(bad)] if bad else []; "
                    "raise SystemExit('missing layout markers: '+repr(missing) if missing else 0)"
                ),
            ],
        },
        {
            "name": "build_no_scene_numbers_html",
            "command": [
                python,
                str(SCRIPTS_DIR / "build_html.py"),
                str(valid_no_scene_numbers_batch),
                "--output",
                str(no_scene_numbers_html),
            ],
        },
        {
            "name": "assert_no_scene_numbers_navigation",
            "command": [
                python,
                "-c",
                (
                    "from pathlib import Path; "
                    f"text=Path({str(no_scene_numbers_html)!r}).read_text(encoding='utf-8'); "
                    "required=['<summary id=\"scene-index-title\">场景导航</summary>', "
                    "'内景。<span class=\"proper-name\">测试地点</span> - 夜', "
                    "'外景。<span class=\"proper-name\">测试区域</span> - 日']; "
                    "forbidden=['<summary id=\"scene-index-title\">场次索引</summary>', "
                    "'1 · 内景。', '2 · 外景。']; "
                    "missing=[item for item in required if item not in text]; "
                    "bad=[item for item in forbidden if item in text]; "
                    "raise SystemExit(f'no-scene navigation missing={missing} bad={bad}' if missing or bad else 0)"
                ),
            ],
        },
        {
            "name": "build_valid_batch_markers",
            "command": [
                python,
                str(SCRIPTS_DIR / "batch_markers.py"),
                str(valid_batch),
                "--output",
                str(batch_markers),
            ],
        },
        {
            "name": "export_valid_batch_pdf",
            "command": [
                python,
                str(SCRIPTS_DIR / "export_pdf.py"),
                str(batch_html),
                "--output",
                str(batch_pdf),
            ],
            # SKIP: PDF output deprecated in v0.3. See references/decisions.md.
            "skip": True,
            "skip_reason": "PDF output deprecated in v0.3. See references/decisions.md.",
        },
        {
            "name": "audit_valid_batch_outputs",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(batch_project),
                "--allow-missing-inputs",
            ],
        },
        {
            "name": "finalize_valid_batch_html",
            "command": [
                python,
                str(SCRIPTS_DIR / "finalize_html.py"),
                str(batch_project),
                str(valid_batch),
                "--output",
                str(tmp_dir / "finalized-batch.html"),
                "--allow-missing-inputs",
            ],
        },
    ]
