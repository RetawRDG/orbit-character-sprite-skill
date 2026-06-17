#!/usr/bin/env python3
"""Строит fixed-cell pose-control sheet для генерации ходьбы персонажа.

Это технический скелет движения, не кандидатный арт.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BG = (0, 255, 0, 255)
PANEL = (26, 29, 34, 255)
GUIDE = (70, 90, 110, 255)
TEXT = (226, 232, 220, 255)
BODY = (210, 214, 202, 255)
TORSO = (95, 125, 155, 255)
SUPPORT = (255, 210, 86, 255)
SWING = (96, 195, 255, 255)
FOOT = (42, 45, 52, 255)
ARM = (170, 180, 188, 255)


PHASES = [
    {"name": "contact-a", "support": -1, "swing": 1, "bob": 0, "pass": 0.0},
    {"name": "down-a", "support": -1, "swing": 1, "bob": 4, "pass": 0.35},
    {"name": "passing-b", "support": -1, "swing": 1, "bob": -2, "pass": 0.75},
    {"name": "contact-b", "support": 1, "swing": -1, "bob": 0, "pass": 0.0},
    {"name": "down-b", "support": 1, "swing": -1, "bob": 4, "pass": 0.35},
    {"name": "passing-a", "support": 1, "swing": -1, "bob": -2, "pass": 0.75},
]


def parse_rows(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def direction_vectors(direction: str) -> tuple[tuple[float, float], tuple[float, float]]:
    # Основной вектор шага и перпендикуляр для развода ног/рук.
    if direction == "left":
        return (-1.0, 0.0), (0.0, 1.0)
    if direction == "right":
        return (1.0, 0.0), (0.0, 1.0)
    if direction == "up":
        return (0.0, -1.0), (1.0, 0.0)
    return (0.0, 1.0), (1.0, 0.0)


def add_vec(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    return a[0] + b[0], a[1] + b[1]


def mul_vec(a: tuple[float, float], value: float) -> tuple[float, float]:
    return a[0] * value, a[1] * value


def point(origin: tuple[float, float], *vectors: tuple[float, float]) -> tuple[int, int]:
    x, y = origin
    for vx, vy in vectors:
        x += vx
        y += vy
    return int(round(x)), int(round(y))


def draw_ellipse(draw: ImageDraw.ImageDraw, center: tuple[int, int], rx: int, ry: int, fill: tuple[int, int, int, int]) -> None:
    x, y = center
    draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=fill)


def draw_pose(
    cell: Image.Image,
    direction: str,
    frame_index: int,
    baseline_y: int,
    head_top_y: int,
    center_x: int,
    target_body_height: int,
    label: bool,
) -> dict[str, object]:
    draw = ImageDraw.Draw(cell)
    font = ImageFont.load_default()
    forward, side = direction_vectors(direction)
    phase = PHASES[frame_index]
    scale = target_body_height / 120.0

    def sx(value: float) -> int:
        return max(1, int(round(value * scale)))

    def sw(value: float) -> int:
        return max(1, int(round(value * scale)))

    bob = int(round(float(phase["bob"]) * scale))
    pelvis = (float(center_x), float(baseline_y - sx(54) + bob))
    shoulder = (float(center_x), float(baseline_y - sx(90) + bob))
    head_center = (float(center_x), float(head_top_y + sx(18) + bob))

    stride = 22.0 * scale
    side_gap = 9.0 * scale
    support_sign = float(phase["support"])
    swing_sign = float(phase["swing"])
    pass_amount = float(phase["pass"])
    support_foot = point(pelvis, mul_vec(forward, support_sign * stride), mul_vec(side, -support_sign * side_gap), (0, sx(50)))
    swing_forward = swing_sign * stride * (1.0 - pass_amount)
    swing_foot = point(pelvis, mul_vec(forward, swing_forward), mul_vec(side, -swing_sign * side_gap), (0, sx(50 - 8 * pass_amount)))
    support_knee = point(pelvis, mul_vec(forward, support_sign * 9 * scale), mul_vec(side, -support_sign * 4 * scale), (0, sx(22)))
    swing_knee = point(pelvis, mul_vec(forward, swing_forward * 0.4), mul_vec(side, -swing_sign * 4 * scale), (0, sx(20 - 8 * pass_amount)))

    arm_swing = 16.0 * scale
    left_arm = point(shoulder, mul_vec(forward, -support_sign * arm_swing), mul_vec(side, -18 * scale), (0, sx(30)))
    right_arm = point(shoulder, mul_vec(forward, support_sign * arm_swing), mul_vec(side, 18 * scale), (0, sx(30)))
    left_shoulder = point(shoulder, mul_vec(side, -18 * scale))
    right_shoulder = point(shoulder, mul_vec(side, 18 * scale))

    # Направляющие всегда в одинаковой ячейке.
    draw.line((0, baseline_y, cell.width, baseline_y), fill=GUIDE)
    draw.line((0, head_top_y, cell.width, head_top_y), fill=GUIDE)
    draw.line((center_x, 0, center_x, cell.height), fill=GUIDE)
    draw.line((0, int(pelvis[1]), cell.width, int(pelvis[1])), fill=(44, 58, 72, 255))

    torso_box = (
        int(center_x - sx(24)),
        int(shoulder[1] - sx(2)),
        int(center_x + sx(24)),
        int(pelvis[1] + sx(18)),
    )
    draw.rounded_rectangle(torso_box, radius=sx(8), fill=TORSO, outline=BODY)
    draw_ellipse(draw, (int(head_center[0]), int(head_center[1])), sx(24), sx(20), BODY)

    # Рюкзак в back/side читается как отдельная масса, но не является финальным артом.
    if direction in {"up", "left", "right"}:
        pack_offset = point(shoulder, mul_vec(forward, -8 * scale), (0, sx(18)))
        draw.rounded_rectangle(
            (pack_offset[0] - sx(16), pack_offset[1] - sx(18), pack_offset[0] + sx(16), pack_offset[1] + sx(22)),
            radius=sx(5),
            fill=(66, 78, 88, 255),
            outline=BODY,
        )

    for shoulder_pt, hand_pt in ((left_shoulder, left_arm), (right_shoulder, right_arm)):
        draw.line((shoulder_pt, hand_pt), fill=ARM, width=sw(7))
        draw_ellipse(draw, hand_pt, sx(6), sx(6), ARM)

    draw.line(((int(pelvis[0]), int(pelvis[1])), support_knee, support_foot), fill=SUPPORT, width=sw(8))
    draw.line(((int(pelvis[0]), int(pelvis[1])), swing_knee, swing_foot), fill=SWING, width=sw(8))
    draw_ellipse(draw, support_foot, sx(12), sx(5), FOOT)
    draw_ellipse(draw, swing_foot, sx(12), sx(5), FOOT)
    draw_ellipse(draw, support_foot, sx(5), sx(5), SUPPORT)
    draw_ellipse(draw, swing_foot, sx(5), sx(5), SWING)

    if label:
        draw.text((8, 6), f"{frame_index + 1} {phase['name']}", fill=TEXT, font=font)
        draw.text((8, 20), direction, fill=TEXT, font=font)

    return {
        "direction": direction,
        "frame": frame_index + 1,
        "phase": phase["name"],
        "support_sign": phase["support"],
        "swing_sign": phase["swing"],
        "support_foot": support_foot,
        "swing_foot": swing_foot,
        "baseline_y": baseline_y,
        "head_top_y": head_top_y,
        "center_x": center_x,
    }


def make_sheet(rows: list[str], frames: int, cell_size: tuple[int, int], target_body_height: int, label: bool) -> tuple[Image.Image, dict[str, object]]:
    cell_w, cell_h = cell_size
    baseline_y = cell_h - max(8, round(cell_h * 0.12))
    target_body_height = min(target_body_height, baseline_y - 4)
    head_top_y = max(4, baseline_y - target_body_height)
    center_x = cell_w // 2
    sheet = Image.new("RGBA", (cell_w * frames, cell_h * len(rows)), BG)
    metadata: dict[str, object] = {
        "cell_size": [cell_w, cell_h],
        "target_body_height": target_body_height,
        "baseline_y": baseline_y,
        "head_top_y": head_top_y,
        "center_x": center_x,
        "rows": rows,
        "frames": frames,
        "poses": [],
    }

    for row_index, direction in enumerate(rows):
        for frame_index in range(frames):
            cell = Image.new("RGBA", (cell_w, cell_h), PANEL)
            pose = draw_pose(cell, direction, frame_index % len(PHASES), baseline_y, head_top_y, center_x, target_body_height, label)
            sheet.alpha_composite(cell, (frame_index * cell_w, row_index * cell_h))
            metadata["poses"].append(pose)
    return sheet, metadata


def make_direction_gif(sheet: Image.Image, row_index: int, frames: int, cell_size: tuple[int, int], path: Path, duration: int) -> None:
    cell_w, cell_h = cell_size
    sequence: list[Image.Image] = []
    for frame_index in range(frames):
        sequence.append(sheet.crop((frame_index * cell_w, row_index * cell_h, (frame_index + 1) * cell_w, (row_index + 1) * cell_h)).convert("RGB"))
    sequence[0].save(path, save_all=True, append_images=sequence[1:], duration=duration, loop=0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a fixed-cell pose-control sheet for walk-cycle image generation.")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--rows", default="down,left,right,up")
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--cell-width", type=int, default=96)
    parser.add_argument("--cell-height", type=int, default=96)
    parser.add_argument("--target-body-height", type=int, default=64)
    parser.add_argument("--frame-ms", type=int, default=120)
    parser.add_argument("--no-labels", action="store_true")
    args = parser.parse_args()

    rows = parse_rows(args.rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    sheet, metadata = make_sheet(rows, args.frames, (args.cell_width, args.cell_height), args.target_body_height, not args.no_labels)
    sheet_path = args.out_dir / f"{args.prefix}_pose_control_sheet.png"
    metadata_path = args.out_dir / f"{args.prefix}_pose_control.json"
    sheet.save(sheet_path)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    for row_index, row in enumerate(rows):
        make_direction_gif(sheet, row_index, args.frames, (args.cell_width, args.cell_height), args.out_dir / f"{args.prefix}_pose_{row}.gif", args.frame_ms)

    print(f"sheet={sheet_path}")
    print(f"metadata={metadata_path}")


if __name__ == "__main__":
    main()
