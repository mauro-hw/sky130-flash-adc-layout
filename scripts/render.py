#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Mauro Rodriguez Blasco
"""
A picture of a cell of mag/ for the README: every layer of the cell and its subcells in its
colour, labels on the blocks, a legend and a scale bar.

    python3 scripts/render.py CELL [--width 1200] [--out docs/images/CELL.png]

It reads the .mag files directly, applying each subcell's transform, so it needs neither Magic
nor a display (Magic's own 'plot pnm' draws only some layers without one). The labels of the
comparator's and the ADC's blocks are in LABELS; other cells get the legend and the scale bar.
Needs Pillow.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("render.py needs Pillow: pip install pillow")

ROOT = Path(__file__).resolve().parent.parent
MAG = ROOT / "mag"
UNIT = 0.005   # um per internal unit (magscale 1 2)

# Bottom to top: the name in the legend, Magic's layers and the colour (RGBA).
STYLE = [
    ("n-well", ("nwell",), (205, 205, 125, 90)),
    ("diffusion", ("ndiff", "pdiff"), (40, 170, 60, 200)),
    ("well and substrate taps", ("psubdiff", "nsubdiff", "psubdiffcont", "nsubdiffcont"), (120, 200, 230, 200)),
    ("poly", ("poly",), (220, 40, 40, 200)),
    ("resistor", ("xpolyres", "ppolyres"), (235, 125, 35, 230)),
    ("transistor gate", ("nmos", "pmos", "nmoslvt", "pmoslvt", "pmoshvt"), (160, 60, 160, 230)),
    ("local interconnect", ("locali",), (110, 110, 230, 120)),
    ("metal 1", ("metal1",), (90, 160, 250, 110)),
    ("metal 2", ("metal2",), (250, 110, 180, 130)),
    ("contacts and vias", ("ndiffc", "pdiffc", "polycont", "viali", "xpolycontact", "m2contact"), (30, 30, 30, 220)),
]
GROUP = {layer: i for i, (_, layers, _) in enumerate(STYLE) for layer in layers}

# Labels: (title, detail, the point it names in um, the side it goes on).
LABELS = {
    "comparator": [("Bias mirror", "XM8, XM5, XM7", (19.5, 17.2), "right"),
                   ("Second stage", "XM6", (31.0, 14.0), "right"),
                   ("Input pair", "XM1, XM2, common centroid", (20.5, 3.4), "right"),
                   ("Current mirror", "XM3, XM4", (32.5, -6.25), "right"),
                   ("Bias resistor", "1.26 MΩ, ten strips", (-4.5, 4.4), "left")],
    "adc": [(f"Comparator {k}", "", (34.0, (k - 1) * 29.4 + 4.4), "right") for k in range(1, 8)]
           + [("Encoder", "thermometer to 3 bits", (52.5, 104.0), "right"),
              ("Reference ladder", "8 steps, one per comparator", (-37.0, 94.0), "left")],
}
TITLES = {"comparator": "A comparator in SKY130", "adc": "A 3-bit flash ADC in SKY130"}


def font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for folder in ("/usr/share/fonts/dejavu-sans-fonts", "/usr/share/fonts/truetype/dejavu",
                   "/usr/share/fonts/TTF", "/Library/Fonts"):
        if (Path(folder) / name).is_file():
            return ImageFont.truetype(str(Path(folder) / name), size)
    return ImageFont.load_default()


def read(cell: str, cache: dict) -> tuple[list, list]:
    """The rectangles of a cell, as (group, x1, y1, x2, y2), and its subcells with transforms."""
    if cell in cache:
        return cache[cell]
    rects, uses, layer = [], [], None
    lines = (MAG / f"{cell}.mag").read_text().splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"<< (\S+) >>", line)
        if m:
            layer = m.group(1)
        elif line.startswith("rect") and layer != "checkpaint":
            rects.append((GROUP.get(layer, -1), *map(int, line.split()[1:5])))   # -1: not drawn
        elif line.startswith("use "):
            transform = next(l for l in lines[i + 1:] if l.startswith("transform"))
            uses.append((line.split()[1], tuple(map(int, transform.split()[1:7]))))
    cache[cell] = (rects, uses)
    return cache[cell]


def flatten(cell: str) -> list:
    out, cache = [], {}

    def walk(name, t):
        a, b, c, d, e, f = t
        rects, uses = read(name, cache)
        for g, x1, y1, x2, y2 in rects:
            xs, ys = (a * x1 + b * y1 + c, a * x2 + b * y2 + c), (d * x1 + e * y1 + f, d * x2 + e * y2 + f)
            out.append((g, min(xs), min(ys), max(xs), max(ys)))
        for child, (ca, cb, cc, cd, ce, cf) in uses:
            walk(child, (a * ca + b * cd, a * cb + b * ce, a * cc + b * cf + c,
                         d * ca + e * cd, d * cb + e * ce, d * cc + e * cf + f))
    walk(cell, (1, 0, 0, 0, 1, 0))
    return out


def render(cell: str, width: int) -> Image.Image:
    rects = flatten(cell)
    x0, y0 = min(r[1] for r in rects), min(r[2] for r in rects)
    x1, y1 = max(r[3] for r in rects), max(r[4] for r in rects)
    labels = LABELS.get(cell, [])
    left = 330 if any(side == "left" for *_, side in labels) else 40
    right, top, bottom = 360, 110, 190
    s = (width - left - right) / (x1 - x0)
    h = int((y1 - y0) * s)
    img = Image.new("RGBA", (width, h + top + bottom), (255, 255, 255, 255))

    def px(x_um, y_um):
        return left + (x_um / UNIT - x0) * s, top + h - (y_um / UNIT - y0) * s

    for g, (_, _, colour) in enumerate(STYLE):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        for gg, ax, ay, bx, by in rects:
            if gg == g:
                draw.rectangle([px(ax * UNIT, by * UNIT), px(bx * UNIT, ay * UNIT)], fill=colour)
        img = Image.alpha_composite(img, layer)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)
    big, mid, small = font(34, True), font(22, True), font(19)
    draw.text((left, 30), TITLES.get(cell, cell), fill=(0, 0, 0), font=big)
    draw.text((left, 74), f"{(x1 - x0) * UNIT:.1f} × {(y1 - y0) * UNIT:.1f} µm", fill=(80, 80, 80), font=small)
    # labels on each side, from top to bottom, at least 56 px apart, each with a thin line
    # that leaves what it names horizontally and bends to its text
    edge = {"right": left + (x1 - x0) * s + 30, "left": left - 30}
    for side in ("right", "left"):
        mine = sorted((px(*p)[1], px(*p)[0], t, d) for t, d, p, sd in labels if sd == side)
        last = -1e9
        for ay, ax, title, detail in mine:
            ty = max(ay, last + 56)
            last = ty
            ex = edge[side]
            bend = ex - 18 if side == "right" else ex + 18
            draw.line([(ax, ay), (bend, ay), (ex, ty)], fill=(120, 120, 120), width=1)
            tx = ex + 6 if side == "right" else 15
            draw.text((tx, ty - 14), title, fill=(0, 0, 0), font=mid)
            if detail:
                draw.text((tx, ty + 12), detail, fill=(90, 90, 90), font=small)
    # the legend in a band under the drawing, and the scale bar
    lx, ly = left, top + h + 40
    columns = 3
    colw = (width - left - 40) // columns
    for i, (name, _, colour) in enumerate(STYLE):
        x, y = lx + colw * (i % columns), ly + 32 * (i // columns)
        draw.rectangle([x, y, x + 26, y + 20], fill=colour[:3])
        draw.text((x + 36, y - 1), name, fill=(30, 30, 30), font=small)
    bar = 10 if (x1 - x0) * UNIT < 60 else 20
    by = ly + 32 * ((len(STYLE) + columns - 1) // columns) + 10
    draw.rectangle([lx, by, lx + bar * s / UNIT, by + 8], fill=(0, 0, 0))
    draw.text((lx + bar * s / UNIT + 12, by - 6), f"{bar} µm", fill=(0, 0, 0), font=small)
    return img


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    ap.add_argument("cell")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--out")
    args = ap.parse_args()
    if not (MAG / f"{args.cell}.mag").is_file():
        sys.exit(f"No cell {args.cell} in mag/")
    out = Path(args.out) if args.out else ROOT / "docs" / "images" / f"{args.cell}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img = render(args.cell, args.width)
    img.save(out, optimize=True)
    print(f"{out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}: {img.width} × {img.height} px")
    return 0


if __name__ == "__main__":
    sys.exit(main())
