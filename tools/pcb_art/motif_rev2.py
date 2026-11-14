#!/usr/bin/env python3
"""Original artwork for the bottom of the rev 2 board: a moon over a night sea,
with the field lines of the three key magnets rising out of the water.

Drawn in code so it belongs to the project and can be published with it.
Writes a grayscale image whose four gray levels map straight onto the four PCB
tones of art.py (0 laminate, 1 copper under mask, 2 bare copper, 3 silkscreen).

    python3 motif_rev2.py OUT.png [--width-mm 60 --height-mm 34 --pixel 0.15]
"""
from __future__ import annotations

import argparse
import math

from PIL import Image, ImageDraw

GRAY = {0: 0, 1: 90, 2: 160, 3: 255}  # inside art.py's default thresholds (60, 120, 190)


def draw(width_mm: float = 60.0, height_mm: float = 34.0, pixel: float = 0.15, ss: int = 4) -> Image.Image:
    w, h = round(width_mm / pixel), round(height_mm / pixel)
    W, H = w * ss, h * ss
    img = Image.new("L", (W, H), GRAY[0])
    d = ImageDraw.Draw(img)
    horizon = H * 0.62

    # Moon: bare copper disc, with a crescent of copper-under-mask eating into it.
    mx, my, r = W * 0.72, H * 0.30, H * 0.20
    d.ellipse((mx - r, my - r, mx + r, my + r), fill=GRAY[2])
    d.ellipse((mx - r * 0.55, my - r * 1.05, mx + r * 1.45, my + r * 0.95), fill=GRAY[1])
    # A thin silkscreen rim on the lit edge.
    d.arc((mx - r, my - r, mx + r, my + r), 110, 250, fill=GRAY[3], width=max(2, ss * 2))

    # Field lines of three magnets standing on the horizon, like dipoles seen side-on.
    keys = [W * 0.18, W * 0.36, W * 0.54]
    for kx in keys:
        for k in (1, 2, 3, 4):
            a = H * 0.06 * k
            pts = []
            for i in range(0, 181, 3):
                t = math.radians(i)
                # r = a sin^2(theta) is a dipole field line; draw the upper half only
                rr = a * math.sin(t) ** 2 * 2.2
                pts.append((kx + rr * math.cos(t), horizon - rr * math.sin(t)))
            d.line(pts, fill=GRAY[2] if k % 2 else GRAY[1], width=max(2, ss * 2))
        d.rectangle((kx - ss * 3, horizon - ss * 10, kx + ss * 3, horizon), fill=GRAY[3])  # the magnet

    # Sea: wave lines in copper-under-mask, getting closer towards the horizon.
    y, gap = H - ss * 2, ss * 10
    while y > horizon:
        amp = gap * 0.25
        pts = [(x, y + amp * math.sin(x / (gap * 1.7) + y / 37)) for x in range(0, W + 1, ss * 2)]
        d.line(pts, fill=GRAY[1], width=max(2, ss * 2))
        y -= gap
        gap = max(ss * 4, gap * 0.86)

    # Moonlight on the water: broken silkscreen streaks under the moon.
    sy = horizon + ss * 6
    i = 0
    while sy < H - ss * 4:
        half = r * (0.9 - 0.5 * (sy - horizon) / (H - horizon)) * (0.6 + 0.4 * math.sin(i * 1.7))
        d.line((mx - half, sy, mx + half, sy), fill=GRAY[3], width=max(2, ss * 2))
        sy += ss * 7
        i += 1

    d.line((0, horizon, W, horizon), fill=GRAY[2], width=max(2, ss * 2))
    return img.resize((w, h), Image.Resampling.NEAREST)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--width-mm", type=float, default=60.0)
    ap.add_argument("--height-mm", type=float, default=34.0)
    ap.add_argument("--pixel", type=float, default=0.15)
    a = ap.parse_args()
    draw(a.width_mm, a.height_mm, a.pixel).save(a.out)
