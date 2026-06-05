#!/usr/bin/env python3
"""Scan source screenplay PDF markers into source-markers.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import audit


SCENE_MARKER_TYPES = {"scene_no", "split_scene"}
SCENE_MARGIN_WIDTH = 96.0
ROMAN_NUMERAL_RE = re.compile(r"[IVXLCDM]+")
DEFAULT_PAGE_WIDTH = 612.0
DEFAULT_PAGE_HEIGHT = 792.0
PAIR_Y_TOLERANCE = 3

TEXT_OP_RE = re.compile(
    rb"(?P<prefix>q\s+1 0 0 -1 0 (?P<height>\d+(?:\.\d+)?)\s+cm\s+)?"
    rb"BT\s+.*?"
    rb"(?P<a>-?\d+(?:\.\d+)?)\s+0\s+0\s+(?P<d>-?\d+(?:\.\d+)?)\s+"
    rb"(?P<x>-?\d+(?:\.\d+)?)\s+(?P<y>-?\d+(?:\.\d+)?)\s+Tm\s+"
    rb"/[^\s]+\s+\d+\s+Tf\s+\((?P<text>.*?)\)\s+Tj\s+ET",
    re.S,
)
TEXT_BLOCK_RE = re.compile(
    rb"(?P<prefix>q\s+1 0 0 -1 0 (?P<height>\d+(?:\.\d+)?)\s+cm\s+)?BT\b(?P<body>.*?)\bET",
    re.S,
)
TM_RE = re.compile(
    rb"(?P<a>-?\d+(?:\.\d+)?)\s+0\s+0\s+(?P<d>-?\d+(?:\.\d+)?)\s+"
    rb"(?P<x>-?\d+(?:\.\d+)?)\s+(?P<y>-?\d+(?:\.\d+)?)\s+Tm"
)
TJ_RE = re.compile(rb"\((?P<text>(?:\\.|[^\\)])*)\)\s+Tj", re.S)


@dataclass
class ScanResult:
    markers: list[dict[str, Any]]
    assumptions: dict[str, Any]
    stats: dict[str, int]
    unmatched_scene_candidates: list[dict[str, Any]]


def iter_text_ops(data: bytes) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    for block in TEXT_BLOCK_RE.finditer(data):
        body = block.group("body")
        matrix: re.Match[bytes] | None = None
        for token in re.finditer(
            rb"(?:-?\d+(?:\.\d+)?\s+){6}Tm|\((?:\\.|[^\\)])*\)\s+Tj", body, re.S
        ):
            value = token.group(0)
            tm_match = TM_RE.fullmatch(value)
            if tm_match is not None:
                matrix = tm_match
                continue
            text_match = TJ_RE.fullmatch(value)
            if text_match is None or matrix is None:
                continue
            d = float(matrix.group("d"))
            height_raw = block.group("height")
            page_height = (
                float(height_raw) if height_raw is not None else DEFAULT_PAGE_HEIGHT
            )
            y_raw = float(matrix.group("y"))
            flipped = bool(block.group("prefix")) or d < 0
            ops.append(
                {
                    "text": text_match.group("text"),
                    "x": float(matrix.group("x")),
                    "y": page_height - y_raw if flipped else y_raw,
                    "source_layer": "flipped" if flipped else "normal",
                }
            )
    return ops


def pdf_unescape(data: bytes) -> str:
    out: list[str] = []
    i = 0
    while i < len(data):
        char = data[i]
        if char != 92:
            out.append(chr(char))
            i += 1
            continue
        i += 1
        if i >= len(data):
            break
        char = data[i]
        escapes = {
            ord("n"): "\n",
            ord("r"): "\r",
            ord("t"): "\t",
            ord("b"): "\b",
            ord("f"): "\f",
            ord("("): "(",
            ord(")"): ")",
            ord("\\"): "\\",
        }
        if char in escapes:
            out.append(escapes[char])
            i += 1
        elif 48 <= char <= 55:
            octal = bytes([char])
            i += 1
            for _ in range(2):
                if i < len(data) and 48 <= data[i] <= 55:
                    octal += bytes([data[i]])
                    i += 1
                else:
                    break
            out.append(chr(int(octal, 8)))
        elif char in (10, 13):
            i += 2 if char == 13 and i + 1 < len(data) and data[i + 1] == 10 else 1
        else:
            out.append(chr(char))
            i += 1
    return "".join(out)


def normalize_pdf_text(text: str) -> str:
    return (
        text.replace("Õ", "'")
        .replace("’", "'")
        .replace("É", "...")
        .replace("Ò", '"')
        .replace("Ó", '"')
        .replace("Ñ", "-")
    )


def pdf_objects(pdf_path: Path) -> dict[int, bytes]:
    blob = pdf_path.read_bytes()
    return {
        int(match.group(1)): match.group(2)
        for match in re.finditer(rb"(\d+)\s+0\s+obj\b(.*?)\bendobj\b", blob, re.S)
    }


def content_stream(objects: dict[int, bytes], content_id: int) -> bytes:
    obj = objects.get(content_id, b"")
    stream = re.search(rb"stream\r?\n(.*?)\r?\nendstream", obj, re.S)
    if not stream:
        return b""
    data = stream.group(1)
    if b"/FlateDecode" in obj:
        try:
            data = zlib.decompress(data)
        except zlib.error:
            return b""
    return data


def page_content_ids(objects: dict[int, bytes]) -> list[tuple[int, int]]:
    pages: list[tuple[int, int]] = []
    for obj_id in sorted(objects):
        obj = objects[obj_id]
        if b"/Type /Page" not in obj or b"/Type /Pages" in obj:
            continue
        match = re.search(rb"/Contents\s+(\d+)\s+0\s+R", obj)
        if match:
            pages.append((obj_id, int(match.group(1))))
    return pages


def marker_type(text: str) -> str | None:
    upper = text.upper().replace("’", "'")
    if "CONT'D" in upper or "CONTINUED" in upper:
        return "contd"
    if upper.strip() in {"(MORE)", "MORE"}:
        return "more"
    if upper.strip() in {"OMITTED", "OMMITTED"}:
        return "omitted"
    if any(token in upper for token in ("V.O.", "O.S.", "O.C.")):
        return "voice_or_position"
    return None


def scene_label_type(text: str) -> str | None:
    label = re.sub(r"\s+", " ", text.upper().strip())
    if not label or len(label) > 24:
        return None
    if label in {"MORE", "(MORE)", "OMITTED", "OMMITTED"}:
        return None
    if not re.search(r"[A-Z0-9]", label):
        return None
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9 ./_-]*", label):
        return None
    if (
        re.fullmatch(r"\d+", label)
        or ROMAN_NUMERAL_RE.fullmatch(label)
        or re.fullmatch(r"[A-Z]", label)
    ):
        return "scene_no"
    if re.search(r"\d", label):
        return "split_scene"
    return None


def canonical_scene_label(text: str) -> str:
    return re.sub(r"[\s._/-]+", "", text.upper())


def scene_marker_position(
    kind: str, x: float, page_width: float = DEFAULT_PAGE_WIDTH
) -> str | None:
    if kind not in SCENE_MARKER_TYPES:
        return None
    if x <= SCENE_MARGIN_WIDTH:
        return "left"
    if x >= page_width - SCENE_MARGIN_WIDTH:
        return "right"
    return None


def scene_pair_key(
    marker: dict[str, Any],
) -> tuple[object, object, object, object, int]:
    y = marker.get("y", 0)
    return (
        marker.get("pdf_page"),
        marker.get("display_page"),
        marker.get("type"),
        marker.get("scene_key")
        or canonical_scene_label(str(marker.get("scene_no") or "")),
        round(float(y) / PAIR_Y_TOLERANCE) * PAIR_Y_TOLERANCE,
    )


def split_paired_scene_markers(
    markers: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    positions_by_key: dict[tuple[object, object, object, object, int], set[str]] = {}
    for marker in markers:
        if marker.get("type") not in SCENE_MARKER_TYPES:
            continue
        position = marker.get("position")
        if isinstance(position, str):
            positions_by_key.setdefault(scene_pair_key(marker), set()).add(position)

    paired_keys = {
        key
        for key, positions in positions_by_key.items()
        if positions == {"left", "right"}
    }
    kept: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    for marker in markers:
        if marker.get("type") not in SCENE_MARKER_TYPES:
            kept.append(marker)
        elif scene_pair_key(marker) in paired_keys:
            kept.append(marker)
        else:
            unmatched.append(marker)
    return kept, unmatched


def compact_candidate(marker: dict[str, Any]) -> dict[str, Any]:
    return {
        "pdf_page": marker.get("pdf_page"),
        "display_page": marker.get("display_page"),
        "type": marker.get("type"),
        "text": marker.get("text"),
        "position": marker.get("position"),
        "x": marker.get("x"),
        "y": marker.get("y"),
    }


def scan_pdf_detailed(pdf_path: Path, displayed_page_offset: int) -> ScanResult:
    objects = pdf_objects(pdf_path)
    markers: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str, int, int]] = set()
    text_ops = 0
    scene_candidates = 0
    pages = page_content_ids(objects)
    for page_index, (_page_obj, content_id) in enumerate(pages, start=1):
        data = content_stream(objects, content_id)
        for op in iter_text_ops(data):
            text_ops += 1
            raw_text = normalize_pdf_text(pdf_unescape(op["text"]))
            text = re.sub(r"\s+", " ", raw_text).strip()
            if not text:
                continue
            kind = marker_type(text)
            x = float(op["x"])
            position = None
            if kind is None:
                scene_kind = scene_label_type(text)
                if scene_kind is None:
                    continue
                position = scene_marker_position(scene_kind, x)
                if position is None:
                    continue
                kind = scene_kind
                scene_candidates += 1
            y = float(op["y"])
            key = (kind, page_index, text, round(x), round(y))
            if key in seen:
                continue
            seen.add(key)
            marker: dict[str, Any] = {
                "type": kind,
                "pdf_page": page_index,
                "display_page": page_index + displayed_page_offset,
                "text": text,
                "source_layer": str(op["source_layer"]),
                "x": round(x, 3),
                "y": round(y, 3),
            }
            if kind in SCENE_MARKER_TYPES:
                marker["scene_no"] = text
                marker["scene_key"] = canonical_scene_label(text)
                marker["position"] = position
            markers.append(marker)
    kept, unmatched = split_paired_scene_markers(markers)
    assumptions = {
        "text_operator": "Tj",
        "page_width_default": DEFAULT_PAGE_WIDTH,
        "page_height_default": DEFAULT_PAGE_HEIGHT,
        "scene_margin_width": SCENE_MARGIN_WIDTH,
        "scene_pairing": "same pdf/display page, type, normalized label, y bucket, left+right",
        "scene_pair_y_tolerance": PAIR_Y_TOLERANCE,
        "displayed_page_offset": displayed_page_offset,
    }
    stats = {
        "pdf_pages_with_content": len(pages),
        "pdf_objects": len(objects),
        "text_ops_seen": text_ops,
        "scene_candidates": scene_candidates,
        "scene_candidates_unmatched": len(unmatched),
        "markers_kept": len(kept),
    }
    return ScanResult(
        markers=kept,
        assumptions=assumptions,
        stats=stats,
        unmatched_scene_candidates=[
            compact_candidate(marker) for marker in unmatched[:10]
        ],
    )


def scan_pdf(pdf_path: Path, displayed_page_offset: int) -> list[dict[str, Any]]:
    return scan_pdf_detailed(pdf_path, displayed_page_offset).markers


def write_inventory(
    project_file: Path, config: dict[str, Any], markers: list[dict[str, Any]]
) -> Path:
    inputs = audit.section(config, "inputs")
    outputs = audit.section(config, "outputs")
    pdf_path = audit.resolve_path(project_file, inputs.get("screenplay_pdf"))
    out_path = audit.resolve_path(
        project_file, outputs.get("marker_inventory") or "work/source-markers.json"
    )
    if out_path is None:
        raise ValueError("marker inventory output path is missing")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "source": {"screenplay_pdf": str(pdf_path) if pdf_path else None},
        "markers": markers,
    }
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan source screenplay PDF markers.")
    parser.add_argument("project", type=Path, help="Path to project.yaml")
    args = parser.parse_args(argv)

    project_file = args.project.expanduser().resolve()
    config = audit.load_simple_yaml(project_file)
    inputs = audit.section(config, "inputs")
    page_mapping = audit.section(config, "page_mapping")
    pdf_path = audit.resolve_path(project_file, inputs.get("screenplay_pdf"))
    if pdf_path is None or not pdf_path.exists():
        print(f"FAIL file.missing screenplay_pdf={pdf_path}", file=sys.stderr)
        return 1
    offset = int(page_mapping.get("displayed_page_offset", 0))
    markers = scan_pdf(pdf_path, offset)
    out_path = write_inventory(project_file, config, markers)
    counts: dict[str, int] = {}
    for marker in markers:
        counts[marker["type"]] = counts.get(marker["type"], 0) + 1
    print(f"INFO marker_inventory {out_path}")
    for kind in sorted(counts):
        print(f"INFO marker_count {kind}={counts[kind]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
