#!/usr/bin/env python3
"""Собирает visual review assets из generated character sprite sheet.

Скрипт принимает chroma-key sheet, режет его на равные ячейки,
триммит фон внутри ячеек и собирает contact/silhouette/GIF для ревью.
Это не scale gate: нормализация здесь может скрыть разные исходные bbox.
Перед ним обязательно запускать audit_walk_sheet.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from core.chroma import KEY_RGB as GREEN, clean_key, is_key_pixel

PREVIEW_BG = (18, 20, 25)
PANEL_BG = (24, 27, 34)
LABEL = (224, 216, 184)
SUBTLE = (128, 135, 140)
SILHOUETTE = (5, 6, 8, 255)


def trim_key(frame: Image.Image, pad: int) -> Image.Image:
    rgba = frame.convert("RGBA")
    pixels = rgba.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(rgba.height):
        for x in range(rgba.width):
            if not is_key_pixel(pixels[x, y]):
                xs.append(x)
                ys.append(y)
    if not xs:
        return rgba
    box = (
        max(min(xs) - pad, 0),
        max(min(ys) - pad, 0),
        min(max(xs) + pad + 1, rgba.width),
        min(max(ys) + pad + 1, rgba.height),
    )
    return rgba.crop(box)


def normalize(frame: Image.Image, width: int, height: int) -> Image.Image:
    scale = min(width / frame.width, height / frame.height)
    resized = frame.resize((max(1, int(frame.width * scale)), max(1, int(frame.height * scale))), Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (width, height), GREEN + (255,))
    canvas.alpha_composite(resized, ((width - resized.width) // 2, (height - resized.height) // 2))
    return canvas


def make_silhouette(frame: Image.Image) -> Image.Image:
    rgba = frame.convert("RGBA")
    out = Image.new("RGBA", rgba.size, GREEN + (255,))
    src = rgba.load()
    dst = out.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            if not is_key_pixel(src[x, y]):
                dst[x, y] = SILHOUETTE
    return out


def cell_with_panel(frame: Image.Image, panel_width: int, panel_height: int) -> Image.Image:
    out = Image.new("RGBA", (panel_width, panel_height), PANEL_BG + (255,))
    rgba = clean_key(frame)
    out.alpha_composite(rgba, ((panel_width - rgba.width) // 2, (panel_height - rgba.height) // 2))
    return out


def make_contact(frames: list[list[Image.Image]], rows: list[str], prefix: str, silhouette: bool) -> Image.Image:
    font = ImageFont.load_default()
    pad = 14
    gap = 10
    label_w = 58
    panel_w = frames[0][0].width
    panel_h = frames[0][0].height
    width = pad * 2 + label_w + len(frames[0]) * panel_w + (len(frames[0]) - 1) * gap
    height = pad * 2 + 20 + len(rows) * panel_h + (len(rows) - 1) * gap
    out = Image.new("RGBA", (width, height), PREVIEW_BG + (255,))
    draw = ImageDraw.Draw(out)
    title = f"{prefix} / silhouette" if silhouette else f"{prefix} / contact"
    draw.text((pad, 6), title, fill=LABEL, font=font)
    for row_index, row_name in enumerate(rows):
        y = pad + 20 + row_index * (panel_h + gap)
        draw.text((pad, y + 8), row_name, fill=LABEL, font=font)
        for col_index, frame in enumerate(frames[row_index]):
            img = make_silhouette(frame) if silhouette else frame
            panel = cell_with_panel(img, panel_w, panel_h)
            x = pad + label_w + col_index * (panel_w + gap)
            out.alpha_composite(panel, (x, y))
    return out


def make_walk_strip(frames: list[list[Image.Image]]) -> Image.Image:
    panel_w = frames[0][0].width
    panel_h = frames[0][0].height
    out = Image.new("RGB", (len(frames[0]) * panel_w, len(frames) * panel_h), GREEN)
    for row_index, row in enumerate(frames):
        for col_index, frame in enumerate(row):
            out.paste(frame.convert("RGB"), (col_index * panel_w, row_index * panel_h))
    return out


def make_direction_gif(row_frames: list[Image.Image], path: Path, duration: int) -> None:
    rgb_frames = [frame.convert("RGB") for frame in row_frames]
    atlas = Image.new("RGB", (rgb_frames[0].width, rgb_frames[0].height * len(rgb_frames)), GREEN)
    for index, frame in enumerate(rgb_frames):
        atlas.paste(frame, (0, index * frame.height))
    palette = atlas.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    gif_frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in rgb_frames]
    gif_frames[0].save(path, save_all=True, append_images=gif_frames[1:], duration=duration, loop=0)


def split_sheet(image: Image.Image, row_names: list[str], cols: int, trim_pad: int, cell_width: int, cell_height: int) -> list[list[Image.Image]]:
    rows = len(row_names)
    src_w, src_h = image.size
    frames: list[list[Image.Image]] = []
    for row in range(rows):
        row_frames: list[Image.Image] = []
        for col in range(cols):
            left = round(col * src_w / cols)
            upper = round(row * src_h / rows)
            right = round((col + 1) * src_w / cols)
            lower = round((row + 1) * src_h / rows)
            raw = image.crop((left, upper, right, lower))
            row_frames.append(normalize(trim_key(raw, trim_pad), cell_width, cell_height))
        frames.append(row_frames)
    return frames


def split_sheet_auto(
    image: Image.Image,
    row_names: list[str],
    cols: int,
    trim_pad: int,
    cell_width: int,
    cell_height: int,
) -> list[list[Image.Image]]:
    # Генератор может дать много отдельных деталей. Режем по ожидаемой сетке,
    # а видимый bbox ищем внутри каждой ячейки, чтобы блики/gear не ломали счёт.
    src_w, src_h = image.size
    frames: list[list[Image.Image]] = []
    for row_index, _row in enumerate(row_names):
        row_frames: list[Image.Image] = []
        for col in range(cols):
            cell_box = (
                round(col * src_w / cols),
                round(row_index * src_h / len(row_names)),
                round((col + 1) * src_w / cols),
                round((row_index + 1) * src_h / len(row_names)),
            )
            raw = image.crop(cell_box)
            row_frames.append(normalize(trim_key(raw, trim_pad), cell_width, cell_height))
        frames.append(row_frames)
    return frames


def main() -> None:
    parser = argparse.ArgumentParser(description="Build visual review pack after audit_walk_sheet.py passes.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--rows", default="down,right,up,left")
    parser.add_argument("--cols", type=int, default=6)
    parser.add_argument("--cell-width", type=int, default=420)
    parser.add_argument("--cell-height", type=int, default=520)
    parser.add_argument("--trim-pad", type=int, default=12)
    parser.add_argument("--frame-ms", type=int, default=110)
    parser.add_argument("--auto-detect", action="store_true")
    args = parser.parse_args()

    row_names = [row.strip() for row in args.rows.split(",") if row.strip()]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    source = Image.open(args.input).convert("RGBA")
    if args.auto_detect:
        frames = split_sheet_auto(source, row_names, args.cols, args.trim_pad, args.cell_width, args.cell_height)
    else:
        frames = split_sheet(source, row_names, args.cols, args.trim_pad, args.cell_width, args.cell_height)

    contact = make_contact(frames, row_names, args.prefix, False)
    silhouette = make_contact(frames, row_names, args.prefix, True)
    strip = make_walk_strip(frames)

    contact_path = args.out_dir / f"{args.prefix}_contact.png"
    silhouette_path = args.out_dir / f"{args.prefix}_silhouette.png"
    strip_path = args.out_dir / f"{args.prefix}_walk_strip.png"
    contact.save(contact_path)
    silhouette.save(silhouette_path)
    strip.save(strip_path)

    for row_name, row_frames in zip(row_names, frames):
        make_direction_gif(row_frames, args.out_dir / f"{args.prefix}_walk_{row_name}.gif", args.frame_ms)
        for index, frame in enumerate(row_frames, 1):
            frame.save(args.out_dir / f"{args.prefix}_{row_name}_frame_{index:02d}.png")

    print(f"contact={contact_path}")
    print(f"silhouette={silhouette_path}")
    print(f"walk_strip={strip_path}")


if __name__ == "__main__":
    main()
