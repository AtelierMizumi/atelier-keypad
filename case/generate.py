#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["shapely>=2.0", "ezdxf>=1.1"]
# ///
"""Generates the Atelier6K stacked acrylic case from the KiCad board file.

    uv run case/generate.py           # rev 0 board
    uv run case/generate.py --rev1    # rev 1 board: FR4 plate, MCU module under the PCB

The case follows the PCB outline exactly and uses the PCB itself as one layer
of the stack, so the four M3 screws clamp acrylic and PCB in a single column
and no dimension depends on two stacks adding up to the same height:

    plate         3 mm   switch plate, top surface 5.0 mm above the PCB
    top-frame     2 mm   spacer ring between PCB and plate
    (PCB)
    bottom-frame  5 mm   ring around the underside components, diffuses underglow
    base          3 mm   bottom, with hex pockets that hold the M3 nuts

Every position (outline, screws, switches, buttons, USB, component keep-outs)
is read from the board file, so the case stays in step with the PCB.
"""
from __future__ import annotations

import json
import sys
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import ezdxf
from ezdxf import units
from shapely import affinity
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
PCB_FILE = ROOT / "hardware" / "atelier6k" / "atelier6k.kicad_pcb"
PCB_FILE_REV1 = ROOT / "hardware" / "rev1" / "atelier6k-rev1.kicad_pcb"

ARC = 24  # segments per quarter circle when curves are turned into polylines


# --- parameters --------------------------------------------------------------

@dataclass(frozen=True)
class Params:
    t_base: float = 3.0
    t_bottom_frame: float = 5.0
    t_top_frame: float = 2.0
    t_plate: float = 3.0

    wall: float = 3.0            # frame wall width
    lug_radius: float = 5.0      # material around each screw inside the frames
    clearance: float = 0.5       # gap between a frame and any component courtyard
    fillet: float = 1.0          # inside corner radius of the frames

    screw_hole: float = 3.2      # M3 clearance
    nut_af: float = 5.6          # M3 nut is 5.5 mm across flats
    nut_thickness: float = 2.4

    mx_cutout: float = 14.0      # Cherry MX plate cut-out
    mx_corner: float = 0.3
    tact_cutout: float = 6.8     # 6 x 6 mm tact switch body passes through the plate
    tact_corner: float = 0.6
    usb_bay: float = 10.6        # HRO receptacle is 8.94 mm wide
    usb_depth: float = 7.35      # receptacle body length from its mouth
    reset_hole: float = 4.0

    washer: float = 0.0          # M3 washer between top frame and plate, per screw
    plate_material: str = "clear"
    module_hole: float = 4.0     # access holes for the MCU module's BOOT and RESET buttons

    screw_lengths: tuple = (8, 10, 12, 14, 16, 20)


# --- reading the KiCad board -------------------------------------------------

def _parse_sexpr(text: str):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|\(|\)|[^\s()]+', text)
    stack: list = [[]]
    for tok in tokens:
        if tok == "(":
            stack.append([])
        elif tok == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(tok[1:-1] if tok.startswith('"') else tok)
    return stack[0][0]


def _kids(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


@dataclass
class Board:
    outline: Polygon
    corner_radius: float
    thickness: float
    mount_holes: list
    mx: list
    tact: list
    usb: tuple | None
    reset: tuple | None
    keepouts_top: dict = field(default_factory=dict)
    keepouts_bottom: dict = field(default_factory=dict)
    module: tuple | None = None          # rev 1: middle of the MCU module's USB end
    module_buttons: list = field(default_factory=list)

    @property
    def centre(self):
        minx, miny, maxx, maxy = self.outline.bounds
        return ((minx + maxx) / 2, (miny + maxy) / 2)


def _footprint_keepouts(fp, to_board, fp_rot):
    """Bounding boxes of a footprint's pads, courtyard and fab outline per side."""
    pts = {"F": [], "B": []}
    for pad in _kids(fp, "pad"):
        at = _kids(pad, "at")[0][1:]
        px, py = float(at[0]), float(at[1])
        prot = float(at[2]) if len(at) > 2 else 0.0
        sx, sy = (float(v) for v in _kids(pad, "size")[0][1:3])
        if round((prot - fp_rot) / 90) % 2:
            sx, sy = sy, sx
        layers = " ".join(_kids(pad, "layers")[0][1:])
        for side in "FB":
            if f"{side}.Cu" in layers or "*.Cu" in layers:
                for dx in (-sx / 2, sx / 2):
                    for dy in (-sy / 2, sy / 2):
                        pts[side].append(to_board(px + dx, py + dy))
    for kind in ("fp_line", "fp_rect", "fp_circle", "fp_poly", "fp_arc"):
        for item in _kids(fp, kind):
            layer = _kids(item, "layer")[0][1]
            side, _, name = layer.partition(".")
            if name not in ("CrtYd", "Fab") or side not in pts:
                continue
            raw = [c[1:3] for c in item[1:] if isinstance(c, list) and c[0] in ("start", "end", "mid", "center")]
            for poly in _kids(item, "pts"):
                raw += [c[1:3] for c in poly[1:] if isinstance(c, list) and c[0] == "xy"]
            xy = [(float(a), float(b)) for a, b in raw]
            if kind == "fp_circle" and len(xy) >= 2:
                (cx, cy), edge = xy[0], xy[1]
                r = math.dist((cx, cy), edge)
                xy = [(cx - r, cy - r), (cx + r, cy + r), (cx - r, cy + r), (cx + r, cy - r)]
            pts[side] += [to_board(x, y) for x, y in xy]
    out = {}
    for side, p in pts.items():
        if p:
            xs, ys = [q[0] for q in p], [q[1] for q in p]
            out[side] = box(min(xs), min(ys), max(xs), max(ys))
    return out


def load_board(path: Path = PCB_FILE) -> Board:
    root = _parse_sexpr(Path(path).read_text())

    xs, ys, radius = [], [], 0.0
    for kind in ("gr_line", "gr_arc", "gr_rect"):
        for item in _kids(root, kind):
            if _kids(item, "layer")[0][1] != "Edge.Cuts":
                continue
            pts = {c[0]: (float(c[1]), float(c[2])) for c in item[1:]
                   if isinstance(c, list) and c[0] in ("start", "end", "mid")}
            xs += [p[0] for p in pts.values()]
            ys += [p[1] for p in pts.values()]
            if kind == "gr_arc":
                radius = max(radius, abs(pts["start"][0] - pts["end"][0]))
    if not xs:
        raise ValueError("no Edge.Cuts outline found")
    outline = box(min(xs) + radius, min(ys) + radius, max(xs) - radius, max(ys) - radius)
    outline = outline.buffer(radius, quad_segs=ARC) if radius else outline

    thickness = float(_kids(_kids(root, "general")[0], "thickness")[0][1])
    board = Board(outline, radius, thickness, [], [], [], None, None)

    for fp in _kids(root, "footprint"):
        lib = fp[1]
        ref = next((p[2] for p in _kids(fp, "property") if p[1] == "Reference"), "?")
        at = _kids(fp, "at")[0][1:]
        ax, ay = float(at[0]), float(at[1])
        rot = float(at[2]) if len(at) > 2 else 0.0
        th = math.radians(rot)

        def to_board(x, y, ax=ax, ay=ay, th=th):
            return (ax + x * math.cos(th) + y * math.sin(th),
                    ay - x * math.sin(th) + y * math.cos(th))

        if "MountingHole" in lib:
            board.mount_holes.append((ax, ay))
            continue
        if "Cherry-MX" in lib or "MXOnly" in lib:
            board.mx.append((ax, ay))
        elif "RP2040-Zero" in lib:
            # Under the board, USB end at the footprint origin. BOOT and RESET sit
            # 5.0 mm either side of the centre line, 16.2 mm from the USB end
            # (scaled from Waveshare's drawing, not measured on a module).
            board.module = (ax, ay)
            board.module_buttons = [(ax - 5.0, ay + 16.2), (ax + 5.0, ay + 16.2)]
        elif "SW_PUSH_6mm" in lib:
            board.tact.append(to_board(3.25, 2.25))  # centre of the 6.5 x 4.5 pin pattern
        elif "TYPE-C" in lib.upper():
            # Footprint origin is the receptacle mouth; the body runs towards the pads.
            if to_board(0, -1)[1] <= ay:
                raise ValueError("case generator expects the USB receptacle on the top edge")
            board.usb = (ax, ay)
        elif "SKQG" in lib or ref == "SW4":
            board.reset = (ax, ay)

        for side, shape in _footprint_keepouts(fp, to_board, rot).items():
            (board.keepouts_top if side == "F" else board.keepouts_bottom)[ref] = shape

    board.mount_holes.sort()
    board.mx.sort(key=lambda p: (round(p[1]), p[0]))
    board.tact.sort(key=lambda p: p[1])
    return board


# --- the design --------------------------------------------------------------

@dataclass
class Layer:
    name: str
    thickness: float
    z0: float            # bottom surface, mm, with the PCB top surface at z = 0
    shape: Polygon
    material: str
    purpose: str


@dataclass
class Screw:
    length: int
    nut_engagement: float
    recess_from_bottom: float


@dataclass
class Case:
    board: Board
    params: Params
    layers: list
    screw: Screw
    washer: float = 0.0

    def layer(self, name: str) -> Layer:
        return next(l for l in self.layers if l.name == name)

    @property
    def height(self) -> float:
        return self.layers[-1].z0 + self.layers[-1].thickness - self.layers[0].z0


def _square(x, y, side, corner):
    half = side / 2
    sq = box(x - half, y - half, x + half, y + half)
    return sq.buffer(-corner).buffer(corner, quad_segs=ARC) if corner else sq


def _hexagon(x, y, across_flats):
    r = across_flats / 2 / math.cos(math.pi / 6)
    return Polygon([(x + r * math.cos(math.radians(a)), y + r * math.sin(math.radians(a)))
                    for a in range(0, 360, 60)])


def _single(shape) -> Polygon:
    if isinstance(shape, MultiPolygon):
        shape = max(shape.geoms, key=lambda g: g.area)
    return shape


def _usb_bay(board: Board, p: Params, width: float, corner: float = 0.0) -> Polygon:
    ux, uy = board.usb
    top = board.outline.bounds[1]
    bay = box(ux - width / 2, top - 5, ux + width / 2, uy + p.usb_depth + p.clearance)
    return bay.buffer(-corner).buffer(corner, quad_segs=ARC) if corner else bay


def _frame(board: Board, p: Params, keepouts: dict) -> Polygon:
    holes = [Point(h) for h in board.mount_holes]
    ring = board.outline.difference(board.outline.buffer(-p.wall, quad_segs=ARC))
    lugs = unary_union([h.buffer(p.lug_radius, quad_segs=ARC) for h in holes])
    body = ring.union(lugs).intersection(board.outline)
    # Fillet the inside corners where the lugs meet the walls.
    body = body.buffer(p.fillet, quad_segs=ARC).buffer(-p.fillet, quad_segs=ARC).intersection(board.outline)

    relief = unary_union([k.buffer(p.clearance, quad_segs=ARC) for k in keepouts.values()])
    body = body.difference(relief)
    if board.usb:
        body = body.difference(_usb_bay(board, p, p.usb_bay))
    # Drop slivers and soften the corners the reliefs leave behind.
    body = _single(body.buffer(-0.4, quad_segs=ARC).buffer(0.4, quad_segs=ARC))
    for h in holes:
        body = body.difference(h.buffer(p.screw_hole / 2, quad_segs=ARC))
    return _single(body)


def design(board: Board, p: Params = Params()) -> Case:
    holes = [Point(h) for h in board.mount_holes]
    screw_holes = unary_union([h.buffer(p.screw_hole / 2, quad_segs=ARC) for h in holes])

    plate = board.outline.difference(screw_holes)
    for x, y in board.mx:
        plate = plate.difference(_square(x, y, p.mx_cutout, p.mx_corner))
    for x, y in board.tact:
        plate = plate.difference(_square(x, y, p.tact_cutout, p.tact_corner))
    if board.usb:
        plate = plate.difference(_usb_bay(board, p, p.usb_bay, corner=1.0))
    plate = _single(plate)

    top_frame = _frame(board, p, board.keepouts_top)
    bottom_frame = _frame(board, p, board.keepouts_bottom)

    base = board.outline
    for x, y in board.mount_holes:
        base = base.difference(_hexagon(x, y, p.nut_af))
    if board.reset:
        base = base.difference(Point(board.reset).buffer(p.reset_hole / 2, quad_segs=ARC))
    for xy in board.module_buttons:
        base = base.difference(Point(xy).buffer(p.module_hole / 2, quad_segs=ARC))

    z_pcb_bottom = -board.thickness
    z_bottom_frame = z_pcb_bottom - p.t_bottom_frame
    z_base = z_bottom_frame - p.t_base
    layers = [
        Layer("base", p.t_base, z_base, base, "clear",
              "Bottom. Hex pockets hold the M3 nuts; the small hole reaches the reset button."),
        Layer("bottom-frame", p.t_bottom_frame, z_bottom_frame, bottom_frame, "frosted",
              "Ring around the underside parts. Frosted acrylic spreads the underglow."),
        Layer("top-frame", p.t_top_frame, 0.0, top_frame, "clear",
              "Spacer between PCB and plate; sets the switch height."),
        Layer("plate", p.t_plate, p.t_top_frame + p.washer, plate, p.plate_material,
              "Switch plate. Top surface is 5.0 mm above the PCB, the Cherry MX seating height."
              if not p.washer else
              f"Switch plate, a {p.t_plate:g} mm FR4 board the switches clip into. "
              f"A {p.washer:g} mm M3 washer on each screw sets its height."),
    ]
    if board.module:
        layers[0].purpose = ("Bottom. Hex pockets hold the M3 nuts; the two small holes reach "
                             "the module's BOOT and RESET buttons.")
        layers[1].purpose = ("Ring around the underside parts, open at the top edge for the MCU "
                             "module and its USB-C socket. Frosted acrylic spreads the underglow.")

    z_top = p.t_top_frame + p.washer + p.t_plate
    base_top = z_base + p.t_base
    best = None
    for length in p.screw_lengths:
        tip = z_top - length
        recess = tip - z_base
        if recess >= 0:
            best = Screw(length, round(min(p.nut_thickness, base_top - tip), 3), round(recess, 3))
    if best is None:
        raise ValueError("no standard screw length fits the stack")
    return Case(board, p, layers, best, p.washer)


def params_for(board: Board) -> Params:
    """Rev 1 boards (MCU module under the PCB) get an FR4 plate on a 3 mm frame plus washers."""
    if board.module:
        return Params(t_top_frame=3.0, t_plate=1.6, washer=0.5, plate_material="fr4")
    return Params()


# --- output ------------------------------------------------------------------

def _is_circle(coords):
    pts = list(coords)[:-1]
    if len(pts) < 16:
        return None
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    radii = [math.hypot(x - cx, y - cy) for x, y in pts]
    r = sum(radii) / len(radii)
    return (cx, cy, r) if max(radii) - min(radii) < 1e-3 else None


def _to_cad(shape, board: Board, dx=0.0, dy=0.0):
    """KiCad has Y pointing down. Flip it so the DXF reads as a normal top view,
    with the part's lower-left corner at (dx, dy)."""
    minx, _, _, maxy = board.outline.bounds
    return affinity.affine_transform(shape, [1, 0, 0, -1, dx - minx, dy + maxy])


def _emit(msp, shape: Polygon, suffix=""):
    msp.add_lwpolyline(list(shape.exterior.coords)[:-1], close=True,
                       dxfattribs={"layer": f"CUT-OUTLINE{suffix}"})
    for ring in shape.interiors:
        circle = _is_circle(ring.coords)
        if circle:
            cx, cy, r = circle
            msp.add_circle((cx, cy), round(r, 4), dxfattribs={"layer": f"CUT-INNER{suffix}"})
        else:
            msp.add_lwpolyline(list(ring.coords)[:-1], close=True,
                               dxfattribs={"layer": f"CUT-INNER{suffix}"})


def _new_doc(suffixes=("",)):
    doc = ezdxf.new("R2010", setup=True)
    doc.units = units.MM
    doc.header["$MEASUREMENT"] = 1
    for s in suffixes:
        doc.layers.add(f"CUT-OUTLINE{s}", color=1)   # red
        doc.layers.add(f"CUT-INNER{s}", color=5)     # blue: cut these first
    doc.layers.add("NOTES", color=8)                 # grey: do not cut
    return doc


def _material(layer: Layer) -> str:
    return "FR4 (order as a PCB)" if layer.material == "fr4" else f"{layer.material} acrylic"


def _label(layer: Layer) -> str:
    return f"{layer.name}  {layer.thickness:g} mm  {_material(layer)}  x1"


def write_dxf(case: Case, out_dir: Path) -> list:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    board, files = case.board, []
    width = board.outline.bounds[2] - board.outline.bounds[0]

    for layer in case.layers:
        doc = _new_doc()
        msp = doc.modelspace()
        _emit(msp, _to_cad(layer.shape, board))
        msp.add_text(_label(layer), height=2.5, dxfattribs={"layer": "NOTES"}).set_placement((0, -6))
        path = out_dir / f"atelier6k-case-{layer.name}-{layer.thickness:g}mm.dxf"
        doc.saveas(path)
        files.append(path)

    # Overview sheet: the parts side by side, one DXF layer pair per thickness.
    ordered = sorted(case.layers, key=lambda l: (l.thickness, l.name))
    suffixes = sorted({f"-{l.thickness:g}mm" for l in ordered})
    doc = _new_doc(suffixes)
    msp = doc.modelspace()
    for i, layer in enumerate(ordered):
        dx = i * (width + 8.0)
        _emit(msp, _to_cad(layer.shape, board, dx=dx), suffix=f"-{layer.thickness:g}mm")
        msp.add_text(_label(layer), height=2.5, dxfattribs={"layer": "NOTES"}).set_placement((dx, -6))
    path = out_dir / "atelier6k-case-all.dxf"
    doc.saveas(path)
    files.append(path)
    return files


def _rings(shape, board: Board):
    """Polygon as rings in model coordinates: origin at the board centre, Y up."""
    cx, cy = board.centre
    conv = lambda coords: [[round(x - cx, 3), round(cy - y, 3)] for x, y in list(coords)[:-1]]
    return conv(shape.exterior.coords), [conv(r.coords) for r in shape.interiors]


def write_model(case: Case, path: Path) -> Path:
    board = case.board
    cx, cy = board.centre
    pt = lambda p: [round(p[0] - cx, 3), round(cy - p[1], 3)]
    layers = []
    for layer in case.layers:
        outer, holes = _rings(layer.shape, board)
        layers.append({"name": layer.name, "thickness": layer.thickness, "z0": round(layer.z0, 3),
                       "material": layer.material, "purpose": layer.purpose,
                       "outer": outer, "holes": holes})
    outer, _ = _rings(board.outline, board)
    data = {
        "units": "mm",
        "origin": "board centre, PCB top surface at z = 0, +Y towards the USB edge",
        "pcb": {"thickness": board.thickness, "outline": outer, "kicad_centre": [cx, cy]},
        "layers": layers,
        "switches": [pt(p) for p in board.mx],
        "buttons": [pt(p) for p in board.tact],
        "screws": [pt(p) for p in board.mount_holes],
        "usb": pt(board.usb) if board.usb else None,
        "module": pt(board.module) if board.module else None,
        "module_buttons": [pt(b) for b in board.module_buttons],
        "washer": case.washer,
        "screw": {"size": "M3", "length": case.screw.length,
                  "nut_engagement": case.screw.nut_engagement,
                  "recess_from_bottom": case.screw.recess_from_bottom,
                  "nut_thickness": case.params.nut_thickness},
        "height": round(case.height, 3),
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":")))
    return path


_FILL = {"clear": "#bfe3f5", "frosted": "#e9eef2", "fr4": "#9fcfa8"}


def write_svg(case: Case, path: Path) -> Path:
    """2D drawing of the four parts, top view, in stacking order."""
    board = case.board
    minx, miny, maxx, maxy = board.outline.bounds
    w, h = maxx - minx, maxy - miny
    gap, pad, label_h = 10.0, 8.0, 16.0
    order = list(reversed(case.layers))  # plate first
    total_w = pad * 2 + len(order) * w + (len(order) - 1) * gap
    total_h = pad * 2 + h + label_h
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w:.2f} {total_h:.2f}" '
           f'width="{total_w * 4:.0f}" height="{total_h * 4:.0f}" font-family="system-ui, sans-serif">',
           f'<rect width="100%" height="100%" rx="3" fill="#ffffff"/>']
    for i, layer in enumerate(order):
        ox = pad + i * (w + gap) - minx
        oy = pad - miny
        d = []
        for ring in [layer.shape.exterior, *layer.shape.interiors]:
            pts = list(ring.coords)[:-1]
            d.append("M" + " L".join(f"{x + ox:.2f},{y + oy:.2f}" for x, y in pts) + " Z")
        out.append(f'<path d="{" ".join(d)}" fill="{_FILL[layer.material]}" fill-rule="evenodd" '
                   f'stroke="#12303f" stroke-width="0.25"/>')
        tx = pad + i * (w + gap)
        out.append(f'<text x="{tx:.2f}" y="{pad + h + 6:.2f}" font-size="4" font-weight="600" fill="#12303f">'
                   f'{len(order) - i}. {layer.name}</text>')
        out.append(f'<text x="{tx:.2f}" y="{pad + h + 11.5:.2f}" font-size="3.2" fill="#4a6472">'
                   f'{layer.thickness:g} mm {_material(layer)}</text>')
    out.append("</svg>")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out))
    return path


def main():
    rev1 = "--rev1" in sys.argv[1:]
    tag = "-rev1" if rev1 else ""
    board = load_board(PCB_FILE_REV1 if rev1 else PCB_FILE)
    case = design(board, params_for(board))
    files = write_dxf(case, ROOT / "case" / f"dxf{tag}")
    files.append(write_svg(case, ROOT / "docs" / "images" / f"case{tag}-layers.svg"))
    files.append(write_model(case, ROOT / "site" / "assets" / f"case{tag}.json"))
    print(f"PCB {board.thickness:g} mm, case height {case.height:g} mm, "
          f"screws M3x{case.screw.length} (nut engagement {case.screw.nut_engagement:g} mm, "
          f"{case.screw.recess_from_bottom:g} mm below flush)")
    for layer in reversed(case.layers):
        print(f"  {layer.name:13s} {layer.thickness:g} mm  z {layer.z0:+.2f} .. {layer.z0 + layer.thickness:+.2f}")
    for f in files:
        print("  wrote", f.relative_to(ROOT))


if __name__ == "__main__":
    main()
