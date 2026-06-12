#!/usr/bin/env python3
"""Build study HTML from translation batch JSON."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, TypedDict

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
TRAILING_REVISION_ASTERISK_RE = re.compile(r"\s*\[\[\*\]\]\s*$")
PROTECTED_ENTRY_TYPES = {
    "page_heading",
    "scene_heading",
    "character",
    "parenthetical",
    "transition",
    "format_marker",
    "note",
}
LIST_LIKE_RE = re.compile(r"^\s*(?:[-+•]|\d+[.)])\s+")
SCREEN_TEXT_RE = re.compile(
    r"^\s*(?:SUPER|TITLE|TITLES|CHYRON|CAPTION|SUBTITLE|TEXT|ON SCREEN)\b[:.]?",
    re.I,
)
PROJECT_CONFIG_NAME = "project.yaml"
READER_NOTES_PATH = Path("references") / "reader_notes.md"
FRONT_MATTER_PATH = Path("references") / "front_matter.md"
SUBTITLE_LABELS_WITH_TIME = {"字幕匹配", "字幕差异"}


class DisplayUnit(TypedDict):
    type: str
    entries: list[str]
    text: str
    metadata: dict[str, Any]
    entry_objects: list[dict[str, Any]]

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

.reader-rights {
  margin: 1rem 0 0;
  padding: 0.55rem 0.75rem;
  color: var(--accent);
  font-size: 0.94rem;
  font-weight: 700;
  border: 1px solid color-mix(in srgb, var(--accent) 38%, var(--rule));
  background: color-mix(in srgb, var(--accent) 7%, var(--paper));
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

.entry-line-with-revision-asterisk {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  column-gap: 0.85rem;
  align-items: baseline;
}

.entry-line-text {
  min-width: 0;
}

.revision-asterisk {
  justify-self: end;
  color: var(--muted);
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-weight: 700;
}

.scene-heading {
  display: grid;
  grid-template-columns: minmax(2.4rem, 4rem) minmax(0, 1fr) minmax(2.4rem, 4rem);
  column-gap: 0.9rem;
  align-items: stretch;
  margin: 1.35rem 0 0.7rem;
  padding: 0.16rem 0;
  font-weight: 700;
  border-block: 1px solid color-mix(in srgb, var(--accent) 22%, var(--rule));
}

.scene-heading-no-markers {
  grid-template-columns: minmax(0, 1fr);
}

.scene-heading .entry-content {
  display: flex;
  align-items: center;
  min-height: 2.25rem;
  padding: 0.34rem 0.76rem;
  background: color-mix(in srgb, var(--accent) 6%, var(--paper));
  border-left: 4px solid color-mix(in srgb, var(--accent) 70%, var(--rule));
}

.scene-heading p {
  color: var(--accent);
  line-height: 1.45;
}

.scene-heading p,
.transition p,
.format-marker p,
.character p {
  font-weight: 700;
}

.scene-marker-slot {
  min-width: 0;
  align-self: center;
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

.scene-heading-no-markers .entry-content {
  grid-column: 1;
}

.entry.note {
  width: min(100%, 40rem);
  margin: 0.8rem auto 0.95rem;
}

.entry.note p {
  margin: 0;
  padding-left: 0.9rem;
  color: var(--muted);
  font-size: 0.93rem;
  line-height: 1.62;
  border-left: 3px solid color-mix(in srgb, var(--accent) 28%, var(--rule));
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

.parallel-dialogue {
  width: min(100%, 42rem);
  margin: 0.95rem auto 0.85rem;
}

.parallel-dialogue-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: clamp(0.8rem, 5vw, 2.6rem);
  align-items: start;
}

.parallel-dialogue-column {
  min-width: 0;
}

.parallel-dialogue-speaker {
  margin: 0 0 0.28rem;
  font-weight: 700;
  text-align: center;
}

.parallel-dialogue-lines p {
  margin: 0 0 0.08rem;
  line-height: 1.62;
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

.reader-annotation {
  color: var(--accent);
  text-decoration: underline dotted color-mix(in srgb, var(--accent) 64%, var(--rule));
  text-underline-offset: 0.18em;
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

  .scene-heading-no-markers {
    grid-template-columns: minmax(0, 1fr);
  }

  .scene-heading .entry-content {
    padding: 0.3rem 0.55rem;
  }

  .character,
  .dialogue,
  .parenthetical {
    width: 100%;
  }

  .entry.note {
    width: 100%;
  }

  .parallel-dialogue {
    width: 100%;
    font-size: 0.92rem;
  }

  .parallel-dialogue-grid {
    column-gap: 0.7rem;
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
  const root = document.querySelector(".screenplay-study");
  const storageKey = root?.dataset.progressKey;
  let saveTimer = 0;

  const storageAvailable = () => {
    if (!storageKey) return false;
    try {
      const probeKey = `${storageKey}:probe`;
      localStorage.setItem(probeKey, "1");
      localStorage.removeItem(probeKey);
      return true;
    } catch {
      return false;
    }
  };

  const canUseStorage = storageAvailable();

  const currentPage = () => {
    const pages = [...document.querySelectorAll(".script-page[data-display-page]")];
    let selected = pages[0] || null;
    for (const page of pages) {
      if (page.getBoundingClientRect().top <= window.innerHeight * 0.35) {
        selected = page;
      }
    }
    return selected?.dataset.displayPage || "";
  };

  const saveProgress = () => {
    if (!canUseStorage) return;
    const payload = {
      page: currentPage(),
      scrollY: Math.max(0, Math.round(window.scrollY)),
      updatedAt: new Date().toISOString(),
    };
    try {
      localStorage.setItem(storageKey, JSON.stringify(payload));
    } catch {
      // Local storage can fail in private or restricted browser contexts.
    }
  };

  const scheduleSave = () => {
    window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(saveProgress, 150);
  };

  if (canUseStorage && !window.location.hash) {
    try {
      const payload = JSON.parse(localStorage.getItem(storageKey) || "null");
      if (payload && Number.isFinite(payload.scrollY) && payload.scrollY > 0) {
        window.requestAnimationFrame(() => {
          window.scrollTo({ top: payload.scrollY, behavior: "auto" });
        });
      }
    } catch {
      // Ignore invalid saved progress.
    }
  }

  window.addEventListener("scroll", scheduleSave, { passive: true });
  window.addEventListener("beforeunload", saveProgress);
  window.addEventListener("pagehide", saveProgress);

  if (sceneIndex) {
    const closeSceneIndex = () => {
      sceneIndex.open = false;
      saveProgress();
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
  }
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
    label = entry_subtitle_display_label(entry)
    label_html = (
        f'<span class="subtitle-label">{html.escape(label)}</span>' if label else ""
    )
    return render_text_paragraph(str(entry["translation"]), prefix_html=label_html)


def split_trailing_revision_asterisk(text: str) -> tuple[str, bool]:
    if TRAILING_REVISION_ASTERISK_RE.search(text):
        return TRAILING_REVISION_ASTERISK_RE.sub("", text).rstrip(), True
    return text, False


def render_revision_asterisk() -> str:
    return '<span class="revision-asterisk" aria-label="源剧本修订星号">*</span>'


def render_text_paragraph(text: str, prefix_html: str = "") -> str:
    body_text, has_revision_asterisk = split_trailing_revision_asterisk(text)
    body_html = f"{prefix_html}{render_inline_markup(body_text)}"
    if has_revision_asterisk:
        return (
            '<p class="entry-line-with-revision-asterisk">'
            f'<span class="entry-line-text">{body_html}</span>'
            f"{render_revision_asterisk()}</p>"
        )
    return f"<p>{body_html}</p>"


def render_inline_markup(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\[\[(.+?)\]\]", r'<span class="reader-annotation">\1</span>', escaped)
    escaped = re.sub(r"__(.+?)__", r'<span class="proper-name">\1</span>', escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r'<strong class="emphasis">\1</strong>', escaped)
    escaped = re.sub(
        r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r'<em class="term">\1</em>', escaped
    )
    return escaped


def layout_source_ids(entry: dict[str, Any], layout: dict[str, Any]) -> str:
    source_ids = layout.get("source_entry_ids")
    if not isinstance(source_ids, list):
        source_ids = [entry.get("id")]
    return ",".join(
        str(source_id)
        for source_id in source_ids
        if isinstance(source_id, (str, int)) and str(source_id).strip()
    )


def render_parallel_dialogue(
    entry: dict[str, Any], attrs: list[str], layout: dict[str, Any]
) -> str | None:
    columns = layout.get("columns")
    if not isinstance(columns, list) or not columns:
        return None

    rendered_columns: list[str] = []
    for column in columns:
        if not isinstance(column, dict):
            continue
        speaker = str(column.get("speaker") or "").strip()
        lines = column.get("lines")
        if not isinstance(lines, list) or not lines:
            continue
        line_html = "\n".join(
            f"      {render_text_paragraph(str(line))}"
            for line in lines
            if isinstance(line, (str, int, float)) and str(line).strip()
        )
        if not line_html:
            continue
        speaker_html = (
            f'    <p class="parallel-dialogue-speaker">{render_inline_markup(speaker)}</p>\n'
            if speaker
            else ""
        )
        rendered_columns.append(
            "  <div class=\"parallel-dialogue-column\">\n"
            f"{speaker_html}"
            "    <div class=\"parallel-dialogue-lines\">\n"
            f"{line_html}\n"
            "    </div>\n"
            "  </div>"
        )

    if not rendered_columns:
        return None

    source_ids = layout_source_ids(entry, layout)
    if source_ids:
        attrs.append(
            f'data-layout-source-ids="{html.escape(source_ids, quote=True)}"'
        )
    attrs.append('data-layout-type="parallel_dialogue"')
    return (
        f"<div {' '.join(attrs)}>\n"
        '  <div class="parallel-dialogue-grid">\n'
        f"{chr(10).join(rendered_columns)}\n"
        "  </div>\n"
        "</div>"
    )


def render_entry(entry: dict[str, Any]) -> str:
    entry_type = str(entry["type"])
    classes = f"entry {ENTRY_CLASS.get(entry_type, 'entry-unknown')}"
    attrs = [
        f'id="{html.escape(str(entry["id"]), quote=True)}"',
        f'class="{classes}"',
        f'data-source-entry-ids="{html.escape(str(entry["id"]), quote=True)}"',
        f'data-entry-type="{html.escape(entry_type, quote=True)}"',
        f'data-pdf-page="{entry["pdf_page"]}"',
        f'data-display-page="{entry["display_page"]}"',
    ]
    markers = [
        marker for marker in entry.get("markers", []) or [] if isinstance(marker, dict)
    ]
    layout = entry.get("layout")
    if isinstance(layout, dict) and layout.get("type") == "parallel_dialogue":
        attrs[1] = f'class="{classes} parallel-dialogue"'
        parallel_html = render_parallel_dialogue(entry, attrs, layout)
        if parallel_html is not None:
            return parallel_html

    content = render_entry_content(entry)
    if entry_type == "scene_heading":
        left, right, other = split_side_markers(markers)
        left_html = "".join(render_marker(marker, visible=True) for marker in left)
        right_html = "".join(render_marker(marker, visible=True) for marker in right)
        other_html = "".join(render_marker(marker) for marker in other)
        if not left and not right:
            attrs[1] = f'class="{classes} scene-heading-no-markers"'
            return (
                f"<div {' '.join(attrs)}>"
                f'<div class="entry-content">{other_html}{content}</div>'
                "</div>"
            )
        return (
            f"<div {' '.join(attrs)}>"
            f'<span class="scene-marker-slot scene-marker-left">{left_html}</span>'
            f'<div class="entry-content">{other_html}{content}</div>'
            f'<span class="scene-marker-slot scene-marker-right">{right_html}</span>'
            "</div>"
        )
    marker_html = "".join(render_marker(marker) for marker in markers)
    return f"<div {' '.join(attrs)}>{marker_html}{content}</div>"


def entry_id(entry: dict[str, Any]) -> str:
    return str(entry.get("id") or "")


def entry_translation(entry: dict[str, Any]) -> str:
    return str(entry.get("translation") or "").strip()


def has_entry_markers(entry: dict[str, Any]) -> bool:
    markers = entry.get("markers")
    return isinstance(markers, list) and any(
        isinstance(marker, dict) for marker in markers
    )


def has_revision_marker(entry: dict[str, Any]) -> bool:
    return validate_batch.has_rendered_revision_asterisk(entry.get("translation"))


def has_explicit_reflow_off(entry: dict[str, Any]) -> bool:
    return entry.get("preserve_line_breaks") is True or entry.get("reflow") is False


def is_list_like(entry: dict[str, Any]) -> bool:
    text = entry_translation(entry)
    return LIST_LIKE_RE.search(text) is not None


def is_screen_text_like(entry: dict[str, Any]) -> bool:
    source = str(entry.get("source") or "")
    translation = entry_translation(entry)
    return (
        SCREEN_TEXT_RE.search(source) is not None
        or SCREEN_TEXT_RE.search(translation) is not None
    )


def is_lyric_or_poetry_like(entry: dict[str, Any]) -> bool:
    text = entry_translation(entry)
    return "♪" in text or "\n" in text


def is_protected_entry(entry: dict[str, Any]) -> bool:
    entry_type = str(entry.get("type") or "")
    layout = entry.get("layout")
    return (
        entry_type in PROTECTED_ENTRY_TYPES
        or has_entry_markers(entry)
        or has_revision_marker(entry)
        or has_explicit_reflow_off(entry)
        or is_list_like(entry)
        or is_screen_text_like(entry)
        or is_lyric_or_poetry_like(entry)
        or isinstance(layout, dict)
    )


def display_unit_type(entry: dict[str, Any]) -> str:
    entry_type = str(entry.get("type") or "")
    if entry_type == "dialogue":
        return "dialogue"
    if entry_type == "action":
        return "prose"
    return "protected"


def source_entry_ids(entries: list[dict[str, Any]]) -> list[str]:
    return [item for entry in entries if (item := entry_id(entry))]


def entry_subtitle_label(entry: dict[str, Any]) -> str:
    label = entry.get("subtitle_label")
    return label if isinstance(label, str) else ""


def format_subtitle_time(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return ""
    total_seconds = int(value)
    if total_seconds < 0:
        return ""
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def entry_subtitle_display_label(entry: dict[str, Any]) -> str:
    label = entry_subtitle_label(entry)
    if label not in SUBTITLE_LABELS_WITH_TIME:
        return label
    time_label = format_subtitle_time(entry.get("subtitle_start"))
    return f"{label} {time_label}" if time_label else label


def merged_display_text(entries: list[dict[str, Any]]) -> str:
    return "".join(entry_translation(entry) for entry in entries).strip()


def make_display_unit(unit_type: str, entries: list[dict[str, Any]]) -> DisplayUnit:
    ids = source_entry_ids(entries)
    return {
        "type": unit_type,
        "entries": ids,
        "text": merged_display_text(entries),
        "metadata": {"source_entry_ids": ids},
        "entry_objects": entries,
    }


def can_merge_entries(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    if int(previous.get("display_page", -1)) != int(current.get("display_page", -2)):
        return False
    if is_protected_entry(previous) or is_protected_entry(current):
        return False
    previous_type = str(previous.get("type") or "")
    current_type = str(current.get("type") or "")
    if previous_type == current_type == "action":
        return True
    return (
        previous_type == current_type == "dialogue"
        and entry_subtitle_display_label(previous) == entry_subtitle_display_label(current)
    )


def reflow_grouping_pass(entries: list[dict[str, Any]]) -> list[DisplayUnit]:
    display_units: list[DisplayUnit] = []
    pending: list[dict[str, Any]] = []

    def flush_pending() -> None:
        nonlocal pending
        if pending:
            display_units.append(make_display_unit(display_unit_type(pending[0]), pending))
            pending = []

    for entry in entries:
        if entry.get("layout_hidden") is True:
            continue
        if is_protected_entry(entry):
            flush_pending()
            display_units.append(make_display_unit("protected", [entry]))
            continue
        if pending and can_merge_entries(pending[-1], entry):
            pending.append(entry)
            continue
        flush_pending()
        pending = [entry]

    flush_pending()
    return display_units


def unit_primary_entry(unit: DisplayUnit) -> dict[str, Any]:
    return unit["entry_objects"][0]


def unit_attrs(unit: DisplayUnit, classes: str) -> list[str]:
    entry = unit_primary_entry(unit)
    source_ids = ",".join(unit["entries"])
    return [
        f'id="{html.escape(str(entry["id"]), quote=True)}"',
        f'class="{classes}"',
        f'data-display-unit-type="{html.escape(unit["type"], quote=True)}"',
        f'data-source-entry-ids="{html.escape(source_ids, quote=True)}"',
        f'data-entry-type="{html.escape(str(entry["type"]), quote=True)}"',
        f'data-pdf-page="{entry["pdf_page"]}"',
        f'data-display-page="{entry["display_page"]}"',
    ]


def render_display_unit(unit: DisplayUnit) -> str:
    if unit["type"] == "protected":
        return render_entry(unit_primary_entry(unit))

    entry = unit_primary_entry(unit)
    entry_type = str(entry["type"])
    classes = f"entry {ENTRY_CLASS.get(entry_type, 'entry-unknown')} display-unit"
    attrs = unit_attrs(unit, classes)
    label = entry_subtitle_display_label(entry)
    label_html = (
        f'<span class="subtitle-label">{html.escape(label)}</span>' if label else ""
    )
    content = render_text_paragraph(unit["text"], prefix_html=label_html)
    return f"<div {' '.join(attrs)}>{content}</div>"


def project_file_for_batch(batch_path: Path | None, project_path: Path | None = None) -> Path | None:
    if project_path is not None:
        return project_path.expanduser().resolve()
    if batch_path is None:
        return None
    for parent in batch_path.resolve().parents:
        candidate = parent / PROJECT_CONFIG_NAME
        if candidate.exists():
            return candidate
    return None


def parse_simple_yaml_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def load_project_config_for_batch(
    batch_path: Path | None, project_path: Path | None = None
) -> dict[str, Any]:
    project_file = project_file_for_batch(batch_path, project_path)
    if project_file is None:
        return {}
    data: dict[str, Any] = {}
    current: str | None = None
    for raw_line in project_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not raw_line.startswith(" "):
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = parse_simple_yaml_scalar(value)
                current = None
            else:
                data[key] = {}
                current = key
            continue
        if current is None or not isinstance(data.get(current), dict):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[current][key.strip()] = parse_simple_yaml_scalar(value)
    return data


def load_reader_notes_for_batch(
    batch_path: Path | None, project_path: Path | None = None
) -> str | None:
    project_file = project_file_for_batch(batch_path, project_path)
    if project_file is None:
        return None
    reader_notes_path = project_file.parent / READER_NOTES_PATH
    if not reader_notes_path.exists():
        return None
    return reader_notes_path.read_text(encoding="utf-8")


def load_front_matter_for_batch(
    batch_path: Path | None, project_path: Path | None = None
) -> str | None:
    project_file = project_file_for_batch(batch_path, project_path)
    if project_file is None:
        return None
    front_matter_path = project_file.parent / FRONT_MATTER_PATH
    if not front_matter_path.exists():
        return None
    return front_matter_path.read_text(encoding="utf-8")


def config_section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name)
    return value if isinstance(value, dict) else {}


def batch_title(batch: dict[str, Any], config: dict[str, Any] | None = None) -> str:
    project_config = config_section(config or {}, "project")
    title = (
        batch.get("chinese_title")
        or project_config.get("chinese_title")
        or batch.get("title")
        or batch.get("project_title")
        or project_config.get("title")
        or batch.get("batch_id")
        or "screenplay-study"
    )
    return str(title)


def progress_key(batch: dict[str, Any], config: dict[str, Any] | None = None) -> str:
    batch_id = batch.get("batch_id")
    project_config = config_section(config or {}, "project")
    title = (
        batch.get("project_title")
        or project_config.get("title")
        or project_config.get("chinese_title")
        or batch_title(batch, config)
    )
    key_parts = [
        "screenplay-study-progress",
        str(batch_id) if isinstance(batch_id, str) and batch_id.strip() else title,
        title,
    ]
    return ":".join(key_parts)


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


def source_lines_path_for_batch(batch_path: Path | None) -> Path | None:
    if batch_path is None:
        return None
    for parent in batch_path.resolve().parents:
        for candidate in (parent / "source-lines.json", parent / "work" / "source-lines.json"):
            if candidate.exists():
                return candidate
    return None


def load_source_rows_for_batch(batch_path: Path | None) -> list[dict[str, Any]]:
    source_lines_path = source_lines_path_for_batch(batch_path)
    if source_lines_path is None:
        return []
    payload = json.loads(source_lines_path.read_text(encoding="utf-8"))
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def source_page_total(batch: dict[str, Any], source_rows: list[dict[str, Any]]) -> int | None:
    display_pages = [
        row.get("display_page")
        for row in source_rows
        if isinstance(row.get("display_page"), int) and row.get("display_page") > 0
    ]
    if display_pages:
        return max(display_pages)

    source_pages = batch.get("source_pages")
    if isinstance(source_pages, dict) and isinstance(source_pages.get("end"), int):
        end = source_pages["end"]
        if end > 0:
            return end

    entry_pages = [
        entry.get("display_page")
        for entry in body_entries(batch)
        if isinstance(entry.get("display_page"), int) and entry.get("display_page") > 0
    ]
    return max(entry_pages) if entry_pages else None


def title_page_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pdf_pages = [
        row.get("pdf_page")
        for row in source_rows
        if isinstance(row.get("pdf_page"), int)
    ]
    if not pdf_pages:
        return []
    first_pdf_page = min(pdf_pages)
    rows = [
        row
        for row in source_rows
        if row.get("pdf_page") == first_pdf_page
        and row.get("zone") != "page_number"
        and isinstance(row.get("text"), str)
        and row.get("text", "").strip()
    ]
    return sorted(
        rows,
        key=lambda row: (
            -float(row.get("y", 0) if isinstance(row.get("y"), (int, float)) else 0),
            float(row.get("x", 0) if isinstance(row.get("x"), (int, float)) else 0),
        ),
    )


def title_page_title_item(value: str, config: dict[str, Any] | None = None) -> str:
    project_config = config_section(config or {}, "project")
    chinese_title = project_config.get("chinese_title")
    if isinstance(chinese_title, str) and chinese_title.strip():
        return f"剧本名：__{chinese_title.strip()}__（原文：{value}）"
    return f"剧本名：__{value}__"


def title_page_translation_items(
    source_rows: list[dict[str, Any]], config: dict[str, Any] | None = None
) -> list[str]:
    rows = title_page_rows(source_rows)
    texts = [str(row.get("text", "")).strip() for row in rows]
    items: list[str] = []
    if texts:
        items.append(title_page_title_item(texts[0], config))
    return items


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


def render_reader_note_markdown(markdown: str, list_class: str = "term-note-list") -> str:
    chunks: list[str] = []
    paragraph_lines: list[str] = []
    list_items: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        text = " ".join(paragraph_lines)
        chunks.append(f"    <p>{render_inline_markup(text)}</p>")
        paragraph_lines.clear()

    def flush_list() -> None:
        if not list_items:
            return
        class_attr = html.escape(list_class, quote=True)
        chunks.append(f'    <ul class="{class_attr}">')
        chunks.extend(list_items)
        chunks.append("    </ul>")
        list_items.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            flush_list()
            continue
        if line.startswith("#"):
            flush_paragraph()
            flush_list()
            heading = line.lstrip("#").strip()
            if heading:
                chunks.append(f"    <h3>{render_inline_markup(heading)}</h3>")
            continue
        if line.startswith("- "):
            flush_paragraph()
            item = line[2:].strip()
            if item:
                list_items.append(f"      <li>{render_inline_markup(item)}</li>")
            continue
        flush_list()
        paragraph_lines.append(line)

    flush_paragraph()
    flush_list()
    return "\n".join(chunks)


def render_front_matter(
    batch: dict[str, Any],
    source_rows: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
    front_matter_markdown: str | None = None,
) -> str:
    if front_matter_markdown and front_matter_markdown.strip():
        body = render_reader_note_markdown(front_matter_markdown)
        return "\n".join(
            ['    <div class="reader-front-matter">', body, "    </div>"]
        )

    items: list[str] = []
    front_matter = front_matter_entries(batch)
    if front_matter:
        for entry in front_matter:
            translation = entry.get("translation")
            if isinstance(translation, str) and translation.strip():
                items.append(f"      <p>{render_inline_markup(translation.strip())}</p>")
    else:
        for translation in title_page_translation_items(source_rows, config):
            items.append(f"      <p>{render_inline_markup(translation)}</p>")
    if not items:
        return ""
    return "\n".join(['    <div class="reader-front-matter">', *items, "    </div>"])


def render_cover(
    batch: dict[str, Any],
    source_rows: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
    front_matter_markdown: str | None = None,
) -> str:
    title = html.escape(batch_title(batch, config))
    page_total = source_page_total(batch, source_rows)
    page_total_text = (
        f"原剧本共 {page_total} 页" if page_total is not None else "原剧本页数未知"
    )
    front_matter = render_front_matter(
        batch, source_rows, config, front_matter_markdown
    )
    return f"""  <header class="reader-header">
    <p class="reader-kicker">中文剧本学习版</p>
    <h1 class="reader-title">{title}</h1>
    <p class="reader-meta">{html.escape(page_total_text)}</p>
    <p class="reader-rights">本中文剧本学习版仅供个人学习与研究使用，请勿商用或公开传播。</p>
{front_matter}
  </header>"""


def render_reader_note(
    batch: dict[str, Any], reader_notes_markdown: str | None = None
) -> str:
    if reader_notes_markdown and reader_notes_markdown.strip():
        body = render_reader_note_markdown(reader_notes_markdown)
        return f"""  <section class="reader-note" aria-labelledby="reader-note-title">
    <h2 id="reader-note-title">阅读说明</h2>
{body}
  </section>"""

    subtitle_text = (
        "已参考提供的中文字幕，方便对照对白。"
        if batch.get("has_subtitles")
        else "未提供参考字幕，译文仅依据剧本正文生成。"
    )
    return f"""  <section class="reader-note" aria-labelledby="reader-note-title">
    <h2 id="reader-note-title">阅读说明</h2>
    <p><span class="proper-name">下划线</span>用于人物、地点、片名等专名；<strong class="emphasis">加粗</strong>用于音效、银幕重点或剧本强调；<em class="term">斜体</em>用于英文剧本术语、缩写或格式说明。</p>
    <p>对应原剧本显示页码；场号保留原剧本边栏编号。</p>
    <p>{html.escape(subtitle_text)}</p>
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


def render_pages(display_units: list[DisplayUnit]) -> str:
    chunks: list[str] = []
    current_page: int | None = None
    for unit in display_units:
        entry = unit_primary_entry(unit)
        display_page = int(entry["display_page"])
        if display_page != current_page:
            if current_page is not None:
                chunks.append("  </section>")
            chunks.append(render_page_open(display_page))
            current_page = display_page
        chunks.append(render_display_unit(unit))
    if current_page is not None:
        chunks.append("  </section>")
    return "\n".join(chunks)


def build_html(
    batch: dict[str, Any],
    batch_path: Path | None = None,
    project_path: Path | None = None,
) -> str:
    config = load_project_config_for_batch(batch_path, project_path)
    title_text = batch_title(batch, config)
    title = html.escape(title_text)
    progress_key_attr = html.escape(progress_key(batch, config), quote=True)
    batch_id_attr = html.escape(str(batch.get("batch_id") or title_text), quote=True)
    source_rows = load_source_rows_for_batch(batch_path)
    front_matter_markdown = load_front_matter_for_batch(batch_path, project_path)
    cover = render_cover(batch, source_rows, config, front_matter_markdown)
    reader_notes_markdown = load_reader_notes_for_batch(batch_path, project_path)
    note = render_reader_note(batch, reader_notes_markdown)
    entries = body_entries(batch)
    display_units = reflow_grouping_pass(entries)
    scene_index = render_scene_index(entries)
    body = render_pages(display_units)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{STYLE}</style>
</head>
<body>
  <main class="screenplay-study" data-batch-id="{batch_id_attr}" data-progress-key="{progress_key_attr}">
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
    parser.add_argument("--project", type=Path, help="Optional path to project.yaml.")
    args = parser.parse_args()

    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    if not isinstance(batch, dict):
        print("FAIL batch.root root must be object", file=sys.stderr)
        return 1
    findings = validate_batch.validate_batch(batch, batch_path=args.batch)
    failures = [finding for finding in findings if finding.level == "FAIL"]
    if failures:
        for finding in failures:
            print(finding.render(), file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        build_html(batch, args.batch, args.project), encoding="utf-8"
    )
    print(f"INFO html {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
