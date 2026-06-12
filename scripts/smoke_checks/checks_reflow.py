#!/usr/bin/env python3
"""Reflow project checks: batch context, subtitle timestamps, HTML reflow."""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SmokeCheck, json_fixture


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    reflow_project_dir = tmp_dir / "reflow-project"
    reflow_batch_dir = reflow_project_dir / "work" / "batches"
    reflow_batch = reflow_batch_dir / "reflow-batch.json"
    reflow_source_lines = reflow_project_dir / "work" / "source-lines.json"
    reflow_subtitles = reflow_project_dir / "work" / "subtitles.json"
    reflow_project = reflow_project_dir / "project.yaml"
    reflow_html = reflow_project_dir / "dist" / "reflow.html"

    reflow_batch_dir.mkdir(parents=True)
    (reflow_project_dir / "dist").mkdir()
    (reflow_project_dir / "references").mkdir()
    reflow_subtitles.write_text(
        json_fixture(
            {
                "version": 1,
                "source": "fixture.ass",
                "events": [
                    {
                        "start": 2.0,
                        "end": 4.0,
                        "text": "合成任务甲到底是什么 What is Synthetic Task Alpha exactly?",
                    },
                    {
                        "start": 12.0,
                        "end": 14.0,
                        "text": "字幕压缩这句较长的合成对白 The subtitles compress this longer synthetic line.",
                    },
                    {
                        "start": 820.0,
                        "end": 822.0,
                        "text": "这句补充合成对白显示时间较靠后 This additional synthetic line appears later.",
                    },
                    {
                        "start": 900.0,
                        "end": 901.5,
                        "text": "This synthetic misclassified line should match subtitles.",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    reflow_project.write_text(
        "\n".join(
            [
                "project:",
                "  title: Synthetic Case Title",
                "  chinese_title: 合成案例标题",
                "",
                "outputs:",
                "  subtitles_json: work/subtitles.json",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reflow_project_dir / "work" / "logs").mkdir(parents=True)
    (reflow_project_dir / "work" / "logs" / "stage-1-2-findings.json").write_text(
        json_fixture(
            {
                "version": 1,
                "stage": "STAGE 1-2",
                "overall_state": "PASS",
                "records": [],
                "signal_counts": {
                    "structural_signal": 0,
                    "warning_signal": 0,
                    "noise_signal": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    (reflow_project_dir / "references" / "reader_notes.md").write_text(
        "\n".join(
            [
                "# 阅读说明",
                "",
                "下划线用于人物、地点、片名等专名；**加粗**用于音效、银幕重点或剧本强调；*斜体*用于英文剧本术语、缩写或格式说明。",
                "",
                "对应原剧本显示页码；场号保留原剧本边栏编号。",
                "",
                "已参考提供的中文字幕，方便对照对白。",
                "",
                "## 格式约定",
                "",
                "| English | Chinese | Notes |",
                "|---------|---------|-------|",
                "| CONT'D | 续 | 同一说话者或同一格式块延续。 |",
                "| MORE | 下页续 | 页尾对白延续提示。 |",
                "",
                "### 本剧本出现的专业术语",
                "",
                "- **行尾星号（*）**：修订稿标记，译文原位保留，不作为剧情正文翻译。",
            ]
        ),
        encoding="utf-8",
    )
    (reflow_project_dir / "references" / "front_matter.md").write_text(
        "\n".join(
            [
                "剧本名：__合成案例标题__（原文：SYNTHETIC CASE TITLE）",
                "",
                "编剧：__作者甲__（Author Alpha）",
                "",
                "改编自__作者乙__（Author Beta）的合成文本",
                "",
                "稿本日期：2022 年 12 月 15 日",
            ]
        ),
        encoding="utf-8",
    )
    reflow_source_lines.write_text(
        json_fixture(
            {
                "version": 1,
                "source": {"screenplay_pdf": "fixture.pdf"},
                "rows": [
                    {
                        "pdf_page": 1,
                        "display_page": 0,
                        "text": "SYNTHETIC CASE TITLE",
                        "zone": "body",
                    },
                    {
                        "pdf_page": 1,
                        "display_page": 0,
                        "text": "Screenplay by",
                        "zone": "body",
                    },
                    {
                        "pdf_page": 1,
                        "display_page": 0,
                        "text": "Author Alpha",
                        "zone": "body",
                    },
                    {
                        "pdf_page": 13,
                        "display_page": 12,
                        "text": "INT. TEST LOCATION - DAY",
                        "zone": "body",
                        "x": 72.0,
                    },
                    {
                        "pdf_page": 13,
                        "display_page": 12,
                        "text": "CHARACTER_ALPHA",
                        "zone": "body",
                        "x": 240.0,
                    },
                    {
                        "pdf_page": 13,
                        "display_page": 12,
                        "text": "What is Synthetic Task Alpha?",
                        "zone": "body",
                        "x": 180.0,
                    },
                    {
                        "pdf_page": 13,
                        "display_page": 12,
                        "text": "exactly?",
                        "zone": "body",
                        "x": 180.0,
                    },
                    {
                        "pdf_page": 13,
                        "display_page": 12,
                        "text": "MYSTERY",
                        "zone": "body",
                        "x": 240.0,
                    },
                    {
                        "pdf_page": 13,
                        "display_page": 12,
                        "text": "(This synthetic misclassified line should match subtitles.)",
                        "zone": "body",
                        "x": 180.0,
                    },
                    {
                        "pdf_page": 13,
                        "display_page": 12,
                        "text": "CHARACTER_BETA",
                        "zone": "body",
                        "x": 240.0,
                    },
                    {
                        "pdf_page": 13,
                        "display_page": 12,
                        "text": "The subtitles compress this longer synthetic line.",
                        "zone": "body",
                        "x": 180.0,
                    },
                    {
                        "pdf_page": 13,
                        "display_page": 12,
                        "text": "This additional synthetic line appears later.",
                        "zone": "body",
                        "x": 180.0,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (reflow_project_dir / "work" / "source-markers.json").write_text(
        json_fixture(
            {
                "version": 1,
                "source": {"screenplay_pdf": "fixture.pdf"},
                "markers": [],
            }
        ),
        encoding="utf-8",
    )
    reflow_batch.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "reflow",
                "source_pages": {"start": 12, "end": 12},
                "has_subtitles": True,
                "entries": [
                    {
                        "id": "r000",
                        "type": "scene_heading",
                        "pdf_page": 13,
                        "display_page": 12,
                        "source": "INT. TEST LOCATION - DAY",
                        "translation": "内景。测试地点 - 日",
                    },
                    {
                        "id": "r001",
                        "type": "action",
                        "pdf_page": 13,
                        "display_page": 12,
                        "source": "A synthetic object lands. The label reads:",
                        "translation": "一个合成道具落下。标签写着：“《",
                    },
                    {
                        "id": "r002",
                        "type": "action",
                        "pdf_page": 13,
                        "display_page": 12,
                        "source": "Synthetic Continuity Check",
                        "translation": "合成连续性检查》。”",
                    },
                    {
                        "id": "r003",
                        "type": "character",
                        "pdf_page": 13,
                        "display_page": 12,
                        "source": "CHARACTER_ALPHA",
                        "translation": "__角色甲__",
                    },
                    {
                        "id": "r004",
                        "type": "dialogue",
                        "pdf_page": 13,
                        "display_page": 12,
                        "source": "What is Synthetic Task Alpha?",
                        "translation": "__合成任务甲__",
                        "subtitle_label": "字幕匹配",
                        "subtitle_event_index": 0,
                        "subtitle_start": 2.0,
                        "subtitle_end": 4.0,
                    },
                    {
                        "id": "r005",
                        "type": "dialogue",
                        "pdf_page": 13,
                        "display_page": 12,
                        "source": "exactly?",
                        "translation": "到底是什么？",
                        "subtitle_label": "字幕匹配",
                        "subtitle_event_index": 0,
                        "subtitle_start": 2.0,
                        "subtitle_end": 4.0,
                    },
                    {
                        "id": "r006",
                        "type": "character",
                        "pdf_page": 13,
                        "display_page": 12,
                        "source": "CHARACTER_BETA",
                        "translation": "__角色乙__",
                    },
                    {
                        "id": "r007",
                        "type": "dialogue",
                        "pdf_page": 13,
                        "display_page": 12,
                        "source": "The subtitles compress this longer synthetic line.",
                        "translation": "字幕压缩这句较长的合成对白。",
                        "subtitle_label": "字幕差异",
                    },
                    {
                        "id": "r008",
                        "type": "dialogue",
                        "pdf_page": 13,
                        "display_page": 12,
                        "source": "This additional synthetic line appears later.",
                        "translation": "这句补充合成对白显示时间较靠后。",
                        "subtitle_label": "字幕未见",
                    },
                    {
                        "id": "r009",
                        "type": "action",
                        "pdf_page": 13,
                        "display_page": 12,
                        "source": "- A child's mouth opens wide, a huge gap between teeth",
                        "translation": "- 一个孩子大张着嘴，门牙之间露出巨大的",
                    },
                    {
                        "id": "r010",
                        "type": "action",
                        "pdf_page": 13,
                        "display_page": 12,
                        "source": "gap, tiny tongue clearly hanging in view.",
                        "translation": "缺口，小舌头清清楚楚地垂在视野里。",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    return [
        {
            "name": "confirm_reflow_stage2",
            "command": [
                python,
                str(SCRIPTS_DIR / "confirm_stage2.py"),
                str(reflow_project),
                "--decision",
                "Reflow fixture uses a preconfirmed empty Stage 2 signal log.",
            ],
        },
        {
            "name": "package_reflow_batch_context",
            "command": [
                python,
                str(SCRIPTS_DIR / "package_batch_context.py"),
                str(reflow_project),
                "--display-page-start",
                "12",
                "--display-page-end",
                "12",
                "--output",
                str(tmp_dir / "reflow-context-package.json"),
            ],
        },
        {
            "name": "assert_reflow_subtitle_timestamps",
            "command": [
                python,
                "-c",
                (
                    "import json; "
                    "from pathlib import Path; "
                    f"data=json.loads(Path({str(tmp_dir / 'reflow-context-package.json')!r}).read_text(encoding='utf-8')); "
                    "timestamps=data.get('subtitle_candidates', {}).get('unique_subtitle_timestamps', []); "
                    "all_timestamps=data.get('subtitle_candidates', {}).get('subtitle_timestamps', []); "
                    "ok=any(len(item.get('entry_ids') or [])==2 "
                    "and item.get('subtitle_event_index')==0 "
                    "and item.get('subtitle_start')==2.0 "
                    "and item.get('subtitle_end')==4.0 "
                    "for item in timestamps) and all(item.get('subtitle_event_index')!=1 for item in timestamps) "
                    "and any(item.get('subtitle_event_index')==1 and item.get('subtitle_match_confidence')=='low' for item in all_timestamps) "
                    "and any(item.get('subtitle_event_index')==3 and item.get('subtitle_start')==900.0 for item in all_timestamps); "
                    "raise SystemExit(0 if ok else 'stable subtitle timestamp missing')"
                ),
            ],
        },
        {
            "name": "assert_subtitle_time_format",
            "command": [
                python,
                "-c",
                (
                    "import sys; "
                    f"sys.path.insert(0, {str(SCRIPTS_DIR)!r}); "
                    "import build_html; "
                    "ok=(build_html.format_subtitle_time(757.62)=='12:37' "
                    "and build_html.format_subtitle_time(65.20)=='01:05' "
                    "and build_html.format_subtitle_time(3915.20)=='01:05:15'); "
                    "raise SystemExit(0 if ok else 'subtitle time format failed')"
                ),
            ],
        },
        {
            "name": "build_reflow_batch_html",
            "command": [
                python,
                str(SCRIPTS_DIR / "build_html.py"),
                str(reflow_batch),
                "--output",
                str(reflow_html),
                "--project",
                str(reflow_project),
            ],
        },
        {
            "name": "assert_reflow_batch_html",
            "command": [
                python,
                "-c",
                (
                    "from pathlib import Path; "
                    f"text=Path({str(reflow_html)!r}).read_text(encoding='utf-8'); "
                    "required=['data-display-unit-type=\"prose\"', 'data-source-entry-ids=\"r001,r002\"', "
                    "'一个合成道具落下。标签写着：“《合成连续性检查》。”', "
                    "'剧本名：<span class=\"proper-name\">合成案例标题</span>（原文：SYNTHETIC CASE TITLE）', "
                    "'编剧：<span class=\"proper-name\">作者甲</span>（Author Alpha）', "
                    "'改编自<span class=\"proper-name\">作者乙</span>（Author Beta）的合成文本', "
                    "'class=\"entry scene-heading scene-heading-no-markers\"', "
                    '\'<div id="r000" class="entry scene-heading scene-heading-no-markers"\', '
                    "'data-source-entry-ids=\"r004,r005\"', '<span class=\"subtitle-label\">字幕匹配 00:02</span>', "
                    "'data-source-entry-ids=\"r009,r010\"', "
                    "'- 一个孩子大张着嘴，门牙之间露出巨大的缺口，小舌头清清楚楚地垂在视野里。', "
                    "'格式约定', '<table>', '<th>English</th>', '<td>CONT&#x27;D</td>', "
                    "'本剧本出现的专业术语', '行尾星号（*）']; "
                    "forbidden=['标题页信息：', '<p>Screenplay by</p>', '<p>Author Alpha</p>', '<span class=\"subtitle-label\">字幕未见 00:', "
                    "'<h3>阅读说明</h3>', '| English | Chinese | Notes |', "
                    '\'id="r000" class="entry scene-heading scene-heading-no-markers" data-source-entry-ids="r000" data-entry-type="scene_heading" data-pdf-page="13" data-display-page="12"><span class="scene-marker-slot\']; '
                    "missing=[item for item in required if item not in text]; "
                    "bad=[item for item in forbidden if item in text]; "
                    "bad += ['reader-note-title-count'] if text.count('>阅读说明<') != 1 else []; "
                    "missing += ['forbidden present: '+repr(bad)] if bad else []; "
                    "raise SystemExit('reflow html missing: '+repr(missing) if missing else 0)"
                ),
            ],
        },
    ]
