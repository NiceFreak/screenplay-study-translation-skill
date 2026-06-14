#!/usr/bin/env python3
"""Advisory subtitle-candidate checks for package_batch_context.

The context package offers advisory lexical candidates per dialogue unit; the
model decides 字幕匹配/差异/未见. There is no auto-confirm, scene-anchor, or
unseen-hint machinery — this check asserts the shape and that the retired
scaffolding stays gone.
"""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SmokeCheck

ASSERT_BODY = """
import package_batch_context as p

events = [
    {"start": 10.0, "end": 12.0, "text": "We should leave now 我们该走了"},
    {"start": 20.0, "end": 22.0, "text": "Lock the door 锁门"},
]
units = [
    {"speaker": "A", "entry_ids": ["d0"], "display_pages": [1], "source": "We should leave now"},
    {"speaker": "A", "entry_ids": ["d1"], "display_pages": [1], "source": "Totally unrelated zzz"},
]

matches = p.subtitle_matches_for_units(events, units, [])
if matches[0].get("candidates") is None:
    raise SystemExit("expected a candidate for the matching unit")
cand = matches[0]["candidates"][0]
if "substring" in cand:
    raise SystemExit("retired 'substring' flag is back")
if matches[1].get("candidates"):
    raise SystemExit("unrelated unit should have no candidate")

sc = p.subtitle_candidates(events, units, [])
removed = [k for k in ("auto_confirm_summary", "scene_anchors", "unseen_hints") if k in sc]
if removed:
    raise SystemExit("retired keys present: " + repr(removed))
for key in ("advisory_matches", "unique_subtitle_timestamps", "selection_note"):
    if key not in sc:
        raise SystemExit("missing key: " + key)

empty = p.subtitle_candidates([], units, [])
if empty.get("available") is not False:
    raise SystemExit("empty-events branch should be unavailable")

raise SystemExit(0)
"""


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    assert_script = tmp_dir / "assert_subtitle_candidates.py"
    assert_script.write_text(
        f"import sys\nsys.path.insert(0, {str(SCRIPTS_DIR)!r})\n" + ASSERT_BODY,
        encoding="utf-8",
    )
    return [{"name": "subtitle_candidates", "command": [python, str(assert_script)]}]
