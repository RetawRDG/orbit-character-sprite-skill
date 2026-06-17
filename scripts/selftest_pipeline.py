#!/usr/bin/env python3
"""End-to-end selftest for the character sprite skill scripts."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROWS = ["down", "right", "up", "left"]
COLS = 6
CELL = (96, 96)
GREEN = (0, 255, 0, 255)
SUIT = (190, 174, 136, 255)
METAL = (61, 77, 88, 255)
VISOR = (210, 142, 28, 255)
TEAL = (39, 222, 224, 255)
BOOT = (39, 42, 48, 255)
OUTLINE = (17, 18, 22, 255)


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def skill_root() -> Path:
    return script_dir().parent


def run_cmd(cmd: list[str], expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=skill_root(), text=True, capture_output=True)
    if result.returncode != expect:
        message = "\n".join(
            [
                f"command failed: {' '.join(cmd)}",
                f"expected={expect} actual={result.returncode}",
                result.stdout,
                result.stderr,
            ]
        )
        raise RuntimeError(message)
    return result


def draw_frame(direction: str, frame: int, bad: bool = False) -> Image.Image:
    image = Image.new("RGBA", CELL, GREEN)
    draw = ImageDraw.Draw(image)
    bob = 1 if frame in {1, 4} else 0
    if bad and direction == "up" and frame == 2:
        bob = 20
    cx = 48
    top = 18 + bob
    bottom = 82 + bob

    # Синтетический good sheet проверяет механику скриптов, не художественный стиль.
    draw.rectangle((cx - 18, top + 20, cx + 18, bottom - 12), fill=OUTLINE)
    draw.rectangle((cx - 15, top + 22, cx + 15, bottom - 14), fill=SUIT)
    draw.ellipse((cx - 18, top, cx + 18, top + 28), fill=OUTLINE)
    draw.ellipse((cx - 15, top + 2, cx + 15, top + 26), fill=SUIT)
    if direction != "up":
        draw.rectangle((cx - 12, top + 12, cx + 12, top + 20), fill=OUTLINE)
        draw.rectangle((cx - 9, top + 14, cx + 9, top + 18), fill=VISOR)
    else:
        draw.rectangle((cx - 13, top + 10, cx + 13, top + 21), fill=METAL)
    draw.rectangle((cx - 8, top + 36, cx + 8, top + 50), fill=METAL)
    draw.rectangle((cx - 2, top + 40, cx + 4, top + 46), fill=TEAL)

    stride = [-5, -2, 1, 5, 2, -1][frame]
    left_x = cx - 10 + stride
    right_x = cx + 4 - stride
    leg_top = bottom - 30
    draw.rectangle((left_x, leg_top, left_x + 8, bottom - 5), fill=OUTLINE)
    draw.rectangle((right_x, leg_top, right_x + 8, bottom - 5), fill=OUTLINE)
    draw.rectangle((left_x - 2, bottom - 6, left_x + 11, bottom), fill=BOOT)
    draw.rectangle((right_x - 2, bottom - 6, right_x + 11, bottom), fill=BOOT)
    return image


def make_sheet(path: Path, bad: bool = False) -> None:
    sheet = Image.new("RGBA", (CELL[0] * COLS, CELL[1] * len(ROWS)), GREEN)
    for row_index, direction in enumerate(ROWS):
        for frame in range(COLS):
            sheet.alpha_composite(draw_frame(direction, frame, bad), (frame * CELL[0], row_index * CELL[1]))
    sheet.save(path)


def export_approved_frames(sheet_path: Path, out_dir: Path, prefix: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(sheet_path).convert("RGBA")
    for row_index, row in enumerate(ROWS):
        for frame in range(COLS):
            cell = sheet.crop((frame * CELL[0], row_index * CELL[1], (frame + 1) * CELL[0], (row_index + 1) * CELL[1]))
            cell.save(out_dir / f"{prefix}_{row}_frame_{frame + 1:02d}.png")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run synthetic good/bad character sprite pipeline selftest.")
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/character_sprite/selftest"))
    args = parser.parse_args()

    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    good_sheet = args.out_dir / "selftest_good_sheet.png"
    bad_sheet = args.out_dir / "selftest_bad_sheet.png"
    make_sheet(good_sheet, bad=False)
    make_sheet(bad_sheet, bad=True)

    py = sys.executable
    scripts = script_dir()
    pose_dir = args.out_dir / "pose"
    audit_dir = args.out_dir / "audit"
    pack_dir = args.out_dir / "pack"
    approved_dir = args.out_dir / "approved"

    run_cmd(
        [
            py,
            str(scripts / "build_pose_control_sheet.py"),
            "--out-dir",
            str(pose_dir),
            "--prefix",
            "selftest",
            "--rows",
            ",".join(ROWS),
        ]
    )
    run_cmd(
        [
            py,
            str(scripts / "audit_walk_sheet.py"),
            "--input",
            str(good_sheet),
            "--out-dir",
            str(audit_dir),
            "--prefix",
            "selftest_good",
            "--rows",
            ",".join(ROWS),
            "--cols",
            str(COLS),
            "--mode",
            "grid",
        ]
    )
    run_cmd(
        [
            py,
            str(scripts / "audit_walk_sheet.py"),
            "--input",
            str(bad_sheet),
            "--out-dir",
            str(audit_dir),
            "--prefix",
            "selftest_bad",
            "--rows",
            ",".join(ROWS),
            "--cols",
            str(COLS),
            "--mode",
            "grid",
        ],
        expect=2,
    )
    export_approved_frames(good_sheet, approved_dir, "selftest_good")
    run_cmd(
        [
            py,
            str(scripts / "pack_approved_walk_sheet.py"),
            "--input-dir",
            str(approved_dir),
            "--out-dir",
            str(pack_dir),
            "--prefix",
            "selftest_good",
            "--rows",
            ",".join(ROWS),
            "--frames",
            str(COLS),
            "--frame-width",
            str(CELL[0]),
            "--frame-height",
            str(CELL[1]),
        ]
    )
    print(f"SELFTEST PASS out={args.out_dir}")


if __name__ == "__main__":
    main()
