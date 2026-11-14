"""Spec for turning a grayscale picture into four-tone PCB art.

A PCB has four visibly different surfaces, darkest to brightest on a dark
solder mask:
  0  mask over bare laminate
  1  mask over copper (copper under the mask shows as a lighter sheen)
  2  bare copper, mask opened (gold with ENIG, silver with HASL)
  3  silkscreen (white ink)
The tool posterises the picture into those four tones and writes a KiCad
footprint whose layers reproduce them.

    cd tools/pcb_art && uv run --no-project --with pytest --with pillow pytest -q
"""
import pytest
from PIL import Image

import art


def strip(levels, w=4, h=2):
    """An image of vertical bands, `w` pixels each, one per gray level."""
    img = Image.new("L", (w * len(levels), h))
    for i, g in enumerate(levels):
        for x in range(i * w, (i + 1) * w):
            for y in range(h):
                img.putpixel((x, y), g)
    return img


def test_quantise_maps_dark_to_0_and_light_to_3():
    tones = art.quantise(strip([0, 80, 170, 255]), thresholds=(64, 128, 200))
    assert [tones[0][x] for x in (0, 4, 8, 12)] == [0, 1, 2, 3]


def test_layers_for_each_tone():
    assert art.LAYERS[0] == set()
    assert art.LAYERS[1] == {"Cu"}
    assert art.LAYERS[2] == {"Cu", "Mask"}
    assert art.LAYERS[3] == {"SilkS"}


def test_rectangles_cover_exactly_the_pixels_of_a_layer():
    tones = art.quantise(strip([0, 80, 170, 255]), thresholds=(64, 128, 200))
    for layer in ("Cu", "Mask", "SilkS"):
        rects = art.rectangles(tones, layer)
        covered = {(x, y) for x0, y0, x1, y1 in rects for x in range(x0, x1) for y in range(y0, y1)}
        expected = {(x, y) for y, row in enumerate(tones) for x, t in enumerate(row) if layer in art.LAYERS[t]}
        assert covered == expected, layer


def test_rectangles_merge_runs_into_few_polygons():
    tones = art.quantise(strip([255], w=50, h=40), thresholds=(64, 128, 200))
    assert len(art.rectangles(tones, "SilkS")) == 1


def test_specks_smaller_than_the_minimum_feature_are_removed():
    img = Image.new("L", (20, 20), 0)
    img.putpixel((10, 10), 255)  # a single white pixel: below 2 x 2 pixels it cannot be printed
    tones = art.despeckle(art.quantise(img, thresholds=(64, 128, 200)), min_px=2)
    assert all(t == 0 for row in tones for t in row)


def test_footprint_has_the_right_layers_and_size(tmp_path):
    out = tmp_path / "art.kicad_mod"
    art.write_footprint(strip([0, 80, 170, 255], w=10, h=10), out, name="ART", width_mm=8.0,
                        thresholds=(64, 128, 200), side="F")
    text = out.read_text()
    assert text.startswith('(footprint "ART"')
    for layer in ('"F.Cu"', '"F.Mask"', '"F.SilkS"'):
        assert f"(layer {layer})" in text
    assert "board_only" in text and "exclude_from_bom" in text
    import re
    coords = [float(v) for pair in re.findall(r"\(xy ([-0-9.]+) ([-0-9.]+)\)", text) for v in pair]
    assert coords and max(abs(v) for v in coords) <= 4.0 + 1e-6


def test_bottom_side_footprint_uses_bottom_layers_and_mirrors(tmp_path):
    out = tmp_path / "art_b.kicad_mod"
    img = Image.new("L", (10, 10), 0)
    for y in range(10):
        for x in (0, 1):
            img.putpixel((x, y), 255)  # white column on the left, 2 px: the smallest printable feature
    art.write_footprint(img, out, name="ART", width_mm=10.0, thresholds=(64, 128, 200), side="B")
    text = out.read_text()
    assert '(layer "B.SilkS")' in text and '"F.' not in text.split("(attr")[1]
    # Seen from below the left column must appear on the left, so in board coordinates it is on the right.
    assert "(xy 4.000000" in text or "(xy 5.000000" in text


def test_preview_shows_four_distinct_tones(tmp_path):
    p = tmp_path / "preview.png"
    art.preview(strip([0, 80, 170, 255], w=10, h=10), p, thresholds=(64, 128, 200), finish="enig", mask="black")
    img = Image.open(p).convert("RGB")
    colours = {img.getpixel((5 + 10 * i, 5)) for i in range(4)}
    assert len(colours) == 4

