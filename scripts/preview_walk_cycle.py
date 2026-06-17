#!/usr/bin/env python3
"""Собирает диагностический preview движения персонажа OrbitSurvive.

Скрипт проверяет движение, силуэт, палитру и экспорт. Он не создаёт
кандидатный финальный арт персонажа.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FRAME_W = 64
FRAME_H = 72
STEPS = 6
DIRECTIONS = ("down", "right", "up", "left")

BG = (19, 21, 27, 255)
LABEL = (222, 215, 184, 255)
SHADOW = (0, 0, 0, 96)
OUTLINE = (30, 24, 24, 255)
DEEP = (48, 40, 38, 255)
SUIT_DARK = (82, 69, 60, 255)
SUIT_MID = (132, 112, 88, 255)
SUIT = (178, 154, 118, 255)
SUIT_LIGHT = (224, 204, 158, 255)
SUIT_HI = (255, 239, 190, 255)
METAL = (68, 80, 76, 255)
METAL_DARK = (43, 51, 52, 255)
CYAN_DARK = (14, 83, 95, 255)
CYAN = (39, 222, 224, 255)
CYAN_HI = (188, 255, 255, 255)
BOOT = (39, 39, 46, 255)
BOOT_HI = (66, 66, 76, 255)
RIM = (100, 219, 229, 255)

STRIDES = (-3, -1, 2, 3, 1, -2)
BOBS = (0, -1, -1, 0, -1, -1)
ARM_SWING = (2, 1, -1, -2, -1, 1)


def rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int, int]) -> None:
    draw.rectangle(box, fill=color)


def ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int, int]) -> None:
    draw.ellipse(box, fill=color)


def poly(draw: ImageDraw.ImageDraw, pts: list[tuple[int, int]], color: tuple[int, int, int, int]) -> None:
    draw.polygon(pts, fill=color)


def line(draw: ImageDraw.ImageDraw, pts: list[tuple[int, int]], color: tuple[int, int, int, int], width: int = 1) -> None:
    draw.line(pts, fill=color, width=width)


def draw_shadow(draw: ImageDraw.ImageDraw, y: int = 63, width: int = 34) -> None:
    ellipse(draw, (32 - width // 2, y - 4, 32 + width // 2, y + 3), SHADOW)


def draw_front_legs(draw: ImageDraw.ImageDraw, step: int, bob: int) -> None:
    stride = STRIDES[step]
    left_x = 22 + stride
    right_x = 35 - stride
    rect(draw, (left_x, 45 + bob, left_x + 8, 59 + bob), OUTLINE)
    rect(draw, (right_x, 45 + bob, right_x + 8, 59 + bob), OUTLINE)
    rect(draw, (left_x + 1, 46 + bob, left_x + 6, 58 + bob), SUIT_DARK)
    rect(draw, (right_x + 1, 46 + bob, right_x + 6, 58 + bob), SUIT_DARK)
    rect(draw, (left_x - 2, 58 + bob, left_x + 10, 64 + bob), BOOT)
    rect(draw, (right_x - 2, 58 + bob, right_x + 10, 64 + bob), BOOT)
    rect(draw, (left_x + 1, 58 + bob, left_x + 8, 59 + bob), BOOT_HI)
    rect(draw, (right_x + 1, 58 + bob, right_x + 8, 59 + bob), BOOT_HI)


def draw_front_arms(draw: ImageDraw.ImageDraw, step: int, bob: int) -> None:
    swing = ARM_SWING[step]
    rect(draw, (13, 31 + bob + swing, 21, 49 + bob + swing), OUTLINE)
    rect(draw, (43, 31 + bob - swing, 51, 49 + bob - swing), OUTLINE)
    rect(draw, (15, 32 + bob + swing, 19, 47 + bob + swing), SUIT_DARK)
    rect(draw, (45, 32 + bob - swing, 49, 47 + bob - swing), SUIT_DARK)
    rect(draw, (12, 47 + bob + swing, 20, 53 + bob + swing), DEEP)
    rect(draw, (44, 47 + bob - swing, 52, 53 + bob - swing), DEEP)
    rect(draw, (15, 34 + bob + swing, 16, 43 + bob + swing), SUIT_LIGHT)
    rect(draw, (48, 34 + bob - swing, 49, 43 + bob - swing), SUIT)


def draw_front_body(draw: ImageDraw.ImageDraw, bob: int) -> None:
    poly(draw, [(19, 28 + bob), (45, 28 + bob), (50, 45 + bob), (45, 56 + bob), (19, 56 + bob), (14, 45 + bob)], OUTLINE)
    poly(draw, [(21, 29 + bob), (43, 29 + bob), (47, 44 + bob), (43, 54 + bob), (21, 54 + bob), (17, 44 + bob)], SUIT_MID)
    rect(draw, (24, 34 + bob, 40, 50 + bob), METAL_DARK)
    rect(draw, (27, 36 + bob, 37, 48 + bob), METAL)
    rect(draw, (30, 37 + bob, 34, 47 + bob), CYAN_DARK)
    rect(draw, (20, 29 + bob, 44, 33 + bob), SUIT_LIGHT)
    rect(draw, (18, 42 + bob, 21, 51 + bob), SUIT_DARK)
    rect(draw, (43, 42 + bob, 46, 51 + bob), DEEP)
    rect(draw, (22, 31 + bob, 33, 32 + bob), SUIT_HI)
    rect(draw, (42, 35 + bob, 44, 43 + bob), RIM)


def draw_front_helmet(draw: ImageDraw.ImageDraw, bob: int) -> None:
    ellipse(draw, (16, 4 + bob, 48, 30 + bob), OUTLINE)
    ellipse(draw, (19, 5 + bob, 45, 28 + bob), SUIT_LIGHT)
    rect(draw, (13, 15 + bob, 19, 27 + bob), SUIT_DARK)
    rect(draw, (45, 15 + bob, 51, 27 + bob), SUIT_DARK)
    rect(draw, (19, 8 + bob, 44, 14 + bob), SUIT_HI)
    rect(draw, (21, 17 + bob, 43, 23 + bob), OUTLINE)
    rect(draw, (23, 18 + bob, 41, 22 + bob), CYAN)
    rect(draw, (25, 18 + bob, 33, 19 + bob), CYAN_HI)
    rect(draw, (39, 18 + bob, 41, 22 + bob), CYAN_DARK)
    rect(draw, (18, 25 + bob, 46, 29 + bob), DEEP)


def draw_down(step: int) -> Image.Image:
    img = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bob = BOBS[step]
    draw_shadow(d)
    draw_front_legs(d, step, bob)
    draw_front_arms(d, step, bob)
    draw_front_body(d, bob)
    draw_front_helmet(d, bob)
    return img


def draw_up(step: int) -> Image.Image:
    img = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bob = BOBS[step]
    draw_shadow(d)
    draw_front_legs(d, step, bob)

    swing = ARM_SWING[step]
    rect(d, (12, 31 + bob - swing, 20, 51 + bob - swing), OUTLINE)
    rect(d, (44, 31 + bob + swing, 52, 51 + bob + swing), OUTLINE)
    rect(d, (15, 33 + bob - swing, 18, 49 + bob - swing), SUIT_DARK)
    rect(d, (46, 33 + bob + swing, 49, 49 + bob + swing), SUIT_DARK)

    poly(d, [(18, 27 + bob), (46, 27 + bob), (51, 45 + bob), (45, 56 + bob), (19, 56 + bob), (13, 45 + bob)], OUTLINE)
    poly(d, [(20, 29 + bob), (44, 29 + bob), (47, 44 + bob), (43, 54 + bob), (21, 54 + bob), (17, 44 + bob)], SUIT_DARK)
    rect(d, (23, 31 + bob, 41, 53 + bob), METAL_DARK)
    rect(d, (26, 33 + bob, 38, 51 + bob), METAL)
    rect(d, (29, 36 + bob, 35, 49 + bob), CYAN_DARK)
    rect(d, (20, 29 + bob, 44, 32 + bob), SUIT)
    rect(d, (43, 34 + bob, 46, 48 + bob), RIM)
    line(d, [(24, 33 + bob), (18, 48 + bob)], SUIT_LIGHT, 2)
    line(d, [(40, 33 + bob), (46, 48 + bob)], DEEP, 2)

    ellipse(d, (15, 4 + bob, 49, 31 + bob), OUTLINE)
    ellipse(d, (18, 5 + bob, 46, 29 + bob), SUIT)
    rect(d, (20, 8 + bob, 44, 14 + bob), SUIT_LIGHT)
    rect(d, (22, 10 + bob, 42, 16 + bob), SUIT_HI)
    rect(d, (19, 23 + bob, 45, 29 + bob), DEEP)
    rect(d, (13, 16 + bob, 19, 27 + bob), SUIT_DARK)
    rect(d, (45, 16 + bob, 51, 27 + bob), SUIT_DARK)
    rect(d, (28, 6 + bob, 36, 9 + bob), SUIT_HI)
    return img


def draw_right(step: int) -> Image.Image:
    img = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bob = BOBS[step]
    stride = STRIDES[step]
    swing = ARM_SWING[step]
    draw_shadow(d, width=30)

    rect(d, (18 + stride, 46 + bob, 27 + stride, 61 + bob), OUTLINE)
    rect(d, (31 - stride, 45 + bob, 40 - stride, 61 + bob), OUTLINE)
    rect(d, (20 + stride, 47 + bob, 25 + stride, 59 + bob), SUIT_DARK)
    rect(d, (33 - stride, 46 + bob, 38 - stride, 59 + bob), SUIT_DARK)
    rect(d, (17 + stride, 59 + bob, 31 + stride, 65 + bob), BOOT)
    rect(d, (30 - stride, 59 + bob, 44 - stride, 65 + bob), BOOT)
    rect(d, (20 + stride, 59 + bob, 29 + stride, 60 + bob), BOOT_HI)

    rect(d, (16, 29 + bob, 25, 54 + bob), OUTLINE)
    rect(d, (18, 31 + bob, 23, 52 + bob), SUIT_DARK)
    rect(d, (37, 32 + bob + swing, 49, 46 + bob + swing), OUTLINE)
    rect(d, (39, 34 + bob + swing, 47, 44 + bob + swing), SUIT_MID)
    rect(d, (45, 43 + bob + swing, 51, 49 + bob + swing), DEEP)

    poly(d, [(23, 27 + bob), (43, 29 + bob), (47, 45 + bob), (42, 55 + bob), (22, 54 + bob), (18, 43 + bob)], OUTLINE)
    poly(d, [(25, 29 + bob), (41, 30 + bob), (44, 44 + bob), (40, 53 + bob), (24, 52 + bob), (21, 43 + bob)], SUIT_MID)
    rect(d, (31, 35 + bob, 42, 51 + bob), METAL_DARK)
    rect(d, (34, 37 + bob, 40, 49 + bob), METAL)
    rect(d, (24, 30 + bob, 40, 33 + bob), SUIT_LIGHT)
    rect(d, (41, 34 + bob, 44, 45 + bob), RIM)

    ellipse(d, (17, 5 + bob, 48, 31 + bob), OUTLINE)
    ellipse(d, (20, 6 + bob, 45, 29 + bob), SUIT_LIGHT)
    rect(d, (39, 15 + bob, 54, 23 + bob), OUTLINE)
    rect(d, (41, 16 + bob, 52, 22 + bob), CYAN)
    rect(d, (43, 16 + bob, 48, 17 + bob), CYAN_HI)
    rect(d, (20, 9 + bob, 39, 14 + bob), SUIT_HI)
    rect(d, (16, 16 + bob, 21, 27 + bob), SUIT_DARK)
    rect(d, (45, 23 + bob, 48, 29 + bob), DEEP)
    rect(d, (51, 18 + bob, 54, 21 + bob), CYAN_DARK)
    return img


def mirror(img: Image.Image) -> Image.Image:
    return img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)


def draw_frame(direction: str, step: int) -> Image.Image:
    if direction == "down":
        return draw_down(step)
    if direction == "right":
        return draw_right(step)
    if direction == "up":
        return draw_up(step)
    if direction == "left":
        return mirror(draw_right(step))
    raise ValueError(direction)


def scaled(img: Image.Image, scale: int) -> Image.Image:
    return img.resize((img.width * scale, img.height * scale), Image.Resampling.NEAREST)


def with_bg(img: Image.Image, scale: int) -> Image.Image:
    base = Image.new("RGBA", (img.width * scale, img.height * scale), BG)
    base.alpha_composite(scaled(img, scale))
    return base


def make_sheet(frames: dict[tuple[str, int], Image.Image]) -> Image.Image:
    sheet = Image.new("RGBA", (FRAME_W * STEPS, FRAME_H * len(DIRECTIONS)), (0, 0, 0, 0))
    for row, direction in enumerate(DIRECTIONS):
        for step in range(STEPS):
            sheet.alpha_composite(frames[(direction, step)], (step * FRAME_W, row * FRAME_H))
    return sheet


def make_silhouette(img: Image.Image) -> Image.Image:
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    src = img.load()
    dst = out.load()
    for y in range(img.height):
        for x in range(img.width):
            if src[x, y][3] > 0:
                dst[x, y] = (8, 8, 10, 255)
    return out


def make_contact(frames: dict[tuple[str, int], Image.Image], scale: int, silhouette: bool = False) -> Image.Image:
    label_w = 62
    gap = 10
    pad = 12
    font = ImageFont.load_default()
    cell_w = FRAME_W * scale
    cell_h = FRAME_H * scale
    w = label_w + pad * 2 + STEPS * cell_w + (STEPS - 1) * gap
    h = pad * 2 + len(DIRECTIONS) * cell_h + (len(DIRECTIONS) - 1) * gap
    out = Image.new("RGBA", (w, h), BG)
    d = ImageDraw.Draw(out)
    for row, direction in enumerate(DIRECTIONS):
        y = pad + row * (cell_h + gap)
        d.text((pad, y + 5), direction, fill=LABEL, font=font)
        for step in range(STEPS):
            img = frames[(direction, step)]
            if silhouette:
                img = make_silhouette(img)
            out.alpha_composite(with_bg(img, scale), (label_w + pad + step * (cell_w + gap), y))
    return out


def make_walk_sequence(frames: dict[tuple[str, int], Image.Image], scale: int) -> list[Image.Image]:
    font = ImageFont.load_default()
    sequence: list[Image.Image] = []
    for direction in DIRECTIONS:
        for step in range(STEPS):
            canvas = Image.new("RGBA", (FRAME_W * scale + 110, FRAME_H * scale + 38), BG)
            d = ImageDraw.Draw(canvas)
            d.text((10, 10), f"walk/{direction}", fill=LABEL, font=font)
            canvas.alpha_composite(with_bg(frames[(direction, step)], scale), (55, 30))
            sequence.append(canvas.convert("RGB"))
    return sequence


def make_shared_palette_gif_frames(sequence: list[Image.Image]) -> list[Image.Image]:
    atlas = Image.new("RGB", (sequence[0].width, sequence[0].height * len(sequence)), BG[:3])
    for index, frame in enumerate(sequence):
        atlas.paste(frame, (0, index * frame.height))
    palette_source = atlas.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    return [frame.quantize(palette=palette_source, dither=Image.Dither.NONE) for frame in sequence]


def make_walk_strip(sequence: list[Image.Image]) -> Image.Image:
    columns = STEPS
    rows = len(DIRECTIONS)
    w = sequence[0].width
    h = sequence[0].height
    strip = Image.new("RGB", (columns * w, rows * h), BG[:3])
    for index, frame in enumerate(sequence):
        x = (index % columns) * w
        y = (index // columns) * h
        strip.paste(frame, (x, y))
    return strip


def main() -> None:
    parser = argparse.ArgumentParser(description="Диагностический preview walk-cycle, не генератор финального персонажа.")
    parser.add_argument("--out-dir", default="outputs/character_sprite")
    parser.add_argument("--prefix", default="hero_walk_second_pass")
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--frame-ms", type=int, default=105)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = {(direction, step): draw_frame(direction, step) for direction in DIRECTIONS for step in range(STEPS)}
    sheet = make_sheet(frames)
    contact = make_contact(frames, args.scale, False)
    silhouette = make_contact(frames, args.scale, True)
    walk_sequence = make_walk_sequence(frames, args.scale)
    walk_strip = make_walk_strip(walk_sequence)
    gif_frames = make_shared_palette_gif_frames(walk_sequence)

    sheet_path = out_dir / f"{args.prefix}_sheet.png"
    contact_path = out_dir / f"{args.prefix}_contact.png"
    silhouette_path = out_dir / f"{args.prefix}_silhouette.png"
    strip_path = out_dir / f"{args.prefix}_walk_strip.png"
    gif_path = out_dir / f"{args.prefix}_walk.gif"

    sheet.save(sheet_path)
    contact.save(contact_path)
    silhouette.save(silhouette_path)
    walk_strip.save(strip_path)
    gif_frames[0].save(gif_path, save_all=True, append_images=gif_frames[1:], duration=args.frame_ms, loop=0)

    print(f"sheet={sheet_path}")
    print(f"contact={contact_path}")
    print(f"silhouette={silhouette_path}")
    print(f"walk_strip={strip_path}")
    print(f"gif={gif_path}")


if __name__ == "__main__":
    main()
