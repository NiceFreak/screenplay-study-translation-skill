#!/usr/bin/env python3
"""Wrapped-parenthetical reflow checks for build_html.

A parenthetical description the source wrapped across lines (an unclosed "（"
opener plus continuations) reflows into one parenthetical; self-contained
wrylies with balanced parens are never merged.
"""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SmokeCheck

ASSERT_BODY = """
import build_html as B

def par(eid, tr):
    return {"id": eid, "type": "parenthetical", "pdf_page": 2, "display_page": 1,
            "source": "x", "translation": tr}

# Wrapped description: unclosed opener + continuation -> one merged parenthetical.
wrapped = [par("p1", "（房间陷入黑暗，海浪声远远传来，"), par("p2", "一盏孤灯在风里摇晃。）")]
out = B.merge_wrapped_parentheticals(wrapped)
if len(out) != 1:
    raise SystemExit("wrapped parenthetical not merged: " + str(len(out)))
if out[0]["translation"] != "（房间陷入黑暗，海浪声远远传来，一盏孤灯在风里摇晃。）":
    raise SystemExit("merged text wrong: " + out[0]["translation"])

# Two balanced wrylies must NOT merge (distinct directions).
wrylies = [par("w1", "（停顿）"), par("w2", "（对玛丽说）")]
if len(B.merge_wrapped_parentheticals(wrylies)) != 2:
    raise SystemExit("balanced wrylies were wrongly merged")

# A wrapped opener only absorbs parenthetical continuations, not other types.
mixed = [par("m1", "（灯光忽明忽暗，"), {"id": "m2", "type": "action", "pdf_page": 2,
         "display_page": 1, "source": "y", "translation": "门开了。"}]
if len(B.merge_wrapped_parentheticals(mixed)) != 2:
    raise SystemExit("wrapped opener wrongly absorbed a non-parenthetical")

# End to end: the wrapped parenthetical renders as one contiguous line.
batch = {"version": 1, "batch_id": "p", "source_pages": {"start": 1, "end": 1},
         "has_subtitles": False, "entries": [
    {"id": "s1", "type": "scene_heading", "pdf_page": 2, "display_page": 1,
     "source": "INT. X - NIGHT", "translation": "内景。X — 夜"},
    par("p1", "（房间陷入黑暗，海浪声远远传来，"), par("p2", "一盏孤灯在风里摇晃。）")]}
h = B.build_html(batch)
if "（房间陷入黑暗，海浪声远远传来，一盏孤灯在风里摇晃。）" not in h:
    raise SystemExit("wrapped parenthetical not contiguous in HTML")

raise SystemExit(0)
"""


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    assert_script = tmp_dir / "assert_paren_reflow.py"
    assert_script.write_text(
        f"import sys\nsys.path.insert(0, {str(SCRIPTS_DIR)!r})\n" + ASSERT_BODY,
        encoding="utf-8",
    )
    return [{"name": "paren_reflow", "command": [python, str(assert_script)]}]
