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
TF_RE = re.compile(rb"/(?P<font>[^\s/]+)\s+(?P<size>-?\d+(?:\.\d+)?)\s+Tf")
TD_RE = re.compile(rb"(?P<tx>-?\d+(?:\.\d+)?)\s+(?P<ty>-?\d+(?:\.\d+)?)\s+T[dD]")
TJ_RE = re.compile(rb"\((?P<text>(?:\\.|[^\\)])*)\)\s*Tj", re.S)
ARRAY_TJ_RE = re.compile(rb"\[(?P<items>.*?)\]\s*TJ", re.S)
ARRAY_TJ_STRING_RE = re.compile(rb"\((?P<text>(?:\\.|[^\\)])*)\)", re.S)
TEXT_TOKEN_RE = re.compile(
    rb"(?:-?\d+(?:\.\d+)?\s+){6}Tm|"
    rb"/[^\s/]+\s+-?\d+(?:\.\d+)?\s+Tf|"
    rb"-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?\s+T[dD]|"
    rb"\((?:\\.|[^\\)])*\)\s*Tj|"
    rb"\[(?:\\.|[^\]])*\]\s*TJ",
    re.S,
)


@dataclass
class ScanResult:
    known_markers: list[dict[str, Any]]
    unclassified_signals: list[dict[str, Any]]
    noise_candidates: list[dict[str, Any]]
    assumptions: dict[str, Any]
    stats: dict[str, int]

    @property
    def markers(self) -> list[dict[str, Any]]:
        return self.known_markers


def iter_text_ops(data: bytes) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    for block in TEXT_BLOCK_RE.finditer(data):
        body = block.group("body")
        matrix: re.Match[bytes] | None = None
        matrix_values: dict[str, float] | None = None
        font_resource: str | None = None
        font_size: float | None = None
        for token in TEXT_TOKEN_RE.finditer(body):
            value = token.group(0)
            tm_match = TM_RE.fullmatch(value)
            if tm_match is not None:
                matrix = tm_match
                matrix_values = {
                    "a": float(tm_match.group("a")),
                    "d": float(tm_match.group("d")),
                    "x": float(tm_match.group("x")),
                    "y": float(tm_match.group("y")),
                }
                continue
            tf_match = TF_RE.fullmatch(value)
            if tf_match is not None:
                font_resource = tf_match.group("font").decode(
                    "latin1", errors="replace"
                )
                font_size = float(tf_match.group("size"))
                continue
            td_match = TD_RE.fullmatch(value)
            if td_match is not None and matrix_values is not None:
                matrix_values["x"] += float(td_match.group("tx")) * matrix_values["a"]
                matrix_values["y"] += float(td_match.group("ty")) * matrix_values["d"]
                continue
            text = text_show_bytes(value)
            if text is None or matrix is None or matrix_values is None:
                continue
            height_raw = block.group("height")
            page_height = (
                float(height_raw) if height_raw is not None else DEFAULT_PAGE_HEIGHT
            )
            y_raw = matrix_values["y"]
            flipped = bool(block.group("prefix")) or matrix_values["d"] < 0
            ops.append(
                {
                    "text": text,
                    "x": matrix_values["x"],
                    "y": page_height - y_raw if flipped else y_raw,
                    "source_layer": "flipped" if flipped else "normal",
                    "font_resource": font_resource,
                    "font_size": font_size,
                }
            )
    return ops


def text_show_bytes(token: bytes) -> bytes | None:
    text_match = TJ_RE.fullmatch(token)
    if text_match is not None:
        return text_match.group("text")
    array_match = ARRAY_TJ_RE.fullmatch(token)
    if array_match is None:
        return None
    return b"".join(
        item.group("text")
        for item in ARRAY_TJ_STRING_RE.finditer(array_match.group("items"))
    )


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


def is_page_object(obj: bytes) -> bool:
    return bool(re.search(rb"/Type\s*/Page\b", obj)) and not bool(
        re.search(rb"/Type\s*/Pages\b", obj)
    )


def is_pages_object(obj: bytes) -> bool:
    return bool(re.search(rb"/Type\s*/Pages\b", obj))


def root_pages_object_id(objects: dict[int, bytes]) -> int | None:
    for obj_id in sorted(objects):
        obj = objects[obj_id]
        if not re.search(rb"/Type\s*/Catalog\b", obj):
            continue
        match = re.search(rb"/Pages\s+(\d+)\s+0\s+R", obj)
        if match:
            return int(match.group(1))
    return None


def kids_object_ids(obj: bytes) -> list[int]:
    array = re.search(rb"/Kids\s*\[(.*?)\]", obj, re.S)
    if array is None:
        return []
    return [
        int(match.group(1)) for match in re.finditer(rb"(\d+)\s+0\s+R", array.group(1))
    ]


def walk_page_tree(
    objects: dict[int, bytes], obj_id: int, visited: set[int]
) -> list[int]:
    if obj_id in visited:
        return []
    visited.add(obj_id)
    obj = objects.get(obj_id, b"")
    if is_page_object(obj):
        return [obj_id]
    if not is_pages_object(obj):
        return []
    page_ids: list[int] = []
    for kid_id in kids_object_ids(obj):
        page_ids.extend(walk_page_tree(objects, kid_id, visited))
    return page_ids


def page_object_ids(objects: dict[int, bytes]) -> list[int]:
    root_id = root_pages_object_id(objects)
    if root_id is not None:
        page_ids = walk_page_tree(objects, root_id, set())
        if page_ids:
            return page_ids
    return [obj_id for obj_id in sorted(objects) if is_page_object(objects[obj_id])]


def pdf_page_count(objects: dict[int, bytes]) -> int:
    return len(page_object_ids(objects))


def stream_length(objects: dict[int, bytes], obj: bytes) -> int | None:
    indirect = re.search(rb"/Length\s+(\d+)\s+0\s+R", obj)
    if indirect is not None:
        length_obj = objects.get(int(indirect.group(1)), b"").strip()
        if length_obj.isdigit():
            return int(length_obj)
    direct = re.search(rb"/Length\s+(\d+)\b", obj)
    return int(direct.group(1)) if direct is not None else None


def strip_stream_delimiter(data: bytes) -> bytes:
    if data.endswith(b"\r\n"):
        return data[:-2]
    if data.endswith((b"\r", b"\n")):
        return data[:-1]
    return data


def raw_content_stream(
    objects: dict[int, bytes], content_id: int
) -> tuple[bytes, bool]:
    obj = objects.get(content_id, b"")
    stream = re.search(rb"\bstream(?:\r\n|\n|\r)", obj)
    if stream is None:
        return b"", False
    start = stream.end()
    length = stream_length(objects, obj)
    if length is not None and start + length <= len(obj):
        return obj[start : start + length], True

    end = obj.find(b"endstream", start)
    if end < 0:
        return b"", False
    return strip_stream_delimiter(obj[start:end]), False


def content_stream(objects: dict[int, bytes], content_id: int) -> bytes:
    obj = objects.get(content_id, b"")
    data, _exact_length = raw_content_stream(objects, content_id)
    if b"/FlateDecode" in obj:
        try:
            return zlib.decompress(data)
        except zlib.error:
            stripped = strip_stream_delimiter(data)
            if stripped != data:
                try:
                    return zlib.decompress(stripped)
                except zlib.error:
                    return b""
            return b""
    return data


def page_content_ids(objects: dict[int, bytes]) -> list[tuple[int, int, int]]:
    pages: list[tuple[int, int, int]] = []
    for page_number, obj_id in enumerate(page_object_ids(objects), start=1):
        obj = objects[obj_id]
        match = re.search(rb"/Contents\s+(\d+)\s+0\s+R", obj)
        if match:
            pages.append((page_number, obj_id, int(match.group(1))))
            continue
        array = re.search(rb"/Contents\s*\[(.*?)\]", obj, re.S)
        if array:
            for item in re.finditer(rb"(\d+)\s+0\s+R", array.group(1)):
                pages.append((page_number, obj_id, int(item.group(1))))
    return pages


def font_resource_object_ids(obj: bytes) -> dict[str, int]:
    fonts = re.search(rb"/Font\s*<<(.*?)>>", obj, re.S)
    if fonts is None:
        return {}
    return {
        match.group("resource").decode("latin1", errors="replace"): int(
            match.group("object_id")
        )
        for match in re.finditer(
            rb"/(?P<resource>[^\s/]+)\s+(?P<object_id>\d+)\s+0\s+R",
            fonts.group(1),
        )
    }


def font_names_for_object(
    objects: dict[int, bytes], obj_id: int, visited: set[int] | None = None
) -> list[str]:
    if visited is None:
        visited = set()
    if obj_id in visited:
        return []
    visited.add(obj_id)
    obj = objects.get(obj_id, b"")
    names = [
        match.group("name").decode("latin1", errors="replace")
        for match in re.finditer(
            rb"/(?:BaseFont|FontName)\s*/(?P<name>[^\s<>\[\]()]+)", obj
        )
    ]
    for descendant in re.finditer(rb"/DescendantFonts\s*\[(.*?)\]", obj, re.S):
        for ref in re.finditer(rb"(\d+)\s+0\s+R", descendant.group(1)):
            names.extend(font_names_for_object(objects, int(ref.group(1)), visited))
    return names


def style_tags_for_font_name(font_name: str) -> set[str]:
    normalized = font_name.split("+", 1)[-1].lower()
    styles: set[str] = set()
    if re.search(r"bold|black|heavy|demibold|semi[-_]?bold|extra[-_]?bold", normalized):
        styles.add("bold")
    if re.search(r"italic|oblique|slanted", normalized):
        styles.add("italic")
    return styles


def page_font_styles(
    objects: dict[int, bytes], page_obj_id: int
) -> dict[str, set[str]]:
    resources = font_resource_object_ids(objects.get(page_obj_id, b""))
    styles: dict[str, set[str]] = {}
    for resource, font_obj_id in resources.items():
        font_styles: set[str] = set()
        for font_name in font_names_for_object(objects, font_obj_id):
            font_styles.update(style_tags_for_font_name(font_name))
        if font_styles:
            styles[resource] = font_styles
    return styles


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


def has_structural_shape(text: str) -> bool:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned or len(cleaned) > 80:
        return False
    if re.fullmatch(r"[A-Z0-9][A-Z0-9 ./_'()-]*", cleaned):
        return True
    return bool(re.search(r"\b[A-Z][A-Z0-9./'-]{1,}\b", cleaned))


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
        "signal": marker.get("signal", "unclassified"),
        "pdf_page": marker.get("pdf_page"),
        "display_page": marker.get("display_page"),
        "type": marker.get("type"),
        "text": marker.get("text"),
        "position": marker.get("position"),
        "x": marker.get("x"),
        "y": marker.get("y"),
    }


def raw_signal(
    kind: str,
    page_number: int,
    displayed_page_offset: int,
    text: str,
    op: dict[str, Any],
) -> dict[str, Any]:
    return {
        "signal": kind,
        "pdf_page": page_number,
        "display_page": page_number + displayed_page_offset,
        "text": text,
        "source_layer": str(op["source_layer"]),
        "x": round(float(op["x"]), 3),
        "y": round(float(op["y"]), 3),
    }


def scan_pdf_detailed(pdf_path: Path, displayed_page_offset: int) -> ScanResult:
    objects = pdf_objects(pdf_path)
    markers: list[dict[str, Any]] = []
    unclassified_signals: list[dict[str, Any]] = []
    noise_candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str, int, int]] = set()
    text_ops = 0
    scene_candidates = 0
    unclassified_seen = 0
    noise_seen = 0
    pages = page_content_ids(objects)
    pages_with_content: set[int] = set()
    for page_number, _page_obj, content_id in pages:
        pages_with_content.add(page_number)
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
                    if has_structural_shape(text):
                        unclassified_seen += 1
                        if len(unclassified_signals) < 50:
                            unclassified_signals.append(
                                raw_signal(
                                    "unclassified",
                                    page_number,
                                    displayed_page_offset,
                                    text,
                                    op,
                                )
                            )
                    elif (
                        x < SCENE_MARGIN_WIDTH
                        or x > DEFAULT_PAGE_WIDTH - SCENE_MARGIN_WIDTH
                    ):
                        noise_seen += 1
                        if len(noise_candidates) < 50:
                            noise_candidates.append(
                                raw_signal(
                                    "low_confidence_margin_text",
                                    page_number,
                                    displayed_page_offset,
                                    text,
                                    op,
                                )
                            )
                    continue
                position = scene_marker_position(scene_kind, x)
                if position is None:
                    noise_seen += 1
                    if len(noise_candidates) < 50:
                        noise_candidates.append(
                            raw_signal(
                                "scene_label_outside_margin",
                                page_number,
                                displayed_page_offset,
                                text,
                                op,
                            )
                        )
                    continue
                kind = scene_kind
                scene_candidates += 1
            y = float(op["y"])
            key = (kind, page_number, text, round(x), round(y))
            if key in seen:
                continue
            seen.add(key)
            marker: dict[str, Any] = {
                "type": kind,
                "pdf_page": page_number,
                "display_page": page_number + displayed_page_offset,
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
    unclassified_signals.extend(compact_candidate(marker) for marker in unmatched[:50])
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
        "pdf_pages_total": pdf_page_count(objects),
        "pdf_pages_with_content": len(pages_with_content),
        "pdf_objects": len(objects),
        "text_ops_seen": text_ops,
        "scene_candidates": scene_candidates,
        "known_markers": len(kept),
        "unclassified_signals": len(unmatched) + unclassified_seen,
        "noise_candidates": noise_seen,
    }
    return ScanResult(
        known_markers=kept,
        unclassified_signals=unclassified_signals,
        noise_candidates=noise_candidates,
        assumptions=assumptions,
        stats=stats,
    )


def scan_pdf(pdf_path: Path, displayed_page_offset: int) -> list[dict[str, Any]]:
    return scan_pdf_detailed(pdf_path, displayed_page_offset).known_markers


def write_inventory(
    project_file: Path,
    config: dict[str, Any],
    markers: list[dict[str, Any]],
    scan: ScanResult | None = None,
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
        "known_markers": markers,
        "unclassified_signals": scan.unclassified_signals if scan is not None else [],
        "noise_candidates": scan.noise_candidates if scan is not None else [],
        "markers": markers,
    }
    if scan is not None:
        payload["structural_signal"] = {
            "known_markers": scan.known_markers,
            "unclassified_signals": scan.unclassified_signals,
        }
        payload["warning_signal"] = scan.unclassified_signals
        payload["noise_signal"] = scan.noise_candidates
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
    scan = scan_pdf_detailed(pdf_path, offset)
    markers = scan.known_markers
    out_path = write_inventory(project_file, config, markers, scan)
    counts: dict[str, int] = {}
    for marker in markers:
        counts[marker["type"]] = counts.get(marker["type"], 0) + 1
    print(f"INFO marker_inventory {out_path}")
    for kind in sorted(counts):
        print(f"INFO marker_count {kind}={counts[kind]}")
    print(f"INFO signal_count structural={len(scan.known_markers)}")
    print(f"INFO signal_count warning={len(scan.unclassified_signals)}")
    print(f"INFO signal_count noise={len(scan.noise_candidates)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
