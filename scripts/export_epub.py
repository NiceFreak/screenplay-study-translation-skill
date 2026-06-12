#!/usr/bin/env python3
"""Export screenplay study HTML to an EPUB reading edition."""

from __future__ import annotations

import argparse
import html
import re
import sys
import uuid
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

try:
    from ebooklib import epub
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by environment
    raise SystemExit(
        "FAIL dependency.ebooklib_missing install dependencies with: "
        "python3 -m pip install -r requirements.txt"
    ) from exc

import audit


EPUB_CSS = """
body {
  margin: 0;
  padding: 0;
  color: #1f1f1f;
  background: #ffffff;
  font-family: serif;
  line-height: 1.65;
}

h1, h2, h3 {
  font-family: sans-serif;
  line-height: 1.35;
}

h1 {
  margin: 0 0 1.4em;
  text-align: center;
}

h2 {
  margin: 0 0 1em;
  border-bottom: 1px solid #d6d6d6;
  padding-bottom: 0.45em;
}

p {
  margin: 0 0 0.7em;
}

a {
  color: #4a4035;
}

.epub-cover {
  text-align: center;
}

.epub-kicker,
.reader-kicker,
.reader-meta,
.reader-rights,
.source-page-label,
.scene-index-page {
  color: #666666;
  font-family: sans-serif;
  font-size: 0.92em;
}

.reader-rights,
.epub-rights {
  margin: 1.4em 0;
  border: 1px solid #d6d6d6;
  padding: 0.7em;
  font-weight: bold;
}

.reader-header,
.reader-note,
.script-page,
.epub-section {
  margin: 0 0 1.4em;
}

.epub-cover,
.reader-header,
.script-page {
  page-break-before: always;
  break-before: page;
}

.reader-note,
.epub-section {
  page-break-before: always;
  break-before: page;
}

.scene-index-list {
  margin: 0;
  padding-left: 1.2em;
}

nav ol,
.epub-nav ol {
  list-style: none;
  margin: 0;
  padding-left: 0;
}

nav li,
.epub-nav li {
  list-style: none;
}

nav ol ol,
.epub-nav ol ol {
  margin-left: 1.2em;
  padding-left: 0;
}

.scene-index-list li {
  margin: 0 0 0.45em;
}

.entry {
  margin: 0 0 0.45em;
}

.entry-line-with-revision-asterisk {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  column-gap: 0.8em;
  align-items: baseline;
}

.entry-line-text {
  min-width: 0;
}

.revision-asterisk {
  justify-self: end;
  margin-left: 0.8em;
  color: #666666;
  font-family: monospace;
  font-size: 1.18em;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}

.scene-heading {
  margin: 1.1em 0 0.75em;
  border-top: 1px solid #d6d6d6;
  border-bottom: 1px solid #d6d6d6;
  padding: 0.45em 0;
  font-family: sans-serif;
  font-weight: bold;
}

.scene-marker-slot {
  display: inline;
  color: #666666;
  font-family: monospace;
  margin-right: 0.5em;
}

.entry-content {
  display: block;
}

.character {
  margin-top: 0.9em;
  font-family: sans-serif;
  font-weight: bold;
  text-align: center;
}

.dialogue,
.parenthetical {
  margin-left: 1.5em;
  margin-right: 1.5em;
}

.transition,
.format-marker {
  margin-top: 0.8em;
  font-family: sans-serif;
  font-weight: bold;
  text-align: right;
}

.parallel-dialogue-grid {
  display: block;
}

.parallel-dialogue-column {
  margin-bottom: 0.8em;
}

.subtitle-label {
  display: inline-block;
  margin-right: 0.45em;
  border: 1px solid #9a866b;
  padding: 0.08em 0.45em;
  background-color: #f3eadf;
  color: #3c3026;
  font-family: sans-serif;
  font-size: 0.78em;
  font-weight: bold;
  line-height: 1.2;
  white-space: nowrap;
}

.proper-name {
  text-decoration: underline;
}

.emphasis {
  font-weight: bold;
}

.term {
  font-style: italic;
}

.reader-annotation {
  color: #4a4035;
  text-decoration: underline;
}

.marker-structured-only,
.screen-only,
script,
style {
  display: none;
}
""".strip()


@dataclass
class Section:
    id: str
    title: str
    html: str


@dataclass
class SceneLink:
    href: str
    title: str


@dataclass
class PagePart:
    section: Section
    open_tag: str
    inner: str


@dataclass
class AnchorLocation:
    link: SceneLink
    page_index: int
    offset: int


@dataclass
class ChapterItem:
    section: Section
    epub_item: epub.EpubHtml
    page_label: str | None = None
    scene_links: list[SceneLink] | None = None


class StudyHTMLParser(HTMLParser):
    """Small purpose-built parser for generated study HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.stack: list[dict[str, Any]] = []
        self.sections: list[Section] = []
        self.scene_links: list[SceneLink] = []
        self.title_parts: list[str] = []
        self._in_title = False
        self._current_link: dict[str, Any] | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        if tag == "title":
            self._in_title = True
            return
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        normalized_attrs = self._normalized_attrs(tag, attrs)
        if tag in {"header", "section", "details"} and self._is_top_section(
            tag, attr_map
        ):
            self.stack.append(
                {
                    "tag": tag,
                    "depth": 1,
                    "attrs": attr_map,
                    "parts": [self._open_tag(tag, normalized_attrs)],
                    "text": [],
                }
            )
            return

        if self.stack:
            self.stack[-1]["depth"] += 1
            self.stack[-1]["parts"].append(self._open_tag(tag, normalized_attrs))

        if tag == "a" and self._inside_scene_index() and attr_map.get("href"):
            self._current_link = {"href": attr_map.get("href", ""), "text": []}

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if self._skip_depth:
            return
        if self.stack:
            self.stack[-1]["parts"].append(self._self_closing_tag(tag, attrs))

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            return
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return

        if self._current_link is not None and tag == "a":
            title = collapse_ws("".join(self._current_link["text"]))
            href = str(self._current_link["href"]).lstrip("#")
            if href and title:
                self.scene_links.append(SceneLink(href=href, title=title))
            self._current_link = None

        if not self.stack:
            return
        current = self.stack[-1]
        current["parts"].append(f"</{tag}>")
        current["depth"] -= 1
        if current["depth"] == 0:
            section = self.stack.pop()
            body = "".join(section["parts"])
            self.sections.append(
                Section(
                    id=self._section_id(section["attrs"], len(self.sections) + 1),
                    title=self._section_title(section["attrs"], section["text"]),
                    html=body,
                )
            )

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
            return
        if self._skip_depth:
            return
        if self.stack:
            escaped = html.escape(data, quote=False)
            self.stack[-1]["parts"].append(escaped)
            self.stack[-1]["text"].append(data)
        if self._current_link is not None:
            self._current_link["text"].append(data)

    def handle_entityref(self, name: str) -> None:
        text = f"&{name};"
        if self._in_title:
            self.title_parts.append(html.unescape(text))
            return
        if self._skip_depth:
            return
        if self.stack:
            self.stack[-1]["parts"].append(text)
            self.stack[-1]["text"].append(html.unescape(text))
        if self._current_link is not None:
            self._current_link["text"].append(html.unescape(text))

    def handle_charref(self, name: str) -> None:
        text = f"&#{name};"
        if self._in_title:
            self.title_parts.append(html.unescape(text))
            return
        if self._skip_depth:
            return
        if self.stack:
            self.stack[-1]["parts"].append(text)
            self.stack[-1]["text"].append(html.unescape(text))
        if self._current_link is not None:
            self._current_link["text"].append(html.unescape(text))

    def _is_top_section(self, tag: str, attrs: dict[str, str]) -> bool:
        classes = class_set(attrs)
        if self.stack:
            return False
        return (
            tag == "header"
            or "reader-note" in classes
            or "script-page" in classes
            or "scene-index" in classes
        )

    def _inside_scene_index(self) -> bool:
        if not self.stack:
            return False
        classes = class_set(self.stack[-1]["attrs"])
        return "scene-index" in classes

    def _section_id(self, attrs: dict[str, str], index: int) -> str:
        existing = attrs.get("id")
        if existing:
            return sanitize_id(existing)
        classes = class_set(attrs)
        if "reader-header" in classes:
            return "cover"
        if "reader-note" in classes:
            return "reader-notes"
        if "scene-index" in classes:
            return "scene-index"
        page = attrs.get("data-display-page") or attrs.get("data-page")
        if page:
            return f"page-{sanitize_id(page)}"
        return f"section-{index:03d}"

    def _section_title(self, attrs: dict[str, str], text_parts: list[str]) -> str:
        classes = class_set(attrs)
        text = collapse_ws("".join(text_parts))
        if "reader-header" in classes:
            return "封面"
        if "reader-note" in classes:
            return "阅读说明"
        if "scene-index" in classes:
            return "场次索引" if "场次索引" in text else "场景导航"
        page = attrs.get("data-display-page") or attrs.get("data-page")
        if page is not None:
            return f"原剧本第 {page} 页"
        return text[:40] if text else "正文"

    def _open_tag(self, tag: str, attrs: list[tuple[str, str]]) -> str:
        rendered = "".join(
            f' {name}="{html.escape(value, quote=True)}"' for name, value in attrs
        )
        return f"<{tag}{rendered}>"

    def _self_closing_tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        normalized = self._normalized_attrs(tag, attrs)
        rendered = "".join(
            f' {name}="{html.escape(value, quote=True)}"' for name, value in normalized
        )
        return f"<{tag}{rendered} />"

    def _normalized_attrs(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> list[tuple[str, str]]:
        normalized: list[tuple[str, str]] = []
        for key, value in attrs:
            if key.lower().startswith("on"):
                continue
            if key == "style":
                continue
            if value is None:
                value = key
            normalized.append((key, value))
        return normalized


def collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def class_set(attrs: dict[str, str]) -> set[str]:
    return {item for item in attrs.get("class", "").split() if item}


def sanitize_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]+", "-", str(value).strip())
    return cleaned.strip("-") or "section"


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return cleaned or "chapter"


def load_project(project_file: Path) -> dict[str, Any]:
    if not project_file.exists():
        raise FileNotFoundError(f"project.yaml not found: {project_file}")
    return audit.load_simple_yaml(project_file)


def configured_html_path(project_file: Path, config: dict[str, Any]) -> Path:
    outputs = audit.section(config, "outputs")
    configured = audit.resolve_path(project_file, outputs.get("html"))
    return configured or project_file.parent / "dist" / "screenplay-study.html"


def default_output_path(project_file: Path) -> Path:
    return project_file.parent / "dist" / "screenplay-study.epub"


def configured_output_path(project_file: Path, config: dict[str, Any]) -> Path:
    outputs = audit.section(config, "outputs")
    configured = audit.resolve_path(project_file, outputs.get("epub"))
    return configured or default_output_path(project_file)


def project_metadata(config: dict[str, Any]) -> dict[str, str]:
    project = audit.section(config, "project")
    title = str(project.get("chinese_title") or project.get("title") or "剧本学习版")
    source_title = str(project.get("title") or title)
    language = str(project.get("target_language") or "zh-CN")
    return {
        "title": title,
        "source_title": source_title,
        "language": language,
    }


def parse_html(path: Path) -> StudyHTMLParser:
    parser = StudyHTMLParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def page_number(section: Section) -> int:
    match = re.search(r'data-(?:display-)?page=["\'](-?\d+)["\']', section.html)
    if match:
        return int(match.group(1))
    match = re.search(r"第\s*(-?\d+)\s*页", section.title)
    return int(match.group(1)) if match else 0


def has_scene_numbers(links: list[SceneLink]) -> bool:
    return any(re.match(r"\s*[\w.-]+\s*[·.]", link.title) for link in links)


def scene_page_map(links: list[SceneLink]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for link in links:
        match = re.search(r"第\s*(-?\d+)\s*页", link.title)
        if match:
            mapping[link.href] = int(match.group(1))
    return mapping


def page_part(section: Section) -> PagePart | None:
    match = re.match(r"(?s)\s*(<section\b[^>]*>)(.*)</section>\s*$", section.html)
    if match is None:
        return None
    return PagePart(section=section, open_tag=match.group(1), inner=match.group(2))


def anchor_locations(parts: list[PagePart], links: list[SceneLink]) -> list[AnchorLocation]:
    locations: list[AnchorLocation] = []
    seen: set[str] = set()
    for link in links:
        if link.href in seen:
            continue
        seen.add(link.href)
        for page_index, part in enumerate(parts):
            offset = anchor_offset(part.inner, link.href)
            if offset >= 0:
                locations.append(
                    AnchorLocation(link=link, page_index=page_index, offset=offset)
                )
                break
    locations.sort(key=lambda item: (item.page_index, item.offset))
    return locations


def anchor_offset(fragment: str, anchor_id: str) -> int:
    pattern = re.compile(
        rf"<[^>]+\bid=[\"']{re.escape(anchor_id)}[\"'][^>]*>", re.I
    )
    match = pattern.search(fragment)
    return match.start() if match else -1


def page_scene_links(body_sections: list[Section], links: list[SceneLink]) -> dict[str, list[SceneLink]]:
    parts = [part for section in body_sections if (part := page_part(section))]
    output: dict[str, list[SceneLink]] = {section.id: [] for section in body_sections}
    if parts:
        for location in anchor_locations(parts, links):
            output.setdefault(parts[location.page_index].section.id, []).append(
                location.link
            )
    mapped_pages = scene_page_map(links)
    if mapped_pages:
        by_page = {page_number(section): section.id for section in body_sections}
        for link in links:
            if any(link.href == existing.href for values in output.values() for existing in values):
                continue
            section_id = by_page.get(mapped_pages.get(link.href, -999999))
            if section_id:
                output.setdefault(section_id, []).append(link)
    return output


def section_document(title: str, body: str, css_href: str = "style.css") -> str:
    return f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="zh-CN">
<head>
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="{css_href}" />
</head>
<body>
{body}
</body>
</html>
"""


def wrap_section(section: Section) -> str:
    if re.search(r"<html\b", section.html, re.I):
        return section.html
    return section_document(section.title, section.html)


def cover_document(title: str, source_title: str) -> str:
    body = f"""  <section class="epub-cover">
    <p class="epub-kicker">中文剧本学习版</p>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(source_title)}</p>
    <p class="epub-rights">本中文剧本学习版仅供个人学习与研究使用，请勿商用或公开传播。</p>
  </section>"""
    return section_document(title, body)


def cover_section(
    parsed_sections: list[Section], title: str, source_title: str
) -> Section:
    for section in parsed_sections:
        if "reader-header" in section.html:
            return Section(id="cover", title="封面", html=section.html)
    return Section(
        id="cover",
        title="封面",
        html=cover_document(title, source_title),
    )


def item_with_content(
    section: Section,
    file_name: str,
    language: str,
    css: epub.EpubItem,
) -> epub.EpubHtml:
    item = epub.EpubHtml(title=section.title, file_name=file_name, lang=language)
    item.content = wrap_section(section)
    item.add_item(css)
    return item


def page_title(section: Section) -> str:
    match = re.search(r"原剧本第\s*(-?\d+)\s*页", section.html)
    if match:
        return f"原剧本第 {match.group(1)} 页"
    return section.title


def toc_for_items(items: list[ChapterItem]) -> tuple[Any, ...]:
    toc: list[Any] = []
    for item in items:
        scenes = item.scene_links or []
        if item.page_label and scenes:
            toc.append(
                (
                    epub.Section(item.page_label, item.epub_item.file_name),
                    [
                        epub.Link(
                            f"{item.epub_item.file_name}#{scene.href}",
                            scene.title,
                            f"toc-{slug(scene.href)}",
                        )
                        for scene in scenes
                    ],
                )
            )
        else:
            toc.append(item.epub_item)
    return tuple(toc)


def build_epub(
    project_file: Path, html_path: Path, output_path: Path, config: dict[str, Any]
) -> None:
    metadata = project_metadata(config)
    parsed = parse_html(html_path)
    title = metadata["title"]
    if parsed.title_parts and not title:
        title = collapse_ws("".join(parsed.title_parts))

    cover = cover_section(parsed.sections, title, metadata["source_title"])
    reader_notes = [
        section
        for section in parsed.sections
        if "reader-note" in section.html
    ]
    body_sections = [
        section for section in parsed.sections if "script-page" in section.html
    ]
    scenes_by_page = page_scene_links(body_sections, parsed.scene_links)

    book = epub.EpubBook()
    book.set_identifier(f"screenplay-study-{uuid.uuid4()}")
    book.set_title(title)
    book.set_language(metadata["language"])
    book.add_author("screenplay-study-translation")

    css = epub.EpubItem(
        uid="style",
        file_name="style.css",
        media_type="text/css",
        content=EPUB_CSS,
    )
    book.add_item(css)

    spine_items: list[epub.EpubHtml] = []
    toc_items: list[ChapterItem] = []

    cover_item = item_with_content(cover, "cover.xhtml", metadata["language"], css)
    book.add_item(cover_item)
    spine_items.append(cover_item)
    toc_items.append(ChapterItem(section=cover, epub_item=cover_item))

    for prefix, sections in [("reader-notes", reader_notes)]:
        for index, section in enumerate(sections, start=1):
            item = item_with_content(
                section,
                (
                    f"{prefix}-{index:02d}.xhtml"
                    if len(sections) > 1
                    else f"{prefix}.xhtml"
                ),
                metadata["language"],
                css,
            )
            book.add_item(item)
            spine_items.append(item)
            toc_items.append(ChapterItem(section=section, epub_item=item))

    for index, page_section in enumerate(body_sections, start=1):
        title_for_page = page_title(page_section)
        chapter = Section(
            id=page_section.id,
            title=title_for_page,
            html=page_section.html,
        )
        item = item_with_content(
            chapter,
            f"chapter-{index:03d}.xhtml",
            metadata["language"],
            css,
        )
        book.add_item(item)
        spine_items.append(item)
        toc_items.append(
            ChapterItem(
                section=chapter,
                epub_item=item,
                page_label=title_for_page,
                scene_links=scenes_by_page.get(page_section.id, []),
            )
        )

    book.toc = toc_for_items(toc_items)
    book.spine = spine_items
    book.add_item(epub.EpubNcx())
    nav_item = epub.EpubNav()
    nav_item.add_item(css)
    book.add_item(nav_item)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    validate_epub(output_path)


def validate_epub(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError(f"EPUB output missing or empty: {path}")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        required = {"mimetype", "META-INF/container.xml"}
        missing = sorted(required - names)
        if missing:
            raise ValueError(f"EPUB missing required files: {missing}")
    book = epub.read_epub(str(path))
    if not book.spine:
        raise ValueError("EPUB spine is empty")
    if not list(book.get_items()):
        raise ValueError("EPUB contains no items")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export the configured study HTML to an EPUB reading edition."
    )
    parser.add_argument("project", type=Path, help="Path to project.yaml.")
    parser.add_argument(
        "--html",
        type=Path,
        help="HTML input path. Defaults to outputs.html or dist/screenplay-study.html.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="EPUB output path. Defaults to outputs.epub or dist/screenplay-study.epub.",
    )
    args = parser.parse_args()

    project_file = args.project.expanduser().resolve()
    try:
        config = load_project(project_file)
        html_path = (
            args.html.expanduser().resolve()
            if args.html is not None
            else configured_html_path(project_file, config)
        )
        if not html_path.exists():
            raise FileNotFoundError(f"HTML input not found: {html_path}")
        output_path = (
            args.output.expanduser().resolve()
            if args.output is not None
            else configured_output_path(project_file, config)
        )
        build_epub(project_file, html_path, output_path, config)
    except Exception as exc:
        print(f"FAIL export_epub {exc}", file=sys.stderr)
        return 1
    print(f"INFO epub {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
