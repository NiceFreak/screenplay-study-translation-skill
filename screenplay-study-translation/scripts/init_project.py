#!/usr/bin/env python3
"""Initialize a screenplay study translation project."""

from __future__ import annotations

import argparse
from pathlib import Path


def yaml_scalar(value: str | None) -> str:
    if value is None:
        return "null"
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def project_yaml(
    title: str,
    screenplay_pdf: str,
    subtitles: str | None,
    paper_size: str,
    page_offset: int,
) -> str:
    return "\n".join(
        [
            "project:",
            f"  title: {yaml_scalar(title)}",
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a screenplay study project."
    )
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--title", default="Untitled Screenplay")
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
    for relative in ("inputs", "work", "work/batches", "work/reports", "dist"):
        (project_dir / relative).mkdir(parents=True, exist_ok=True)

    project_file = project_dir / "project.yaml"
    if project_file.exists() and not args.force:
        print(f"FAIL project.exists {project_file}")
        return 1
    project_file.write_text(
        project_yaml(
            title=args.title,
            screenplay_pdf=args.screenplay_pdf,
            subtitles=args.subtitles,
            paper_size=args.paper_size,
            page_offset=args.displayed_page_offset,
        ),
        encoding="utf-8",
    )
    print(f"INFO project {project_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
