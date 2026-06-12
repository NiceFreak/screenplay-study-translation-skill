#!/usr/bin/env python3
"""PDF fixture generation and marker scanning checks."""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import FIXTURES_DIR, SCRIPTS_DIR, SmokeCheck


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    pdf_scan_project = tmp_dir / "pdf-scan-project.yaml"
    pdf_scan_source = tmp_dir / "source.pdf"
    pdf_scan_inventory = tmp_dir / "source-markers.json"
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

    return [
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
            "name": "scan_markers_tj_array_text",
            "command": [
                python,
                "-c",
                (
                    "import sys; "
                    f"sys.path.insert(0, {str(SCRIPTS_DIR)!r}); "
                    "import scan_markers; "
                    "stream=b'BT 1 0 0 1 72 720 Tm /F1 12 Tf [(OM) -10 (ITTED)] TJ ET'; "
                    "ops=scan_markers.iter_text_ops(stream); "
                    "text=scan_markers.pdf_unescape(ops[0]['text']) if ops else ''; "
                    "raise SystemExit(0 if text == 'OMITTED' else f'TJ array text mismatch: {text!r}')"
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
                str(FIXTURES_DIR / "pdf-scan" / "expected-counts.json"),
            ],
        },
    ]
