#!/usr/bin/env python3
"""Merge, finalize, EPUB export, and cost-report checks."""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SmokeCheck, json_fixture


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    merge_project_dir = tmp_dir / "merge-project"
    merge_batch_dir = merge_project_dir / "work" / "batches"
    invalid_merge_project_dir = tmp_dir / "invalid-merge-project"
    invalid_merge_batch_dir = invalid_merge_project_dir / "work" / "batches"
    merge_markers = merge_project_dir / "work" / "source-markers.json"
    merge_html = merge_project_dir / "dist" / "screenplay-study.html"
    merge_epub = merge_project_dir / "dist" / "screenplay-study.epub"
    merge_project = merge_project_dir / "project.yaml"
    merge_batch_first = merge_batch_dir / "translated-p001-001.json"
    merge_batch_second = merge_batch_dir / "translated-p002-002.json"
    merged_batch = merge_batch_dir / "translated-p001-002.json"
    merge_context_dir = merge_project_dir / "work" / "context"
    merge_context = merge_context_dir / "batch-context-p001-001.json"
    merge_subtitles = merge_project_dir / "work" / "subtitles.json"
    merge_validation_log = merge_project_dir / "work" / "logs" / "merge-validation.json"
    invalid_merge_batch_first = invalid_merge_batch_dir / "translated-p001-001.json"
    invalid_merge_batch_second = invalid_merge_batch_dir / "translated-p002-002.json"
    invalid_merged_batch = invalid_merge_batch_dir / "translated-p001-002.json"
    invalid_merge_validation_log = (
        invalid_merge_project_dir / "work" / "logs" / "merge-validation.json"
    )

    merge_batch_dir.mkdir(parents=True)
    merge_context_dir.mkdir(parents=True)
    (merge_project_dir / "work").mkdir(exist_ok=True)
    (merge_project_dir / "dist").mkdir()
    invalid_merge_batch_dir.mkdir(parents=True)
    merge_project.write_text(
        "\n".join(
            [
                "project:",
                "  title: Merge Fixture",
                "  chinese_title: 合并样例",
                "  source_language: en",
                "  target_language: zh-CN",
                "",
                "inputs:",
                "  screenplay_pdf: missing-source.pdf",
                f"  subtitles: {merge_subtitles}",
                "",
                "outputs:",
                f"  marker_inventory: {merge_markers}",
                f"  html: {merge_html}",
                f"  epub: {merge_epub}",
                "  pdf: null",
                "",
                "audit:",
                "  require_subtitles: true",
                "  require_structured_markers: true",
                "  paper_size: A4",
                "",
            ]
        ),
        encoding="utf-8",
    )
    merge_markers.write_text(
        json_fixture(
            {
                "version": 1,
                "source": {"screenplay_pdf": "missing-source.pdf"},
                "markers": [
                    {
                        "type": "scene_no",
                        "pdf_page": 2,
                        "display_page": 1,
                        "text": "1",
                    },
                    {
                        "type": "scene_no",
                        "pdf_page": 2,
                        "display_page": 1,
                        "text": "1",
                    },
                    {
                        "type": "omitted",
                        "pdf_page": 3,
                        "display_page": 2,
                        "text": "OMITTED",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    merge_batch_first.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "translated-p001-001",
                "source_pages": {"start": 1, "end": 1},
                "has_subtitles": True,
                "front_matter": [
                    {
                        "id": "front-001",
                        "type": "note",
                        "pdf_page": 1,
                        "display_page": 0,
                        "source": "Written by AUTHOR_ALPHA",
                        "translation": "编剧：__作者甲__",
                    }
                ],
                "entries": [
                    {
                        "id": "p001-e001",
                        "type": "scene_heading",
                        "pdf_page": 2,
                        "display_page": 1,
                        "source": "INT. TEST LOCATION - NIGHT",
                        "translation": "内景。__测试地点__ - 夜",
                        "markers": [
                            {"type": "scene_no", "text": "1", "position": "left"},
                            {"type": "scene_no", "text": "1", "position": "right"},
                        ],
                    },
                    {
                        "id": "p001-e002",
                        "type": "dialogue",
                        "pdf_page": 2,
                        "display_page": 1,
                        "source": "Synthetic cue lands.",
                        "translation": "出现一记**合成提示音**。",
                        "subtitle_label": "字幕匹配",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    merge_subtitles.write_text(
        json_fixture(
            {
                "version": 1,
                "events": [
                    {
                        "start": 65.2,
                        "end": 66.4,
                        "text": "出现一记合成提示音。",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    merge_context.write_text(
        json_fixture(
            {
                "subtitle_candidates": {
                    "subtitle_timestamps": [
                        {
                            "entry_ids": ["p001-e002"],
                            "subtitle_event_index": 0,
                            "subtitle_start": 65.2,
                            "subtitle_end": 66.4,
                            "subtitle_match_confidence": "low",
                        }
                    ],
                    "unique_subtitle_timestamps": [],
                }
            }
        ),
        encoding="utf-8",
    )
    merge_batch_second.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "translated-p002-002",
                "source_pages": {"start": 2, "end": 2},
                "has_subtitles": False,
                "entries": [
                    {
                        "id": "p002-e001",
                        "type": "format_marker",
                        "pdf_page": 3,
                        "display_page": 2,
                        "source": "OMITTED",
                        "translation": "本场删去",
                        "markers": [{"type": "omitted", "text": "OMITTED"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    invalid_merge_batch_first.write_text(
        merge_batch_first.read_text(encoding="utf-8"), encoding="utf-8"
    )
    invalid_merge_batch_second.write_text(
        json_fixture(
            {
                "version": 1,
                "batch_id": "translated-p002-002",
                "source_pages": {"start": 2, "end": 2},
                "has_subtitles": False,
                "entries": [
                    {
                        "id": "p002-e001",
                        "type": "dialogue",
                        "pdf_page": 3,
                        "display_page": 2,
                        "source": "We wait.",
                        "translation": "待译对白：We wait.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    return [
        {
            "name": "finalize_unmerged_batches_rejected",
            "command": [
                python,
                str(SCRIPTS_DIR / "finalize_html.py"),
                str(merge_project),
                "--allow-missing-inputs",
            ],
            "expect_failure": True,
        },
        {
            "name": "merge_batch_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "merge_batches.py"),
                "--batch-dir",
                str(merge_batch_dir),
                "--output",
                str(merged_batch),
            ],
        },
        {
            "name": "assert_merge_validation_log_pass",
            "command": [
                python,
                "-c",
                (
                    "import json, sys; from pathlib import Path; "
                    f"log=Path({str(merge_validation_log)!r}); "
                    "payload=json.loads(log.read_text(encoding='utf-8')); "
                    "state=payload.get('overall_state'); "
                    "results=payload.get('results', []); "
                    "bad=state not in {'PASS', 'WARN'} or len(results)!=2; "
                    "sys.exit(f'merge validation log invalid: {state} {len(results)}' if bad else 0)"
                ),
            ],
        },
        {
            "name": "merge_batch_validation_failure_blocks_output",
            "command": [
                python,
                "-c",
                (
                    "import subprocess, sys; from pathlib import Path; "
                    "result=subprocess.run(["
                    f"{python!r}, "
                    f"{str(SCRIPTS_DIR / 'merge_batches.py')!r}, "
                    "'--batch-dir', "
                    f"{str(invalid_merge_batch_dir)!r}, "
                    "'--output', "
                    f"{str(invalid_merged_batch)!r}"
                    "], text=True, capture_output=True, check=False); "
                    "text=result.stdout + result.stderr; "
                    "bad_exit=result.returncode == 0; "
                    "missing='FAIL merge_validation.failed_batches' not in text; "
                    f"output_exists=Path({str(invalid_merged_batch)!r}).exists(); "
                    "raise SystemExit('merge validation failure did not block: '+text "
                    "if bad_exit or missing or output_exists else 0)"
                ),
            ],
        },
        {
            "name": "assert_merge_validation_log_fail",
            "command": [
                python,
                "-c",
                (
                    "import json, sys; from pathlib import Path; "
                    f"log=Path({str(invalid_merge_validation_log)!r}); "
                    "payload=json.loads(log.read_text(encoding='utf-8')); "
                    "state=payload.get('overall_state'); "
                    "failed=payload.get('failed_batches', []); "
                    "bad=state!='FAIL' or not failed; "
                    "sys.exit(f'failed merge validation log invalid: {state} {failed}' if bad else 0)"
                ),
            ],
        },
        {
            "name": "validate_merged_batch_fixture_final",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(merged_batch),
                "--final",
            ],
        },
        {
            "name": "assert_merged_batch_subtitle_timestamps",
            "command": [
                python,
                "-c",
                (
                    "import json; from pathlib import Path; "
                    f"data=json.loads(Path({str(merged_batch)!r}).read_text(encoding='utf-8')); "
                    "entry=next(item for item in data['entries'] if item['id']=='p001-e002'); "
                    "bad=entry.get('subtitle_event_index')!=0 or entry.get('subtitle_start')!=65.2 "
                    "or entry.get('subtitle_end')!=66.4 or entry.get('subtitle_match_confidence')!='low'; "
                    "raise SystemExit('merged timestamp missing or invalid' if bad else 0)"
                ),
            ],
        },
        {
            "name": "finalize_merged_batch_html",
            "command": [
                python,
                str(SCRIPTS_DIR / "finalize_html.py"),
                str(merge_project),
                "--allow-missing-inputs",
            ],
        },
        {
            "name": "assert_merged_html_pages",
            "command": [
                python,
                "-c",
                (
                    "from pathlib import Path; "
                    f"text=Path({str(merge_html)!r}).read_text(encoding='utf-8'); "
                    "required=['原剧本第 1 页', '原剧本第 2 页', '本场删去', '~01:05']; "
                    "missing=[item for item in required if item not in text]; "
                    "raise SystemExit('merged html missing: '+repr(missing) if missing else 0)"
                ),
            ],
        },
        {
            "name": "export_merged_epub",
            "command": [
                python,
                str(SCRIPTS_DIR / "export_epub.py"),
                str(merge_project),
            ],
        },
        {
            "name": "assert_merged_epub",
            "command": [
                python,
                "-c",
                (
                    "from pathlib import Path\n"
                    "import zipfile\n"
                    "from ebooklib import epub\n"
                    f"path=Path({str(merge_epub)!r})\n"
                    "bad=[]\n"
                    "if not path.exists() or path.stat().st_size == 0:\n"
                    "    bad.append('missing')\n"
                    "book=epub.read_epub(str(path))\n"
                    "names={item.get_name() for item in book.get_items()}\n"
                    "spine=[item[0] if isinstance(item, tuple) else item for item in book.spine]\n"
                    "if 'cover.xhtml' not in names:\n"
                    "    bad.append('cover')\n"
                    "if not any(name.startswith('chapter-') for name in names):\n"
                    "    bad.append('chapter')\n"
                    "if len(spine) < 3:\n"
                    "    bad.append('spine')\n"
                    "with zipfile.ZipFile(path) as archive:\n"
                    "    text='\\n'.join(\n"
                    "        archive.read(name).decode('utf-8', errors='ignore')\n"
                    "        for name in archive.namelist()\n"
                    "        if name.endswith(('.xhtml', '.html'))\n"
                    "    )\n"
                    "if '本中文剧本学习版仅供个人学习与研究使用，请勿商用或公开传播。' not in text:\n"
                    "    bad.append('rights')\n"
                    "if '原剧本第 1 页' not in text:\n"
                    "    bad.append('toc-page')\n"
                    "if '~01:05' not in text:\n"
                    "    bad.append('subtitle-time')\n"
                    "if '内景。测试地点' not in text:\n"
                    "    bad.append('toc-scene')\n"
                    "raise SystemExit('epub assertion failed: '+repr(bad) if bad else 0)\n"
                ),
            ],
        },
        {
            "name": "assert_finalize_cost_report",
            "command": [
                python,
                "-c",
                (
                    "import json; from pathlib import Path; "
                    f"path=Path({str(merge_project_dir / 'work' / 'reports' / 'cost-report.json')!r}); "
                    "data=json.loads(path.read_text(encoding='utf-8')); "
                    "estimate=data.get('cost_estimate', {}); "
                    "ok=estimate.get('status')=='estimated' "
                    "and estimate.get('estimated_total_usd') is not None "
                    "and estimate.get('not_billing_authority') is True; "
                    "raise SystemExit(0 if ok else 'finalize cost report missing estimate')"
                ),
            ],
        },
    ]
