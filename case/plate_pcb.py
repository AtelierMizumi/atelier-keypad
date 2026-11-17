#!/usr/bin/env python3
"""The rev 1 switch plate as a KiCad board: an Edge.Cuts outline and nothing else.

    uv run --quiet --no-project --with shapely --with ezdxf case/plate_pcb.py <out.kicad_pcb>

The plate is 1.6 mm FR4 ordered as a second PCB (docs/rev1-board.md), so the fab
house wants Gerbers, not a DXF. scripts/fab.sh rev1 runs this, then kicad-cli
turns the file into Gerbers. The geometry is the case model's plate, in KiCad
board coordinates, so the cut-outs follow the rev 1 board exactly.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

from shapely.geometry import Polygon

import generate as g

STROKE = 0.05


def plate_shape() -> Polygon:
    board = g.load_board(g.PCB_FILE_REV1)
    return g.design(board, g.params_for(board)).layer("plate").shape


def _block(text: str, head: str) -> str:
    """The balanced s-expression starting at `(head`, copied as written."""
    start = text.index(f"({head}")
    depth = 0
    for i in range(start, len(text)):
        depth += {"(": 1, ")": -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i + 1]
    raise ValueError(f"unbalanced ({head} block")


def _stroke() -> str:
    return f'(stroke (width {STROKE}) (type solid)) (fill no) (layer "Edge.Cuts") (uuid "{uuid.uuid4()}")'


def _poly(coords) -> str:
    pts = " ".join(f"(xy {x:.4f} {y:.4f})" for x, y in list(coords)[:-1])
    return f"\t(gr_poly (pts {pts}) {_stroke()})"


def _ring(coords) -> str:
    circle = g._is_circle(coords)
    if circle:
        cx, cy, r = circle
        return f"\t(gr_circle (center {cx:.4f} {cy:.4f}) (end {cx + r:.4f} {cy:.4f}) {_stroke()})"
    return _poly(coords)


def write_plate_pcb(shape: Polygon, path: Path, thickness: float = 1.6) -> Path:
    # Layer table copied from the rev 1 board, so KiCad reads both files the same way.
    layers = _block(g.PCB_FILE_REV1.read_text(), "layers")
    items = [_poly(shape.exterior.coords)] + [_ring(r.coords) for r in shape.interiors]
    text = "\n".join([
        "(kicad_pcb",
        "\t(version 20260206)",
        '\t(generator "pcbnew")',
        '\t(generator_version "10.0")',
        f"\t(general (thickness {thickness:g}) (legacy_teardrops no))",
        '\t(paper "A4")',
        f"\t{layers}",
        *items,
        ")",
        "",
    ])
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: plate_pcb.py <out.kicad_pcb>")
    print(write_plate_pcb(plate_shape(), Path(sys.argv[1])))


if __name__ == "__main__":
    main()
