#!/usr/bin/env python3
"""Subtitle auto-confirm, scene anchor, and unseen-hint checks.

Exercises the package_batch_context pre-confirm functions on in-memory synthetic
bilingual data (no project scaffolding needed):

- a unique near-identical (substring) match auto-confirms even when it runs
  backward in subtitle time (films cut and reorder dialogue), and is flagged
  order_relocated rather than rejected;
- a similar-but-not-identical match (full term overlap but not a substring,
  including a hidden-negation line) does NOT auto-confirm, so a reworded line is
  left for the model to mark as 字幕差异;
- an unanchored scene yields an advisory unseen hint;
- pure-Chinese subtitles do not auto-confirm (no regression).
"""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SmokeCheck

ASSERT_BODY = """
import package_batch_context as p

# Distinct long bilingual events in time order; the English half (>=16 compacted
# chars) drives substring matching, the Chinese half is the reusable translation.
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

def unit(eid, src):
    return {"speaker": "A", "entry_ids": [eid], "display_pages": [1], "source": src}

# Test A: in-order substring matches auto-confirm; a backward (relocated) one
# still auto-confirms instead of being vetoed.
units = [unit("d0", EN[0]), unit("d1", EN[1]), unit("d2", EN[5]), unit("dx", EN[0])]
matches = p.subtitle_matches_for_units(events, units, [])
summary = p.annotate_order_and_autoconfirm(matches, None)

if summary["auto_confirmed"] != 4:
    raise SystemExit("auto_confirmed=" + str(summary["auto_confirmed"]) + " expected 4")
if summary["relocations"] != 1:
    raise SystemExit("relocations=" + str(summary["relocations"]) + " expected 1")
if matches[0].get("auto_label") != "字幕匹配":
    raise SystemExit("first unit not auto-confirmed")
if matches[3].get("auto_label") != "字幕匹配":
    raise SystemExit("relocated unit should still auto-confirm")
if matches[3].get("order_relocated") is not True:
    raise SystemExit("relocated unit missing order_relocated")
if matches[3]["candidates"][0].get("order_consistent") is not False:
    raise SystemExit("relocated unit should be order-inconsistent")
if matches[0]["candidates"][0].get("substring") is not True:
    raise SystemExit("near-identical match missing substring flag")

# Test B: full term overlap but NOT a substring (reordered + a hidden negation)
# must not auto-confirm, so a reworded line stays for the model.
events_b = [
    {"start": 0.0, "end": 3.0, "text": "we quietly sell the family farm 我们悄悄卖掉农场"},
    {"start": 5.0, "end": 8.0, "text": "I will sell the harbor tonight 我今晚会卖掉港口"},
]
units_b = [
    unit("b0", "sell the family farm quietly tonight"),
    unit("b1", "I will not sell the harbor tonight"),
]
matches_b = p.subtitle_matches_for_units(events_b, units_b, [])
summary_b = p.annotate_order_and_autoconfirm(matches_b, None)
if summary_b["auto_confirmed"] != 0:
    raise SystemExit("similar-not-identical auto_confirmed=" + str(summary_b["auto_confirmed"]))
for m in matches_b:
    if not m.get("candidates"):
        raise SystemExit("expected a high-score candidate for term-overlap unit")
    if m["candidates"][0].get("substring") is not False:
        raise SystemExit("term-overlap candidate wrongly flagged substring")
    if "auto_label" in m:
        raise SystemExit("term-overlap/negation unit must not auto-confirm")

# Test C: scene anchors land on auto-confirmed lines; an unmatched scene -> hint.
units_sc = [unit("da", EN[0]), unit("db", "unrelated gibberish zzzqqq nomatchhere"), unit("dc", EN[2])]
matches_sc = p.subtitle_matches_for_units(events, units_sc, [])
p.annotate_order_and_autoconfirm(matches_sc, None)

def heading(eid, no, page):
    return {"id": eid, "type": "scene_heading", "display_page": page,
            "markers": [{"type": "scene_no", "text": no, "scene_no": no, "position": "left"}]}

source_entries = [
    heading("s1", "1", 1), {"id": "da", "type": "dialogue", "display_page": 1},
    heading("s2", "2", 2), {"id": "db", "type": "dialogue", "display_page": 2},
    heading("s3", "3", 3), {"id": "dc", "type": "dialogue", "display_page": 3},
]
anchors = p.scene_dialogue_anchors(source_entries, matches_sc)
if len(anchors) != 3:
    raise SystemExit("anchor count=" + str(len(anchors)) + " expected 3")
if anchors[0]["subtitle_start"] != 0.0:
    raise SystemExit("scene 1 anchor start=" + str(anchors[0]["subtitle_start"]))
if anchors[1]["subtitle_start"] is not None:
    raise SystemExit("scene 2 should be unanchored")
if anchors[2]["subtitle_start"] != 20.0:
    raise SystemExit("scene 3 anchor start=" + str(anchors[2]["subtitle_start"]))

hints = p.unseen_scene_hints(anchors)
if len(hints) != 1 or hints[0]["scene_no"] != "2":
    raise SystemExit("unseen hint mismatch")
if hints[0]["window_start"] != 0.0 or hints[0]["window_end"] != 20.0:
    raise SystemExit("unseen window mismatch")
if hints[0]["confidence"] != "low":
    raise SystemExit("unseen hint should be low confidence")

# Test D: pure-Chinese subtitles -> no substring evidence -> no auto-confirm.
zh_events = [{"start": i * 10.0, "end": i * 10.0 + 3.0, "text": "纯中文台词" + str(i)} for i in range(3)]
zh_matches = p.subtitle_matches_for_units(zh_events, [unit("z0", EN[0])], [])
if p.annotate_order_and_autoconfirm(zh_matches, None)["auto_confirmed"] != 0:
    raise SystemExit("pure-Chinese auto-confirmed")

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
