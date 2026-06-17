#!/usr/bin/env python3
"""Unit tests for first-success helper scripts."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from build_prompt_pack import build as build_prompt_pack  # noqa: E402
from validate_first_success import validate as validate_first_success  # noqa: E402
from validate_runtime_contract import read_runtime_contract, validate as validate_runtime_contract  # noqa: E402
from validate_sheet_contract import validate_sheet  # noqa: E402


class FirstSuccessToolTests(unittest.TestCase):
    def test_prompt_pack_uses_pose_metadata_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pose_json = root / "pose.json"
            pose_json.write_text(
                json.dumps(
                    {
                        "cell_size": [96, 96],
                        "target_body_height": 64,
                        "rows": ["down"],
                        "poses": [
                            {"direction": "down", "frame": 1, "phase": "contact-a", "support_sign": -1, "swing_sign": 1},
                            {"direction": "down", "frame": 2, "phase": "down-a", "support_sign": -1, "swing_sign": 1},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            payload = build_prompt_pack(
                argparse.Namespace(
                    pose_json=pose_json,
                    out_dir=root,
                    prefix="hero",
                    identity="approved hero",
                    mass_class="heavy",
                    gait_style="slow stomp",
                    palette_constraints="teal lights",
                    cell_width=96,
                    cell_height=96,
                    target_body_height=64,
                )
            )
        prompt = payload["prompts"]["down"]["prompt"]
        self.assertIn("walk/down", prompt)
        self.assertIn("slow stomp", prompt)
        self.assertIn("frame 1: contact-a", prompt)

    def test_sheet_contract_rejects_uneven_grid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sheet.png"
            Image.new("RGBA", (193, 96), (0, 255, 0, 255)).save(path)
            report = validate_sheet(path, ["down"], 2, 96, 96)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("not divisible" in failure for failure in report["failures"]))

    def test_runtime_contract_reads_walk_rows(self) -> None:
        source = """
const FRAME_SIZE := Vector2i(96, 96)
const FRAME_COUNT := 6
const ROWS := {
  "walk_down": 0,
  "walk_right": 1,
  "walk_up": 2,
  "walk_left": 3,
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "player_visual.gd"
            path.write_text(source, encoding="utf-8")
            contract = read_runtime_contract(path)
        report = validate_runtime_contract(contract, {"frame_size": [96, 96], "frames": 6, "rows": ["down", "right", "up", "left"]})
        self.assertEqual(report["status"], "pass")

    def test_runtime_contract_reads_nested_state_direction_rows(self) -> None:
        source = """
const FRAME_SIZE := Vector2i(96, 96)
const FRAME_COUNT := 6
const STATE_IDLE := "idle"
const STATE_WALK := "walk"
const DIR_DOWN := "down"
const DIR_RIGHT := "right"
const DIR_UP := "up"
const DIR_LEFT := "left"
const ROWS := {
  STATE_IDLE: {DIR_DOWN: 0, DIR_RIGHT: 1, DIR_UP: 2, DIR_LEFT: 3},
  STATE_WALK: {DIR_DOWN: 4, DIR_RIGHT: 5, DIR_UP: 6, DIR_LEFT: 7},
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "player_visual.gd"
            path.write_text(source, encoding="utf-8")
            contract = read_runtime_contract(path)
        report = validate_runtime_contract(contract, {"frame_size": [96, 96], "frames": 6, "rows": ["down", "right", "up", "left"]})
        self.assertEqual(report["status"], "pass")

    def test_first_success_passes_with_matching_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / "audit.json"
            manifest = root / "manifest.json"
            sheet = root / "runtime.png"
            gif = root / "runtime.gif"
            audit.write_text(json.dumps({"status": "pass", "rows": ["down"], "cols": 2, "failures": []}), encoding="utf-8")
            manifest.write_text(json.dumps({"frame_size": [16, 16], "rows": ["down"], "frames": 2}), encoding="utf-8")
            Image.new("RGBA", (32, 16), (0, 0, 0, 0)).save(sheet)
            frames = [Image.new("RGB", (16, 16), (idx * 50, 0, 0)) for idx in range(2)]
            frames[0].save(gif, save_all=True, append_images=frames[1:], duration=80, loop=0)
            code, report = validate_first_success(
                argparse.Namespace(
                    work_dir=root,
                    prefix="hero",
                    rows="down",
                    frames=2,
                    audit_metrics=audit,
                    runtime_manifest=manifest,
                    runtime_sheet=sheet,
                    runtime_gif=gif,
                    report_json=None,
                    report_md=None,
                )
            )
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "pass")


if __name__ == "__main__":
    unittest.main()
