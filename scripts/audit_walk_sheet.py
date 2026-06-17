#!/usr/bin/env python3
"""Проверяет generated walk sheet до художественного approval.

Скрипт специально строгий: сначала меряет сырые видимые пиксели
без нормализации, а preview-артефакты строит только после фиксации ошибок.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from PIL import Image, ImageDraw, ImageFont

from core.chroma import KEY_RGBA as GREEN, is_key_pixel

PREVIEW_BG = (18, 20, 25, 255)
PANEL_BG = (24, 27, 34, 255)
TEXT = (232, 230, 216, 255)
FAIL = (255, 92, 92, 255)
GUIDE = (92, 168, 255, 255)
SILHOUETTE = (4, 5, 7, 255)


@dataclass(frozen=True)
class FrameMetric:
    row: str
    frame: int
    source_box: tuple[int, int, int, int]
    tight_bbox: tuple[int, int, int, int]
    visible_width: int
    visible_height: int
    center_x: float
    head_y: int
    foot_y: int
    touches_edge: bool


def visible_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(rgba.height):
        for x in range(rgba.width):
            if not is_key_pixel(pixels[x, y]):
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def crop_with_box(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    return image.crop(box).convert("RGBA")


def split_grid(image: Image.Image, rows: list[str], cols: int) -> list[list[tuple[int, int, int, int]]]:
    boxes: list[list[tuple[int, int, int, int]]] = []
    for row_index, _row in enumerate(rows):
        row_boxes: list[tuple[int, int, int, int]] = []
        for col in range(cols):
            row_boxes.append(
                (
                    round(col * image.width / cols),
                    round(row_index * image.height / len(rows)),
                    round((col + 1) * image.width / cols),
                    round((row_index + 1) * image.height / len(rows)),
                )
            )
        boxes.append(row_boxes)
    return boxes


def split_auto(image: Image.Image, rows: list[str], cols: int, source_pad: int) -> list[list[tuple[int, int, int, int]]]:
    """Find visible bounds inside each grid cell.

    Detailed HD-2D/pixel art often has disconnected highlights and gear bits.
    Cell-local key-mask bounds are safer than global connected-component counts.
    """

    grid = split_grid(image, rows, cols)
    boxes: list[list[tuple[int, int, int, int]]] = []
    for row_index, row_boxes in enumerate(grid):
        out_row: list[tuple[int, int, int, int]] = []
        for col_index, cell_box in enumerate(row_boxes):
            cell = image.crop(cell_box)
            bbox = visible_bbox(cell)
            if bbox is None:
                raise ValueError(f"auto-detect found no visible pixels in row {rows[row_index]} frame {col_index + 1}")
            left, top, right, bottom = bbox
            cell_left, cell_top, _cell_right, _cell_bottom = cell_box
            out_row.append(
                (
                    max(0, cell_left + left - source_pad),
                    max(0, cell_top + top - source_pad),
                    min(image.width, cell_left + right + source_pad),
                    min(image.height, cell_top + bottom + source_pad),
                )
            )
        boxes.append(out_row)
    return boxes


def edge_margins_for(source: Image.Image, edge_margin_px: int | None, edge_margin_ratio: float, vertical_edge_margin_ratio: float) -> tuple[int, int]:
    if edge_margin_px is not None:
        return edge_margin_px, edge_margin_px
    return (
        max(0, round(source.width * edge_margin_ratio)),
        max(0, round(source.height * vertical_edge_margin_ratio)),
    )


def frame_metric(
    image: Image.Image,
    row: str,
    frame: int,
    source_box: tuple[int, int, int, int],
    edge_margin_px: int | None,
    edge_margin_ratio: float,
    vertical_edge_margin_ratio: float,
) -> tuple[FrameMetric, Image.Image]:
    source = crop_with_box(image, source_box)
    bbox = visible_bbox(source)
    if bbox is None:
        raise ValueError(f"{row} frame {frame}: no visible pixels")

    left, top, right, bottom = bbox
    visible = source.crop(bbox)
    edge_margin_x, edge_margin_y = edge_margins_for(source, edge_margin_px, edge_margin_ratio, vertical_edge_margin_ratio)
    touches_edge = (
        left <= edge_margin_x
        or top <= edge_margin_y
        or source.width - right <= edge_margin_x
        or source.height - bottom <= edge_margin_y
    )
    metric = FrameMetric(
        row=row,
        frame=frame,
        source_box=source_box,
        tight_bbox=bbox,
        visible_width=right - left,
        visible_height=bottom - top,
        center_x=(left + right) / 2.0,
        head_y=top,
        foot_y=bottom,
        touches_edge=touches_edge,
    )
    return metric, visible


def row_metrics(metrics: list[FrameMetric]) -> dict[str, object]:
    heights = [metric.visible_height for metric in metrics]
    widths = [metric.visible_width for metric in metrics]
    feet = [metric.foot_y for metric in metrics]
    heads = [metric.head_y for metric in metrics]
    return {
        "frames": len(metrics),
        "avg_height": round(mean(heights), 3),
        "height_range": [min(heights), max(heights)],
        "width_range": [min(widths), max(widths)],
        "foot_y_range": [min(feet), max(feet)],
        "head_y_range": [min(heads), max(heads)],
        "edge_touches": [metric.frame for metric in metrics if metric.touches_edge],
    }


def validate(
    rows: list[str],
    by_row: dict[str, list[FrameMetric]],
    anchor_row: str,
    max_direction_height_drift: float,
    max_frame_height_drift: float,
    max_baseline_drift_ratio: float,
    max_baseline_drift_px: int | None,
    max_head_drift_ratio: float,
    max_head_drift_px: int | None,
    expected_cols: int,
) -> list[str]:
    failures: list[str] = []
    if anchor_row not in by_row:
        failures.append(f"anchor row '{anchor_row}' is missing")
        return failures

    anchor_avg = mean(metric.visible_height for metric in by_row[anchor_row])
    for row in rows:
        metrics = by_row.get(row, [])
        if len(metrics) != expected_cols:
            failures.append(f"{row}: expected {expected_cols} frames, got {len(metrics)}")
            continue

        heights = [metric.visible_height for metric in metrics]
        feet = [metric.foot_y for metric in metrics]
        heads = [metric.head_y for metric in metrics]
        cell_heights = [metric.source_box[3] - metric.source_box[1] for metric in metrics]
        cell_height = mean(cell_heights)
        row_avg = mean(heights)
        frame_drift = (max(heights) - min(heights)) / max(row_avg, 1.0)
        direction_drift = abs(row_avg - anchor_avg) / max(anchor_avg, 1.0)
        baseline_drift = max(feet) - min(feet)
        head_drift = max(heads) - min(heads)
        baseline_limit = max_baseline_drift_px if max_baseline_drift_px is not None else max(1, round(cell_height * max_baseline_drift_ratio))
        head_limit = max_head_drift_px if max_head_drift_px is not None else max(1, round(cell_height * max_head_drift_ratio))
        edge_touches = [metric.frame for metric in metrics if metric.touches_edge]

        if frame_drift > max_frame_height_drift:
            failures.append(f"{row}: per-frame height drift {frame_drift:.1%} > {max_frame_height_drift:.1%}")
        if direction_drift > max_direction_height_drift:
            failures.append(f"{row}: avg height drift from {anchor_row} {direction_drift:.1%} > {max_direction_height_drift:.1%}")
        if baseline_drift > baseline_limit:
            failures.append(f"{row}: foot baseline drift {baseline_drift}px > {baseline_limit}px")
        if head_drift > head_limit:
            failures.append(f"{row}: head/top drift {head_drift}px > {head_limit}px")
        if edge_touches:
            failures.append(f"{row}: visible pixels touch source cell edge in frames {edge_touches}")

    return failures


def read_godot_constants(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    constants: dict[str, int] = {}
    pattern = re.compile(r"^const\s+(VIEWPORT_W|VIEWPORT_H|PLAYER_W|PLAYER_H|PIXEL_SCALE)\s*:=\s*(\d+)")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if match:
            constants[match.group(1)] = int(match.group(2))
    return constants


def metric_to_dict(metric: FrameMetric) -> dict[str, object]:
    return {
        "row": metric.row,
        "frame": metric.frame,
        "source_box": list(metric.source_box),
        "tight_bbox": list(metric.tight_bbox),
        "visible_width": metric.visible_width,
        "visible_height": metric.visible_height,
        "center_x": round(metric.center_x, 3),
        "head_y": metric.head_y,
        "foot_y": metric.foot_y,
        "touches_edge": metric.touches_edge,
    }


def make_fixed_cell_strip(
    rows: list[str],
    by_row_images: dict[str, list[Image.Image]],
    by_row_metrics: dict[str, list[FrameMetric]],
    cell_pad: int,
    show_guides: bool,
) -> Image.Image:
    max_w = max(image.width for images in by_row_images.values() for image in images)
    max_h = max(image.height for images in by_row_images.values() for image in images)
    label_w = 74
    cell_w = max_w + cell_pad * 2
    cell_h = max_h + cell_pad * 2
    out = Image.new("RGBA", (label_w + cell_w * len(next(iter(by_row_images.values()))), cell_h * len(rows)), PREVIEW_BG)
    draw = ImageDraw.Draw(out)
    font = ImageFont.load_default()

    for row_index, row in enumerate(rows):
        y = row_index * cell_h
        draw.rectangle((0, y, label_w - 1, y + cell_h - 1), fill=PREVIEW_BG)
        draw.text((8, y + 10), row, fill=TEXT, font=font)
        for frame_index, image in enumerate(by_row_images[row]):
            x = label_w + frame_index * cell_w
            panel = Image.new("RGBA", (cell_w, cell_h), PANEL_BG)
            panel.alpha_composite(image, ((cell_w - image.width) // 2, cell_h - cell_pad - image.height))
            if show_guides:
                panel_draw = ImageDraw.Draw(panel)
                panel_draw.line((0, cell_h - cell_pad, cell_w, cell_h - cell_pad), fill=GUIDE)
                panel_draw.line((cell_w // 2, 0, cell_w // 2, cell_h), fill=GUIDE)
            out.alpha_composite(panel, (x, y))
            metric = by_row_metrics[row][frame_index]
            color = FAIL if metric.touches_edge else TEXT
            draw.text((x + 5, y + 5), str(frame_index + 1), fill=color, font=font)
    return out


def make_row_gif(row_images: list[Image.Image], path: Path, duration: int, cell_pad: int) -> None:
    max_w = max(image.width for image in row_images)
    max_h = max(image.height for image in row_images)
    cell_w = max_w + cell_pad * 2
    cell_h = max_h + cell_pad * 2
    sequence: list[Image.Image] = []
    for image in row_images:
        panel = Image.new("RGBA", (cell_w, cell_h), PANEL_BG)
        panel.alpha_composite(image, ((cell_w - image.width) // 2, cell_h - cell_pad - image.height))
        sequence.append(panel.convert("RGB"))
    atlas = Image.new("RGB", (cell_w, cell_h * len(sequence)), PREVIEW_BG[:3])
    for index, frame in enumerate(sequence):
        atlas.paste(frame, (0, index * cell_h))
    palette = atlas.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    gif_frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in sequence]
    gif_frames[0].save(path, save_all=True, append_images=gif_frames[1:], duration=duration, loop=0)


def run(args: argparse.Namespace) -> int:
    rows = [row.strip() for row in args.rows.split(",") if row.strip()]
    image = Image.open(args.input).convert("RGBA")
    if args.mode == "grid":
        boxes = split_grid(image, rows, args.cols)
    else:
        boxes = split_auto(image, rows, args.cols, args.source_pad)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    by_row_metrics: dict[str, list[FrameMetric]] = {row: [] for row in rows}
    by_row_images: dict[str, list[Image.Image]] = {row: [] for row in rows}
    for row, row_boxes in zip(rows, boxes):
        for index, source_box in enumerate(row_boxes, 1):
            metric, visible = frame_metric(
                image,
                row,
                index,
                source_box,
                args.edge_margin,
                args.edge_margin_ratio,
                args.vertical_edge_margin_ratio,
            )
            by_row_metrics[row].append(metric)
            by_row_images[row].append(visible)

    failures = validate(
        rows,
        by_row_metrics,
        args.anchor_row,
        args.max_direction_height_drift,
        args.max_frame_height_drift,
        args.max_baseline_drift_ratio,
        args.max_baseline_drift,
        args.max_head_drift_ratio,
        args.max_head_drift,
        args.cols,
    )

    metrics_path = args.out_dir / f"{args.prefix}_metrics.json"
    fixed_strip_path = args.out_dir / f"{args.prefix}_fixed_cell_strip.png"
    silhouette_path = args.out_dir / f"{args.prefix}_silhouette_strip.png"

    row_summary = {row: row_metrics(metrics) for row, metrics in by_row_metrics.items()}
    report = {
        "status": "pass" if not failures else "fail",
        "source": str(args.input),
        "mode": args.mode,
        "rows": rows,
        "cols": args.cols,
        "anchor_row": args.anchor_row,
        "godot_constants": read_godot_constants(args.constants_gd),
        "thresholds": {
            "max_direction_height_drift": args.max_direction_height_drift,
            "max_frame_height_drift": args.max_frame_height_drift,
            "max_baseline_drift_ratio": args.max_baseline_drift_ratio,
            "max_baseline_drift": args.max_baseline_drift,
            "max_head_drift_ratio": args.max_head_drift_ratio,
            "max_head_drift": args.max_head_drift,
            "edge_margin_ratio": args.edge_margin_ratio,
            "vertical_edge_margin_ratio": args.vertical_edge_margin_ratio,
            "edge_margin": args.edge_margin,
        },
        "failures": failures,
        "summary": row_summary,
        "frames": {row: [metric_to_dict(metric) for metric in metrics] for row, metrics in by_row_metrics.items()},
        "outputs": {
            "fixed_cell_strip": str(fixed_strip_path),
            "silhouette_strip": str(silhouette_path),
        },
    }
    metrics_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    make_fixed_cell_strip(rows, by_row_images, by_row_metrics, args.cell_pad, True).save(fixed_strip_path)
    # Для силуэтов метрики не нужны; передаём фейковые пустые списки не используется при show_guides=False.
    silhouette_images: dict[str, list[Image.Image]] = {}
    for row, images in by_row_images.items():
        silhouette_images[row] = []
        for image in images:
            silhouette = Image.new("RGBA", image.size, (0, 0, 0, 0))
            alpha_source = image.convert("RGBA")
            src = alpha_source.load()
            dst = silhouette.load()
            for y in range(alpha_source.height):
                for x in range(alpha_source.width):
                    if not is_key_pixel(src[x, y]):
                        dst[x, y] = SILHOUETTE
            silhouette_images[row].append(silhouette)
    make_fixed_cell_strip(rows, silhouette_images, by_row_metrics, args.cell_pad, False).save(silhouette_path)

    for row in rows:
        gif_path = args.out_dir / f"{args.prefix}_{row}.gif"
        make_row_gif(by_row_images[row], gif_path, args.frame_ms, args.cell_pad)
        report["outputs"][f"{row}_gif"] = str(gif_path)
    metrics_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if failures:
        print(f"FAIL metrics={metrics_path}")
        for failure in failures:
            print(f"- {failure}")
        return 2 if not args.warn_only else 0

    print(f"PASS metrics={metrics_path}")
    print(f"fixed_cell_strip={fixed_strip_path}")
    print(f"silhouette_strip={silhouette_path}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Strict audit for walk-sheet frame scale, cells, clipping, and baseline.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--rows", default="down,left,right,up")
    parser.add_argument("--cols", type=int, default=6)
    parser.add_argument("--mode", choices=["auto", "grid"], default="grid")
    parser.add_argument("--anchor-row", default="down")
    parser.add_argument("--source-pad", type=int, default=12)
    parser.add_argument("--edge-margin", type=int, default=None, help="Absolute clipping margin override in pixels.")
    parser.add_argument("--edge-margin-ratio", type=float, default=0.0)
    parser.add_argument("--vertical-edge-margin-ratio", type=float, default=0.0)
    parser.add_argument("--cell-pad", type=int, default=24)
    parser.add_argument("--frame-ms", type=int, default=120)
    parser.add_argument("--max-direction-height-drift", type=float, default=0.05)
    parser.add_argument("--max-frame-height-drift", type=float, default=0.10)
    parser.add_argument("--max-baseline-drift-ratio", type=float, default=0.12)
    parser.add_argument("--max-baseline-drift", type=int, default=None, help="Absolute baseline drift override in pixels.")
    parser.add_argument("--max-head-drift-ratio", type=float, default=0.12)
    parser.add_argument("--max-head-drift", type=int, default=None, help="Absolute head/top drift override in pixels.")
    parser.add_argument("--constants-gd", type=Path, default=Path("scripts/core/constants.gd"))
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    try:
        raise SystemExit(run(args))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
