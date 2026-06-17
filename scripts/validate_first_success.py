#!/usr/bin/env python3
"""Validate that a generated character has the minimum playable handoff artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageSequence


def parse_rows(value: str) -> list[str]:
    rows = [part.strip() for part in value.split(",") if part.strip()]
    if not rows:
        raise ValueError("--rows must contain at least one row")
    return rows


def require_file(path: Path, failures: list[str]) -> bool:
    if not path.exists():
        failures.append(f"missing file: {path}")
        return False
    if path.is_file() and path.stat().st_size <= 0:
        failures.append(f"empty file: {path}")
        return False
    return True


def load_json(path: Path, failures: list[str]) -> dict[str, object]:
    if not require_file(path, failures):
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exact JSON exception text is implementation detail.
        failures.append(f"invalid json {path}: {exc}")
        return {}


def image_size(path: Path, failures: list[str]) -> tuple[int, int] | None:
    if not require_file(path, failures):
        return None
    try:
        with Image.open(path) as image:
            return image.size
    except Exception as exc:  # pragma: no cover
        failures.append(f"cannot open image {path}: {exc}")
        return None


def gif_frame_count(path: Path, failures: list[str]) -> int | None:
    if not require_file(path, failures):
        return None
    try:
        with Image.open(path) as image:
            return sum(1 for _ in ImageSequence.Iterator(image))
    except Exception as exc:  # pragma: no cover
        failures.append(f"cannot open gif {path}: {exc}")
        return None


def default_path(work_dir: Path, prefix: str, suffix: str) -> Path:
    return work_dir / f"{prefix}{suffix}"


def validate(args: argparse.Namespace) -> tuple[int, dict[str, object]]:
    failures: list[str] = []
    warnings: list[str] = []
    rows = parse_rows(args.rows)
    audit_metrics = args.audit_metrics or default_path(args.work_dir, args.prefix, "_audit_metrics.json")
    runtime_manifest = args.runtime_manifest or default_path(args.work_dir, args.prefix, "_approved_manifest.json")
    runtime_sheet = args.runtime_sheet or default_path(args.work_dir, args.prefix, "_approved_runtime_sheet.png")
    runtime_gif = args.runtime_gif or default_path(args.work_dir, args.prefix, "_approved_walk.gif")

    audit = load_json(audit_metrics, failures)
    if audit:
        if audit.get("status") != "pass":
            failures.append(f"audit status is {audit.get('status')!r}, expected 'pass'")
        if audit.get("rows") != rows:
            failures.append(f"audit rows {audit.get('rows')} != expected {rows}")
        if audit.get("cols") != args.frames:
            failures.append(f"audit cols {audit.get('cols')} != expected frames {args.frames}")
        if audit.get("failures"):
            failures.append("audit failures are present: " + "; ".join(str(item) for item in audit.get("failures", [])))

    manifest = load_json(runtime_manifest, failures)
    frame_size: tuple[int, int] | None = None
    if manifest:
        raw_frame_size = manifest.get("frame_size")
        if isinstance(raw_frame_size, list) and len(raw_frame_size) == 2:
            frame_size = (int(raw_frame_size[0]), int(raw_frame_size[1]))
        if manifest.get("rows") != rows:
            failures.append(f"runtime manifest rows {manifest.get('rows')} != expected {rows}")
        if manifest.get("frames") != args.frames:
            failures.append(f"runtime manifest frames {manifest.get('frames')} != expected {args.frames}")
        runtime_validation = manifest.get("runtime_validation")
        if isinstance(runtime_validation, dict):
            warnings.extend(str(item) for item in runtime_validation.get("warnings", []))

    sheet_size = image_size(runtime_sheet, failures)
    if frame_size and sheet_size:
        expected_size = (frame_size[0] * args.frames, frame_size[1] * len(rows))
        if sheet_size != expected_size:
            failures.append(f"runtime sheet size {sheet_size} != expected {expected_size}")

    frames_in_gif = gif_frame_count(runtime_gif, failures)
    if frames_in_gif is not None:
        expected_gif_frames = args.frames * len(rows)
        if frames_in_gif != expected_gif_frames:
            failures.append(f"runtime gif frames {frames_in_gif} != expected {expected_gif_frames}")

    report = {
        "status": "pass" if not failures else "fail",
        "work_dir": str(args.work_dir),
        "prefix": args.prefix,
        "rows": rows,
        "frames": args.frames,
        "artifacts": {
            "audit_metrics": str(audit_metrics),
            "runtime_manifest": str(runtime_manifest),
            "runtime_sheet": str(runtime_sheet),
            "runtime_gif": str(runtime_gif),
        },
        "warnings": warnings,
        "failures": failures,
    }
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.report_md:
        args.report_md.parent.mkdir(parents=True, exist_ok=True)
        args.report_md.write_text(render_markdown(report), encoding="utf-8")
    return (0 if not failures else 2), report


def render_markdown(report: dict[str, object]) -> str:
    lines = [f"# First success validation: {report['status']}", ""]
    lines.append(f"Work dir: `{report['work_dir']}`")
    lines.append(f"Prefix: `{report['prefix']}`")
    lines.append("")
    lines.append("## Artifacts")
    artifacts = report.get("artifacts", {})
    if isinstance(artifacts, dict):
        for name, path in artifacts.items():
            lines.append(f"- `{name}`: `{path}`")
    lines.append("")
    lines.append("## Warnings")
    warnings = report.get("warnings", [])
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Failures")
    failures = report.get("failures", [])
    if failures:
        for item in failures:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate first-success playable character artifacts.")
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--rows", default="down,right,up,left")
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--audit-metrics", type=Path, default=None)
    parser.add_argument("--runtime-manifest", type=Path, default=None)
    parser.add_argument("--runtime-sheet", type=Path, default=None)
    parser.add_argument("--runtime-gif", type=Path, default=None)
    parser.add_argument("--report-json", type=Path, default=None)
    parser.add_argument("--report-md", type=Path, default=None)
    args = parser.parse_args()

    code, report = validate(args)
    print(f"{report['status'].upper()} first_success")
    for failure in report["failures"]:
        print(f"- {failure}")
    raise SystemExit(code)


if __name__ == "__main__":
    main()
