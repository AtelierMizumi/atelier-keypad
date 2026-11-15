#!/usr/bin/env python3
"""Sealed case for Atelier rev 2 (Hall effect), generated from hardware/he/circuit.py.

The PCB is inside the case, not a layer of the sandwich:

    z (mm, PCB top = 0)
     4.5  cover      2 mm translucent blue acrylic: switch, button and screw holes only
     2.5  gasket     0.5 mm EVA foam ring, closes the seam under the cover
     2.0  spacer     2 mm ring; a 1.2 mm ledge and screw lugs clamp the board edge from above
     0.0  pcb-ring   2 mm ring around the 1.2 mm board edge, 0.25 mm clearance
    -2.0  lower-wall 5 mm ring; a 1.2 mm ledge carries the board on a 1.0 mm EVA strip
                     squeezed to 0.8 mm
    -7.0  base       3 mm clear acrylic: nut pockets, BOOT hole
   -10.0  pad        1.5 mm self-adhesive silicone, the base outline less 0.5 mm:
                     the whole underside grips the desk and keeps the nuts in
   -11.5  desk

Magnetic switches have no contacts, so the board can be conformally coated all
over; the only openings are the switch holes, the two buttons and the USB slot.
The case sits flat and low: tilted rubber discs met the desk on one edge and let
the case's front edge touch it (docs/superpowers/specs/2026-11-16-rev2-flat-case-grip.md).

    uv run case/generate_he.py        # DXF in case/dxf-he/, model JSON for the site
"""
# /// script
# requires-python = ">=3.10"
# dependencies = ["shapely>=2.0", "ezdxf>=1.1"]
# ///
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hardware" / "he"))
import circuit  # noqa: E402

ARC = 24
WALL = 4.0
LEDGE = 1.2
RING_CLEARANCE = 0.25
LUG_RADIUS = 3.5
SCREW_HOLE = 3.3
NUT_AF = 5.6
NUT_THICKNESS = 2.4
SWITCH_HOLE = 14.0
BUTTON_HOLE = 6.8
BOOT_HOLE = 4.0
USB_SLOT = 13.0
PAD_T = 1.5                     # silicone sheet under the whole base
PAD_INSET = 0.5                 # stays inside the acrylic edge, so it does not peel
PAD_BOOT_HOLE = 6.0             # wider than the base's BOOT hole: room for a toothpick
SCREW_LENGTHS = (10, 12, 14, 16)
UNDER_GASKET = 1.0              # EVA strip on the lower ledge, under the board edge
UNDER_GASKET_COMPRESSED = 0.8   # squeezed 20 % when the screws are tight


@dataclass
class Layer:
    name: str
    thickness: float
    z0: float
    shape: Polygon
    material: str
    label: str
    sub: str


@dataclass
class Screw:
    length: int
    tip_z: float
    nut_engagement: float
    material: str = "nylon"


@dataclass
class Case:
    pcb: Polygon
    layers: list
    screws: list
    switches: list
    buttons: list
    usb: tuple
    boot: tuple
    feet: list                      # none since the flat case: the pad is a layer
    screw: Screw
    bottom_parts: dict = field(default_factory=dict)

    def layer(self, name: str) -> Layer:
        return next(l for l in self.layers if l.name == name)


def _rounded(x0, y0, x1, y1, r) -> Polygon:
    return box(x0, y0, x1, y1).buffer(-r, quad_segs=ARC).buffer(r, quad_segs=ARC)


def _single(shape) -> Polygon:
    if isinstance(shape, MultiPolygon):
        shape = max(shape.geoms, key=lambda g: g.area)
    return shape


def design() -> Case:
    pcb = _rounded(*circuit.OUTLINE, circuit.OUTLINE_RADIUS)
    outer = pcb.buffer(WALL, quad_segs=ARC)
    parts = {p.ref: p for p in circuit.parts()}
    usb = (parts["J1"].x, parts["J1"].y)
    boot = (parts["SW3"].x, parts["SW3"].y)
    buttons = [(parts[r].x + 3.25, parts[r].y + 2.25) for r in ("SW1", "SW2")]  # THT origin is pin 1
    switches = [circuit.KEYS[k] for k in circuit.KEY_ORDER]
    screws = list(circuit.HOLES)

    holes = unary_union([Point(h).buffer(SCREW_HOLE / 2, quad_segs=ARC) for h in screws])
    lugs = unary_union([Point(h).buffer(LUG_RADIUS, quad_segs=ARC) for h in screws])
    slot = box(usb[0] - USB_SLOT / 2, outer.bounds[1] - 1, usb[0] + USB_SLOT / 2, usb[1])

    ledge_ring = outer.difference(pcb.buffer(-LEDGE, quad_segs=ARC)).union(lugs)
    lower_wall = _single(ledge_ring.difference(slot).difference(holes))
    spacer = _single(ledge_ring.difference(slot).difference(holes))
    pcb_ring = _single(outer.difference(pcb.buffer(RING_CLEARANCE, quad_segs=ARC)).difference(slot))

    cover = outer.difference(holes)
    for x, y in switches:
        cover = cover.difference(box(x - SWITCH_HOLE / 2, y - SWITCH_HOLE / 2, x + SWITCH_HOLE / 2, y + SWITCH_HOLE / 2))
    for x, y in buttons:
        cover = cover.difference(box(x - BUTTON_HOLE / 2, y - BUTTON_HOLE / 2, x + BUTTON_HOLE / 2, y + BUTTON_HOLE / 2))

    base = outer
    for x, y in screws:
        r = NUT_AF / 2 / math.cos(math.pi / 6)
        base = base.difference(Polygon([(x + r * math.cos(math.radians(a)), y + r * math.sin(math.radians(a)))
                                        for a in range(0, 360, 60)]))
    base = base.difference(Point(boot).buffer(BOOT_HOLE / 2, quad_segs=ARC))
    pad = outer.buffer(-PAD_INSET, quad_segs=ARC).difference(Point(boot).buffer(PAD_BOOT_HOLE / 2, quad_segs=ARC))

    lower_top = -(circuit.THICKNESS + UNDER_GASKET_COMPRESSED)   # PCB top is z = 0
    ring_t = round(-lower_top, 3)                                # the ring fills board + strip
    stack = [
        ("pad", PAD_T, pad, "silicone", "Grip pad", f"{PAD_T:g} mm silicone sheet, the whole underside"),
        ("base", 3.0, base, "clear", "Base", "3 mm clear acrylic; nut pockets, BOOT hole"),
        ("lower-wall", 5.0, lower_wall, "blue", "Lower wall", "5 mm blue acrylic; ledge carries the board"),
        ("pcb-ring", ring_t, pcb_ring, "blue", "Board ring", "2 mm blue acrylic around the board edge"),
        ("spacer", 2.0, spacer, "blue", "Spacer", "2 mm blue acrylic; ledge clamps the board"),
        ("gasket", 0.5, spacer, "eva", "Gasket", "0.5 mm EVA foam, seals the cover"),
        ("cover", 2.0, _single(cover), "blue", "Cover", "2 mm translucent blue; the only top surface"),
    ]
    z = lower_top - 5.0 - 3.0 - PAD_T
    layers = []
    for name, t, shape, material, label, sub in stack:
        layers.append(Layer(name, t, z, shape, material, label, sub))
        z += t

    top = layers[-1].z0 + layers[-1].thickness
    base_z0 = layers[1].z0                     # the base: nut pockets; layers[0] is the pad
    nut_top = base_z0 + NUT_THICKNESS
    best = None
    for length in SCREW_LENGTHS:
        tip = top - length
        if tip >= base_z0:  # never below the base, so it cannot scratch the desk
            best = Screw(length, round(tip, 3), round(nut_top - max(tip, base_z0), 3))
    if best is None:
        raise ValueError("no screw length fits")

    feet: list = []

    bottom = {p.ref: (p.x, p.y) for p in parts.values() if p.side == "B"}
    return Case(pcb, layers, screws, switches, buttons, usb, boot, feet, best, bottom)


# ----------------------------------------------------------------- output

def _model(case: Case):
    x0, y0, x1, y1 = case.pcb.bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    pt = lambda p: [round(p[0] - cx, 3), round(cy - p[1], 3)]
    rings = lambda shape: ([pt(c) for c in list(shape.exterior.coords)[:-1]],
                           [[pt(c) for c in list(r.coords)[:-1]] for r in shape.interiors])
    return cx, cy, pt, rings


def write_model(case: Case, path: Path) -> Path:
    cx, cy, pt, rings = _model(case)
    layers = []
    for i, l in enumerate(case.layers):
        outer, holes = rings(l.shape)
        layers.append({"name": l.name, "thickness": l.thickness, "z0": round(l.z0, 3), "material": l.material,
                       "label": l.label, "sub": l.sub, "order": i - 3 if i < 3 else i - 2,
                       "outer": outer, "holes": holes})
    data = {
        "generic": True, "units": "mm",
        "origin": "board centre, PCB top surface at z = 0, +Y towards the USB edge",
        "pcb": {"thickness": circuit.THICKNESS, "outline": rings(case.pcb)[0], "kicad_centre": [cx, cy], "order": 0.0,
                "label": "PCB", "sub": f"{circuit.THICKNESS:g} mm, coated; sensors on the underside, under each switch"},
        "layers": layers,
        "switches": [pt(p) for p in case.switches],
        "switch_label": ["Magnetic switches", "3 × Gateron Magnetic Jade, PCB mount"],
        "buttons": [pt(p) for p in case.buttons],
        "screws": [pt(p) for p in case.screws],
        "usb": pt(case.usb),
        "feet": [pt((x, y)) + [h] for x, y, h in case.feet],
        "tilt_deg": 0,
        "screw": {"size": "M3 nylon", "length": case.screw.length, "nut_engagement": case.screw.nut_engagement,
                  "nut_thickness": NUT_THICKNESS},
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":")))
    return path


def write_dxf(case: Case, out_dir: Path) -> list[Path]:
    import ezdxf

    from scale_bar import add_scale_bar
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for layer in case.layers:
        if layer.material == "eva":
            continue  # cut by hand from foam tape, using the spacer outline
        doc = ezdxf.new("R2010", units=ezdxf.units.MM)
        msp = doc.modelspace()
        x0, _, _, y1 = case.layer("cover").shape.bounds
        conv = lambda coords: [(x - x0, y1 - y) for x, y in coords]  # CAD: y up, origin bottom-left
        msp.add_lwpolyline(conv(layer.shape.exterior.coords), close=True)
        for ring in layer.shape.interiors:
            msp.add_lwpolyline(conv(ring.coords), close=True)
        path = out_dir / f"atelier-he-{layer.name}-{layer.thickness:g}mm-{layer.material}.dxf"
        add_scale_bar(doc, msp, origin=(0.0, -8.0))
        doc.saveas(path)
        written.append(path)
    return written


def main() -> None:
    case = design()
    files = write_dxf(case, ROOT / "case" / "dxf-he")
    write_model(case, ROOT / "site" / "assets" / "case-he.json")
    print(f"wrote {len(files)} DXF files and site/assets/case-he.json; "
          f"M3 x {case.screw.length} nylon, flat on a {PAD_T:g} mm silicone pad")


if __name__ == "__main__":
    main()
