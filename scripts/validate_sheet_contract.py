#!/usr/bin/env python3
"""Validate fixed-cell sheet dimensions before audit or runtime export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def parse_rows(value: str) -> list[str]:
    rows = [part.strip() for part in value.split(",") if part.strip()]
    if not rows:
        raise ValueError("--rows must contain at least one row")
    return rows


def validate_sheet(path: Path, rows: list[str], cols: int, cell_width: int | None, cell_height: int | None) -> dict[str, object]:
    if cols <= 0:
        raise ValueError("--cols must be positive")
    with Image.open(path) as image:
        width, height = image.size
    failures: list[str] = []
    if width % cols != 0:
        failures.append(f"sheet width {width}px is not divisible by cols={cols}")
    if height % len(rows) != 0:
        failures.append(f"sheet height {height}px is not divisible by rows={len(rows)}")

    actual_cell_width = width // cols if width % cols == 0 else None
    actual_cell_height = height // len(rows) if height % len(rows) == 0 else None
    if cell_width is not None and actual_cell_width != cell_width:
        failures.append(f"cell width {actual_cell_width}px != expected {cell_width}px")
    if cell_height is not None and actual_cell_height != cell_height:
        failures.append(f"cell height {actual_cell_height}px != expected {cell_height}px")

    return {
        "status": "pass" if not failures else "fail",
        "source": str(path),
        "rows": rows,
        "cols": cols,
        "sheet_size": [width, height],
        "cell_size": [actual_cell_width, actual_cell_height],
        "expected_cell_size": [cell_width, cell_height],
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a sprite sheet's exact fixed-cell grid contract.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--rows", default="down,right,up,left")
    parser.add_argument("--cols", type=int, default=6)
    parser.add_argument("--cell-width", type=int, default=None)
    parser.add_argument("--cell-height", type=int, default=None)
    parser.add_argument("--report-json", type=Path, default=None)
    args = parser.parse_args()

    report = validate_sheet(args.input, parse_rows(args.rows), args.cols, args.cell_width, args.cell_height)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{report['status'].upper()} sheet_contract source={args.input}")
    for failure in report["failures"]:
        print(f"- {failure}")
    raise SystemExit(0 if report["status"] == "pass" else 2)


if __name__ == "__main__":
    main()
