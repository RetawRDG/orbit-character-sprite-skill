#!/usr/bin/env python3
"""Unit tests for shared chroma-key detection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from core.chroma import clean_key, is_key_pixel, soften_green_spill  # noqa: E402


class ChromaTests(unittest.TestCase):
    def test_green_key_and_spill_are_removed(self) -> None:
        self.assertTrue(is_key_pixel((0, 255, 0, 255)))
        self.assertTrue(is_key_pixel((60, 180, 60, 255)))
        self.assertTrue(is_key_pixel((0, 0, 0, 0)))

    def test_cyan_teal_lights_are_preserved(self) -> None:
        self.assertFalse(is_key_pixel((39, 222, 224, 255)))
        self.assertFalse(is_key_pixel((0, 180, 180, 255)))
        self.assertFalse(is_key_pixel((20, 150, 170, 255)))

    def test_clean_key_preserves_teal_pixel(self) -> None:
        image = Image.new("RGBA", (3, 1), (0, 0, 0, 0))
        image.putpixel((0, 0), (0, 255, 0, 255))
        image.putpixel((1, 0), (39, 222, 224, 255))
        image.putpixel((2, 0), (80, 150, 80, 255))

        cleaned = clean_key(image)
        self.assertEqual(cleaned.getpixel((0, 0))[3], 0)
        self.assertEqual(cleaned.getpixel((1, 0)), (39, 222, 224, 255))
        self.assertEqual(cleaned.getpixel((2, 0))[3], 0)

    def test_soften_green_spill_does_not_damage_teal(self) -> None:
        image = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
        image.putpixel((0, 0), (39, 222, 224, 255))
        image.putpixel((1, 0), (100, 138, 100, 255))

        cleaned = soften_green_spill(image)
        self.assertEqual(cleaned.getpixel((0, 0)), (39, 222, 224, 255))
        self.assertLess(cleaned.getpixel((1, 0))[3], 255)


if __name__ == "__main__":
    unittest.main()

