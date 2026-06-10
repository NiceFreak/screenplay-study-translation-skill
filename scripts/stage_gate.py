#!/usr/bin/env python3
"""Shared pipeline gate checks."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

import audit


BLOCKING_STATES = {"ISSUE DETECTED", "UNCERTAIN"}


def work_dir_path(project_file: Path, config: dict[str, Any]) -> Path:
    outputs = audit.section(config, "outputs")
    work_dir = audit.resolve_path(project_file, outputs.get("work_dir") or "work")
    return work_dir if work_dir is not None else project_file.parent / "work"


def finding_log_path(project_file: Path, config: dict[str, Any]) -> Path:
    return work_dir_path(project_file, config) / "logs" / "stage-1-2-findings.json"


def confirmation_path(project_file: Path, config: dict[str, Any]) -> Path:
    return work_dir_path(project_file, config) / "logs" / "stage-2-confirmation.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stage2_summary(log: dict[str, Any]) -> tuple[str, int]:
    state = str(log.get("overall_state") or "UNCERTAIN")
    records = log.get("records")
    return state, len(records) if isinstance(records, list) else 0


def signal_counts(log: dict[str, Any]) -> dict[str, int]:
    counts = {"structural_signal": 0, "warning_signal": 0, "noise_signal": 0}
    stored_counts = log.get("signal_counts")
    if isinstance(stored_counts, dict):
        for signal_name in counts:
            value = stored_counts.get(signal_name)
            if isinstance(value, int):
                counts[signal_name] = value
        return counts
    records = log.get("records")
    if not isinstance(records, list):
        return counts
    for record in records:
        if not isinstance(record, dict):
            continue
        code = str(record.get("code") or "")
        for signal_name in counts:
            if code.startswith(signal_name + "."):
                counts[signal_name] += 1
    return counts


def records_digest(log: dict[str, Any]) -> str:
    records = log.get("records")
    payload = records if isinstance(records, list) else []
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def check_stage2_confirmation(
    project_file: Path, config: dict[str, Any]
) -> tuple[bool, list[str]]:
    log_path = finding_log_path(project_file, config)
    confirm_path = confirmation_path(project_file, config)
    lines: list[str] = []
    if not log_path.exists():
        return False, [f"FAIL stage2.finding_log_missing {log_path}"]

    log = load_json(log_path)
    state, record_count = stage2_summary(log)
    counts = signal_counts(log)
    lines.append(f"INFO stage2.finding_log {log_path}")
    lines.append(f"INFO stage2.finding_state state={state} records={record_count}")
    lines.append(
        "INFO stage2.signal_counts "
        f"structural={counts['structural_signal']} "
        f"warning={counts['warning_signal']} noise={counts['noise_signal']}"
    )
    if state in BLOCKING_STATES:
        lines.append(f"FAIL stage2.findings_blocking state={state}")
        return False, lines

    if not confirm_path.exists():
        lines.append(f"FAIL stage2.confirmation_missing {confirm_path}")
        return False, lines

    confirmation = load_json(confirm_path)
    lines.append(f"INFO stage2.confirmation {confirm_path}")
    if not confirmation.get("confirmed") or not confirmation.get(
        "approved_for_stage_3"
    ):
        lines.append("FAIL stage2.confirmation_unapproved")
        return False, lines

    expected_log = str(log_path)
    if confirmation.get("source_finding_log") != expected_log:
        lines.append(
            "FAIL stage2.confirmation_stale "
            f"source_finding_log={confirmation.get('source_finding_log')}"
        )
        return False, lines
    if confirmation.get("source_overall_state") != state:
        lines.append(
            "FAIL stage2.confirmation_stale "
            f"source_overall_state={confirmation.get('source_overall_state')}"
        )
        return False, lines
    if confirmation.get("source_records_count") != record_count:
        lines.append(
            "FAIL stage2.confirmation_stale "
            f"source_records_count={confirmation.get('source_records_count')}"
        )
        return False, lines
    if confirmation.get("source_records_digest") != records_digest(log):
        lines.append("FAIL stage2.confirmation_stale source_records_digest")
        return False, lines

    lines.append("INFO stage2.confirmed approved_for_stage_3=true")
    return True, lines
