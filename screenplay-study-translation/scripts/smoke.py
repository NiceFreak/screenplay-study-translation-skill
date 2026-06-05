#!/usr/bin/env python3
"""Run the skill repository's low-cost smoke checks."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypedDict


ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "screenplay-study-translation"
SCRIPTS_DIR = SKILL_DIR / "scripts"


class Check(TypedDict):
    name: str
    command: list[str]


class SmokeCheck(Check, total=False):
    expect_failure: bool


def json_fixture(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def run_check(
    name: str,
    command: list[str],
    env: dict[str, str] | None = None,
    expect_failure: bool = False,
) -> bool:
    print(f"== {name}", flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, check=False)
    if expect_failure and result.returncode != 0:
        print(f"PASS {name} expected_failure exit={result.returncode}", flush=True)
        return True
    if not expect_failure and result.returncode == 0:
        print(f"PASS {name}", flush=True)
        return True
    print(f"FAIL {name} exit={result.returncode}", flush=True)
    return False


def main() -> int:
    python = sys.executable
    env = os.environ.copy()
    env.setdefault("PYTHONPYCACHEPREFIX", "/private/tmp/codex-pycache")
    tmp_dir = Path(tempfile.mkdtemp(prefix="screenplay-skill-smoke-"))
    env.setdefault("RUFF_CACHE_DIR", str(tmp_dir / "ruff-cache"))
    pdf_scan_project = tmp_dir / "pdf-scan-project.yaml"
    pdf_scan_source = tmp_dir / "source.pdf"
    pdf_scan_inventory = tmp_dir / "source-markers.json"
    subtitle_fixture_dir = SKILL_DIR / "assets" / "fixtures" / "subtitles"
    valid_batch = SKILL_DIR / "assets" / "fixtures" / "batches" / "valid" / "batch.json"
    valid_no_scene_numbers_batch = (
        SKILL_DIR
        / "assets"
        / "fixtures"
        / "batches"
        / "valid-no-scene-numbers"
        / "batch.json"
    )
    batch_html = tmp_dir / "batch.html"
    no_scene_numbers_html = tmp_dir / "no-scene-numbers.html"
    batch_pdf = tmp_dir / "batch.pdf"
    batch_markers = tmp_dir / "batch-source-markers.json"
    batch_project = tmp_dir / "batch-project.yaml"
    merge_project_dir = tmp_dir / "merge-project"
    merge_batch_dir = merge_project_dir / "work" / "batches"
    merge_markers = merge_project_dir / "work" / "source-markers.json"
    merge_html = merge_project_dir / "dist" / "screenplay-study.html"
    merge_project = merge_project_dir / "project.yaml"
    merge_batch_first = merge_batch_dir / "translated-p001-001.json"
    merge_batch_second = merge_batch_dir / "translated-p002-002.json"
    merged_batch = merge_batch_dir / "translated-p001-002.json"
    initialized_project_dir = tmp_dir / "initialized-project"
    initialized_project = initialized_project_dir / "project.yaml"
    sample_project_dir = tmp_dir / "sample-project"
    sample_project = sample_project_dir / "project.yaml"
    sample_pdf = sample_project_dir / "inputs" / "sample.pdf"
    sample_batch = tmp_dir / "sample-structure-batch.json"
    sample_html = tmp_dir / "sample-structure.html"
    sample_draft_batch = tmp_dir / "sample-draft-batch.json"
    sample_draft_page_batch = tmp_dir / "sample-draft-page-batch.json"
    sample_draft_page_html = tmp_dir / "sample-draft-page.html"
    sample_draft_html = tmp_dir / "sample-draft.html"
    clean_project_dir = tmp_dir / "clean-project"
    pdf_scan_project.write_text(
        "\n".join(
            [
                "project:",
                "  title: PDF Scan Fixture",
                "  source_language: en",
                "  target_language: zh-CN",
                "",
                "inputs:",
                f"  screenplay_pdf: {pdf_scan_source}",
                "  subtitles: null",
                "",
                "outputs:",
                f"  marker_inventory: {pdf_scan_inventory}",
                "  html: null",
                "  pdf: null",
                "",
                "page_mapping:",
                "  displayed_page_offset: -1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    batch_project.write_text(
        "\n".join(
            [
                "project:",
                "  title: Batch HTML Fixture",
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
                f"  pdf: {batch_pdf}",
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
    (clean_project_dir / "work" / "batches").mkdir(parents=True)
    (clean_project_dir / "work" / "reports").mkdir(parents=True)
    (clean_project_dir / "dist").mkdir(parents=True)
    for relative in [
        "work/batches/draft.json",
        "work/batches/translated-p001-002.json",
        "work/batches/translated-p001-004.json",
        "work/reports/sample-validation.txt",
        "work/reports/temp.txt",
        "dist/screenplay-study.html",
        "dist/preview.html",
    ]:
        (clean_project_dir / relative).write_text("fixture\n", encoding="utf-8")

    merge_batch_dir.mkdir(parents=True)
    (merge_project_dir / "work").mkdir(exist_ok=True)
    (merge_project_dir / "dist").mkdir()
    merge_project.write_text(
        "\n".join(
            [
                "project:",
                "  title: Merge Fixture",
                "  source_language: en",
                "  target_language: zh-CN",
                "",
                "inputs:",
                "  screenplay_pdf: missing-source.pdf",
                "  subtitles: null",
                "",
                "outputs:",
                f"  marker_inventory: {merge_markers}",
                f"  html: {merge_html}",
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
                "has_subtitles": False,
                "front_matter": [
                    {
                        "id": "front-001",
                        "type": "note",
                        "pdf_page": 1,
                        "display_page": 0,
                        "source": "Written by CASEY",
                        "translation": "编剧：__凯西__",
                    }
                ],
                "entries": [
                    {
                        "id": "p001-e001",
                        "type": "scene_heading",
                        "pdf_page": 2,
                        "display_page": 1,
                        "source": "INT. ROOM - NIGHT",
                        "translation": "内景。__房间__ - 夜",
                        "markers": [
                            {"type": "scene_no", "text": "1", "position": "left"},
                            {"type": "scene_no", "text": "1", "position": "right"},
                        ],
                    },
                    {
                        "id": "p001-e002",
                        "type": "action",
                        "pdf_page": 2,
                        "display_page": 1,
                        "source": "A knock lands.",
                        "translation": "传来一记**敲门声**。",
                    },
                ],
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

    checks: list[SmokeCheck] = [
        {
            "name": "py_compile",
            "command": [
                python,
                "-m",
                "py_compile",
                str(SCRIPTS_DIR / "audit.py"),
                str(SCRIPTS_DIR / "assert_marker_counts.py"),
                str(SCRIPTS_DIR / "audit_draft.py"),
                str(SCRIPTS_DIR / "batch_markers.py"),
                str(SCRIPTS_DIR / "build_html.py"),
                str(SCRIPTS_DIR / "clean_project.py"),
                str(SCRIPTS_DIR / "draft_batch.py"),
                str(SCRIPTS_DIR / "extract_pdf.py"),
                str(SCRIPTS_DIR / "export_pdf.py"),
                str(SCRIPTS_DIR / "finalize_html.py"),
                str(SCRIPTS_DIR / "init_project.py"),
                str(SCRIPTS_DIR / "make_pdf_fixture.py"),
                str(SCRIPTS_DIR / "make_sample_batch.py"),
                str(SCRIPTS_DIR / "merge_batches.py"),
                str(SCRIPTS_DIR / "parse_subtitles.py"),
                str(SCRIPTS_DIR / "scan_markers.py"),
                str(SCRIPTS_DIR / "smoke.py"),
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(SCRIPTS_DIR / "validate_sample.py"),
            ],
        },
        {
            "name": "make_pdf_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "make_pdf_fixture.py"),
                str(pdf_scan_source),
            ],
        },
        {
            "name": "scan_pdf_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "scan_markers.py"),
                str(pdf_scan_project),
            ],
        },
        {
            "name": "assert_pdf_fixture_counts",
            "command": [
                python,
                str(SCRIPTS_DIR / "assert_marker_counts.py"),
                str(pdf_scan_inventory),
                str(
                    SKILL_DIR
                    / "assets"
                    / "fixtures"
                    / "pdf-scan"
                    / "expected-counts.json"
                ),
            ],
        },
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
                str(subtitle_fixture_dir / "expected-counts.json"),
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
                str(subtitle_fixture_dir / "expected-counts.json"),
            ],
        },
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
            "name": "init_sample_project",
            "command": [
                python,
                str(SCRIPTS_DIR / "init_project.py"),
                str(sample_project_dir),
                "--title",
                "Sample Validation Fixture",
                "--screenplay-pdf",
                str(sample_pdf),
            ],
        },
        {
            "name": "make_sample_pdf",
            "command": [
                python,
                str(SCRIPTS_DIR / "make_pdf_fixture.py"),
                str(sample_pdf),
            ],
        },
        {
            "name": "extract_sample_pdf_text",
            "command": [
                python,
                str(SCRIPTS_DIR / "extract_pdf.py"),
                str(sample_project),
            ],
        },
        {
            "name": "assert_sample_pdf_title_text",
            "command": [
                python,
                "-c",
                (
                    "import json; "
                    "from pathlib import Path; "
                    f"data=json.loads(Path({str(sample_project_dir / 'work' / 'source-lines.json')!r}).read_text(encoding='utf-8')); "
                    "texts=[row.get('text') for row in data.get('rows', [])]; "
                    "raise SystemExit(0 if 'SAMPLE TITLE' in texts else 'missing title-page text')"
                ),
            ],
        },
        {
            "name": "validate_sample_project",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_sample.py"),
                str(sample_project),
            ],
        },
        {
            "name": "make_sample_structure_batch",
            "command": [
                python,
                str(SCRIPTS_DIR / "make_sample_batch.py"),
                str(sample_project),
                "--output",
                str(sample_batch),
            ],
        },
        {
            "name": "make_sample_draft_batch",
            "command": [
                python,
                str(SCRIPTS_DIR / "draft_batch.py"),
                str(sample_project),
                "--output",
                str(sample_draft_batch),
            ],
        },
        {
            "name": "make_sample_draft_page_batch",
            "command": [
                python,
                str(SCRIPTS_DIR / "draft_batch.py"),
                str(sample_project),
                "--display-page-start",
                "0",
                "--display-page-end",
                "0",
                "--output",
                str(sample_draft_page_batch),
            ],
        },
        {
            "name": "assert_sample_draft_page_batch",
            "command": [
                python,
                "-c",
                (
                    "import json; "
                    "from pathlib import Path; "
                    f"data=json.loads(Path({str(sample_draft_page_batch)!r}).read_text(encoding='utf-8')); "
                    "pages={entry['display_page'] for entry in data['entries']}; "
                    "ok=data['source_pages']=={'start': 0, 'end': 0} and pages=={0}; "
                    "raise SystemExit(0 if ok else f'unexpected page batch: source_pages={data[\"source_pages\"]} pages={pages}')"
                ),
            ],
        },
        {
            "name": "build_sample_draft_page_html",
            "command": [
                python,
                str(SCRIPTS_DIR / "build_html.py"),
                str(sample_draft_page_batch),
                "--output",
                str(sample_draft_page_html),
            ],
        },
        {
            "name": "audit_sample_draft_page_html_range",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(sample_project),
                "--html",
                str(sample_draft_page_html),
                "--display-page-start",
                "0",
                "--display-page-end",
                "0",
            ],
        },
        {
            "name": "validate_sample_draft_batch",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(sample_draft_batch),
            ],
        },
        {
            "name": "audit_sample_draft_batch",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit_draft.py"),
                str(sample_draft_batch),
            ],
        },
        {
            "name": "build_sample_draft_html",
            "command": [
                python,
                str(SCRIPTS_DIR / "build_html.py"),
                str(sample_draft_batch),
                "--output",
                str(sample_draft_html),
            ],
        },
        {
            "name": "audit_sample_draft_html",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(sample_project),
                "--html",
                str(sample_draft_html),
            ],
        },
        {
            "name": "clean_sample_project_dry_run",
            "command": [
                python,
                str(SCRIPTS_DIR / "clean_project.py"),
                str(sample_project_dir),
            ],
        },
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
                    "forbidden=['translated-p001-004.json', 'sample-validation.txt', 'screenplay-study.html']; "
                    "missing=[item for item in required if item not in out]; "
                    "bad=[item for item in forbidden if item in out]; "
                    "raise SystemExit(f'clean candidates missing={missing} bad={bad}' if missing or bad else 0)"
                ),
            ],
        },
        {
            "name": "validate_sample_structure_batch",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(sample_batch),
            ],
        },
        {
            "name": "build_sample_structure_html",
            "command": [
                python,
                str(SCRIPTS_DIR / "build_html.py"),
                str(sample_batch),
                "--output",
                str(sample_html),
            ],
        },
        {
            "name": "audit_sample_structure_html",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(sample_project),
                "--html",
                str(sample_html),
            ],
        },
        {
            "name": "valid_batch_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(
                    SKILL_DIR
                    / "assets"
                    / "fixtures"
                    / "batches"
                    / "valid"
                    / "batch.json"
                ),
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
            "name": "validate_merged_batch_fixture_final",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(merged_batch),
                "--final",
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
                    "required=['原剧本第 1 页', '原剧本第 2 页', '本场删去']; "
                    "missing=[item for item in required if item not in text]; "
                    "raise SystemExit('merged html missing: '+repr(missing) if missing else 0)"
                ),
            ],
        },
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
                    "from pathlib import Path; "
                    f"text=Path({str(batch_html)!r}).read_text(encoding='utf-8'); "
                    "required=['<style>', '原剧本第 1 页', 'scene-marker-left', 'scene-marker-right', "
                    "'position: fixed;', 'scroll-padding-top', 'document.addEventListener(\"pointerdown\"', "
                    "'const closeSceneIndex = () =>', 'closeSceneIndex();', "
                    "'font-weight: 700;', 'border: 1px solid color-mix(in srgb, var(--accent) 42%, var(--rule));', "
                    "'<details class=\"scene-index\"', '<summary id=\"scene-index-title\">场次索引</summary>', "
                    "'本剧本出现的格式术语', '<strong>INSERT SHOT</strong>', '<strong>O.S.</strong>', '<strong>OMITTED</strong>', "
                    "'1 · 内景。<span class=\"proper-name\">房间</span> - 夜', "
                    "'<span class=\"proper-name\">凯西</span>', "
                    "'<strong class=\"emphasis\">敲门声</strong>', "
                    "'<em class=\"term\">画外音</em>']; "
                    "missing=[item for item in required if item not in text]; "
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
                    "'内景。<span class=\"proper-name\">房间</span> - 夜', "
                    "'外景。<span class=\"proper-name\">街道</span> - 日']; "
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
        {
            "name": "invalid_batch_subtitle_label",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(
                    SKILL_DIR
                    / "assets"
                    / "fixtures"
                    / "batches"
                    / "invalid-subtitle-label"
                    / "batch.json"
                ),
            ],
            "expect_failure": True,
        },
        {
            "name": "invalid_batch_final_placeholder",
            "command": [
                python,
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(
                    SKILL_DIR
                    / "assets"
                    / "fixtures"
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
                str(SKILL_DIR / "assets" / "fixtures" / "minimal" / "project.yaml"),
                "--allow-missing-inputs",
            ],
        },
        {
            "name": "broken_links_fixture_audit",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(
                    SKILL_DIR / "assets" / "fixtures" / "broken-links" / "project.yaml"
                ),
                "--allow-missing-inputs",
            ],
            "expect_failure": True,
        },
        {
            "name": "unstructured_fixture_audit",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(
                    SKILL_DIR / "assets" / "fixtures" / "unstructured" / "project.yaml"
                ),
                "--allow-missing-inputs",
            ],
            "expect_failure": True,
        },
    ]

    ok = True
    for check in checks:
        ok = (
            run_check(
                check["name"],
                check["command"],
                env=env,
                expect_failure=bool(check.get("expect_failure", False)),
            )
            and ok
        )

    ruff = shutil.which("ruff")
    if ruff:
        ok = run_check("ruff", [ruff, "check", str(SCRIPTS_DIR)], env=env) and ok
    else:
        print("WARN ruff not installed; skipped lint", flush=True)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
