#!/usr/bin/env python3
"""Generate math-based GB/GBC-compatible psychedelic backgrounds."""

from __future__ import annotations

import argparse
import html
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from PIL import Image, ImageDraw, ImageFont


WIDTH = 160
HEIGHT = 144
TILE = 8
DEFAULT_COUNT = 48
DEFAULT_SEED = 1337
GB_STUDIO_SOFT_TILE_LIMIT = 192
LOW_TILE_MOTIF_COUNT = 16
DEFAULT_EXPLORER_SEEDS = 12
DEFAULT_EXPLORER_BEST = 12
DEFAULT_ANIMATION_COUNT = 6
DEFAULT_ANIMATION_FRAMES = 4
DEFAULT_PALETTE_LAB_COUNT = 12
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "generated"

GB_PALETTE = [
    (248, 248, 248),
    (176, 176, 176),
    (88, 88, 88),
    (8, 8, 8),
]

GBC_PALETTES = [
    [(248, 248, 232), (184, 208, 176), (88, 128, 112), (24, 40, 48)],
    [(255, 240, 200), (216, 168, 96), (136, 88, 72), (48, 32, 40)],
    [(240, 232, 255), (176, 152, 216), (96, 88, 144), (32, 32, 72)],
    [(232, 248, 255), (136, 200, 224), (64, 120, 168), (16, 40, 88)],
    [(240, 248, 208), (168, 208, 120), (88, 136, 80), (32, 64, 48)],
    [(255, 232, 224), (216, 144, 136), (136, 72, 96), (48, 24, 56)],
    [(240, 240, 240), (176, 184, 192), (96, 112, 128), (24, 32, 48)],
    [(248, 240, 216), (192, 176, 144), (112, 96, 88), (32, 32, 32)],
]

PATTERNS = [
    "plasma",
    "rings",
    "vortex",
    "moire",
    "lissajous",
    "checker_warp",
    "cellular",
    "hyperspace",
    "orbitals",
    "scan_dream",
    "petals",
    "interference",
    "title_plate",
    "topographic",
    "star_tunnel",
    "magic_circle",
    "crt_glitch",
    "damask",
    "rain_diagonal",
    "heat_shimmer",
    "snow_static",
    "fog_bands",
    "wave_grid",
    "circuit_board",
    "flower_of_life",
    "pinwheel",
    "checker_tunnel",
    "lace",
    "divider_card",
    "letterbox_card",
    "spotlight_plate",
    "corner_bloom",
    "split_panel",
    "signal_bars",
    "ripple_field",
    "woven",
]

FAMILY_PATTERNS = {
    "all": PATTERNS,
    "op_art": [
        "plasma",
        "rings",
        "vortex",
        "moire",
        "lissajous",
        "checker_warp",
        "hyperspace",
        "petals",
        "pinwheel",
        "checker_tunnel",
        "ripple_field",
        "woven",
    ],
    "scene_cards": [
        "title_plate",
        "divider_card",
        "letterbox_card",
        "spotlight_plate",
        "corner_bloom",
        "split_panel",
    ],
    "text_safe": [
        "title_plate",
        "divider_card",
        "letterbox_card",
        "spotlight_plate",
        "corner_bloom",
        "split_panel",
    ],
    "glitch": [
        "crt_glitch",
        "scan_dream",
        "signal_bars",
        "snow_static",
        "interference",
    ],
    "maps": [
        "topographic",
        "cellular",
        "circuit_board",
        "flower_of_life",
        "magic_circle",
    ],
    "weather": [
        "rain_diagonal",
        "heat_shimmer",
        "snow_static",
        "fog_bands",
    ],
    "ornamental": [
        "damask",
        "lace",
        "flower_of_life",
        "wave_grid",
        "woven",
    ],
}

TEXT_SAFE_PATTERNS = set(FAMILY_PATTERNS["text_safe"])
ANIMATION_PATTERNS = [
    "rings",
    "vortex",
    "star_tunnel",
    "pinwheel",
    "checker_tunnel",
    "signal_bars",
    "ripple_field",
    "fog_bands",
]


@dataclass(frozen=True)
class GeneratedImage:
    mode: str
    style: str
    family: str
    name: str
    pattern: str
    seed: int
    variant: int
    tags: tuple[str, ...]
    path: Path
    colors_total: int
    max_colors_per_tile: int
    tile_errors: int
    total_tiles: int
    unique_tiles: int
    over_soft_tile_limit: bool


def flatten_palette(colors: Iterable[tuple[int, int, int]]) -> list[int]:
    flat: list[int] = []
    for r, g, b in colors:
        flat.extend([r, g, b])
    flat.extend([0, 0, 0] * (256 - len(flat) // 3))
    return flat


def normalize(v: float) -> float:
    return (math.sin(v) + 1.0) * 0.5


def quantize(v: float) -> int:
    return max(0, min(3, int(v * 4.0)))


def fract(v: float) -> float:
    return v - math.floor(v)


def noise01(x: float, y: float, seed: int) -> float:
    return fract(math.sin(x * 12.9898 + y * 78.233 + seed * 37.719) * 43758.5453)


def periodic_line(v: float, period: float, width: float) -> float:
    distance = abs((v % period) - period * 0.5)
    return 1.0 if distance < width else 0.0


def pattern_value(pattern: str, x: int, y: int, variant: int, seed: int, width: int, height: int) -> float:
    nx = (x - width / 2) / width
    ny = (y - height / 2) / height
    r = math.sqrt(nx * nx + ny * ny) + 0.0001
    a = math.atan2(ny, nx)
    s = seed * 0.011 + variant * 0.73

    if pattern == "plasma":
        v = (
            math.sin((nx * 23.0) + s)
            + math.sin((ny * 19.0) - s * 0.7)
            + math.sin((nx + ny) * 31.0 + s * 1.3)
        )
        return normalize(v)

    if pattern == "rings":
        v = math.sin(r * 92.0 + s) + 0.5 * math.sin(a * 6.0 + s)
        return normalize(v)

    if pattern == "vortex":
        v = math.sin(r * 70.0 + a * (5.0 + variant % 5) + s)
        v += 0.5 * math.cos((nx - ny) * 28.0 - s)
        return normalize(v)

    if pattern == "moire":
        v = math.sin(nx * 60.0 + s) * math.cos(ny * 55.0 - s)
        v += math.sin((nx * nx - ny * ny) * 180.0)
        return normalize(v)

    if pattern == "lissajous":
        v = math.sin(nx * (28 + variant % 7) + math.sin(ny * 17.0 + s) * 3.0)
        v += math.cos(ny * (31 + variant % 5) + math.sin(nx * 13.0 - s) * 3.0)
        return normalize(v)

    if pattern == "checker_warp":
        wx = x + math.sin(y * 0.13 + s) * 11.0
        wy = y + math.cos(x * 0.11 - s) * 9.0
        cell = (int(wx // (6 + variant % 5)) + int(wy // (7 + variant % 4))) % 2
        ripple = normalize(r * 80.0 - s)
        return (cell * 0.55) + ripple * 0.45

    if pattern == "cellular":
        best = 9999.0
        for i in range(7):
            px = math.sin(s + i * 12.9898) * 0.48
            py = math.cos(s * 1.3 + i * 78.233) * 0.48
            dist = (nx - px) * (nx - px) + (ny - py) * (ny - py)
            best = min(best, dist)
        return normalize(math.sqrt(best) * 55.0 - s)

    if pattern == "hyperspace":
        v = math.sin((1.0 / r) * 1.8 + a * 8.0 + s)
        v += math.cos(r * 45.0 - s)
        return normalize(v)

    if pattern == "orbitals":
        v = 0.0
        for i in range(1, 5):
            cx = math.sin(s * 0.2 + i) * 0.22
            cy = math.cos(s * 0.3 + i * 1.7) * 0.22
            rr = math.sqrt((nx - cx) ** 2 + (ny - cy) ** 2)
            v += math.sin(rr * (50.0 + i * 7.0) - s)
        return normalize(v)

    if pattern == "scan_dream":
        scan = math.sin(y * (0.4 + (variant % 5) * 0.05) + s)
        bend = math.sin((x + scan * 14.0) * 0.19 + s)
        return normalize(scan + bend + math.sin(r * 42.0))

    if pattern == "petals":
        petals = math.sin(a * (6 + variant % 7) + s)
        v = math.sin(r * 80.0 + petals * 3.0)
        return normalize(v)

    if pattern == "interference":
        p1 = math.sin(math.sqrt((nx + 0.28) ** 2 + (ny - 0.1) ** 2) * 75.0 + s)
        p2 = math.sin(math.sqrt((nx - 0.25) ** 2 + (ny + 0.15) ** 2) * 81.0 - s)
        return normalize(p1 + p2)

    if pattern == "title_plate":
        edge = max(abs(nx) * 2.0, abs(ny) * 2.0)
        field = math.sin((nx * 36.0 + math.sin(ny * 14.0 + s) * 4.0))
        field += math.cos((ny * 32.0 + math.sin(nx * 12.0 - s) * 3.0))
        divider = 1.0 if abs(y - height * 0.32) < 2 or abs(y - height * 0.68) < 2 else 0.0
        calm_center = 0.42 if abs(ny) < 0.18 and abs(nx) < 0.42 else normalize(field)
        return max(divider, calm_center * min(1.0, edge + 0.25))

    if pattern == "topographic":
        terrain = (
            math.sin(nx * 11.0 + s)
            + math.cos(ny * 13.0 - s)
            + math.sin((nx + ny) * 16.0 + s * 0.3)
        )
        contour = abs(fract(terrain * 1.7) - 0.5)
        shade = normalize(terrain * 0.8)
        return 0.92 if contour < 0.055 else shade * 0.55

    if pattern == "star_tunnel":
        streaks = math.sin(a * (26 + variant % 12) + (1.0 / r) * 2.2 + s)
        rings = math.sin(r * 90.0 - s)
        return normalize(streaks * 1.3 + rings * 0.55)

    if pattern == "magic_circle":
        ring = max(
            periodic_line(r * 180.0, 24.0, 1.2),
            periodic_line(r * 180.0 + 8.0, 42.0, 1.0),
        )
        spokes = 1.0 if abs(math.sin(a * (8 + variant % 8))) < 0.075 else 0.0
        inner = 1.0 if abs(math.sin((nx * nx + ny * ny) * 420.0 + s)) > 0.94 else 0.0
        return max(ring, spokes * (0.25 < r < 0.48), inner * (r < 0.25))

    if pattern == "crt_glitch":
        band = int(y // (6 + variant % 5))
        shift = int((noise01(band, variant, seed) - 0.5) * 22.0)
        scan = 0.25 if y % 4 in (0, 1) else 0.72
        tear = 0.95 if noise01(band, 11, seed) > 0.82 and x % 5 < 2 else 0.0
        wave = normalize((x + shift) * 0.24 + math.sin(y * 0.21 + s) * 2.0)
        return max(tear, scan * 0.45 + wave * 0.55)

    if pattern == "damask":
        sx = abs(nx)
        motif = math.cos(sx * 42.0 + math.sin(ny * 18.0 + s) * 4.0)
        motif += math.cos(ny * 48.0 + math.sin(sx * 26.0 - s) * 3.0)
        petals = math.sin(math.atan2(ny, sx + 0.001) * 10.0 + r * 50.0)
        return normalize(motif + petals)

    if pattern == "rain_diagonal":
        slant = (x + y * (2 + variant % 3) + int(s * 5.0)) % 17
        drops = 0.95 if slant < 2 else 0.15
        wind = normalize(math.sin((x - y) * 0.08 + s) + math.sin(y * 0.22))
        return max(drops, wind * 0.55)

    if pattern == "heat_shimmer":
        wobble = math.sin(y * 0.14 + s) * 9.0 + math.sin(y * 0.033 - s) * 18.0
        bands = math.sin((x + wobble) * 0.18) + math.sin(y * 0.3 + s)
        haze = math.sin((ny * ny + abs(nx)) * 65.0 - s)
        return normalize(bands + haze * 0.45)

    if pattern == "snow_static":
        grain = noise01(x, y, seed + variant)
        chunks = noise01(x // 4, y // 4, seed + variant * 3)
        scan = 0.18 if y % 3 == 0 else 0.0
        return max(grain * 0.8, chunks * 0.65, scan)

    if pattern == "fog_bands":
        bands = math.sin(y * 0.11 + math.sin(x * 0.055 + s) * 2.5)
        slow = math.sin((x + y) * 0.035 - s)
        return 0.2 + normalize(bands + slow * 0.8) * 0.62

    if pattern == "wave_grid":
        wx = x + math.sin(y * 0.12 + s) * 10.0
        wy = y + math.sin(x * 0.1 - s) * 8.0
        vertical = periodic_line(wx, 16.0, 1.4)
        horizontal = periodic_line(wy, 16.0, 1.4)
        fill = normalize(math.sin((wx + wy) * 0.12))
        return max(vertical, horizontal, fill * 0.5)

    if pattern == "circuit_board":
        tx = x // TILE
        ty = y // TILE
        lx = x % TILE
        ly = y % TILE
        cell = noise01(tx, ty, seed + variant)
        node = (lx - 3.5) ** 2 + (ly - 3.5) ** 2 < 5.0 and cell > 0.58
        hline = ly in (3, 4) and noise01(tx, ty * 3, seed) > 0.42
        vline = lx in (3, 4) and noise01(tx * 3, ty, seed) > 0.52
        trace = hline or vline or node
        base = 0.18 + (0.16 if (tx + ty + variant) % 2 else 0.0)
        return 0.95 if trace else base

    if pattern == "flower_of_life":
        value = 0.0
        radius = 0.18 + (variant % 4) * 0.015
        for iy in range(-2, 3):
            for ix in range(-2, 3):
                cx = (ix + (0.5 if iy % 2 else 0.0)) * radius * 0.95
                cy = iy * radius * 0.82
                rr = math.sqrt((nx - cx) ** 2 + (ny - cy) ** 2)
                value = max(value, 1.0 if abs(rr - radius) < 0.012 else 0.0)
        shade = normalize(math.sin(nx * 22.0 + s) + math.sin(ny * 18.0 - s))
        return max(value, shade * 0.35)

    if pattern == "pinwheel":
        arms = math.sin(a * (5 + variant % 7) + r * 95.0 + s)
        counter = math.cos(a * (7 + variant % 5) - r * 60.0)
        return normalize(arms + counter * 0.7)

    if pattern == "checker_tunnel":
        radius_band = int((math.log(r + 0.01) * 11.0 + s * 2.0) % 2)
        angle_band = int(((a + math.pi) / (math.pi * 2.0)) * (18 + variant % 10)) % 2
        ripple = normalize(math.sin(r * 100.0 + s))
        return 0.9 if radius_band ^ angle_band else ripple * 0.45

    if pattern == "lace":
        weave_a = math.sin(nx * 80.0 + math.sin(ny * 24.0 + s) * 2.0)
        weave_b = math.sin(ny * 74.0 + math.sin(nx * 21.0 - s) * 2.0)
        knots = math.sin((nx + ny) * 58.0) * math.sin((nx - ny) * 62.0)
        return normalize(weave_a + weave_b + knots)

    if pattern == "divider_card":
        border = 0.94 if x < 4 or x >= width - 4 or y < 4 or y >= height - 4 else 0.0
        divider = 0.92 if abs(y - height * 0.5) < 2 else 0.0
        corner_pattern = normalize(math.sin((abs(nx) + abs(ny)) * 64.0 + s))
        quiet = 0.35 if abs(nx) < 0.38 and abs(ny) < 0.25 else corner_pattern
        return max(border, divider, quiet)

    if pattern == "letterbox_card":
        band = y < height * 0.2 or y > height * 0.8
        border = 0.95 if x < 4 or x >= width - 4 or y < 4 or y >= height - 4 else 0.0
        band_wave = normalize(math.sin(x * 0.28 + s) + math.sin((x + y) * 0.12))
        quiet_center = 0.32 + normalize(math.sin(x * 0.035 + s)) * 0.12
        rule = 0.9 if abs(y - height * 0.22) < 2 or abs(y - height * 0.78) < 2 else 0.0
        return max(border, rule, band_wave if band else quiet_center)

    if pattern == "spotlight_plate":
        edge = min(1.0, max(abs(nx) * 2.2, abs(ny) * 2.2))
        rays = normalize(math.sin(a * (12 + variant % 8) + s) + math.sin(r * 55.0))
        center = math.sqrt((nx * 1.4) ** 2 + (ny * 2.0) ** 2)
        quiet = 0.28 if center < 0.32 else rays * edge
        frame = 0.92 if abs(center - 0.38) < 0.012 else 0.0
        return max(quiet, frame)

    if pattern == "corner_bloom":
        corner_distance = min(
            math.sqrt((nx + 0.5) ** 2 + (ny + 0.45) ** 2),
            math.sqrt((nx - 0.5) ** 2 + (ny + 0.45) ** 2),
            math.sqrt((nx + 0.5) ** 2 + (ny - 0.45) ** 2),
            math.sqrt((nx - 0.5) ** 2 + (ny - 0.45) ** 2),
        )
        bloom = normalize(math.sin(corner_distance * 95.0 + s) + math.sin(a * 8.0))
        center_quiet = 0.36 if abs(nx) < 0.36 and abs(ny) < 0.22 else bloom
        rule = 0.85 if abs(x - width * 0.5) < 1 or abs(y - height * 0.5) < 1 else 0.0
        return max(center_quiet, rule * (1.0 if corner_distance < 0.42 else 0.0))

    if pattern == "split_panel":
        left_panel = x < width * 0.36
        right_panel = x > width * 0.64
        rule = 0.92 if abs(x - width * 0.36) < 2 or abs(x - width * 0.64) < 2 else 0.0
        side_pattern = normalize(math.sin(y * 0.32 + s) + math.sin((x + y) * 0.16))
        center = 0.34 + normalize(math.sin(y * 0.045 - s)) * 0.08
        return max(rule, side_pattern if left_panel or right_panel else center)

    if pattern == "signal_bars":
        bars = periodic_line(y + math.sin(x * 0.08 + s) * 7.0, 18.0, 2.0)
        carrier = normalize(math.sin(x * 0.33 + s) + math.sin((x + y) * 0.15))
        dropout = 0.0 if noise01(y // 8, variant, seed) > 0.78 and x % 3 else carrier
        return max(bars, dropout * 0.8)

    if pattern == "ripple_field":
        value = 0.0
        for i in range(5):
            cx = math.sin(s * 0.21 + i * 1.8) * 0.42
            cy = math.cos(s * 0.17 + i * 2.1) * 0.36
            rr = math.sqrt((nx - cx) ** 2 + (ny - cy) ** 2)
            value += math.sin(rr * (56.0 + i * 6.0) + s)
        return normalize(value)

    if pattern == "woven":
        warp = math.sin((x + math.sin(y * 0.12 + s) * 3.0) * 0.42)
        weft = math.sin((y + math.sin(x * 0.11 - s) * 3.0) * 0.46)
        over_under = 0.25 if ((x // 8) + (y // 8)) % 2 else -0.25
        return normalize(warp + weft + over_under)

    raise ValueError(f"Unknown pattern: {pattern}")


def pattern_family(pattern: str) -> str:
    for family, patterns in FAMILY_PATTERNS.items():
        if family != "all" and pattern in patterns:
            return family
    return "misc"


def pattern_tags(pattern: str, style: str) -> tuple[str, ...]:
    tags = {pattern_family(pattern), style}
    if pattern in TEXT_SAFE_PATTERNS:
        tags.add("text_safe")
    if pattern in FAMILY_PATTERNS["op_art"]:
        tags.add("op_art")
    if pattern in FAMILY_PATTERNS["glitch"]:
        tags.add("glitch")
    if pattern in FAMILY_PATTERNS["weather"]:
        tags.add("weather")
    if pattern in FAMILY_PATTERNS["maps"]:
        tags.add("maps")
    return tuple(sorted(tags))


def selected_patterns(families: list[str]) -> list[str]:
    patterns: list[str] = []
    for family in families:
        for pattern in FAMILY_PATTERNS[family]:
            if pattern not in patterns:
                patterns.append(pattern)
    return patterns


def tile_palette_id(tile_x: int, tile_y: int, variant: int, seed: int, palette_mode: str) -> int:
    if palette_mode == "image":
        return (variant + seed) % len(GBC_PALETTES)
    if palette_mode == "bands":
        region_x = tile_x // 5
        region_y = tile_y // 4
        return (region_x + region_y * 2 + variant + seed) % len(GBC_PALETTES)
    if palette_mode == "tile":
        return (tile_x * 3 + tile_y * 5 + variant * 7 + seed) % len(GBC_PALETTES)
    raise ValueError(f"Unknown GBC palette mode: {palette_mode}")


def make_gb_image(pattern: str, variant: int, seed: int, width: int, height: int) -> Image.Image:
    img = Image.new("P", (width, height), color=0)
    img.putpalette(flatten_palette(GB_PALETTE))
    pix = img.load()
    for y in range(height):
        for x in range(width):
            pix[x, y] = quantize(pattern_value(pattern, x, y, variant, seed, width, height))
    return img


def make_gbc_image(
    pattern: str,
    variant: int,
    seed: int,
    width: int,
    height: int,
    palette_mode: str,
) -> Image.Image:
    img = Image.new("P", (width, height), color=0)
    img.putpalette(flatten_palette([color for palette in GBC_PALETTES for color in palette]))
    pix = img.load()
    for tile_y in range(height // TILE):
        for tile_x in range(width // TILE):
            palette_id = tile_palette_id(tile_x, tile_y, variant, seed, palette_mode)
            base = palette_id * 4
            for py in range(TILE):
                for px in range(TILE):
                    x = tile_x * TILE + px
                    y = tile_y * TILE + py
                    local = quantize(pattern_value(pattern, x, y, variant, seed, width, height))
                    pix[x, y] = base + local
    return img


def low_tile_pixel(motif: int, tone: int, lx: int, ly: int) -> int:
    lighter = max(0, tone - 1)
    darker = min(3, tone + 1)
    lightest = max(0, tone - 2)
    darkest = min(3, tone + 2)

    if motif == 0:
        return tone
    if motif == 1:
        return darker if ly in (0, 1, 6, 7) else tone
    if motif == 2:
        return darker if lx in (0, 1, 6, 7) else tone
    if motif == 3:
        return darker if lx == ly or lx + ly == 7 else tone
    if motif == 4:
        return lighter if (lx + ly) % 2 else darker
    if motif == 5:
        return darker if (lx + ly) % 4 < 2 else lighter
    if motif == 6:
        return darker if (lx - ly) % 4 < 2 else lighter
    if motif == 7:
        return darker if abs(lx - 3.5) + abs(ly - 3.5) < 3.4 else lighter
    if motif == 8:
        return darkest if (lx - 3.5) ** 2 + (ly - 3.5) ** 2 < 8.0 else tone
    if motif == 9:
        return lighter if lx in (3, 4) or ly in (3, 4) else tone
    if motif == 10:
        return darker if lx in (0, 7) or ly in (0, 7) else lightest
    if motif == 11:
        return darker if ly in (1, 4) else lighter if ly in (2, 5) else tone
    if motif == 12:
        return darker if lx in (1, 4) else lighter if lx in (2, 5) else tone
    if motif == 13:
        return darker if (lx // 2 + ly // 2) % 2 else lighter
    if motif == 14:
        return darkest if abs(lx - ly) < 2 else lightest if abs(lx + ly - 7) < 2 else tone
    if motif == 15:
        return darker if lx in (0, 7) or ly in (0, 7) or (lx + ly) % 5 == 0 else lighter
    raise ValueError(motif)


def low_tile_local(pattern: str, variant: int, seed: int, width: int, height: int, tile_x: int, tile_y: int, lx: int, ly: int) -> int:
    center_x = tile_x * TILE + TILE // 2
    center_y = tile_y * TILE + TILE // 2
    value = pattern_value(pattern, center_x, center_y, variant, seed, width, height)
    tone = quantize(value)
    region_x = tile_x // 2
    region_y = tile_y // 2
    region_center_x = min(width - 1, region_x * TILE * 2 + TILE)
    region_center_y = min(height - 1, region_y * TILE * 2 + TILE)
    motif_value = pattern_value(
        pattern,
        region_center_x,
        region_center_y,
        variant + 5,
        seed + 31,
        width,
        height,
    )
    motif = min(LOW_TILE_MOTIF_COUNT - 1, int(motif_value * LOW_TILE_MOTIF_COUNT))
    if pattern in TEXT_SAFE_PATTERNS and abs(center_x - width / 2) < width * 0.27 and abs(center_y - height / 2) < height * 0.18:
        motif = 0
    return low_tile_pixel(motif, tone, lx, ly)


def make_low_tile_image(
    mode: str,
    pattern: str,
    variant: int,
    seed: int,
    width: int,
    height: int,
    palette_mode: str,
) -> Image.Image:
    img = Image.new("P", (width, height), color=0)
    if mode == "gb":
        img.putpalette(flatten_palette(GB_PALETTE))
    elif mode == "gbc":
        img.putpalette(flatten_palette([color for palette in GBC_PALETTES for color in palette]))
    else:
        raise ValueError(mode)

    pix = img.load()
    for tile_y in range(height // TILE):
        for tile_x in range(width // TILE):
            base = 0
            if mode == "gbc":
                base = tile_palette_id(tile_x, tile_y, variant, seed, palette_mode) * 4
            for ly in range(TILE):
                for lx in range(TILE):
                    local = low_tile_local(pattern, variant, seed, width, height, tile_x, tile_y, lx, ly)
                    pix[tile_x * TILE + lx, tile_y * TILE + ly] = base + local
    return img


def make_image(
    mode: str,
    style: str,
    pattern: str,
    variant: int,
    seed: int,
    width: int,
    height: int,
    gbc_palette_mode: str,
) -> Image.Image:
    if style == "full":
        if mode == "gb":
            return make_gb_image(pattern, variant, seed, width, height)
        if mode == "gbc":
            return make_gbc_image(pattern, variant, seed, width, height, gbc_palette_mode)
    if style == "low_tile":
        return make_low_tile_image(mode, pattern, variant, seed, width, height, gbc_palette_mode)
    raise ValueError(f"Unknown mode/style: {mode}/{style}")


def tile_signature(img: Image.Image, mode: str, tile_x: int, tile_y: int) -> tuple[int, ...]:
    pix = img.load()
    signature = []
    for y in range(tile_y * TILE, tile_y * TILE + TILE):
        for x in range(tile_x * TILE, tile_x * TILE + TILE):
            color = int(pix[x, y])
            signature.append(color % 4 if mode == "gbc" else color)
    return tuple(signature)


def validate_image(img: Image.Image, mode: str) -> tuple[int, int, int, int, int]:
    colors = img.getcolors(maxcolors=256) or []
    colors_total = len(colors)
    max_tile_colors = 0
    tile_errors = 0
    unique_tiles = set()
    pix = img.load()

    for tile_y in range(img.height // TILE):
        for tile_x in range(img.width // TILE):
            unique_tiles.add(tile_signature(img, mode, tile_x, tile_y))
            tile_colors = {
                pix[x, y]
                for y in range(tile_y * TILE, tile_y * TILE + TILE)
                for x in range(tile_x * TILE, tile_x * TILE + TILE)
            }
            max_tile_colors = max(max_tile_colors, len(tile_colors))
            if len(tile_colors) > 4:
                tile_errors += 1
            if mode == "gbc":
                palette_groups = {int(color) // 4 for color in tile_colors}
                if len(palette_groups) > 1:
                    tile_errors += 1

    if mode == "gb" and colors_total > 4:
        tile_errors += 1

    total_tiles = (img.width // TILE) * (img.height // TILE)
    return colors_total, max_tile_colors, tile_errors, total_tiles, len(unique_tiles)


def make_generated_record(
    mode: str,
    style: str,
    pattern: str,
    seed: int,
    variant: int,
    path: Path,
    img: Image.Image,
    tile_budget: int,
    extra_tags: tuple[str, ...] = (),
) -> GeneratedImage:
    colors_total, max_tile_colors, tile_errors, total_tiles, unique_tiles = validate_image(img, mode)
    tags = tuple(sorted(set(pattern_tags(pattern, style)).union(extra_tags)))
    return GeneratedImage(
        mode=mode,
        style=style,
        family=pattern_family(pattern),
        name=path.name,
        pattern=pattern,
        seed=seed,
        variant=variant,
        tags=tags,
        path=path,
        colors_total=colors_total,
        max_colors_per_tile=max_tile_colors,
        tile_errors=tile_errors,
        total_tiles=total_tiles,
        unique_tiles=unique_tiles,
        over_soft_tile_limit=unique_tiles > tile_budget,
    )


def generate(
    mode: str,
    style: str,
    patterns: list[str],
    count: int,
    seed: int,
    output_dir: Path,
    width: int,
    height: int,
    gbc_palette_mode: str,
    tile_budget: int,
) -> list[GeneratedImage]:
    mode_dir_name = mode if style == "full" else f"{mode}_{style}"
    mode_dir = output_dir / mode_dir_name
    mode_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{mode}_psy" if style == "full" else f"{mode}_{style}"
    for stale in mode_dir.glob(f"{prefix}_*.png"):
        stale.unlink()
    generated = []

    for index in range(count):
        pattern = patterns[index % len(patterns)]
        img = make_image(mode, style, pattern, index, seed, width, height, gbc_palette_mode)

        name = f"{prefix}_{index:02d}_{pattern}.png"
        path = mode_dir / name
        img.save(path, optimize=True)
        generated.append(make_generated_record(mode, style, pattern, seed, index, path, img, tile_budget))

    return generated


def make_contact_sheet(images: list[GeneratedImage], output_dir: Path, name: str) -> Path:
    if not images:
        raise ValueError("No images for contact sheet")

    font = ImageFont.load_default()
    with Image.open(images[0].path) as first_image:
        thumb_w, thumb_h = first_image.size
    label_h = 18
    cols = 4
    rows = math.ceil(len(images) / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)

    for index, item in enumerate(images):
        img = Image.open(item.path).convert("RGB")
        x = (index % cols) * thumb_w
        y = (index // cols) * (thumb_h + label_h)
        sheet.paste(img, (x, y))
        label = item.name.removesuffix(".png")
        draw.text((x + 2, y + thumb_h + 3), label[:25], fill=(0, 0, 0), font=font)

    path = output_dir / f"{name}_contact_sheet.png"
    sheet.save(path)
    return path


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def html_asset_path(path_text: str, output_dir: Path) -> str:
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        return str(path.resolve().relative_to(output_dir.resolve()))
    except ValueError:
        return path_text


def palette_preview_image(source: Image.Image, palette: list[tuple[int, int, int]]) -> Image.Image:
    out = Image.new("RGB", source.size)
    source_pix = source.load()
    out_pix = out.load()
    for y in range(source.height):
        for x in range(source.width):
            out_pix[x, y] = palette[int(source_pix[x, y]) % 4]
    return out


def make_palette_lab(patterns: list[str], seed: int, output_dir: Path, width: int, height: int, count: int) -> Optional[Path]:
    if count <= 0:
        return None

    lab_patterns = patterns[:count]
    if not lab_patterns:
        return None

    font = ImageFont.load_default()
    label_h = 18
    sheet = Image.new(
        "RGB",
        (len(GBC_PALETTES) * width, len(lab_patterns) * (height + label_h)),
        "white",
    )
    draw = ImageDraw.Draw(sheet)

    for row, pattern in enumerate(lab_patterns):
        base = make_gb_image(pattern, row, seed, width, height)
        for col, palette in enumerate(GBC_PALETTES):
            x = col * width
            y = row * (height + label_h)
            sheet.paste(palette_preview_image(base, palette), (x, y))
            label = f"{pattern} p{col}"
            draw.text((x + 2, y + height + 3), label[:25], fill=(0, 0, 0), font=font)

    path = output_dir / "palette_lab.png"
    sheet.save(path)
    return path


def score_seed_candidate(img: Image.Image, unique_tiles: int, tile_budget: int) -> float:
    counts = [0, 0, 0, 0]
    for color in img.getdata():
        counts[int(color) % 4] += 1
    total = max(1, sum(counts))
    ratios = [count / total for count in counts]
    balance = 1.0 - min(1.0, sum(abs(ratio - 0.25) for ratio in ratios) / 1.5)
    contrast = (ratios[0] + ratios[3]) * 0.8 + abs((ratios[0] + ratios[1]) - (ratios[2] + ratios[3])) * 0.2
    tile_score = min(1.0, tile_budget / max(1, unique_tiles))
    return balance * 0.45 + contrast * 0.35 + tile_score * 0.2


def make_seed_explorer(
    patterns: list[str],
    base_seed: int,
    output_dir: Path,
    width: int,
    height: int,
    tile_budget: int,
    candidate_seed_count: int,
    best_count: int,
) -> list[GeneratedImage]:
    if candidate_seed_count <= 0 or best_count <= 0:
        return []

    explorer_dir = output_dir / "seed_explorer"
    explorer_dir.mkdir(parents=True, exist_ok=True)
    for stale in explorer_dir.glob("seed_*.png"):
        stale.unlink()

    candidates: list[tuple[float, int, int, str, Image.Image, int]] = []
    for seed_index in range(candidate_seed_count):
        candidate_seed = base_seed + seed_index * 37
        for pattern_index, pattern in enumerate(patterns):
            variant = pattern_index + seed_index
            img = make_gb_image(pattern, variant, candidate_seed, width, height)
            _, _, tile_errors, _, unique_tiles = validate_image(img, "gb")
            if tile_errors:
                continue
            score = score_seed_candidate(img, unique_tiles, tile_budget)
            candidates.append((score, candidate_seed, variant, pattern, img, unique_tiles))

    candidates.sort(key=lambda item: item[0], reverse=True)
    selected: list[tuple[float, int, int, str, Image.Image, int]] = []
    seen_patterns: set[str] = set()
    for candidate in candidates:
        pattern = candidate[3]
        if pattern in seen_patterns:
            continue
        selected.append(candidate)
        seen_patterns.add(pattern)
        if len(selected) >= best_count:
            break
    if len(selected) < best_count:
        selected_patterns_seen = {(item[1], item[2], item[3]) for item in selected}
        for candidate in candidates:
            key = (candidate[1], candidate[2], candidate[3])
            if key in selected_patterns_seen:
                continue
            selected.append(candidate)
            if len(selected) >= best_count:
                break

    generated = []
    for index, (score, candidate_seed, variant, pattern, img, _unique_tiles) in enumerate(selected):
        name = f"seed_{index:02d}_score_{int(score * 1000):03d}_{pattern}_s{candidate_seed}.png"
        path = explorer_dir / name
        img.save(path, optimize=True)
        generated.append(
            make_generated_record(
                "gb",
                "seed_explorer",
                pattern,
                candidate_seed,
                variant,
                path,
                img,
                tile_budget,
                ("seed_explorer",),
            )
        )

    if generated:
        make_contact_sheet(generated, output_dir, "seed_explorer")
    return generated


def make_animation_strip(frame_paths: list[Path], path: Path) -> Path:
    if not frame_paths:
        raise ValueError("No animation frames for strip")
    frames = [Image.open(frame_path).convert("RGB") for frame_path in frame_paths]
    sheet = Image.new("RGB", (frames[0].width * len(frames), frames[0].height), "white")
    for index, frame in enumerate(frames):
        sheet.paste(frame, (index * frame.width, 0))
    sheet.save(path)
    for frame in frames:
        frame.close()
    return path


def make_animations(
    patterns: list[str],
    modes: list[str],
    seed: int,
    output_dir: Path,
    width: int,
    height: int,
    gbc_palette_mode: str,
    tile_budget: int,
    animation_count: int,
    frame_count: int,
) -> list[dict[str, object]]:
    if animation_count <= 0 or frame_count <= 0:
        return []

    animation_patterns = [pattern for pattern in ANIMATION_PATTERNS if pattern in patterns]
    if not animation_patterns:
        animation_patterns = patterns[:animation_count]

    records: list[dict[str, object]] = []
    for mode in modes:
        for index, pattern in enumerate(animation_patterns[:animation_count]):
            anim_dir = output_dir / "animations" / mode / f"anim_{index:02d}_{pattern}"
            anim_dir.mkdir(parents=True, exist_ok=True)
            for stale in anim_dir.glob("frame_*.png"):
                stale.unlink()
            strip_path = anim_dir / "strip.png"
            if strip_path.exists():
                strip_path.unlink()

            frame_paths: list[Path] = []
            frame_records = []
            for frame in range(frame_count):
                variant = index + frame * len(PATTERNS)
                img = make_image(mode, "full", pattern, variant, seed + frame * 23, width, height, gbc_palette_mode)
                frame_path = anim_dir / f"frame_{frame:02d}.png"
                img.save(frame_path, optimize=True)
                frame_paths.append(frame_path)
                frame_records.append(
                    make_generated_record(
                        mode,
                        "animation",
                        pattern,
                        seed + frame * 23,
                        variant,
                        frame_path,
                        img,
                        tile_budget,
                        ("animation",),
                    )
                )

            make_animation_strip(frame_paths, strip_path)
            records.append(
                {
                    "mode": mode,
                    "pattern": pattern,
                    "frameCount": frame_count,
                    "frames": [display_path(frame_path) for frame_path in frame_paths],
                    "strip": display_path(strip_path),
                    "maxUniqueTiles": max(record.unique_tiles for record in frame_records),
                    "tileErrors": sum(record.tile_errors for record in frame_records),
                }
            )
    return records


def write_gallery(output_dir: Path, manifest: dict[str, object]) -> Path:
    images = manifest.get("images", [])
    families = sorted({str(item.get("family", "misc")) for item in images if isinstance(item, dict)})
    styles = sorted({str(item.get("style", "full")) for item in images if isinstance(item, dict)})
    modes = sorted({str(item.get("mode", "gb")) for item in images if isinstance(item, dict)})

    def options(values: list[str]) -> str:
        return "\n".join(f'<option value="{html.escape(value)}">{html.escape(value)}</option>' for value in values)

    cards = []
    for item in images:
        if not isinstance(item, dict):
            continue
        path = html_asset_path(str(item["path"]), output_dir)
        tags = " ".join(str(tag) for tag in item.get("tags", []))
        budget = "under" if not item.get("overSoftTileLimit") else "over"
        text_safe = "true" if item.get("textSafe") else "false"
        cards.append(
            f'''
<article class="card" data-mode="{html.escape(str(item["mode"]))}" data-style="{html.escape(str(item["style"]))}"
  data-family="{html.escape(str(item["family"]))}" data-budget="{budget}" data-text-safe="{text_safe}"
  data-search="{html.escape(str(item["name"]) + " " + str(item["pattern"]) + " " + tags)}">
  <img src="{html.escape(path)}" alt="{html.escape(str(item["name"]))}">
  <div class="meta">
    <strong>{html.escape(str(item["name"]))}</strong>
    <span>{html.escape(str(item["family"]))} / {html.escape(str(item["style"]))} / {html.escape(str(item["mode"]))}</span>
    <span>{html.escape(str(item["uniqueTiles"]))} unique tiles / {html.escape(str(item["colorsTotal"]))} colors</span>
  </div>
</article>'''
        )

    palette_lab = manifest.get("paletteLab")
    seed_sheet = manifest.get("seedExplorerContactSheet")
    extras = []
    if palette_lab:
        extras.append(f'<a href="{html.escape(html_asset_path(str(palette_lab), output_dir))}">Palette lab</a>')
    if seed_sheet:
        extras.append(f'<a href="{html.escape(html_asset_path(str(seed_sheet), output_dir))}">Seed explorer sheet</a>')

    html_text = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Psychedelic Background Gallery</title>
<style>
body {{ margin: 0; font: 14px/1.4 system-ui, sans-serif; background: #111; color: #eee; }}
header {{ position: sticky; top: 0; z-index: 2; background: #181818; border-bottom: 1px solid #333; padding: 12px 16px; }}
h1 {{ margin: 0 0 10px; font-size: 20px; }}
.controls {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
input, select, label {{ background: #222; color: #eee; border: 1px solid #444; border-radius: 4px; padding: 6px 8px; }}
label {{ display: inline-flex; gap: 6px; align-items: center; }}
a {{ color: #9bdcff; }}
.extras {{ display: flex; gap: 12px; margin-top: 8px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; padding: 16px; }}
.card {{ background: #1b1b1b; border: 1px solid #333; border-radius: 6px; overflow: hidden; }}
.card[hidden] {{ display: none; }}
.card img {{ width: 100%; image-rendering: pixelated; display: block; background: #fff; }}
.meta {{ display: grid; gap: 2px; padding: 8px; }}
.meta strong {{ font-size: 12px; overflow-wrap: anywhere; }}
.meta span {{ color: #bbb; font-size: 12px; }}
</style>
</head>
<body>
<header>
  <h1>Psychedelic Background Gallery</h1>
  <div class="controls">
    <input id="search" type="search" placeholder="Search patterns">
    <select id="mode"><option value="">All modes</option>{options(modes)}</select>
    <select id="style"><option value="">All styles</option>{options(styles)}</select>
    <select id="family"><option value="">All families</option>{options(families)}</select>
    <label><input id="budget" type="checkbox"> Under soft tile budget</label>
    <label><input id="textSafe" type="checkbox"> Text-safe</label>
  </div>
  <div class="extras">{' '.join(extras)}</div>
</header>
<main class="grid" id="grid">
{''.join(cards)}
</main>
<script>
const controls = {{
  search: document.querySelector('#search'),
  mode: document.querySelector('#mode'),
  style: document.querySelector('#style'),
  family: document.querySelector('#family'),
  budget: document.querySelector('#budget'),
  textSafe: document.querySelector('#textSafe')
}};
const cards = Array.from(document.querySelectorAll('.card'));
function applyFilters() {{
  const query = controls.search.value.trim().toLowerCase();
  for (const card of cards) {{
    const show =
      (!query || card.dataset.search.toLowerCase().includes(query)) &&
      (!controls.mode.value || card.dataset.mode === controls.mode.value) &&
      (!controls.style.value || card.dataset.style === controls.style.value) &&
      (!controls.family.value || card.dataset.family === controls.family.value) &&
      (!controls.budget.checked || card.dataset.budget === 'under') &&
      (!controls.textSafe.checked || card.dataset.textSafe === 'true');
    card.hidden = !show;
  }}
}}
Object.values(controls).forEach(control => control.addEventListener('input', applyFilters));
applyFilters();
</script>
</body>
</html>
'''
    path = output_dir / "gallery.html"
    path.write_text(html_text)
    return path


def write_manifest(
    output_dir: Path,
    generated: list[GeneratedImage],
    width: int,
    height: int,
    seed: int,
    gbc_palette_mode: str,
    tile_budget: int,
    families: list[str],
    render_styles: list[str],
    palette_lab: Optional[Path],
    seed_explorer_contact_sheet: Optional[Path],
    animations: list[dict[str, object]],
) -> tuple[Path, dict[str, object]]:
    payload = {
        "width": width,
        "height": height,
        "tileSize": TILE,
        "seed": seed,
        "families": families,
        "renderStyles": render_styles,
        "gbcPaletteMode": gbc_palette_mode,
        "softTileBudget": tile_budget,
        "paletteLab": display_path(palette_lab) if palette_lab else None,
        "seedExplorerContactSheet": display_path(seed_explorer_contact_sheet) if seed_explorer_contact_sheet else None,
        "animations": animations,
        "gbPalette": GB_PALETTE,
        "gbcPalettes": GBC_PALETTES,
        "images": [
            {
                "mode": item.mode,
                "style": item.style,
                "family": item.family,
                "name": item.name,
                "pattern": item.pattern,
                "seed": item.seed,
                "variant": item.variant,
                "tags": list(item.tags),
                "textSafe": "text_safe" in item.tags,
                "path": display_path(item.path),
                "colorsTotal": item.colors_total,
                "maxColorsPerTile": item.max_colors_per_tile,
                "tileErrors": item.tile_errors,
                "totalTiles": item.total_tiles,
                "uniqueTiles": item.unique_tiles,
                "duplicateTiles": item.total_tiles - item.unique_tiles,
                "overSoftTileLimit": item.over_soft_tile_limit,
            }
            for item in generated
        ],
    }
    path = output_dir / "manifest.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--width", type=int, default=WIDTH)
    parser.add_argument("--height", type=int, default=HEIGHT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--modes", nargs="+", choices=("gb", "gbc"), default=["gb", "gbc"])
    parser.add_argument("--families", nargs="+", choices=sorted(FAMILY_PATTERNS), default=["all"])
    parser.add_argument("--render-styles", nargs="+", choices=("full", "low_tile"), default=["full", "low_tile"])
    parser.add_argument(
        "--gbc-palette-mode",
        choices=("image", "bands", "tile"),
        default="image",
        help="How GBC palettes are assigned: image-wide, broad regions, or old per-tile chaos.",
    )
    parser.add_argument("--tile-budget", type=int, default=GB_STUDIO_SOFT_TILE_LIMIT)
    parser.add_argument("--fail-on-tile-budget", action="store_true")
    parser.add_argument("--palette-lab-count", type=int, default=DEFAULT_PALETTE_LAB_COUNT)
    parser.add_argument("--explore-seeds", type=int, default=DEFAULT_EXPLORER_SEEDS)
    parser.add_argument("--explore-best", type=int, default=DEFAULT_EXPLORER_BEST)
    parser.add_argument("--animation-count", type=int, default=DEFAULT_ANIMATION_COUNT)
    parser.add_argument("--animation-frames", type=int, default=DEFAULT_ANIMATION_FRAMES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.width % TILE != 0 or args.height % TILE != 0:
        raise SystemExit("Width and height must be divisible by 8")
    if args.count <= 0:
        raise SystemExit("Count must be positive")
    if args.tile_budget <= 0:
        raise SystemExit("Tile budget must be positive")
    if args.palette_lab_count < 0 or args.explore_seeds < 0 or args.explore_best < 0:
        raise SystemExit("Optional generated counts cannot be negative")
    if args.animation_count < 0 or args.animation_frames < 0:
        raise SystemExit("Animation counts cannot be negative")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    patterns = selected_patterns(args.families)
    all_generated: list[GeneratedImage] = []
    for style in args.render_styles:
        for mode in args.modes:
            generated = generate(
                mode,
                style,
                patterns,
                args.count,
                args.seed,
                args.output_dir,
                args.width,
                args.height,
                args.gbc_palette_mode,
                args.tile_budget,
            )
            all_generated.extend(generated)
            sheet_name = mode if style == "full" else f"{mode}_{style}"
            sheet = make_contact_sheet(generated, args.output_dir, sheet_name)
            print(sheet)

    palette_lab = make_palette_lab(patterns, args.seed, args.output_dir, args.width, args.height, args.palette_lab_count)
    if palette_lab:
        print(palette_lab)

    seed_generated = make_seed_explorer(
        patterns,
        args.seed,
        args.output_dir,
        args.width,
        args.height,
        args.tile_budget,
        args.explore_seeds,
        args.explore_best,
    )
    all_generated.extend(seed_generated)
    seed_explorer_contact_sheet = args.output_dir / "seed_explorer_contact_sheet.png" if seed_generated else None
    if seed_explorer_contact_sheet:
        print(seed_explorer_contact_sheet)

    animations = make_animations(
        patterns,
        args.modes,
        args.seed,
        args.output_dir,
        args.width,
        args.height,
        args.gbc_palette_mode,
        args.tile_budget,
        args.animation_count,
        args.animation_frames,
    )
    for animation in animations:
        print(animation["strip"])

    manifest, payload = write_manifest(
        args.output_dir,
        all_generated,
        args.width,
        args.height,
        args.seed,
        args.gbc_palette_mode,
        args.tile_budget,
        args.families,
        args.render_styles,
        palette_lab,
        seed_explorer_contact_sheet,
        animations,
    )
    print(manifest)
    gallery = write_gallery(args.output_dir, payload)
    print(gallery)

    error_count = sum(item.tile_errors for item in all_generated)
    error_count += sum(int(animation["tileErrors"]) for animation in animations)
    if error_count:
        raise SystemExit(f"Generated images have {error_count} compatibility errors")
    if args.fail_on_tile_budget:
        over_budget = [item for item in all_generated if item.over_soft_tile_limit]
        if over_budget:
            raise SystemExit(f"{len(over_budget)} generated images exceed the soft tile budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
