#!/usr/bin/env python3
"""Create marker inventory JSON from a translation batch fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def batch_markers(batch: dict[str, Any]) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for entry in batch.get("entries", []):
        if not isinstance(entry, dict):
            continue
        for marker in entry.get("markers", []) or []:
            if not isinstance(marker, dict) or not isinstance(marker.get("type"), str):
                continue
            item = {
                "type": marker["type"],
                "pdf_page": entry.get("pdf_page"),
                "display_page": entry.get("display_page"),
                "text": marker.get("text", ""),
                "source_layer": "batch_fixture",
            }
            if marker["type"] in {"scene_no", "split_scene"}:
                item["scene_no"] = marker.get("text", "")
            markers.append(item)
    return markers


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create marker inventory from batch JSON."
    )
    parser.add_argument("batch", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    payload = {
        "version": 1,
        "source": {"batch": str(args.batch)},
        "markers": batch_markers(batch),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"INFO marker_inventory {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
