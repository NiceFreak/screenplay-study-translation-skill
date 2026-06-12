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


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT
SCRIPTS_DIR = SKILL_DIR / "scripts"


class Check(TypedDict):
    name: str
    command: list[str]


class SmokeCheck(Check, total=False):
    expect_failure: bool
    skip: bool
    skip_reason: str


def json_fixture(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def minimal_text_pdf(page_texts: list[str | None]) -> bytes:
    page_ids: list[int] = []
    content_ids: list[int] = []
    next_id = 4
    for _text in page_texts:
        page_ids.append(next_id)
        content_ids.append(next_id + 1)
        next_id += 2

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids).encode("ascii")
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids ["
        + kids
        + b"] /Count "
        + str(len(page_ids)).encode("ascii")
        + b" >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    }
    for page_id, content_id, text in zip(page_ids, content_ids, page_texts):
        page_obj = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >>"
        )
        if text is not None:
            page_obj += b" /Contents " + f"{content_id} 0 R".encode("ascii")
        objects[page_id] = page_obj + b" >>"
        if text is None:
            continue
        stream = (
            f"BT 1 0 0 1 72 720 Tm /F1 12 Tf ({pdf_escape(text)}) Tj ET\n"
        ).encode("latin1")
        objects[content_id] = (
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"endstream"
        )

    output = bytearray(b"%PDF-1.4\n")
    offsets = {0: 0}
    for obj_id in sorted(objects):
        offsets[obj_id] = len(output)
        output.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        output.extend(objects[obj_id])
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    max_id = max(objects)
    output.extend(f"xref\n0 {max_id + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for obj_id in range(1, max_id + 1):
        output.extend(f"{offsets.get(obj_id, 0):010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


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
    html_fixture_dir = SKILL_DIR / "assets" / "fixtures" / "html"
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
    invalid_subtitle_timestamp_batch = tmp_dir / "invalid-subtitle-timestamp.json"
    invalid_merge_validation_log = (
        invalid_merge_project_dir / "work" / "logs" / "merge-validation.json"
    )
    initialized_project_dir = tmp_dir / "initialized-project"
    initialized_project = initialized_project_dir / "project.yaml"
    sample_project_dir = tmp_dir / "sample-project"
    sample_project = sample_project_dir / "project.yaml"
    sample_pdf = sample_project_dir / "inputs" / "sample.pdf"
    incomplete_project_dir = tmp_dir / "incomplete-extraction-project"
    incomplete_project = incomplete_project_dir / "project.yaml"
    incomplete_pdf = incomplete_project_dir / "inputs" / "two-page.pdf"
    incomplete_source_lines = incomplete_project_dir / "work" / "source-lines.json"
    missing_middle_project_dir = tmp_dir / "missing-middle-page-project"
    missing_middle_project = missing_middle_project_dir / "project.yaml"
    missing_middle_pdf = missing_middle_project_dir / "inputs" / "three-page.pdf"
    sample_batch = tmp_dir / "sample-structure-batch.json"
    sample_html = tmp_dir / "sample-structure.html"
    sample_draft_batch = tmp_dir / "sample-draft-batch.json"
    sample_draft_page_batch = tmp_dir / "sample-draft-page-batch.json"
    sample_context_package = tmp_dir / "sample-context-package.json"
    reflow_project_dir = tmp_dir / "reflow-project"
    reflow_batch_dir = reflow_project_dir / "work" / "batches"
    reflow_batch = reflow_batch_dir / "reflow-batch.json"
    reflow_source_lines = reflow_project_dir / "work" / "source-lines.json"
    reflow_subtitles = reflow_project_dir / "work" / "subtitles.json"
    reflow_project = reflow_project_dir / "project.yaml"
    reflow_html = reflow_project_dir / "dist" / "reflow.html"
    sample_draft_page_html = tmp_dir / "sample-draft-page.html"
    sample_draft_page_audit = tmp_dir / "sample-draft-page-audit.txt"
    sample_draft_html = tmp_dir / "sample-draft.html"
    subtitle_report = tmp_dir / "subtitle-report.txt"
    clean_project_dir = tmp_dir / "clean-project"
    pdf_scan_project.write_text(
        "\n".join(
            [
                "project:",
                "  title: PDF Scan Fixture",
                "  chinese_title: PDF扫描样例",
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
                "  epub: null",
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
    (clean_project_dir / "work" / "batches").mkdir(parents=True)
    (clean_project_dir / "work" / "reports").mkdir(parents=True)
    (clean_project_dir / "dist").mkdir(parents=True)
    for relative in [
        "work/batches/draft.json",
        "work/batches/translated-p001-002.json",
        "work/batches/translated-p001-004.json",
        "work/reports/cost-report.json",
        "work/reports/sample-validation.txt",
        "work/reports/temp.txt",
        "dist/screenplay-study.html",
        "dist/preview.html",
    ]:
        (clean_project_dir / relative).write_text("fixture\n", encoding="utf-8")

    incomplete_project_dir.mkdir(parents=True)
    (incomplete_project_dir / "inputs").mkdir()
    (incomplete_project_dir / "work").mkdir()
    (incomplete_project_dir / "dist").mkdir()
    incomplete_pdf.write_bytes(minimal_text_pdf(["PAGE ONE", "PAGE TWO"]))
    incomplete_project.write_text(
        "\n".join(
            [
                "project:",
                "  title: Incomplete Extraction Fixture",
                "  chinese_title: 抽取不完整样例",
                "  source_language: en",
                "  target_language: zh-CN",
                "",
                "inputs:",
                f"  screenplay_pdf: {incomplete_pdf}",
                "  subtitles: null",
                "",
                "outputs:",
                "  source_lines: work/source-lines.json",
                "  marker_inventory: work/source-markers.json",
                "  html: dist/screenplay-study.html",
                "  epub: dist/screenplay-study.epub",
                "  pdf: null",
                "",
                "page_mapping:",
                "  displayed_page_offset: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    incomplete_source_lines.write_text(
        json_fixture(
            {
                "version": 1,
                "source": {"screenplay_pdf": str(incomplete_pdf)},
                "rows": [
                    {
                        "pdf_page": 1,
                        "display_page": 1,
                        "text": "PAGE ONE",
                        "zone": "body",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

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

    missing_middle_project_dir.mkdir(parents=True)
    (missing_middle_project_dir / "inputs").mkdir()
    (missing_middle_project_dir / "work").mkdir()
    (missing_middle_project_dir / "dist").mkdir()
    missing_middle_pdf.write_bytes(minimal_text_pdf(["PAGE ONE", None, "PAGE THREE"]))
    missing_middle_project.write_text(
        "\n".join(
            [
                "project:",
                "  title: Missing Middle Page Fixture",
                "  chinese_title: 中间页缺失样例",
                "  source_language: en",
                "  target_language: zh-CN",
                "",
                "inputs:",
                f"  screenplay_pdf: {missing_middle_pdf}",
                "  subtitles: null",
                "",
                "outputs:",
                "  source_lines: work/source-lines.json",
                "  marker_inventory: work/source-markers.json",
                "  html: dist/screenplay-study.html",
                "  epub: dist/screenplay-study.epub",
                "  pdf: null",
                "",
                "page_mapping:",
                "  displayed_page_offset: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
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
                "下划线用于人物、地点、片名等专名；**加粗**用于音效、银幕重点或剧本强调；*斜体*用于英文剧本术语、缩写或格式说明。",
                "",
                "对应原剧本显示页码；场号保留原剧本边栏编号。",
                "",
                "已参考提供的中文字幕，方便对照对白。",
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
                ],
            }
        ),
        encoding="utf-8",
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
                str(SCRIPTS_DIR / "confirm_stage2.py"),
                str(SCRIPTS_DIR / "cost_report.py"),
                str(SCRIPTS_DIR / "draft_batch.py"),
                str(SCRIPTS_DIR / "extract_pdf.py"),
                str(SCRIPTS_DIR / "export_epub.py"),
                str(SCRIPTS_DIR / "finalize_html.py"),
                str(SCRIPTS_DIR / "init_project.py"),
                str(SCRIPTS_DIR / "make_pdf_fixture.py"),
                str(SCRIPTS_DIR / "make_sample_batch.py"),
                str(SCRIPTS_DIR / "merge_batches.py"),
                str(SCRIPTS_DIR / "package_batch_context.py"),
                str(SCRIPTS_DIR / "plan_batches.py"),
                str(SCRIPTS_DIR / "parse_subtitles.py"),
                str(SCRIPTS_DIR / "scan_markers.py"),
                str(SCRIPTS_DIR / "smoke.py"),
                str(SCRIPTS_DIR / "stage_gate.py"),
                str(SCRIPTS_DIR / "subtitle_report.py"),
                str(SCRIPTS_DIR / "build_style_profile.py"),
                str(SCRIPTS_DIR / "validate_batch.py"),
                str(SCRIPTS_DIR / "validate_sample.py"),
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
        {
            "name": "pdf_content_stream_exact_length",
            "command": [
                python,
                "-c",
                (
                    "import sys, zlib; "
                    f"sys.path.insert(0, {str(SCRIPTS_DIR)!r}); "
                    "import scan_markers; "
                    "cases=[b'payload-85-xxxxx', b'payload-475-'+b'x'*75]; "
                    "objects={}; "
                    "failed=[]; "
                    "\nfor index, payload in enumerate(cases, start=1):"
                    "\n    compressed=zlib.compress(payload)"
                    "\n    content_id=index"
                    "\n    objects[content_id]=(b'<< /Filter /FlateDecode /Length ' + "
                    "str(len(compressed)).encode('ascii') + "
                    "b' >>\\nstream\\n' + compressed + b'\\nendstream')"
                    "\n    if scan_markers.content_stream(objects, content_id) != payload:"
                    "\n        failed.append(index)"
                    "\nraise SystemExit('content stream exact length failed: ' + "
                    "repr(failed) if failed else 0)"
                ),
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
        {
            "name": "init_sample_project",
            "command": [
                python,
                str(SCRIPTS_DIR / "init_project.py"),
                str(sample_project_dir),
                "--title",
                "Sample Validation Fixture",
                "--chinese-title",
                "样本验证剧本",
                "--screenplay-pdf",
                str(sample_pdf),
                "--subtitles",
                str(subtitle_fixture_dir / "sample.ass"),
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
            "name": "validate_sample_requires_source_lines",
            "command": [
                python,
                "-c",
                (
                    "import subprocess, sys; "
                    "result=subprocess.run(["
                    f"{python!r}, "
                    f"{str(SCRIPTS_DIR / 'validate_sample.py')!r}, "
                    f"{str(sample_project)!r}"
                    "], text=True, capture_output=True, check=False); "
                    "text=result.stdout + result.stderr; "
                    "missing='UNCERTAIN extraction.source_lines_missing' not in text; "
                    "bad_exit=result.returncode == 0; "
                    "raise SystemExit('source-lines gate failed: '+text if missing or bad_exit else 0)"
                ),
            ],
        },
        {
            "name": "validate_sample_detects_incomplete_extraction",
            "command": [
                python,
                "-c",
                (
                    "import subprocess, sys; "
                    "result=subprocess.run(["
                    f"{python!r}, "
                    f"{str(SCRIPTS_DIR / 'validate_sample.py')!r}, "
                    f"{str(incomplete_project)!r}"
                    "], text=True, capture_output=True, check=False); "
                    "text=result.stdout + result.stderr; "
                    "missing='UNCERTAIN extraction.pdf_pages_missing pages=2' not in text; "
                    "bad_exit=result.returncode == 0; "
                    "raise SystemExit('incomplete extraction gate failed: '+text if missing or bad_exit else 0)"
                ),
            ],
        },
        {
            "name": "validate_sample_detects_middle_physical_page_gap",
            "command": [
                python,
                "-c",
                (
                    "import subprocess, sys; "
                    "extract=subprocess.run(["
                    f"{python!r}, "
                    f"{str(SCRIPTS_DIR / 'extract_pdf.py')!r}, "
                    f"{str(missing_middle_project)!r}"
                    "], text=True, capture_output=True, check=False); "
                    "text=extract.stdout + extract.stderr; "
                    "sys.exit('middle-page extraction setup failed: '+text) "
                    "if extract.returncode else None; "
                    "result=subprocess.run(["
                    f"{python!r}, "
                    f"{str(SCRIPTS_DIR / 'validate_sample.py')!r}, "
                    f"{str(missing_middle_project)!r}"
                    "], text=True, capture_output=True, check=False); "
                    "text=result.stdout + result.stderr; "
                    "missing='UNCERTAIN extraction.pdf_pages_missing pages=2' not in text; "
                    "bad_exit=result.returncode == 0; "
                    "raise SystemExit('middle physical page gate failed: '+text if missing or bad_exit else 0)"
                ),
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
            "name": "assert_sample_validation_stage_logs",
            "command": [
                python,
                "-c",
                (
                    "import json; "
                    "from pathlib import Path; "
                    f"report=Path({str(sample_project_dir / 'work' / 'reports' / 'sample-validation.txt')!r}); "
                    f"subtitle=Path({str(sample_project_dir / 'work' / 'reports' / 'subtitle-report.txt')!r}); "
                    f"log=Path({str(sample_project_dir / 'work' / 'logs' / 'stage-1-2-findings.json')!r}); "
                    "report_text=report.read_text(encoding='utf-8'); "
                    "subtitle_text=subtitle.read_text(encoding='utf-8'); "
                    "payload=json.loads(log.read_text(encoding='utf-8')); "
                    "required=['INFO subtitle_report ', 'INFO finding_log ', 'INFO stage_gate.stage_3 requires_stage2_signal_record=true']; "
                    "missing=[item for item in required if item not in report_text]; "
                    "missing += [] if 'INFO subtitle.events count=5' in subtitle_text else ['subtitle count']; "
                    "missing += [] if 'INFO extraction.completeness_verified true' in report_text else ['extraction completeness']; "
                    "missing += [] if 'INFO source_lines.display_pages count=1 pages=0' in report_text else ['source-lines pages']; "
                    "missing += [] if payload.get('stage')=='STAGE 1-2: EXTRACTION + SOURCE SIGNAL SCAN' else ['stage log']; "
                    "missing += [] if payload.get('stage_gate', {}).get('requires_stage2_signal_record_before_stage_3') else ['stage gate']; "
                    "missing += [] if 'INFO structural_signal.known_marker.' in report_text else ['structural signal']; "
                    "missing += [] if 'WARN warning_signal.unclassified.' in report_text else ['warning signal']; "
                    "missing += [] if 'INFO noise_signal.candidate.' in report_text else ['noise signal']; "
                    "raise SystemExit('sample validation logs missing: '+repr(missing) if missing else 0)"
                ),
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
            "name": "draft_batch_requires_stage2_confirmation",
            "command": [
                python,
                "-c",
                (
                    "import subprocess, sys\n"
                    f"process = subprocess.run([{python!r}, {str(SCRIPTS_DIR / 'draft_batch.py')!r}, {str(sample_project)!r}, '--output', {str(sample_draft_batch)!r}], capture_output=True, text=True)\n"
                    "output = process.stdout + process.stderr\n"
                    "if process.returncode == 0: sys.exit('expected draft_batch to fail without stage 2 confirmation')\n"
                    "if 'Stage 2 signal confirmation not found.' not in output: sys.exit('missing stage 2 confirmation message: ' + repr(output))\n"
                    "sys.exit(0)\n"
                ),
            ],
        },
        {
            "name": "confirm_sample_stage2",
            "command": [
                python,
                str(SCRIPTS_DIR / "confirm_stage2.py"),
                str(sample_project),
                "--decision",
                "Synthetic fixture warning signals were recorded without marker rule promotion.",
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
            "name": "package_sample_batch_context",
            "command": [
                python,
                str(SCRIPTS_DIR / "package_batch_context.py"),
                str(sample_project),
                "--display-page-start",
                "0",
                "--display-page-end",
                "0",
                "--output",
                str(sample_context_package),
            ],
        },
        {
            "name": "assert_sample_batch_context",
            "command": [
                python,
                "-c",
                (
                    "import json; "
                    "from pathlib import Path; "
                    f"data=json.loads(Path({str(sample_context_package)!r}).read_text(encoding='utf-8')); "
                    "ok=data.get('kind')=='translation_batch_context' "
                    "and data.get('source_entries') "
                    "and data.get('subtitle_candidates', {}).get('available') is True "
                    "and 'summary' in data.get('subtitle_candidates', {}) "
                    "and 'unique_subtitle_timestamps' in data.get('subtitle_candidates', {}) "
                    "and 'subtitle_timestamps' in data.get('subtitle_candidates', {}) "
                    "and 'source_rows_excerpt' not in data; "
                    "raise SystemExit(0 if ok else 'batch context package contract failed')"
                ),
            ],
        },
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
            "name": "plan_sample_batches",
            "command": [
                python,
                str(SCRIPTS_DIR / "plan_batches.py"),
                str(sample_project),
                "--output",
                str(tmp_dir / "batch-plan.json"),
            ],
        },
        {
            "name": "assert_batch_plan",
            "command": [
                python,
                "-c",
                (
                    "import json; "
                    "from pathlib import Path; "
                    f"data=json.loads(Path({str(tmp_dir / 'batch-plan.json')!r}).read_text(encoding='utf-8')); "
                    "ok=data.get('kind')=='batch_plan' "
                    "and data.get('policy', {}).get('effect', '').startswith('advisory only') "
                    "and isinstance(data.get('ranges'), list); "
                    "raise SystemExit(0 if ok else 'batch plan contract failed')"
                ),
            ],
        },
        {
            "name": "cost_report_sample_project",
            "command": [
                python,
                str(SCRIPTS_DIR / "cost_report.py"),
                str(sample_project),
                "--output",
                str(tmp_dir / "cost-report.json"),
            ],
        },
        {
            "name": "assert_cost_report",
            "command": [
                python,
                "-c",
                (
                    "import json; "
                    "from pathlib import Path; "
                    f"data=json.loads(Path({str(tmp_dir / 'cost-report.json')!r}).read_text(encoding='utf-8')); "
                    "ok=data.get('kind')=='cost_observation_report' "
                    "and data.get('estimate_basis', {}).get('scope', '').startswith('local artifact') "
                    "and data.get('cost_estimate', {}).get('status')=='estimated' "
                    "and data.get('cost_estimate', {}).get('model_name') "
                    "and data.get('cost_estimate', {}).get('estimated_total_usd') is not None "
                    "and data.get('cost_estimate', {}).get('not_billing_authority') is True "
                    "and data.get('summary', {}).get('groups'); "
                    "raise SystemExit(0 if ok else 'cost report contract failed')"
                ),
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
                "sh",
                "-c",
                " ".join(
                    [
                        python,
                        str(SCRIPTS_DIR / "audit.py"),
                        str(sample_project),
                        "--html",
                        str(sample_draft_page_html),
                        "--display-page-start",
                        "0",
                        "--display-page-end",
                        "0",
                        ">",
                        str(sample_draft_page_audit),
                        "&&",
                        "grep",
                        "-q",
                        "'INFO html.display_pages count=1 pages=0'",
                        str(sample_draft_page_audit),
                    ]
                ),
            ],
        },
        {
            "name": "audit_sample_draft_page_html_missing_range",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(sample_project),
                "--html",
                str(sample_draft_page_html),
                "--display-page-start",
                "1",
                "--display-page-end",
                "1",
            ],
            "expect_failure": True,
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
                    "forbidden=['translated-p001-004.json', 'cost-report.json', 'sample-validation.txt', 'screenplay-study.html']; "
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
                    "required=['原剧本第 1 页', '原剧本第 2 页', '本场删去', '字幕匹配 01:05']; "
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
                    "if '字幕匹配 01:05' not in text:\n"
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
                    "'<div id=\"r000\" class=\"entry scene-heading scene-heading-no-markers\"', "
                    "'data-source-entry-ids=\"r004,r005\"', '<span class=\"subtitle-label\">字幕匹配 00:02</span>', "
                    "'本剧本出现的专业术语', '行尾星号（*）']; "
                    "forbidden=['标题页信息：', '<p>Screenplay by</p>', '<p>Author Alpha</p>', '<span class=\"subtitle-label\">字幕未见 00:', "
                    "'id=\"r000\" class=\"entry scene-heading scene-heading-no-markers\" data-source-entry-ids=\"r000\" data-entry-type=\"scene_heading\" data-pdf-page=\"13\" data-display-page=\"12\"><span class=\"scene-marker-slot']; "
                    "missing=[item for item in required if item not in text]; "
                    "bad=[item for item in forbidden if item in text]; "
                    "missing += ['forbidden present: '+repr(bad)] if bad else []; "
                    "raise SystemExit('reflow html missing: '+repr(missing) if missing else 0)"
                ),
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
                    "'font-weight: 700;', 'border: 1px solid color-mix(in srgb, var(--accent) 42%, var(--rule));', "
                    "'.entry.note', '.reader-annotation', '.revision-asterisk', "
                    "'<details class=\"scene-index\"', '<summary id=\"scene-index-title\">场次索引</summary>', "
                    "'本中文剧本学习版仅供个人学习与研究使用，请勿商用或公开传播。', "
                    "'原剧本共 2 页', '未提供参考字幕，译文仅依据剧本正文生成。', "
                    "'<span class=\"proper-name\">下划线</span>用于人物、地点、片名等专名', "
                    "'<strong class=\"emphasis\">加粗</strong>用于音效、银幕重点或剧本强调', "
                    "'<em class=\"term\">斜体</em>用于英文剧本术语、缩写或格式说明', "
                    "'1 · 内景。<span class=\"proper-name\">测试地点</span> - 夜', "
                    "'<span class=\"scene-marker-slot scene-marker-left\"><span class=\"marker marker-scene_no scene-no\" data-marker-type=\"scene_no\" data-marker-position=\"left\">1</span></span>', "
                    "'<span class=\"scene-marker-slot scene-marker-right\"><span class=\"marker marker-scene_no scene-no\" data-marker-type=\"scene_no\" data-marker-position=\"right\">1</span></span>', "
                    "'<span class=\"proper-name\">角色甲</span>', "
                    "'<span class=\"reader-annotation\">提示音</span>', "
                    "'<span class=\"reader-annotation\">屏幕文字</span>', "
                    "'<p class=\"entry-line-with-revision-asterisk\"><span class=\"entry-line-text\">合成动作片段等待。</span><span class=\"revision-asterisk\" aria-label=\"源剧本修订星号\">*</span></p>']; "
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
        if check.get("skip"):
            print(f"SKIP {check['name']} {check['skip_reason']}", flush=True)
            continue
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
