#!/usr/bin/env python3
"""Unit tests for relative audit thresholds."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from audit_walk_sheet import FrameMetric, validate  # noqa: E402


def metric(frame: int, cell_h: int, foot_y: int, head_y: int = 10, visible_h: int = 60) -> FrameMetric:
    return FrameMetric(
        row="down",
        frame=frame,
        source_box=(0, 0, 64, cell_h),
        tight_bbox=(16, head_y, 48, foot_y),
        visible_width=32,
        visible_height=visible_h,
        center_x=32.0,
        head_y=head_y,
        foot_y=foot_y,
        touches_edge=False,
    )


class AuditThresholdTests(unittest.TestCase):
    def test_baseline_drift_is_relative_to_cell_height(self) -> None:
        failures_100 = validate(
            ["down"],
            {"down": [metric(1, 100, 80), metric(2, 100, 93)]},
            "down",
            1.0,
            1.0,
            0.12,
            None,
            1.0,
            None,
            2,
        )
        failures_200 = validate(
            ["down"],
            {"down": [metric(1, 200, 160), metric(2, 200, 186)]},
            "down",
            1.0,
            1.0,
            0.12,
            None,
            1.0,
            None,
            2,
        )
        self.assertTrue(any("foot baseline drift" in failure for failure in failures_100))
        self.assertTrue(any("foot baseline drift" in failure for failure in failures_200))

    def test_head_drift_is_relative_to_cell_height(self) -> None:
        failures = validate(
            ["down"],
            {"down": [metric(1, 100, 80, head_y=6), metric(2, 100, 80, head_y=20)]},
            "down",
            1.0,
            1.0,
            1.0,
            None,
            0.12,
            None,
            2,
        )
        self.assertTrue(any("head/top drift" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()

