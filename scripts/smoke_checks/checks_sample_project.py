#!/usr/bin/env python3
"""End-to-end sample project pipeline checks.

Covers init, extraction gates, Stage 2 confirmation, draft batches, batch
context packaging, batch planning, cost reports, previews, and audits.
"""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import (
    SCRIPTS_DIR,
    SUBTITLE_FIXTURE_DIR,
    SmokeCheck,
    json_fixture,
    minimal_text_pdf,
)


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    subtitle_fixture_dir = SUBTITLE_FIXTURE_DIR
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
    sample_draft_page_html = tmp_dir / "sample-draft-page.html"
    sample_draft_page_audit = tmp_dir / "sample-draft-page-audit.txt"
    sample_draft_html = tmp_dir / "sample-draft.html"

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

    return [
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
    ]
