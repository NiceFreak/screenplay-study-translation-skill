#!/usr/bin/env python3
"""Assert JSON fixture counts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def fixture_counts(inventory_path: Path) -> dict[str, int]:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    events = inventory.get("events")
    if isinstance(events, list):
        counts["events"] = len(events)
    for marker in inventory.get("markers", []):
        if isinstance(marker, dict) and isinstance(marker.get("type"), str):
            marker_type = marker["type"]
            counts[marker_type] = counts.get(marker_type, 0) + 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert JSON fixture counts.")
    parser.add_argument("actual", type=Path)
    parser.add_argument("expected", type=Path)
    args = parser.parse_args()

    actual = fixture_counts(args.actual)
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    ok = True
    for marker_type, expected_count in sorted(expected.items()):
        actual_count = actual.get(marker_type, 0)
        if actual_count != expected_count:
            print(
                f"FAIL marker_count.{marker_type} expected={expected_count} actual={actual_count}"
            )
            ok = False
        else:
            print(
                f"INFO marker_count.{marker_type} expected={expected_count} actual={actual_count}"
            )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
