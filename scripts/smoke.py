#!/usr/bin/env python3
"""Run the skill repository's low-cost smoke checks.

Check definitions live in scripts/smoke_checks/, one module per scenario.
Each module writes its own synthetic fixtures and returns an ordered list of
checks; this runner only assembles and executes them.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from smoke_checks import (
    checks_clean_project,
    checks_compile,
    checks_divergence_render,
    checks_html_output,
    checks_merge,
    checks_pdf_scan,
    checks_project_init,
    checks_reflow,
    checks_sample_project,
    checks_static_fixtures,
    checks_style_profile,
    checks_subtitle_autoconfirm,
    checks_subtitles,
    checks_terminology,
)
from smoke_checks.common import ROOT, SCRIPTS_DIR, SmokeCheck

CHECK_MODULES = [
    checks_compile,
    checks_pdf_scan,
    checks_subtitles,
    checks_project_init,
    checks_sample_project,
    checks_reflow,
    checks_clean_project,
    checks_terminology,
    checks_style_profile,
    checks_merge,
    checks_html_output,
    checks_static_fixtures,
    checks_subtitle_autoconfirm,
    checks_divergence_render,
]


def run_check(
    name: str,
    command: list[str],
    env: dict[str, str] | None = None,
    expect_failure: bool = False,
) -> bool:
    print(f"== {name}", flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, check=False)
    if expect_failure and result.returncode != 0:
        print(f"PASS {name} expected_failure exit={result.returncode}", flush=True)
        return True
    if not expect_failure and result.returncode == 0:
        print(f"PASS {name}", flush=True)
        return True
    print(f"FAIL {name} exit={result.returncode}", flush=True)
    return False


def main() -> int:
    python = sys.executable
    env = os.environ.copy()
    tmp_dir = Path(tempfile.mkdtemp(prefix="screenplay-skill-smoke-"))
    env.setdefault("PYTHONPYCACHEPREFIX", str(tmp_dir / "pycache"))
    env.setdefault("RUFF_CACHE_DIR", str(tmp_dir / "ruff-cache"))

    checks: list[SmokeCheck] = []
    for module in CHECK_MODULES:
        checks.extend(module.build_checks(tmp_dir, python))

    ok = True
    for check in checks:
        if check.get("skip"):
            print(f"SKIP {check['name']} {check['skip_reason']}", flush=True)
            continue
        ok = (
            run_check(
                check["name"],
                check["command"],
                env=env,
                expect_failure=bool(check.get("expect_failure", False)),
            )
            and ok
        )

    ruff = shutil.which("ruff")
    if ruff:
        ok = run_check("ruff", [ruff, "check", str(SCRIPTS_DIR)], env=env) and ok
    else:
        print("WARN ruff not installed; skipped lint", flush=True)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
