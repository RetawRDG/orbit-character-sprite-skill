#!/usr/bin/env python3
"""Validate OrbitSurvive player_visual.gd constants against a runtime manifest or CLI contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_rows(value: str) -> list[str]:
    rows = [part.strip() for part in value.split(",") if part.strip()]
    if not rows:
        raise ValueError("--rows must contain at least one row")
    return rows


def read_string_constants(source: str) -> dict[str, str]:
    return dict(re.findall(r"const\s+([A-Za-z_][A-Za-z0-9_]*)\s*:?=\s*[\"']([^\"']+)[\"']", source))


def extract_braced_const_body(source: str, const_name: str) -> str | None:
    const_match = re.search(rf"const\s+{re.escape(const_name)}\s*:?=", source)
    if not const_match:
        return None
    open_index = source.find("{", const_match.end())
    if open_index == -1:
        return None
    depth = 0
    for index in range(open_index, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[open_index + 1 : index]
    return None


def resolve_row_token(token: str, constants: dict[str, str]) -> str:
    token = token.strip()
    if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
        return token[1:-1]
    return constants.get(token, token)


def read_row_keys(source: str) -> list[str]:
    body = extract_braced_const_body(source, "ROWS")
    if body is None:
        return []

    constants = read_string_constants(source)
    token_pattern = r"(\"[^\"]+\"|'[^']+'|[A-Za-z_][A-Za-z0-9_]*)"
    row_keys: list[str] = []

    for raw_key in re.findall(token_pattern + r"\s*:", body):
        key = resolve_row_token(raw_key, constants)
        if "_" in key:
            row_keys.append(key)

    nested_pattern = re.compile(token_pattern + r"\s*:\s*\{(?P<body>[^{}]*)\}", flags=re.DOTALL)
    for match in nested_pattern.finditer(body):
        state = resolve_row_token(match.group(1), constants)
        inner_body = match.group("body")
        for raw_direction in re.findall(token_pattern + r"\s*:", inner_body):
            direction = resolve_row_token(raw_direction, constants)
            row_keys.append(f"{state}_{direction}")

    return list(dict.fromkeys(row_keys))


def read_runtime_contract(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"runtime script not found: {path}")
    source = path.read_text(encoding="utf-8")
    contract: dict[str, object] = {"source": str(path)}
    frame_match = re.search(r"const\s+FRAME_SIZE\s*:?=\s*Vector2i\((\d+),\s*(\d+)\)", source)
    if frame_match:
        contract["frame_size"] = [int(frame_match.group(1)), int(frame_match.group(2))]
    count_match = re.search(r"const\s+FRAME_COUNT\s*:?=\s*(\d+)", source)
    if count_match:
        contract["frames"] = int(count_match.group(1))
    target_match = re.search(r"const\s+TARGET_HEIGHT\s*:?=\s*([0-9.]+)", source)
    if target_match:
        contract["target_height"] = float(target_match.group(1))
    row_keys = read_row_keys(source)
    if row_keys:
        contract["row_keys"] = row_keys
    return contract


def expected_from_args(args: argparse.Namespace) -> dict[str, object]:
    if args.manifest:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        return {
            "frame_size": list(manifest.get("frame_size", [])),
            "frames": manifest.get("frames"),
            "rows": list(manifest.get("rows", [])),
        }
    return {
        "frame_size": [args.frame_width, args.frame_height],
        "frames": args.frames,
        "rows": parse_rows(args.rows),
    }


def validate(contract: dict[str, object], expected: dict[str, object]) -> dict[str, object]:
    failures: list[str] = []
    warnings: list[str] = []
    if contract.get("frame_size") and contract.get("frame_size") != expected.get("frame_size"):
        failures.append(f"FRAME_SIZE {contract.get('frame_size')} != expected {expected.get('frame_size')}")
    elif not contract.get("frame_size"):
        failures.append("FRAME_SIZE not found in runtime script")

    if contract.get("frames") and contract.get("frames") != expected.get("frames"):
        failures.append(f"FRAME_COUNT {contract.get('frames')} != expected {expected.get('frames')}")
    elif not contract.get("frames"):
        warnings.append("FRAME_COUNT not found in runtime script")

    row_keys = contract.get("row_keys")
    expected_rows = expected.get("rows") or []
    if isinstance(row_keys, list) and expected_rows:
        missing = [f"walk_{row}" for row in expected_rows if f"walk_{row}" not in row_keys]
        if missing:
            failures.append("ROWS missing required walk keys: " + ", ".join(missing))
    elif expected_rows:
        warnings.append("ROWS map not found in runtime script")

    return {
        "status": "pass" if not failures else "fail",
        "runtime_contract": contract,
        "expected": expected,
        "warnings": warnings,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a Godot player_visual.gd runtime sprite contract.")
    parser.add_argument("--runtime-gd", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--rows", default="down,right,up,left")
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--frame-width", type=int, default=96)
    parser.add_argument("--frame-height", type=int, default=96)
    parser.add_argument("--report-json", type=Path, default=None)
    args = parser.parse_args()

    report = validate(read_runtime_contract(args.runtime_gd), expected_from_args(args))
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{report['status'].upper()} runtime_contract runtime={args.runtime_gd}")
    for failure in report["failures"]:
        print(f"- {failure}")
    raise SystemExit(0 if report["status"] == "pass" else 2)


if __name__ == "__main__":
    main()
