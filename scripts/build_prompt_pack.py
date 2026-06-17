#!/usr/bin/env python3
"""Build deterministic image_gen prompt notes from pose-control metadata."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load_pose_metadata(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "poses" not in data or not isinstance(data["poses"], list):
        raise ValueError("pose metadata must contain a poses list")
    return data


def group_poses(metadata: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for pose in metadata["poses"]:
        if not isinstance(pose, dict):
            continue
        direction = str(pose.get("direction", "")).strip()
        if not direction:
            continue
        grouped[direction].append(pose)
    if not grouped:
        raise ValueError("pose metadata has no direction poses")
    return dict(grouped)


def prompt_for_row(
    direction: str,
    poses: list[dict[str, object]],
    identity: str,
    mass_class: str,
    gait_style: str,
    palette_constraints: str,
    cell_size: list[int],
    target_body_height: object,
) -> str:
    phases = "; ".join(
        f"frame {pose.get('frame')}: {pose.get('phase')} support={pose.get('support_sign')} swing={pose.get('swing_sign')}"
        for pose in poses
    )
    return (
        f"Create a fresh fixed-cell walk/{direction} row for the same approved character. "
        f"Use the identity reference as design guidance: {identity}. "
        f"Mass class: {mass_class}. Gait style: {gait_style}. "
        f"Output {len(poses)} frames in exact {cell_size[0]}x{cell_size[1]} cells on pure chroma green #00ff00. "
        f"Target body height near {target_body_height}px. Full body visible, no cropped helmet, boots, backpack, weapon, or limbs. "
        f"Keep palette stable and preserve these non-key colors: {palette_constraints}. "
        f"Pose phases from the control sheet: {phases}. "
        "Do not mirror asymmetric details unless symmetric=true is explicitly recorded in run_note.yml."
    )


def write_markdown(path: Path, payload: dict[str, object]) -> None:
    lines = [f"# {payload['prefix']} image_gen prompt pack", ""]
    lines.append("Generated from pose-control metadata. Use these prompts row-by-row, not as a vague whole-sheet request.")
    lines.append("")
    for row in payload["rows"]:
        row_data = payload["prompts"][row]
        lines.extend([f"## walk/{row}", "", row_data["prompt"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def build(args: argparse.Namespace) -> dict[str, object]:
    metadata = load_pose_metadata(args.pose_json)
    grouped = group_poses(metadata)
    rows = [row for row in metadata.get("rows", grouped.keys()) if row in grouped]
    if not rows:
        rows = list(grouped.keys())
    cell_size = metadata.get("cell_size", [args.cell_width, args.cell_height])
    if not isinstance(cell_size, list) or len(cell_size) != 2:
        cell_size = [args.cell_width, args.cell_height]
    payload: dict[str, object] = {
        "prefix": args.prefix,
        "pose_json": str(args.pose_json),
        "rows": rows,
        "cell_size": cell_size,
        "target_body_height": metadata.get("target_body_height", args.target_body_height),
        "prompts": {},
    }
    for row in rows:
        payload["prompts"][row] = {
            "frames": len(grouped[row]),
            "prompt": prompt_for_row(
                row,
                grouped[row],
                args.identity,
                args.mass_class,
                args.gait_style,
                args.palette_constraints,
                cell_size,
                payload["target_body_height"],
            ),
        }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic row-level image_gen prompts from pose-control metadata.")
    parser.add_argument("--pose-json", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--identity", default="approved identity reference")
    parser.add_argument("--mass-class", default="medium")
    parser.add_argument("--gait-style", default="balanced walk")
    parser.add_argument("--palette-constraints", default="cyan/teal emissive lights must survive chroma-key cleanup")
    parser.add_argument("--cell-width", type=int, default=96)
    parser.add_argument("--cell-height", type=int, default=96)
    parser.add_argument("--target-body-height", type=int, default=64)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    payload = build(args)
    json_path = args.out_dir / f"{args.prefix}_prompt_pack.json"
    md_path = args.out_dir / f"{args.prefix}_prompt_pack.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, payload)
    print(f"json={json_path}")
    print(f"markdown={md_path}")


if __name__ == "__main__":
    main()
