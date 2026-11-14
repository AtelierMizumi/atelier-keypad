#!/usr/bin/env python3
"""Turn a grayscale picture into four-tone PCB art (a KiCad footprint).

A board has four surfaces you can see, darkest to brightest on a dark mask:

    tone 0  solder mask over bare laminate
    tone 1  solder mask over copper        (a lighter sheen under the mask)
    tone 2  bare copper, mask opened       (gold with ENIG, silver with HASL)
    tone 3  silkscreen                     (white ink)

Rev 0's art used only tone 3 against tone 0. Using all four gives shading.

    python3 art.py IN.png OUT.kicad_mod --width 40 --side B --preview OUT.png
                   [--thresholds 60 120 190] [--pixel 0.15] [--finish enig|hasl]
                   [--mask black|green|blue|white]

Fab limits to respect (JLCPCB standard): silkscreen line >= 0.15 mm, copper
feature >= 0.127 mm, mask web >= 0.1 mm. Keep `--pixel` at 0.15 mm or more and
leave `despeckle` on, so no feature is smaller than two pixels.

Art copper has no net. Keep it away from tracks and give its area a
keep-out for zone fills, or the ground pour will merge with it.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

LAYERS: dict[int, set[str]] = {0: set(), 1: {"Cu"}, 2: {"Cu", "Mask"}, 3: {"SilkS"}}

Tones = list[list[int]]


def quantise(img: Image.Image, thresholds: tuple[int, int, int] = (60, 120, 190)) -> Tones:
    g = img.convert("L")
    w, h = g.size
    px = g.load()
    t1, t2, t3 = thresholds
    return [[0 if v < t1 else 1 if v < t2 else 2 if v < t3 else 3
             for v in (px[x, y] for x in range(w))] for y in range(h)]


def _square_cover(mask: list[list[bool]], k: int) -> list[list[bool]]:
    """Pixels that lie in at least one k x k square made only of True pixels (morphological opening)."""
    h, w = len(mask), len(mask[0]) if mask else 0
    s = [[0] * (w + 1) for _ in range(h + 1)]
    for y in range(h):
        row = 0
        for x in range(w):
            row += mask[y][x]
            s[y + 1][x + 1] = s[y][x + 1] + row
    keep = [[False] * w for _ in range(h)]
    for y in range(h - k + 1):
        for x in range(w - k + 1):
            if s[y + k][x + k] - s[y][x + k] - s[y + k][x] + s[y][x] == k * k:
                for yy in range(y, y + k):
                    keep[yy][x:x + k] = [True] * k
    return keep


def despeckle(tones: Tones, min_px: int = 2) -> Tones:
    """Drop features thinner than `min_px`; dropped pixels fall to the next darker tone."""
    out = [row[:] for row in tones]
    for t in (3, 2, 1):
        keep = _square_cover([[v >= t for v in row] for row in out], min_px)
        for y, row in enumerate(out):
            for x, v in enumerate(row):
                if v >= t and not keep[y][x]:
                    row[x] = t - 1
    return out


def rectangles(tones: Tones, layer: str) -> list[tuple[int, int, int, int]]:
    """Cover the pixels whose tone uses `layer` with few rectangles (x0, y0, x1, y1), end-exclusive."""
    done: list[tuple[int, int, int, int]] = []
    active: dict[tuple[int, int], int] = {}  # (x0, x1) -> start row
    for y, row in enumerate(tones + [[0] * (len(tones[0]) if tones else 0)]):
        runs, x = [], 0
        while x < len(row):
            if layer in LAYERS[row[x]]:
                x0 = x
                while x < len(row) and layer in LAYERS[row[x]]:
                    x += 1
                runs.append((x0, x))
            else:
                x += 1
        current = set(runs)
        for key in list(active):
            if key not in current:
                done.append((key[0], active.pop(key), key[1], y))
        for key in runs:
            active.setdefault(key, y)
    return done


def _num(v: float) -> str:
    return f"{v:.6f}"


def write_footprint(img: Image.Image, path: Path, name: str, width_mm: float,
                    thresholds: tuple[int, int, int] = (60, 120, 190), side: str = "F",
                    min_px: int = 2) -> None:
    tones = despeckle(quantise(img, thresholds), min_px)
    h, w = len(tones), len(tones[0])
    px = width_mm / w
    sign = -1 if side == "B" else 1
    p = side + "."

    def poly(x0, y0, x1, y1, layer):
        xa, xb = sign * (x0 - w / 2) * px, sign * (x1 - w / 2) * px
        ya, yb = (y0 - h / 2) * px, (y1 - h / 2) * px
        pts = " ".join(f"(xy {_num(x)} {_num(y)})" for x, y in ((xa, ya), (xb, ya), (xb, yb), (xa, yb)))
        return f'  (fp_poly (pts {pts}) (stroke (width 0) (type solid)) (fill yes) (layer "{p}{layer}"))'

    lines = [f'(footprint "{name}" (version 20240108) (generator "atelier_pcb_art") (layer "{p}Cu")',
             "  (attr board_only exclude_from_pos_files exclude_from_bom)",
             f'  (property "Reference" "G***" (at 0 0 0) (layer "{p}SilkS") (hide yes)'
             " (effects (font (size 1 1) (thickness 0.15))))",
             f'  (property "Value" "{name}" (at 0 0 0) (layer "{p}Fab") (hide yes)'
             " (effects (font (size 1 1) (thickness 0.15))))"]
    for layer in ("Cu", "Mask", "SilkS"):
        lines += [poly(*r, layer) for r in rectangles(tones, layer)]
    lines.append(")")
    Path(path).write_text("\n".join(lines) + "\n")


MASKS = {"black": ((22, 22, 26), (48, 48, 56)), "green": ((22, 70, 40), (40, 110, 62)),
         "blue": ((10, 40, 110), (30, 70, 160)), "white": ((225, 225, 222), (205, 205, 200))}
FINISH = {"enig": (212, 175, 92), "hasl": (196, 198, 204)}
SILK = {"black": (240, 240, 235), "green": (240, 240, 235), "blue": (240, 240, 235), "white": (20, 20, 20)}


def preview(img: Image.Image, path: Path, thresholds: tuple[int, int, int] = (60, 120, 190),
            finish: str = "enig", mask: str = "black", min_px: int = 2) -> None:
    tones = despeckle(quantise(img, thresholds), min_px)
    colours = [MASKS[mask][0], MASKS[mask][1], FINISH[finish], SILK[mask]]
    out = Image.new("RGB", (len(tones[0]), len(tones)))
    out.putdata([colours[t] for row in tones for t in row])
    out.save(path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("footprint")
    ap.add_argument("--width", type=float, required=True, help="art width in mm")
    ap.add_argument("--pixel", type=float, default=0.15, help="pixel size in mm")
    ap.add_argument("--side", choices=("F", "B"), default="F")
    ap.add_argument("--thresholds", type=int, nargs=3, default=(60, 120, 190))
    ap.add_argument("--name", default="ART")
    ap.add_argument("--preview")
    ap.add_argument("--finish", choices=tuple(FINISH), default="enig")
    ap.add_argument("--mask", choices=tuple(MASKS), default="black")
    a = ap.parse_args()
    img = Image.open(a.image).convert("L")
    w = max(1, round(a.width / a.pixel))
    img = img.resize((w, max(1, round(img.height * w / img.width))), Image.Resampling.LANCZOS)
    write_footprint(img, Path(a.footprint), a.name, a.width, tuple(a.thresholds), a.side)
    if a.preview:
        preview(img, Path(a.preview), tuple(a.thresholds), a.finish, a.mask)


if __name__ == "__main__":
    main()
