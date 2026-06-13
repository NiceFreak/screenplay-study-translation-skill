#!/usr/bin/env python3
"""Bilingual-subtitle auto-confirm, scene anchor, and unseen-hint checks.

Exercises the package_batch_context pre-confirm functions directly on in-memory
synthetic bilingual data (no project scaffolding needed): ideal in-order matches
auto-confirm, a planted out-of-order line flags order_conflict, an unanchored
scene yields an advisory unseen hint, and pure-Chinese subtitles do not
auto-confirm (no regression).
"""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SmokeCheck

ASSERT_BODY = """
import package_batch_context as p

# Distinct bilingual events in time order; English half drives lexical matching,
# Chinese half is the reusable translation. Distinct vocabulary => one event per
# source, so each match has exactly one candidate.
EN = [
    "alpha bravo charlie delta echo foxtrot golf hotel",
    "india juliet kilo lima mike november oscar papa",
    "quebec romeo sierra tango uniform victor whiskey xray",
    "yankee zulu apple bench cloud drum eagle flute",
    "glass house igloo jungle kettle ladder magnet nettle",
    "orange pencil quartz river saddle tunnel violin window",
]
events = [
    {"start": i * 10.0, "end": i * 10.0 + 3.0, "text": EN[i] + " 中文字幕" + str(i)}
    for i in range(len(EN))
]

# In-order units, plus one planted out-of-order unit matching event 0 last.
units = [
    {"speaker": "A", "entry_ids": ["d0"], "display_pages": [1], "source": EN[0]},
    {"speaker": "A", "entry_ids": ["d1"], "display_pages": [1], "source": EN[1]},
    {"speaker": "B", "entry_ids": ["d4"], "display_pages": [2], "source": EN[4]},
    {"speaker": "B", "entry_ids": ["d5"], "display_pages": [2], "source": EN[5]},
    {"speaker": "C", "entry_ids": ["dx"], "display_pages": [3], "source": EN[0]},
]
matches = p.subtitle_matches_for_units(events, units, [])
summary = p.annotate_order_and_autoconfirm(matches, None)

if summary["auto_confirmed"] != 4:
    raise SystemExit("auto_confirmed=" + str(summary["auto_confirmed"]) + " expected 4")
if summary["order_conflicts"] != 1:
    raise SystemExit("order_conflicts=" + str(summary["order_conflicts"]) + " expected 1")
if matches[0].get("auto_label") != "字幕匹配":
    raise SystemExit("first unit not auto-confirmed")
if matches[4].get("auto_label") is not None:
    raise SystemExit("out-of-order unit was auto-confirmed")
if matches[4].get("order_conflict") is not True:
    raise SystemExit("out-of-order unit missing order_conflict")

# Scene anchors + unseen hint: scene 2 has an unmatched line -> no anchor.
units2 = [
    {"speaker": "A", "entry_ids": ["da"], "display_pages": [1], "source": EN[0]},
    {"speaker": "A", "entry_ids": ["db"], "display_pages": [2],
     "source": "unrelated gibberish zzzqqq nomatchhere"},
    {"speaker": "B", "entry_ids": ["dc"], "display_pages": [3], "source": EN[2]},
]
matches2 = p.subtitle_matches_for_units(events, units2, [])
p.annotate_order_and_autoconfirm(matches2, None)

def heading(entry_id, scene_no, page):
    return {
        "id": entry_id,
        "type": "scene_heading",
        "display_page": page,
        "markers": [{"type": "scene_no", "text": scene_no,
                     "scene_no": scene_no, "position": "left"}],
    }

source_entries = [
    heading("s1", "1", 1),
    {"id": "da", "type": "dialogue", "display_page": 1},
    heading("s2", "2", 2),
    {"id": "db", "type": "dialogue", "display_page": 2},
    heading("s3", "3", 3),
    {"id": "dc", "type": "dialogue", "display_page": 3},
]
anchors = p.scene_dialogue_anchors(source_entries, matches2)
if len(anchors) != 3:
    raise SystemExit("anchor count=" + str(len(anchors)) + " expected 3")
if anchors[0]["subtitle_start"] != 0.0:
    raise SystemExit("scene 1 anchor start=" + str(anchors[0]["subtitle_start"]))
if anchors[1]["subtitle_start"] is not None:
    raise SystemExit("scene 2 should be unanchored")
if anchors[2]["subtitle_start"] != 20.0:
    raise SystemExit("scene 3 anchor start=" + str(anchors[2]["subtitle_start"]))

hints = p.unseen_scene_hints(anchors)
if len(hints) != 1:
    raise SystemExit("unseen hint count=" + str(len(hints)) + " expected 1")
hint = hints[0]
if hint["scene_no"] != "2":
    raise SystemExit("hint scene_no=" + str(hint["scene_no"]))
if hint["window_start"] != 0.0 or hint["window_end"] != 20.0:
    raise SystemExit("hint window mismatch")
if hint["confidence"] != "low":
    raise SystemExit("hint should be low confidence")

# Pure-Chinese subtitles: lexical signals collapse -> no auto-confirm (no regression).
zh_events = [
    {"start": i * 10.0, "end": i * 10.0 + 3.0, "text": "纯中文台词" + str(i)}
    for i in range(3)
]
zh_units = [
    {"speaker": "A", "entry_ids": ["z0"], "display_pages": [1], "source": EN[0]},
]
zh_matches = p.subtitle_matches_for_units(zh_events, zh_units, [])
zh_summary = p.annotate_order_and_autoconfirm(zh_matches, None)
if zh_summary["auto_confirmed"] != 0:
    raise SystemExit("pure-Chinese auto_confirmed=" + str(zh_summary["auto_confirmed"]))

raise SystemExit(0)
"""


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    assert_script = tmp_dir / "assert_subtitle_autoconfirm.py"
    assert_script.write_text(
        f"import sys\nsys.path.insert(0, {str(SCRIPTS_DIR)!r})\n" + ASSERT_BODY,
        encoding="utf-8",
    )
    return [
        {
            "name": "subtitle_autoconfirm",
            "command": [python, str(assert_script)],
        },
    ]
