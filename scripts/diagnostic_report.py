#!/usr/bin/env python3
"""Write an observation-only diagnostic report after Stage 2 validation."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import audit
import stage_gate


SIGNAL_TYPES = ("structural_signal", "warning_signal", "noise_signal")
STATE_MAP = {
    "NO ISSUE DETECTED": "PASS",
    "OUT OF SCOPE FINDING": "PARTIAL",
    "ISSUE DETECTED": "FAIL",
    "UNCERTAIN": "FAIL",
}
FAILURE_MODE_RE = re.compile(r"^## (FM-\d{3})\b", re.MULTILINE)


def diagnostic_path(project_file: Path, config: dict[str, Any]) -> Path:
    return stage_gate.work_dir_path(project_file, config) / "diagnostic" / (
        "diagnostic_report.json"
    )


def frequency(count: int) -> str:
    if count >= 50:
        return "high"
    if count >= 10:
        return "medium"
    return "low"


def signal_name(code: str) -> tuple[str, str] | None:
    for signal_type in SIGNAL_TYPES:
        prefix = signal_type + "."
        if not code.startswith(prefix):
            continue
        parts = code.split(".")
        while parts and parts[-1].isdigit():
            parts.pop()
        return signal_type, ".".join(parts[:2])
    return None


def report_file(project_file: Path, log: dict[str, Any]) -> Path | None:
    value = log.get("report")
    if not value:
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = project_file.parent / path
    return path


def report_signal_counts(path: Path | None) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    if path is None or not path.exists():
        return counts
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) < 2:
            continue
        parsed = signal_name(parts[1])
        if parsed is not None:
            counts[parsed] += 1
    return counts


def fallback_signal_counts(log: dict[str, Any]) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    stored = stage_gate.signal_counts(log)
    for signal_type in SIGNAL_TYPES:
        value = stored.get(signal_type, 0)
        if value > 0:
            counts[(signal_type, f"{signal_type}.count")] = value
    return counts


def key_signals(log: dict[str, Any], path: Path | None) -> list[dict[str, str]]:
    counts = report_signal_counts(path)
    if not counts:
        counts = fallback_signal_counts(log)
    ordered = sorted(
        counts.items(),
        key=lambda item: (
            SIGNAL_TYPES.index(item[0][0]),
            -item[1],
            item[0][1],
        ),
    )
    return [
        {
            "signal": signal,
            "type": signal_type,
            "frequency": frequency(count),
        }
        for (signal_type, signal), count in ordered
    ]


def available_failure_modes() -> set[str]:
    path = Path(__file__).resolve().parent.parent / "references" / (
        "failure_modes.md"
    )
    if not path.exists():
        return set()
    return set(FAILURE_MODE_RE.findall(path.read_text(encoding="utf-8")))


def has_report_token(path: Path | None, tokens: tuple[str, ...]) -> bool:
    if path is None or not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return any(token in text for token in tokens)


def add_failure_match(
    matches: list[dict[str, Any]],
    known_modes: set[str],
    failure_mode_id: str,
    confidence: str,
    evidence: list[str],
) -> None:
    if failure_mode_id in known_modes and evidence:
        matches.append(
            {
                "failure_mode_id": failure_mode_id,
                "confidence": confidence,
                "evidence": evidence,
            }
        )


def failure_mode_matches(
    log: dict[str, Any],
    path: Path | None,
    confirmation_ok: bool,
    confirmation_lines: list[str],
) -> list[dict[str, Any]]:
    known_modes = available_failure_modes()
    matches: list[dict[str, Any]] = []
    state, record_count = stage_gate.stage2_summary(log)
    counts = stage_gate.signal_counts(log)

    if not confirmation_ok and (
        counts["warning_signal"] > 0 or counts["noise_signal"] > 0
    ):
        add_failure_match(
            matches,
            known_modes,
            "FM-001",
            "medium",
            ["Stage 2 signal records exist but confirmation is not approved."],
        )

    if state == "OUT OF SCOPE FINDING" and record_count == 0:
        add_failure_match(
            matches,
            known_modes,
            "FM-003",
            "medium",
            ["overall_state=OUT OF SCOPE FINDING", "records=0"],
        )

    if not confirmation_ok and confirmation_lines:
        add_failure_match(
            matches,
            known_modes,
            "FM-005",
            "low",
            confirmation_lines[:3],
        )

    if has_report_token(path, ("extraction.pdf_pages_missing",)):
        add_failure_match(
            matches,
            known_modes,
            "FM-006",
            "high",
            ["Stage 1 extraction completeness was not verified."],
        )

    return matches


def likely_causes(
    signals: list[dict[str, str]], confirmation_ok: bool
) -> list[dict[str, Any]]:
    signal_names = {signal["signal"] for signal in signals}
    causes: list[dict[str, Any]] = []
    if "warning_signal.unclassified" in signal_names:
        causes.append(
            {
                "cause": "Stage 2 retained unmatched source-structure evidence as warning signals.",
                "supporting_signals": ["warning_signal.unclassified"],
            }
        )
    if "noise_signal.candidate" in signal_names:
        causes.append(
            {
                "cause": "Stage 2 retained low-confidence source candidates for traceability.",
                "supporting_signals": ["noise_signal.candidate"],
            }
        )
    if not confirmation_ok:
        causes.append(
            {
                "cause": "Stage 2 validation artifacts are not confirmed as complete.",
                "supporting_signals": [],
            }
        )
    return causes


def recommended_checks(
    system_state: str, signals: list[dict[str, str]], confirmation_ok: bool
) -> list[str]:
    checks: list[str] = []
    signal_names = {signal["signal"] for signal in signals}
    if not confirmation_ok:
        checks.append("Check work/logs/stage-2-confirmation.json before Stage 3.")
    if "warning_signal.unclassified" in signal_names:
        checks.append(
            "Review warning_signal entries in work/reports/sample-validation.txt."
        )
    if "noise_signal.candidate" in signal_names:
        checks.append(
            "Keep noise_signal candidates as traceability evidence only."
        )
    if system_state == "FAIL":
        checks.append("Review Stage 1-2 validation artifacts before continuing.")
    return checks


def build_report(project_file: Path, batch_id: str) -> dict[str, Any]:
    config = audit.load_simple_yaml(project_file)
    log_path = stage_gate.finding_log_path(project_file, config)
    if not log_path.exists():
        raise FileNotFoundError(f"stage2_finding_log={log_path}")
    log = stage_gate.load_json(log_path)
    report_path = report_file(project_file, log)
    confirmation_ok, confirmation_lines = stage_gate.check_stage2_confirmation(
        project_file, config
    )
    state, _record_count = stage_gate.stage2_summary(log)
    system_state = "FAIL" if not confirmation_ok else STATE_MAP.get(state, "FAIL")
    signals = key_signals(log, report_path)

    return {
        "batch_id": batch_id,
        "system_state": system_state,
        "key_signals": signals,
        "failure_mode_matches": failure_mode_matches(
            log, report_path, confirmation_ok, confirmation_lines
        ),
        "likely_causes": likely_causes(signals, confirmation_ok),
        "repeat_pattern_flag": False,
        "recommended_checks": recommended_checks(
            system_state, signals, confirmation_ok
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Write an observation-only diagnostic report from completed Stage 2 "
            "validation artifacts."
        )
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--batch-id", default="")
    args = parser.parse_args()

    project_file = args.project.expanduser().resolve()
    config = audit.load_simple_yaml(project_file)
    out_path = diagnostic_path(project_file, config)
    payload = build_report(project_file, args.batch_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"INFO diagnostic_report {out_path}")
    print(f"INFO diagnostic.system_state {payload['system_state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
