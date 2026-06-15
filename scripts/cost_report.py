#!/usr/bin/env python3
"""Create a read-only token/cost observation report for a project."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import audit


TRANSLATED_BATCH_RE = re.compile(
    r"^translated-p(?P<start>\d+)(?:-(?P<end>\d+))?\.json$"
)
DEFAULT_MODEL_NAME = "gpt-5.5"
DEFAULT_OVERHEAD_MULTIPLIER = 1.35
DEFAULT_PRICING_SOURCE = (
    "Built-in pricing snapshot (OpenAI/Codex checked 2026-06-11, "
    "Anthropic checked 2026-06-04); verify current pricing before treating "
    "as anything beyond an estimate"
)
MODEL_PRICING_USD_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    "gpt-5.5": {
        "input": 5.0,
        "output": 30.0,
    },
    "gpt-5.4": {
        "input": 2.5,
        "output": 15.0,
    },
    "gpt-5.4-mini": {
        "input": 0.75,
        "output": 4.5,
    },
    "gpt-5.3-codex-spark": {
        "input": 5.0,
        "output": 30.0,
    },
    "gpt-5-codex": {
        "input": 1.25,
        "output": 10.0,
    },
    "gpt-5": {
        "input": 1.25,
        "output": 10.0,
    },
    "gpt-5-mini": {
        "input": 0.25,
        "output": 2.0,
    },
    "gpt-5-nano": {
        "input": 0.05,
        "output": 0.4,
    },
    # Anthropic pricing snapshot checked 2026-06-04 (USD per 1M tokens).
    "claude-opus-4-8": {
        "input": 5.0,
        "output": 25.0,
    },
    "claude-opus-4-7": {
        "input": 5.0,
        "output": 25.0,
    },
    "claude-opus-4-6": {
        "input": 5.0,
        "output": 25.0,
    },
    "claude-sonnet-4-6": {
        "input": 3.0,
        "output": 15.0,
    },
    "claude-haiku-4-5": {
        "input": 1.0,
        "output": 5.0,
    },
}


@dataclass(frozen=True)
class CostEstimateConfig:
    model_name: str | None
    model_name_source: str
    input_usd_per_million_tokens: float | None
    output_usd_per_million_tokens: float | None
    overhead_multiplier: float
    pricing_source: str | None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_work_dir(project_file: Path, config: dict[str, Any]) -> Path:
    outputs = audit.section(config, "outputs")
    work_dir = audit.resolve_path(project_file, outputs.get("work_dir") or "work")
    return work_dir or project_file.parent / "work"


def output_path(
    project_file: Path, config: dict[str, Any], override: Path | None
) -> Path:
    if override is not None:
        path = override.expanduser()
        return path if path.is_absolute() else project_file.parent / path
    return resolve_work_dir(project_file, config) / "reports" / "cost-report.json"


def estimated_tokens_from_bytes(byte_count: int) -> int:
    # Mixed English/Chinese JSON artifacts in this project have varied token
    # density. Four bytes per token is a conservative, portable estimate.
    return max(1, round(byte_count / 4))


def file_observation(path: Path) -> dict[str, Any]:
    byte_count = path.stat().st_size if path.exists() else 0
    return {
        "path": str(path),
        "exists": path.exists(),
        "bytes": byte_count,
        "estimated_tokens": estimated_tokens_from_bytes(byte_count)
        if path.exists()
        else 0,
    }


def translated_batch_range(path: Path) -> tuple[int, int] | None:
    match = TRANSLATED_BATCH_RE.fullmatch(path.name)
    if match is None:
        return None
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    if end < start:
        return None
    return start, end


def batch_observation(path: Path) -> dict[str, Any]:
    observation = file_observation(path)
    batch_range = translated_batch_range(path)
    if batch_range is not None:
        observation["display_pages"] = {
            "start": batch_range[0],
            "end": batch_range[1],
            "count": batch_range[1] - batch_range[0] + 1,
        }
    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError):
        return observation
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if isinstance(entries, list):
        observation["entry_count"] = sum(
            1 for entry in entries if isinstance(entry, dict)
        )
    return observation


def observe_glob(directory: Path, pattern: str) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    return [
        file_observation(path)
        for path in sorted(directory.glob(pattern))
        if path.is_file()
    ]


def observe_existing(paths: list[Path]) -> list[dict[str, Any]]:
    return [
        file_observation(path) for path in paths if path.exists() and path.is_file()
    ]


def observe_batches(batch_dir: Path) -> list[dict[str, Any]]:
    if not batch_dir.exists():
        return []
    return [
        batch_observation(path)
        for path in sorted(batch_dir.glob("translated-p*.json"))
        if path.is_file()
    ]


def sum_field(items: list[dict[str, Any]], field: str) -> int:
    return sum(int(item.get(field) or 0) for item in items)


def summarize_group(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {"count": 0, "bytes": 0, "estimated_tokens": 0}
    return {
        "count": len(items),
        "bytes": sum_field(items, "bytes"),
        "estimated_tokens": sum_field(items, "estimated_tokens"),
        "average_bytes": round(sum_field(items, "bytes") / len(items)),
        "average_estimated_tokens": round(
            sum_field(items, "estimated_tokens") / len(items)
        ),
    }


def optional_float(value: Any, name: str) -> float | None:
    if value in {None, ""}:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if parsed < 0:
        raise ValueError(f"{name} must be non-negative")
    return parsed


def positive_float(value: Any, name: str, default: float) -> float:
    parsed = optional_float(value, name)
    if parsed is None:
        return default
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return parsed


def first_present(*values: Any) -> Any:
    for value in values:
        if value not in {None, ""}:
            return value
    return None


def first_present_with_source(*items: tuple[Any, str]) -> tuple[Any, str]:
    for value, source in items:
        if value not in {None, ""}:
            return value, source
    return None, "missing"


def resolve_cost_estimate_config(
    config: dict[str, Any],
    *,
    model_name: str | None,
    input_price: float | None,
    output_price: float | None,
    overhead_multiplier: float | None,
    pricing_source: str | None,
) -> CostEstimateConfig:
    cost_config = audit.section(config, "cost_estimate")
    environment_model = first_present(
        os.environ.get("OPENAI_MODEL"),
        os.environ.get("CODEX_MODEL"),
        os.environ.get("ANTHROPIC_MODEL"),
        os.environ.get("CLAUDE_MODEL"),
        os.environ.get("MODEL_NAME"),
    )
    resolved_model, model_source = first_present_with_source(
        (model_name, "cli"),
        (cost_config.get("model"), "project_config"),
        (cost_config.get("model_name"), "project_config"),
        (environment_model, "environment"),
        (DEFAULT_MODEL_NAME, "default_codex_assumption"),
    )
    pricing = MODEL_PRICING_USD_PER_MILLION_TOKENS.get(str(resolved_model))
    resolved_input_price = optional_float(
        first_present(
            input_price,
            cost_config.get("input_usd_per_million_tokens"),
            cost_config.get("input_usd_per_1m_tokens"),
            pricing.get("input") if pricing else None,
        ),
        "input_usd_per_million_tokens",
    )
    resolved_output_price = optional_float(
        first_present(
            output_price,
            cost_config.get("output_usd_per_million_tokens"),
            cost_config.get("output_usd_per_1m_tokens"),
            pricing.get("output") if pricing else None,
        ),
        "output_usd_per_million_tokens",
    )
    resolved_overhead = positive_float(
        first_present(overhead_multiplier, cost_config.get("overhead_multiplier")),
        "overhead_multiplier",
        DEFAULT_OVERHEAD_MULTIPLIER,
    )
    resolved_source = first_present(
        pricing_source,
        cost_config.get("pricing_source"),
        DEFAULT_PRICING_SOURCE if pricing else None,
    )
    return CostEstimateConfig(
        model_name=str(resolved_model) if resolved_model is not None else None,
        model_name_source=model_source,
        input_usd_per_million_tokens=resolved_input_price,
        output_usd_per_million_tokens=resolved_output_price,
        overhead_multiplier=resolved_overhead,
        pricing_source=str(resolved_source) if resolved_source is not None else None,
    )


def group_tokens(groups: dict[str, dict[str, Any]], names: list[str]) -> int:
    return sum(int(groups.get(name, {}).get("estimated_tokens") or 0) for name in names)


def build_cost_estimate(
    groups: dict[str, dict[str, Any]], config: CostEstimateConfig
) -> dict[str, Any]:
    input_group_names = ["batch_contexts"]
    output_group_names = ["translated_batches"]
    base_input_tokens = group_tokens(groups, input_group_names)
    base_output_tokens = group_tokens(groups, output_group_names)
    input_tokens = round(base_input_tokens * config.overhead_multiplier)
    output_tokens = round(base_output_tokens * config.overhead_multiplier)
    missing: list[str] = []
    if config.model_name is None:
        missing.append("model_name")
    if config.input_usd_per_million_tokens is None:
        missing.append("input_usd_per_million_tokens")
    if config.output_usd_per_million_tokens is None:
        missing.append("output_usd_per_million_tokens")

    coverage_warnings: list[str] = []
    if groups.get("batch_contexts", {}).get("count", 0) == 0:
        coverage_warnings.append(
            "No batch context artifacts observed; translation input cost may be under-estimated."
        )
    if groups.get("translated_batches", {}).get("count", 0) == 0:
        coverage_warnings.append(
            "No translated batch artifacts observed; translation output cost may be under-estimated."
        )

    estimate: dict[str, Any] = {
        "status": "not_estimated" if missing else "estimated",
        "currency": "USD",
        "model_name": config.model_name,
        "model_name_source": config.model_name_source,
        "pricing_source": config.pricing_source,
        "input_groups": input_group_names,
        "output_groups": output_group_names,
        "base_input_estimated_tokens": base_input_tokens,
        "base_output_estimated_tokens": base_output_tokens,
        "overhead_multiplier": config.overhead_multiplier,
        "input_estimated_tokens": input_tokens,
        "output_estimated_tokens": output_tokens,
        "confidence": "low" if coverage_warnings else "medium",
        "not_billing_authority": True,
        "basis": (
            "project-level screenplay translation proxy from local artifacts; "
            "not runtime API usage"
        ),
        "limitations": [
            "Excludes hidden runtime prompts, cached-token discounts, retries, and failed calls unless represented in local artifacts or overhead_multiplier.",
            "Uses batch context artifacts as input proxies and translated batch artifacts as output proxies.",
        ],
        "coverage_warnings": coverage_warnings,
    }
    if missing:
        estimate["missing_required_inputs"] = missing
        return estimate

    input_usd = input_tokens / 1_000_000 * config.input_usd_per_million_tokens
    output_usd = output_tokens / 1_000_000 * config.output_usd_per_million_tokens
    estimate.update(
        {
            "input_usd_per_million_tokens": config.input_usd_per_million_tokens,
            "output_usd_per_million_tokens": config.output_usd_per_million_tokens,
            "estimated_input_usd": round(input_usd, 6),
            "estimated_output_usd": round(output_usd, 6),
            "estimated_total_usd": round(input_usd + output_usd, 6),
        }
    )
    return estimate


def build_report(
    project_file: Path,
    *,
    model_name: str | None = None,
    input_price: float | None = None,
    output_price: float | None = None,
    overhead_multiplier: float | None = None,
    pricing_source: str | None = None,
) -> dict[str, Any]:
    config = audit.load_simple_yaml(project_file)
    cost_config = resolve_cost_estimate_config(
        config,
        model_name=model_name,
        input_price=input_price,
        output_price=output_price,
        overhead_multiplier=overhead_multiplier,
        pricing_source=pricing_source,
    )
    work_dir = resolve_work_dir(project_file, config)
    outputs = audit.section(config, "outputs")
    source_lines = audit.resolve_path(
        project_file, outputs.get("source_lines") or "work/source-lines.json"
    )
    subtitles_json = audit.resolve_path(
        project_file, outputs.get("subtitles_json") or "work/subtitles.json"
    )
    marker_inventory = audit.resolve_path(
        project_file, outputs.get("marker_inventory") or "work/source-markers.json"
    )
    context_dir = work_dir / "context"
    batch_dir = work_dir / "batches"
    batch_contexts = observe_glob(context_dir, "batch-context-p*.json")
    batches = observe_batches(batch_dir)
    upstream_files = [
        file_observation(path)
        for path in (
            source_lines,
            subtitles_json,
            marker_inventory,
            work_dir / "style-profile.json",
        )
        if path is not None
    ]
    groups = {
        "upstream_artifacts": summarize_group(upstream_files),
        "batch_contexts": summarize_group(batch_contexts),
        "translated_batches": summarize_group(batches),
    }
    total_tokens = sum(
        int(group.get("estimated_tokens") or 0) for group in groups.values()
    )
    return {
        "version": 1,
        "kind": "cost_observation_report",
        "project": {
            "project_file": str(project_file),
            "title": audit.section(config, "project").get("title"),
            "chinese_title": audit.section(config, "project").get("chinese_title"),
        },
        "estimate_basis": {
            "method": "artifact_bytes_divided_by_4",
            "scope": "local artifact size observation only; not API billing data",
        },
        "summary": {
            "estimated_tokens_total": total_tokens,
            "groups": groups,
        },
        "cost_estimate": build_cost_estimate(groups, cost_config),
        "artifacts": {
            "upstream_artifacts": upstream_files,
            "batch_contexts": batch_contexts,
            "translated_batches": batches,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a read-only token/cost observation report."
    )
    parser.add_argument("project", type=Path, help="Path to project.yaml.")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", "--model-name", dest="model_name")
    parser.add_argument("--input-usd-per-million-tokens", type=float)
    parser.add_argument("--output-usd-per-million-tokens", type=float)
    parser.add_argument("--overhead-multiplier", type=float)
    parser.add_argument("--pricing-source")
    args = parser.parse_args()

    project_file = args.project.expanduser().resolve()
    config = audit.load_simple_yaml(project_file)
    report = build_report(
        project_file,
        model_name=args.model_name,
        input_price=args.input_usd_per_million_tokens,
        output_price=args.output_usd_per_million_tokens,
        overhead_multiplier=args.overhead_multiplier,
        pricing_source=args.pricing_source,
    )
    out_path = output_path(project_file, config, args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"INFO cost_report {out_path}")
    print(f"INFO estimated_tokens_total {report['summary']['estimated_tokens_total']}")
    cost_estimate = report.get("cost_estimate", {})
    if cost_estimate.get("status") == "estimated":
        print(f"INFO estimated_total_usd {cost_estimate['estimated_total_usd']}")
    else:
        missing = ", ".join(cost_estimate.get("missing_required_inputs", []))
        print(f"INFO cost_estimate not_estimated missing={missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
