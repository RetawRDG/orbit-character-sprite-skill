"""Shared chroma-key detection and cleanup for character sprite tooling."""

from __future__ import annotations

from PIL import Image


KEY_RGB = (0, 255, 0)
KEY_RGBA = (0, 255, 0, 255)


def is_key_pixel(pixel: tuple[int, int, int, int]) -> bool:
    """Return True for transparent pixels or green-screen key/spill pixels.

    Cyan/teal emissive pixels are intentionally preserved: they have blue close
    to green, while chroma-key spill must be green-dominant over both red/blue.
    """

    r, g, b, a = pixel
    if a <= 0:
        return True

    green_dominance = g - max(r, b)
    if g >= 210 and r <= 100 and b <= 100 and green_dominance >= 110:
        return True

    return (
        g >= 145
        and r <= 135
        and b <= 125
        and green_dominance >= 45
        and g >= r * 1.35
        and g >= b * 1.45
    )


def is_green_spill_pixel(pixel: tuple[int, int, int, int]) -> bool:
    """Return True for residual green fringe that should be softened, not cut."""

    r, g, b, a = pixel
    if a <= 0 or is_key_pixel(pixel):
        return False
    return (
        g > 95
        and r < 145
        and b < 145
        and g - max(r, b) > 28
        and g > r * 1.18
        and g > b * 1.22
    )


def clean_key(image: Image.Image) -> Image.Image:
    """Convert chroma-key pixels to transparent alpha."""

    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            if is_key_pixel(pixels[x, y]):
                pixels[x, y] = (0, 0, 0, 0)
    return rgba


def soften_green_spill(image: Image.Image, alpha_loss: int = 80) -> Image.Image:
    """Reduce residual green fringe after resampling while preserving teal lights."""

    rgba = clean_key(image)
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            if is_green_spill_pixel((r, g, b, a)):
                neutral_green = min(g, max(r, b) + 18)
                pixels[x, y] = (r, neutral_green, b, max(0, a - alpha_loss))
    return rgba

