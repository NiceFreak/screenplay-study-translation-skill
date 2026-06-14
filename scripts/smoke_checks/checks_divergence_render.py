#!/usr/bin/env python3
"""Divergence-aware rendering checks for build_html.

Builds a small synthetic labeled batch and asserts the static (EPUB-safe) HTML:
字幕匹配 renders no marker, 字幕差异/字幕未见 render distinct styled markers, the
scene index carries per-scene divergence counts and a timecode, and the reading
note explains each marker.
"""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SmokeCheck

ASSERT_BODY = """
import build_html

batch = {
    "version": 1,
    "batch_id": "p001-001",
    "source_pages": {"start": 1, "end": 1},
    "has_subtitles": True,
    "entries": [
        {"id": "p001-e001", "type": "scene_heading", "pdf_page": 2, "display_page": 1,
         "source": "INT. CHAPEL - NIGHT", "translation": "内景。__教堂__ — 夜",
         "markers": [{"type": "scene_no", "text": "1", "scene_no": "1", "position": "left"},
                     {"type": "scene_no", "text": "1", "scene_no": "1", "position": "right"}]},
        {"id": "p001-e002", "type": "dialogue", "pdf_page": 2, "display_page": 1,
         "source": "line a", "translation": "这句与成片一致。", "subtitle_label": "字幕匹配",
         "subtitle_event_index": 0, "subtitle_start": 83.0, "subtitle_end": 86.0},
        {"id": "p001-e003", "type": "dialogue", "pdf_page": 2, "display_page": 1,
         "source": "line b", "translation": "这句成片改了说法。", "subtitle_label": "字幕差异"},
        {"id": "p001-e004", "type": "dialogue", "pdf_page": 2, "display_page": 1,
         "source": "line c", "translation": "这句成片没有。", "subtitle_label": "字幕未见"},
    ],
}
h = build_html.build_html(batch)

def need(cond, msg):
    if not cond:
        raise SystemExit(msg)

# 字幕匹配 is silent and never leaks as a visible marker.
need("字幕匹配" not in h, "字幕匹配 leaked into output")
# 差异 / 未见 render distinct styled markers.
need("成片差异" in h and "subtitle-label--diff" in h, "成片差异 marker missing")
need("成片未见" in h and "subtitle-label--unseen" in h, "成片未见 marker missing")
need("字幕差异" not in h and "字幕未见" not in h, "raw label text leaked")
# Scene index: per-scene divergence counts + timecode.
need("1改·1未见" in h, "scene-index divergence count missing")
need('scene-index-divergence' in h, "divergence span missing")
need("01:23" in h and 'scene-index-time' in h, "scene-index timecode missing")
# Body scene heading carries an EPUB-safe summary (the EPUB nav drops index spans).
need('class="scene-meta"' in h and "scene-meta-divergence" in h, "body scene summary missing")
# Reading note explains each marker (all static, EPUB-safe).
need("未标注的对白" in h, "reading note missing baseline explanation")
need("措辞、详略或说法" in h, "reading note missing 差异 explanation")
need("没有找到对应" in h, "reading note missing 未见 explanation")
need("已参考双语字幕，方便对照对白。" in h, "reading note missing bilingual subtitle line")
need("本版是中文剧本学习版" not in h, "removed intro sentence still present")

raise SystemExit(0)
"""


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    assert_script = tmp_dir / "assert_divergence_render.py"
    assert_script.write_text(
        f"import sys\nsys.path.insert(0, {str(SCRIPTS_DIR)!r})\n" + ASSERT_BODY,
        encoding="utf-8",
    )
    return [
        {
            "name": "divergence_render",
            "command": [python, str(assert_script)],
        },
    ]
