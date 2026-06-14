#!/usr/bin/env python3
"""Initialize a screenplay study translation project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
SIGNAL_LIFECYCLE_TEMPLATE = SKILL_DIR / "assets" / "signal_lifecycle.template.json"


def yaml_scalar(value: str | None) -> str:
    if value is None:
        return "null"
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def project_yaml(
    title: str,
    chinese_title: str,
    screenplay_pdf: str,
    subtitles: str | None,
    paper_size: str,
    page_offset: int,
) -> str:
    return "\n".join(
        [
            "project:",
            f"  title: {yaml_scalar(title)}",
            f"  chinese_title: {yaml_scalar(chinese_title)}",
            "  source_language: en",
            "  target_language: zh-CN",
            "",
            "inputs:",
            f"  screenplay_pdf: {yaml_scalar(screenplay_pdf)}",
            f"  subtitles: {yaml_scalar(subtitles)}",
            "",
            "outputs:",
            "  work_dir: work",
            "  dist_dir: dist",
            "  marker_inventory: work/source-markers.json",
            "  subtitles_json: work/subtitles.json",
            "  html: dist/screenplay-study.html",
            "  epub: dist/screenplay-study.epub",
            "  # PDF output is deprecated in v0.3; export_pdf.py is reference-only.",
            "  pdf: null",
            "",
            "page_mapping:",
            "  title_pages: 1",
            "  first_screenplay_pdf_page: 1",
            f"  displayed_page_offset: {page_offset}",
            "",
            "translation:",
            "  batch_size_pages: 10",
            "  subtitle_labels: auto",
            "",
            "audit:",
            "  require_subtitles: false",
            "  require_structured_markers: true",
            f"  paper_size: {yaml_scalar(paper_size)}",
            "  fail_on_missing_required_files: true",
            "",
        ]
    )


def reader_notes_markdown() -> str:
    return "\n".join(
        [
            "# 阅读说明",
            "",
            "本版是中文剧本学习版，对照成片字幕制作；读剧本的重要价值之一，是发现成片对剧本的删改。",
            "",
            "## 对白标识",
            "",
            "- 未标注的对白 = 与成片基本一致（正文绝大多数）。",
            "- 「成片差异」= 剧本这句与成片台词不一致（成片在措辞、详略或说法上有改动）。",
            "- 「成片未见」= 剧本这句在成片字幕里没有找到对应（可能被删或未拍，可对照成片确认）。",
            "",
            "场次索引中的「N改·M未见」是该场与成片不同/未见的对白句数；场景时间码是该场首句台词在成片中的近似位置（用于手动跳转，并非场景起点）。",
            "",
            "__下划线__用于人物、地点、片名等专名；**加粗**用于音效、银幕重点或剧本强调；*斜体*用于英文剧本术语、缩写或格式说明。",
            "",
            "对应原剧本显示页码；场号保留原剧本边栏编号。",
            "",
        ]
    )


def signal_lifecycle_json() -> str:
    if SIGNAL_LIFECYCLE_TEMPLATE.exists():
        return SIGNAL_LIFECYCLE_TEMPLATE.read_text(encoding="utf-8")
    return (
        json.dumps(
            {
                "version": 1,
                "scope": "Stage 2 signal observation only",
                "status_values": ["open", "reviewed", "ignored"],
                "records": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a screenplay study project."
    )
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--title", default="Untitled Screenplay")
    parser.add_argument(
        "--chinese-title",
        required=True,
        help="Required Chinese film title used for the reader-facing HTML cover.",
    )
    parser.add_argument("--screenplay-pdf", default="inputs/screenplay.pdf")
    parser.add_argument("--subtitles")
    parser.add_argument("--paper-size", default="A4")
    parser.add_argument("--displayed-page-offset", type=int, default=-1)
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing project.yaml."
    )
    args = parser.parse_args()

    project_dir = args.project_dir.expanduser().resolve()
    project_dir.mkdir(parents=True, exist_ok=True)
    for relative in (
        "inputs",
        "work",
        "work/batches",
        "work/logs",
        "work/reports",
        "work/signal",
        "references",
        "dist",
    ):
        (project_dir / relative).mkdir(parents=True, exist_ok=True)

    project_file = project_dir / "project.yaml"
    if project_file.exists() and not args.force:
        print(f"FAIL project.exists {project_file}")
        return 1
    project_file.write_text(
        project_yaml(
            title=args.title,
            chinese_title=args.chinese_title,
            screenplay_pdf=args.screenplay_pdf,
            subtitles=args.subtitles,
            paper_size=args.paper_size,
            page_offset=args.displayed_page_offset,
        ),
        encoding="utf-8",
    )
    signal_lifecycle_file = project_dir / "work" / "signal" / "signal_lifecycle.json"
    if not signal_lifecycle_file.exists() or args.force:
        signal_lifecycle_file.write_text(signal_lifecycle_json(), encoding="utf-8")
    reader_notes_file = project_dir / "references" / "reader_notes.md"
    if not reader_notes_file.exists() or args.force:
        reader_notes_file.write_text(reader_notes_markdown(), encoding="utf-8")
    print(f"INFO project {project_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
