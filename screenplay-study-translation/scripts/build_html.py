#!/usr/bin/env python3
"""Build study HTML from translation batch JSON."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

import validate_batch


ENTRY_CLASS = {
    "page_heading": "page-heading",
    "scene_heading": "scene-heading",
    "action": "action",
    "character": "character",
    "parenthetical": "parenthetical",
    "dialogue": "dialogue",
    "transition": "transition",
    "format_marker": "format-marker",
    "note": "note",
}
SIDE_SCENE_MARKERS = {"scene_no", "split_scene"}
TERM_NOTES = [
    (
        "INT.",
        r"\bINT\.",
        "内景，表示场景发生在室内空间。",
    ),
    (
        "EXT.",
        r"\bEXT\.",
        "外景，表示场景发生在室外空间。",
    ),
    (
        "CONT'D",
        r"\(CONT'D\)|\bCONT'D\b",
        "续，表示同一角色对白跨段或跨页延续。",
    ),
    (
        "MORE",
        r"\(MORE\)|\bMORE\b",
        "下页续，表示对白或段落延续到下一页。",
    ),
    (
        "OMITTED",
        r"\bOMITTED\b",
        "删场或本场删去，表示剧本编号中保留但正文省略的场次。",
    ),
    (
        "PROLOGUE",
        r"\bPROLOGUE\b",
        "序章，通常放在正片主要叙事展开之前。",
    ),
    (
        "CHYRON",
        r"\bCHYRON\b",
        "屏幕字幕或字幕卡，常用于交代地点、时间或身份信息。",
    ),
    (
        "V.O.",
        r"\bV\.O\.",
        "voice-over，旁白或画外叙述，声音通常不来自当前画面内的角色。",
    ),
    (
        "O.S.",
        r"\bO\.S\.",
        "off-screen，离画，角色在同一场景空间中但不在画面内。",
    ),
    (
        "O.C.",
        r"\bO\.C\.",
        "off-camera，离镜，与离画相近，强调角色不在摄影机画面中。",
    ),
    (
        "CUT TO",
        r"\bCUT TO\b",
        "切至，剪辑转场指示。",
    ),
    (
        "INSERT SHOT",
        r"\bINSERT SHOT\b",
        "插入镜头，用来强调物件、屏幕、文字或局部动作。",
    ),
    (
        "TITLE ON SCREEN",
        r"\bTITLE ON SCREEN\b|\bTITLE\b",
        "屏幕字幕或标题，用于说明画面上出现的文字信息。",
    ),
]

STYLE = """
:root {
  color-scheme: light;
  --page-bg: #fbfaf7;
  --paper: #fffdf8;
  --ink: #191713;
  --muted: #6c665c;
  --rule: #ded8cc;
  --accent: #2f5d62;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--page-bg);
  color: var(--ink);
  font-family: "Noto Serif SC", "Songti SC", "STSong", "SimSun", serif;
  line-height: 1.72;
}

html {
  scroll-padding-top: 5rem;
}

.screenplay-study {
  padding: 76px 12px 48px;
}

.reader-header,
.reader-note {
  width: min(100%, 820px);
  margin: 0 auto 18px;
  padding: 22px clamp(18px, 5vw, 58px);
  background: var(--paper);
  border: 1px solid var(--rule);
}

.reader-header {
  padding-top: 30px;
  padding-bottom: 28px;
}

.reader-kicker {
  margin: 0 0 0.3rem;
  color: var(--accent);
  font-size: 0.82rem;
  font-weight: 700;
}

.reader-title {
  margin: 0;
  font-size: clamp(1.8rem, 4vw, 2.6rem);
  line-height: 1.2;
}

.reader-meta {
  margin: 0.7rem 0 0;
  color: var(--muted);
  font-size: 0.9rem;
}

.reader-front-matter {
  margin: 1rem 0 0;
  color: var(--muted);
  font-size: 0.95rem;
}

.reader-front-matter p {
  margin: 0.25rem 0;
}

.reader-note h2 {
  margin: 0 0 0.7rem;
  font-size: 1rem;
}

.reader-note h3 {
  margin: 0.9rem 0 0.35rem;
  font-size: 0.94rem;
}

.reader-note p {
  margin: 0.35rem 0;
  color: var(--muted);
  font-size: 0.92rem;
}

.term-note-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  gap: 0.25rem 1rem;
  margin: 0.35rem 0 0;
  padding: 0;
  color: var(--muted);
  font-size: 0.9rem;
  list-style: none;
}

.term-note-list strong {
  color: var(--ink);
}

.scene-index {
  position: fixed;
  top: 0;
  right: 0;
  left: 0;
  z-index: 20;
  width: min(calc(100% - 24px), 820px);
  margin: 10px auto 0;
  background: color-mix(in srgb, var(--paper) 94%, transparent);
  border: 1px solid var(--rule);
  box-shadow: 0 8px 24px rgb(25 23 19 / 0.08);
  backdrop-filter: blur(12px);
  overflow: hidden;
}

.scene-index summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: 3rem;
  padding: 0.55rem clamp(18px, 5vw, 58px);
  cursor: pointer;
  font-weight: 700;
  list-style: none;
}

.scene-index summary::-webkit-details-marker {
  display: none;
}

.scene-index summary::after {
  content: "展开";
  color: var(--accent);
  font-size: 0.86rem;
  font-weight: 400;
}

.scene-index[open] summary::after {
  content: "收起";
}

.scene-index-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  gap: 0.25rem 1rem;
  max-height: min(68vh, 34rem);
  margin: 0;
  padding: 0.85rem clamp(18px, 5vw, 58px) 1rem;
  overflow: auto;
  border-top: 1px solid var(--rule);
  list-style: none;
}

.scene-index-list a {
  color: var(--accent);
  text-decoration: none;
}

.scene-index-list a:hover {
  text-decoration: underline;
}

.scene-index-page {
  color: var(--muted);
  font-size: 0.86em;
}

.script-page {
  width: min(100%, 820px);
  margin: 0 auto 28px;
  padding: 28px clamp(18px, 5vw, 58px) 36px;
  background: var(--paper);
  border: 1px solid var(--rule);
}

.source-page-label {
  margin: 0 0 22px;
  color: var(--muted);
  font-size: 0.82rem;
  text-align: right;
}

.entry {
  margin: 0 0 0.42rem;
}

.entry p {
  margin: 0;
}

.scene-heading {
  display: grid;
  grid-template-columns: minmax(2.4rem, 4rem) minmax(0, 1fr) minmax(2.4rem, 4rem);
  column-gap: 0.9rem;
  align-items: baseline;
  margin: 1.2rem 0 0.58rem;
  font-weight: 700;
}

.scene-heading p,
.transition p,
.format-marker p,
.character p {
  font-weight: 700;
}

.scene-marker-slot {
  min-width: 0;
  color: var(--muted);
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-size: 0.9rem;
  line-height: 1.72;
  text-align: center;
}

.scene-marker-left {
  grid-column: 1;
}

.scene-marker-right {
  grid-column: 3;
}

.entry-content {
  grid-column: 2;
  min-width: 0;
}

.character,
.dialogue,
.parenthetical {
  width: min(100%, 34rem);
  margin-right: auto;
  margin-left: auto;
}

.character {
  margin-top: 0.9rem;
  text-align: center;
}

.parenthetical {
  padding-left: 3rem;
}

.dialogue {
  padding-left: 1.2rem;
}

.transition {
  margin-top: 0.8rem;
  text-align: right;
}

.format-marker {
  margin-top: 0.7rem;
  text-align: center;
}

.subtitle-label {
  display: inline-block;
  margin-right: 0.6em;
  padding: 0.08rem 0.38rem;
  color: var(--accent);
  font-size: 0.78em;
  font-weight: 700;
  line-height: 1.45;
  border: 1px solid color-mix(in srgb, var(--accent) 42%, var(--rule));
  background: color-mix(in srgb, var(--accent) 8%, var(--paper));
}

.proper-name {
  text-decoration: underline;
  text-decoration-thickness: 0.08em;
  text-underline-offset: 0.18em;
}

.emphasis {
  font-weight: 700;
}

.term {
  font-style: italic;
}

.marker-structured-only {
  display: none;
}

@media (max-width: 560px) {
  html {
    scroll-padding-top: 4rem;
  }

  .screenplay-study {
    padding: 58px 0 32px;
  }

  .reader-header,
  .reader-note,
  .script-page {
    margin-bottom: 14px;
    padding: 18px 14px 28px;
    border-width: 0 0 1px;
  }

  .scene-heading {
    grid-template-columns: 2rem minmax(0, 1fr) 2rem;
    column-gap: 0.45rem;
  }

  .character,
  .dialogue,
  .parenthetical {
    width: 100%;
  }

  .scene-index summary {
    min-height: 2.8rem;
    padding: 0.48rem 14px;
  }

  .scene-index {
    width: 100%;
    margin-top: 0;
    border-width: 0 0 1px;
  }

  .scene-index-list {
    max-height: 72vh;
    padding: 0.75rem 14px 1rem;
  }
}
"""

SCRIPT = """
(() => {
  const sceneIndex = document.querySelector(".scene-index");
  if (!sceneIndex) return;

  const closeSceneIndex = () => {
    sceneIndex.open = false;
  };

  document.addEventListener("pointerdown", (event) => {
    if (!sceneIndex.open) return;
    if (sceneIndex.contains(event.target)) return;
    closeSceneIndex();
  }, true);

  sceneIndex.addEventListener("click", (event) => {
    const link = event.target.closest("a[href^='#']");
    if (link) closeSceneIndex();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeSceneIndex();
  });
})();
"""


def marker_class(marker_type: str) -> str:
    extra = " scene-no" if marker_type == "scene_no" else ""
    return f"marker marker-{html.escape(marker_type, quote=True)}{extra}"


def render_marker(marker: dict[str, Any], *, visible: bool = False) -> str:
    marker_type = str(marker.get("type", "unknown"))
    text = html.escape(str(marker.get("text", "")) if visible else "")
    position = marker.get("position")
    position_attr = (
        f' data-marker-position="{html.escape(str(position), quote=True)}"'
        if position
        else ""
    )
    hidden_class = "" if visible else " marker-structured-only"
    hidden_attr = "" if visible else ' aria-hidden="true"'
    return (
        f'<span class="{marker_class(marker_type)}{hidden_class}" '
        f'data-marker-type="{html.escape(marker_type, quote=True)}"{position_attr}{hidden_attr}>{text}</span>'
    )


def split_side_markers(
    markers: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    left: list[dict[str, Any]] = []
    right: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []
    for marker in markers:
        marker_type = marker.get("type")
        if marker_type not in SIDE_SCENE_MARKERS:
            other.append(marker)
            continue
        position = marker.get("position")
        if position == "left" or (position not in {"left", "right"} and not left):
            left.append(marker)
        elif position == "right" or (position not in {"left", "right"} and not right):
            right.append(marker)
        else:
            other.append(marker)
    return left, right, other


def render_entry_content(entry: dict[str, Any]) -> str:
    label = entry.get("subtitle_label")
    label_html = (
        f'<span class="subtitle-label">{html.escape(str(label))}</span>'
        if isinstance(label, str) and label
        else ""
    )
    translation = render_inline_markup(str(entry["translation"]))
    return f"<p>{label_html}{translation}</p>"


def render_inline_markup(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"__(.+?)__", r'<span class="proper-name">\1</span>', escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r'<strong class="emphasis">\1</strong>', escaped)
    escaped = re.sub(
        r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r'<em class="term">\1</em>', escaped
    )
    return escaped


def render_entry(entry: dict[str, Any]) -> str:
    entry_type = str(entry["type"])
    classes = f"entry {ENTRY_CLASS.get(entry_type, 'entry-unknown')}"
    attrs = [
        f'id="{html.escape(str(entry["id"]), quote=True)}"',
        f'class="{classes}"',
        f'data-entry-type="{html.escape(entry_type, quote=True)}"',
        f'data-pdf-page="{entry["pdf_page"]}"',
        f'data-display-page="{entry["display_page"]}"',
    ]
    markers = [
        marker for marker in entry.get("markers", []) or [] if isinstance(marker, dict)
    ]
    content = render_entry_content(entry)
    if entry_type == "scene_heading":
        left, right, other = split_side_markers(markers)
        left_html = "".join(render_marker(marker, visible=True) for marker in left)
        right_html = "".join(render_marker(marker, visible=True) for marker in right)
        other_html = "".join(render_marker(marker) for marker in other)
        return (
            f"<div {' '.join(attrs)}>"
            f'<span class="scene-marker-slot scene-marker-left">{left_html}</span>'
            f'<div class="entry-content">{other_html}{content}</div>'
            f'<span class="scene-marker-slot scene-marker-right">{right_html}</span>'
            "</div>"
        )
    marker_html = "".join(render_marker(marker) for marker in markers)
    return f"<div {' '.join(attrs)}>{marker_html}{content}</div>"


def batch_title(batch: dict[str, Any]) -> str:
    title = (
        batch.get("title")
        or batch.get("project_title")
        or batch.get("batch_id")
        or "screenplay-study"
    )
    return str(title)


def source_page_label(batch: dict[str, Any]) -> str:
    pages = batch.get("source_pages")
    if not isinstance(pages, dict):
        return "页码范围未知"
    start = pages.get("start")
    end = pages.get("end")
    if not isinstance(start, int) or not isinstance(end, int):
        return "页码范围未知"
    if start <= 0:
        entries = batch.get("entries")
        body_pages: list[int] = []
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                display_page = entry.get("display_page")
                if isinstance(display_page, int) and display_page > 0:
                    body_pages.append(display_page)
        if body_pages:
            start = min(body_pages)
            end = max(body_pages)
        else:
            return "页码范围未知"
    if start == end:
        return f"原剧本第 {start} 页"
    return f"原剧本第 {start}-{end} 页"


def scene_marker_text(entry: dict[str, Any]) -> str:
    markers = entry.get("markers")
    if not isinstance(markers, list):
        return ""
    for marker in markers:
        if isinstance(marker, dict) and marker.get("type") in SIDE_SCENE_MARKERS:
            text = marker.get("scene_no") or marker.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return ""


def scene_index_entries(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for entry in entries:
        if entry.get("type") != "scene_heading":
            continue
        scene_no = scene_marker_text(entry)
        if not scene_no:
            continue
        display_page = entry.get("display_page")
        page_text = str(display_page) if isinstance(display_page, int) else "?"
        items.append(
            {
                "id": str(entry.get("id", "")),
                "scene_no": scene_no,
                "title": str(entry.get("translation", "")),
                "page": page_text,
            }
        )
    return items


def scene_navigation_entries(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for entry in entries:
        if entry.get("type") != "scene_heading":
            continue
        display_page = entry.get("display_page")
        page_text = str(display_page) if isinstance(display_page, int) else "?"
        items.append(
            {
                "id": str(entry.get("id", "")),
                "title": str(entry.get("translation", "")),
                "page": page_text,
            }
        )
    return items


def entry_display_page(entry: dict[str, Any]) -> int | None:
    display_page = entry.get("display_page")
    return display_page if isinstance(display_page, int) else None


def front_matter_entries(batch: dict[str, Any]) -> list[dict[str, Any]]:
    front_matter = batch.get("front_matter")
    if isinstance(front_matter, list):
        return [entry for entry in front_matter if isinstance(entry, dict)]
    return []


def body_entries(batch: dict[str, Any]) -> list[dict[str, Any]]:
    entries = batch.get("entries")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def source_and_marker_text(batch: dict[str, Any]) -> str:
    parts: list[str] = []
    entries = batch.get("entries")
    if not isinstance(entries, list):
        return ""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        source = entry.get("source")
        if isinstance(source, str):
            parts.append(source)
        markers = entry.get("markers")
        if not isinstance(markers, list):
            continue
        for marker in markers:
            if not isinstance(marker, dict):
                continue
            marker_text = marker.get("text")
            if isinstance(marker_text, str):
                parts.append(marker_text)
    return "\n".join(parts)


def active_term_notes(batch: dict[str, Any]) -> list[tuple[str, str]]:
    source_text = source_and_marker_text(batch)
    notes: list[tuple[str, str]] = []
    for label, pattern, description in TERM_NOTES:
        if re.search(pattern, source_text, flags=re.I):
            notes.append((label, description))
    return notes


def render_front_matter(batch: dict[str, Any]) -> str:
    items: list[str] = []
    for entry in front_matter_entries(batch):
        translation = entry.get("translation")
        if isinstance(translation, str) and translation.strip():
            items.append(f"      <p>{render_inline_markup(translation.strip())}</p>")
    if not items:
        return ""
    return "\n".join(['    <div class="reader-front-matter">', *items, "    </div>"])


def render_cover(batch: dict[str, Any]) -> str:
    title = html.escape(batch_title(batch))
    page_label = html.escape(source_page_label(batch))
    front_matter = render_front_matter(batch)
    return f"""  <header class="reader-header">
    <p class="reader-kicker">中文剧本学习版</p>
    <h1 class="reader-title">{title}</h1>
    <p class="reader-meta">{page_label} · HTML 阅读版</p>
{front_matter}
  </header>"""


def render_reader_note(batch: dict[str, Any]) -> str:
    subtitle_text = (
        "参考字幕：已启用" if batch.get("has_subtitles") else "参考字幕：未提供"
    )
    term_notes = active_term_notes(batch)
    term_note_html = ""
    if term_notes:
        items = "\n".join(
            "      "
            f"<li><strong>{html.escape(label)}</strong>：{html.escape(description)}</li>"
            for label, description in term_notes
        )
        term_note_html = f"""
    <h3>本剧本出现的格式术语</h3>
    <ul class="term-note-list">
{items}
    </ul>"""
    return f"""  <section class="reader-note" aria-labelledby="reader-note-title">
    <h2 id="reader-note-title">阅读说明</h2>
    <p>下划线用于人物、地点、片名等专名；加粗用于音效、银幕重点或剧本强调；斜体用于英文剧本术语、缩写或格式说明。</p>
    <p>页码对应原剧本显示页码；场号保留原剧本边栏编号。</p>
    <p>{html.escape(subtitle_text)}。HTML 是默认阅读与审校格式；PDF 仅建议在打印、归档或阶段性交付时导出。</p>
{term_note_html}
  </section>"""


def render_scene_index(entries: list[dict[str, Any]]) -> str:
    items = scene_index_entries(entries)
    summary = "场次索引"
    if not items:
        items = scene_navigation_entries(entries)
        summary = "场景导航"
    if not items:
        return ""
    links = []
    for item in items:
        label = render_inline_markup(item["title"])
        if "scene_no" in item:
            label = f"{html.escape(item['scene_no'])} · {label}"
        links.append(
            "      "
            f'<li><a href="#{html.escape(item["id"], quote=True)}">{label}</a> '
            f'<span class="scene-index-page">第 {html.escape(item["page"])} 页</span></li>'
        )
    return f"""  <details class="scene-index" id="scene-index">
    <summary id="scene-index-title">{summary}</summary>
    <ul class="scene-index-list">
{chr(10).join(links)}
    </ul>
  </details>"""


def render_page_open(display_page: int) -> str:
    page_id = f"page-{display_page:03d}"
    return (
        f'<section class="script-page" id="{page_id}" data-display-page="{display_page}">\n'
        f'    <div class="source-page-label">原剧本第 {display_page} 页</div>'
    )


def render_pages(entries: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    current_page: int | None = None
    for entry in entries:
        display_page = int(entry["display_page"])
        if display_page != current_page:
            if current_page is not None:
                chunks.append("  </section>")
            chunks.append(render_page_open(display_page))
            current_page = display_page
        chunks.append(render_entry(entry))
    if current_page is not None:
        chunks.append("  </section>")
    return "\n".join(chunks)


def build_html(batch: dict[str, Any]) -> str:
    title = html.escape(batch_title(batch))
    cover = render_cover(batch)
    note = render_reader_note(batch)
    entries = body_entries(batch)
    scene_index = render_scene_index(entries)
    body = render_pages(entries)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{STYLE}</style>
</head>
<body>
  <main class="screenplay-study" data-batch-id="{title}">
{cover}
{note}
{scene_index}
{body}
  </main>
  <script>{SCRIPT}</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build minimal HTML from translation batch JSON."
    )
    parser.add_argument("batch", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    if not isinstance(batch, dict):
        print("FAIL batch.root root must be object", file=sys.stderr)
        return 1
    findings = validate_batch.validate_batch(batch)
    failures = [finding for finding in findings if finding.level == "FAIL"]
    if failures:
        for finding in failures:
            print(finding.render(), file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(batch), encoding="utf-8")
    print(f"INFO html {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
