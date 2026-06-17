#!/usr/bin/env python3
"""Собирает runtime/review sheet только из утверждённых кадров."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from core.chroma import clean_key, soften_green_spill

PREVIEW_BG = (18, 24, 32, 255)
PANEL_BG = (24, 31, 40, 255)
TEXT = (226, 232, 220, 255)
SILHOUETTE = (4, 5, 7, 255)


def clean_resample_spill(image: Image.Image) -> Image.Image:
    return soften_green_spill(image)


def visible_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("frame has no visible character pixels")
    return bbox


def load_frames(input_dir: Path, prefix: str, rows: list[str], frames: int) -> dict[tuple[str, int], Image.Image]:
    loaded: dict[tuple[str, int], Image.Image] = {}
    missing: list[Path] = []
    for row in rows:
        for index in range(1, frames + 1):
            path = input_dir / f"{prefix}_{row}_frame_{index:02d}.png"
            if not path.exists():
                missing.append(path)
                continue
            loaded[(row, index - 1)] = clean_key(Image.open(path))
    if missing:
        raise FileNotFoundError("missing approved frames:\n" + "\n".join(str(path) for path in missing))
    return loaded


def crop_with_pad(image: Image.Image, bbox: tuple[int, int, int, int], pad: int) -> Image.Image:
    left, top, right, bottom = bbox
    box = (
        max(0, left - pad),
        max(0, top - pad),
        min(image.width, right + pad),
        min(image.height, bottom + pad),
    )
    return image.crop(box)


def resample_filter(name: str) -> Image.Resampling:
    if name == "nearest":
        return Image.Resampling.NEAREST
    if name == "bicubic":
        return Image.Resampling.BICUBIC
    return Image.Resampling.LANCZOS


def read_player_visual_contract(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    source = path.read_text(encoding="utf-8")
    contract: dict[str, object] = {"source": str(path)}
    frame_match = re.search(r"const\s+FRAME_SIZE\s*:=\s*Vector2i\((\d+),\s*(\d+)\)", source)
    if frame_match:
        contract["frame_width"] = int(frame_match.group(1))
        contract["frame_height"] = int(frame_match.group(2))
    target_match = re.search(r"const\s+TARGET_HEIGHT\s*:=\s*([0-9.]+)", source)
    if target_match:
        contract["target_height"] = float(target_match.group(1))
    return contract


def normalize_frames(
    frames: dict[tuple[str, int], Image.Image],
    rows: list[str],
    frame_count: int,
    frame_size: tuple[int, int],
    trim_pad: int,
    canvas_pad: int,
    resample: str,
    max_output_baseline_drift_ratio: float,
    max_output_baseline_drift_px: int | None,
    max_output_head_drift_ratio: float,
    max_output_head_drift_px: int | None,
) -> tuple[dict[tuple[str, int], Image.Image], dict[str, object]]:
    bboxes = {key: visible_bbox(image) for key, image in frames.items()}
    crop_sizes: dict[tuple[str, int], tuple[int, int]] = {}
    for key, image in frames.items():
        crop = crop_with_pad(image, bboxes[key], trim_pad)
        crop_sizes[key] = crop.size

    max_w = max(size[0] for size in crop_sizes.values())
    max_h = max(size[1] for size in crop_sizes.values())
    frame_w, frame_h = frame_size
    available_w = max(1, frame_w - canvas_pad * 2)
    available_h = max(1, frame_h - canvas_pad * 2)
    scale = min(available_w / max_w, available_h / max_h)
    baseline = frame_h - canvas_pad
    baseline_limit = max_output_baseline_drift_px if max_output_baseline_drift_px is not None else max(1, round(frame_h * max_output_baseline_drift_ratio))
    head_limit = max_output_head_drift_px if max_output_head_drift_px is not None else max(1, round(frame_h * max_output_head_drift_ratio))
    resized: dict[tuple[str, int], Image.Image] = {}
    placements: dict[str, object] = {}
    filt = resample_filter(resample)

    for row in rows:
        row_bottoms: list[int] = []
        row_tops: list[int] = []
        for index in range(frame_count):
            key = (row, index)
            crop = crop_with_pad(frames[key], bboxes[key], trim_pad)
            out_w = max(1, int(round(crop.width * scale)))
            out_h = max(1, int(round(crop.height * scale)))
            scaled = crop.resize((out_w, out_h), filt)
            if resample != "nearest":
                scaled = scaled.filter(ImageFilter.SHARPEN)
            scaled = clean_resample_spill(scaled)
            canvas = Image.new("RGBA", frame_size, (0, 0, 0, 0))
            x = (frame_w - out_w) // 2
            y = baseline - out_h
            canvas.alpha_composite(scaled, (x, y))
            resized[key] = canvas
            out_bbox = visible_bbox(canvas)
            row_tops.append(out_bbox[1])
            row_bottoms.append(out_bbox[3])
            placements[f"{row}_{index + 1:02d}"] = {
                "source_bbox": bboxes[key],
                "source_crop_size": crop.size,
                "output_bbox": out_bbox,
                "placed_xy": (x, y),
            }
        baseline_drift = max(row_bottoms) - min(row_bottoms)
        head_drift = max(row_tops) - min(row_tops)
        if baseline_drift > baseline_limit:
            raise ValueError(f"{row}: unstable output baseline {row_bottoms}, drift {baseline_drift}px > {baseline_limit}px")
        if head_drift > head_limit:
            raise ValueError(f"{row}: unstable head/top height {row_tops}, drift {head_drift}px > {head_limit}px")

    manifest = {
        "frame_size": frame_size,
        "rows": rows,
        "frames": frame_count,
        "global_scale": scale,
        "max_source_crop": (max_w, max_h),
        "baseline": baseline,
        "thresholds": {
            "max_output_baseline_drift_ratio": max_output_baseline_drift_ratio,
            "max_output_baseline_drift": max_output_baseline_drift_px,
            "max_output_head_drift_ratio": max_output_head_drift_ratio,
            "max_output_head_drift": max_output_head_drift_px,
            "baseline_limit": baseline_limit,
            "head_limit": head_limit,
        },
        "placements": placements,
    }
    return resized, manifest


def make_sheet(frames: dict[tuple[str, int], Image.Image], rows: list[str], frame_count: int, frame_size: tuple[int, int]) -> Image.Image:
    frame_w, frame_h = frame_size
    sheet = Image.new("RGBA", (frame_w * frame_count, frame_h * len(rows)), (0, 0, 0, 0))
    for row_index, row in enumerate(rows):
        for frame in range(frame_count):
            sheet.alpha_composite(frames[(row, frame)], (frame * frame_w, row_index * frame_h))
    return sheet


def make_contact(frames: dict[tuple[str, int], Image.Image], rows: list[str], frame_count: int, frame_size: tuple[int, int], scale: int, silhouette: bool) -> Image.Image:
    frame_w, frame_h = frame_size
    label_h = 18
    out = Image.new("RGBA", (frame_w * frame_count * scale, len(rows) * (frame_h * scale + label_h)), PREVIEW_BG)
    draw = ImageDraw.Draw(out)
    for row_index, row in enumerate(rows):
        y = row_index * (frame_h * scale + label_h)
        draw.text((6, y + 3), row, fill=TEXT)
        for frame in range(frame_count):
            cell = frames[(row, frame)]
            if silhouette:
                cell = silhouette_frame(cell)
            panel = Image.new("RGBA", frame_size, PANEL_BG)
            panel.alpha_composite(cell)
            out.alpha_composite(panel.resize((frame_w * scale, frame_h * scale), Image.Resampling.NEAREST), (frame * frame_w * scale, y + label_h))
    return out


def silhouette_frame(image: Image.Image) -> Image.Image:
    out = Image.new("RGBA", image.size, (0, 0, 0, 0))
    alpha = image.getchannel("A")
    dst = out.load()
    for y in range(image.height):
        for x in range(image.width):
            if alpha.getpixel((x, y)) > 0:
                dst[x, y] = SILHOUETTE
    return out


def make_gif(frames: dict[tuple[str, int], Image.Image], rows: list[str], frame_count: int, frame_size: tuple[int, int], path: Path, scale: int, duration: int) -> None:
    sequence: list[Image.Image] = []
    for row in rows:
        for frame in range(frame_count):
            panel = Image.new("RGBA", frame_size, PANEL_BG)
            panel.alpha_composite(frames[(row, frame)])
            sequence.append(panel.resize((frame_size[0] * scale, frame_size[1] * scale), Image.Resampling.NEAREST).convert("RGB"))
    atlas = Image.new("RGB", (sequence[0].width, sequence[0].height * len(sequence)), PREVIEW_BG[:3])
    for index, frame in enumerate(sequence):
        atlas.paste(frame, (0, index * frame.height))
    palette = atlas.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    gif_frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in sequence]
    gif_frames[0].save(path, save_all=True, append_images=gif_frames[1:], duration=duration, loop=0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pack approved character frames without redrawing them.")
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--rows", default="down,right,up,left")
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--runtime-gd", type=Path, default=Path("scripts/entities/player_visual.gd"))
    parser.add_argument("--frame-width", type=int, default=None)
    parser.add_argument("--frame-height", type=int, default=None)
    parser.add_argument("--trim-pad", type=int, default=8)
    parser.add_argument("--canvas-pad", type=int, default=6)
    parser.add_argument("--preview-scale", type=int, default=3)
    parser.add_argument("--frame-ms", type=int, default=95)
    parser.add_argument("--resample", choices=["nearest", "lanczos", "bicubic"], default="nearest")
    parser.add_argument("--max-output-baseline-drift-ratio", type=float, default=0.04)
    parser.add_argument("--max-output-baseline-drift", type=int, default=None)
    parser.add_argument("--max-output-head-drift-ratio", type=float, default=0.12)
    parser.add_argument("--max-output-head-drift", type=int, default=None)
    args = parser.parse_args()

    rows = [row.strip() for row in args.rows.split(",") if row.strip()]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    runtime_contract = read_player_visual_contract(args.runtime_gd)
    frame_width = args.frame_width if args.frame_width is not None else runtime_contract.get("frame_width")
    frame_height = args.frame_height if args.frame_height is not None else runtime_contract.get("frame_height")
    if not isinstance(frame_width, int) or not isinstance(frame_height, int):
        raise ValueError("runtime frame size unavailable; pass --frame-width/--frame-height or a valid --runtime-gd")
    frame_size = (frame_width, frame_height)
    source_frames = load_frames(args.input_dir, args.prefix, rows, args.frames)
    normalized, manifest = normalize_frames(
        source_frames,
        rows,
        args.frames,
        frame_size,
        args.trim_pad,
        args.canvas_pad,
        args.resample,
        args.max_output_baseline_drift_ratio,
        args.max_output_baseline_drift,
        args.max_output_head_drift_ratio,
        args.max_output_head_drift,
    )
    manifest["runtime_contract"] = runtime_contract

    sheet = make_sheet(normalized, rows, args.frames, frame_size)
    sheet_path = args.out_dir / f"{args.prefix}_approved_runtime_sheet.png"
    contact_path = args.out_dir / f"{args.prefix}_approved_contact.png"
    silhouette_path = args.out_dir / f"{args.prefix}_approved_silhouette.png"
    gif_path = args.out_dir / f"{args.prefix}_approved_walk.gif"
    manifest_path = args.out_dir / f"{args.prefix}_approved_manifest.json"

    sheet.save(sheet_path)
    make_contact(normalized, rows, args.frames, frame_size, args.preview_scale, False).save(contact_path)
    make_contact(normalized, rows, args.frames, frame_size, args.preview_scale, True).save(silhouette_path)
    make_gif(normalized, rows, args.frames, frame_size, gif_path, args.preview_scale, args.frame_ms)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"sheet={sheet_path}")
    print(f"contact={contact_path}")
    print(f"silhouette={silhouette_path}")
    print(f"gif={gif_path}")
    print(f"manifest={manifest_path}")


if __name__ == "__main__":
    main()
