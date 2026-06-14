#!/usr/bin/env python3
"""Project template audit and project initialization checks."""

from __future__ import annotations

from pathlib import Path

from smoke_checks.common import SCRIPTS_DIR, SKILL_DIR, SmokeCheck


def build_checks(tmp_dir: Path, python: str) -> list[SmokeCheck]:
    initialized_project_dir = tmp_dir / "initialized-project"
    initialized_project = initialized_project_dir / "project.yaml"

    return [
        {
            "name": "project_template_audit",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(SKILL_DIR / "assets" / "project.example.yaml"),
                "--allow-missing-inputs",
            ],
        },
        {
            "name": "init_project_fixture",
            "command": [
                python,
                str(SCRIPTS_DIR / "init_project.py"),
                str(initialized_project_dir),
                "--title",
                "Initialized Fixture",
                "--chinese-title",
                "初始化样例",
            ],
        },
        {
            "name": "audit_initialized_project",
            "command": [
                python,
                str(SCRIPTS_DIR / "audit.py"),
                str(initialized_project),
                "--allow-missing-inputs",
            ],
        },
        {
            "name": "init_project_signal_lifecycle",
            "command": [
                python,
                "-c",
                (
                    "import json, pathlib, sys; "
                    f"path=pathlib.Path({str(initialized_project_dir)!r}) / "
                    "'work' / 'signal' / 'signal_lifecycle.json'; "
                    "payload=json.loads(path.read_text(encoding='utf-8')); "
                    "bad=(payload.get('records') != [] or "
                    "payload.get('status_values') != ['open', 'reviewed', 'ignored']); "
                    "sys.exit(1 if bad else 0)"
                ),
            ],
        },
        {
            "name": "init_project_reader_notes",
            "command": [
                python,
                "-c",
                (
                    "import pathlib, sys; "
                    f"path=pathlib.Path({str(initialized_project_dir)!r}) / "
                    "'references' / 'reader_notes.md'; "
                    "text=path.read_text(encoding='utf-8'); "
                    "required=['# 阅读说明', '__下划线__用于人物、地点、片名等专名', "
                    "'对应原剧本显示页码；场号保留原剧本边栏编号。', "
                    "'未提供参考字幕，译文仅依据剧本正文生成。']; "
                    "forbidden=['本预览保留源剧本', '## 格式约定', "
                    "'| English | Chinese | Notes |', '## 本剧本出现的专业术语', "
                    "'**行尾星号（*）**', '**INT. / EXT.**', "
                    "'**V.O. / O.S. / O.C.**', \"**CONT'D / MORE**\", "
                    "'**CUT TO / BACK TO**', '**SUPER**', "
                    "'已参考双语字幕', '本版是中文剧本学习版', '## 对白标识']; "
                    "bad=[item for item in required if item not in text]; "
                    "bad += [item for item in forbidden if item in text]; "
                    "sys.exit(1 if bad else 0)"
                ),
            ],
        },
    ]
