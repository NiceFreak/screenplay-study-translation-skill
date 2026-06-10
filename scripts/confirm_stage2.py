#!/usr/bin/env python3
"""Confirm Stage 2 signal recording before Stage 3 batch creation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import audit
import stage_gate


def build_confirmation(
    project_file: Path, config: dict[str, Any], decisions: list[str], note: str | None
) -> dict[str, Any]:
    log_path = stage_gate.finding_log_path(project_file, config)
    if not log_path.exists():
        raise FileNotFoundError(f"stage2_finding_log={log_path}")
    log = stage_gate.load_json(log_path)
    state, record_count = stage_gate.stage2_summary(log)
    if state in stage_gate.BLOCKING_STATES:
        raise ValueError(f"stage2 findings are blocking: state={state}")
    return {
        "version": 1,
        "stage": "STAGE 2: SOURCE SIGNAL RECORD CONFIRMATION",
        "project": str(project_file),
        "confirmed": True,
        "approved_for_stage_3": True,
        "source_finding_log": str(log_path),
        "source_overall_state": state,
        "source_records_count": record_count,
        "source_records_digest": stage_gate.records_digest(log),
        "signal_counts": stage_gate.signal_counts(log),
        "notes": decisions,
        "note": note,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write Stage 2 signal confirmation for Stage 3 batch creation."
    )
    parser.add_argument("project", type=Path)
    parser.add_argument(
        "--decision",
        action="append",
        default=[],
        help="Optional Stage 2 signal note. Repeat for multiple notes.",
    )
    parser.add_argument("--note")
    args = parser.parse_args()

    project_file = args.project.expanduser().resolve()
    config = audit.load_simple_yaml(project_file)
    confirmation = build_confirmation(project_file, config, args.decision, args.note)
    out_path = stage_gate.confirmation_path(project_file, config)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(confirmation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"INFO stage2.confirmation {out_path}")
    print("INFO stage2.signal_record confirmed=true approved_for_stage_3=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
