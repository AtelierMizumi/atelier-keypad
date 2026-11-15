"""A 50 mm scale bar for laser-cut DXF files.

A file exported or imported at the wrong scale cuts a case that looks right and
fits nothing. The bar sits on the NOTES layer, which is never cut, so the shop
can measure it in their software before cutting.
"""
from __future__ import annotations

LENGTH = 50.0
LABEL = "50 mm, check before cutting"


def add_scale_bar(doc, msp, origin: tuple[float, float] = (0.0, -12.0)) -> None:
    if "NOTES" not in doc.layers:
        doc.layers.add("NOTES", color=8)   # grey: do not cut
    x, y = origin
    msp.add_line((x, y), (x + LENGTH, y), dxfattribs={"layer": "NOTES"})
    msp.add_text(LABEL, height=2.5, dxfattribs={"layer": "NOTES"}).set_placement((x, y - 4.0))
