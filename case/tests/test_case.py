"""Behavioural spec for the Atelier6K acrylic case generator.

The case is derived from the KiCad board file, so these tests check the design
against the real board: nothing may collide with a component, every cut-out has
to line up with the part it is for, and the stack has to add up.
"""
from pathlib import Path

import ezdxf
import pytest
from shapely.geometry import Point, box

import generate as g

ROOT = Path(__file__).resolve().parents[2]
PCB = ROOT / "hardware" / "atelier6k" / "atelier6k.kicad_pcb"

MX_HOLE = 14.0          # Cherry MX plate cut-out, mm
MX_PLATE_TOP = 5.0      # plate top surface above the PCB top surface, mm
M3_CLEARANCE = 3.2
M3_NUT_AF = 5.5
M3_NUT_T = 2.4
STOCK = {2.0, 3.0, 5.0}  # acrylic sheet thicknesses that are easy to buy


@pytest.fixture(scope="module")
def board():
    return g.load_board(PCB)


@pytest.fixture(scope="module")
def case(board):
    return g.design(board)


def square(x, y, side):
    return box(x - side / 2, y - side / 2, x + side / 2, y + side / 2)


# --- reading the board -------------------------------------------------------

def test_board_geometry_is_read_from_kicad(board):
    minx, miny, maxx, maxy = board.outline.bounds
    assert maxx - minx == pytest.approx(81.28, abs=0.01)
    assert maxy - miny == pytest.approx(73.66, abs=0.01)
    assert len(board.mount_holes) == 4
    assert len(board.mx) == 6
    assert len(board.tact) == 3
    assert board.usb is not None
    assert board.reset is not None
    assert board.thickness > 0.8


def test_tact_centres_are_the_body_centre_not_pin_1(board):
    # Pin 1 is a corner of the 6.5 x 4.5 mm pin pattern.
    xs = sorted(round(p[0], 2) for p in board.tact)
    assert xs[0] == pytest.approx(125.73, abs=0.02)
    ys = sorted(round(p[1], 2) for p in board.tact)
    assert ys == pytest.approx([96.68, 105.41, 114.14], abs=0.02)


# --- the stack ---------------------------------------------------------------

def test_layer_order_and_stock_thickness(case):
    assert [l.name for l in case.layers] == ["base", "bottom-frame", "top-frame", "plate"]
    for layer in case.layers:
        assert layer.thickness in STOCK, layer.name


def test_stack_is_contiguous_around_the_pcb(case, board):
    by = {l.name: l for l in case.layers}
    assert by["top-frame"].z0 == pytest.approx(0.0)
    assert by["plate"].z0 == pytest.approx(by["top-frame"].z0 + by["top-frame"].thickness)
    assert by["bottom-frame"].z0 + by["bottom-frame"].thickness == pytest.approx(-board.thickness)
    assert by["base"].z0 + by["base"].thickness == pytest.approx(by["bottom-frame"].z0)


def test_plate_top_sits_at_the_mx_mounting_height(case):
    plate = case.layer("plate")
    assert plate.z0 + plate.thickness == pytest.approx(MX_PLATE_TOP)


def test_every_layer_is_flush_with_the_pcb_outline(case, board):
    ux, _ = board.usb
    for layer in case.layers:
        # Nothing sticks out past the PCB edge...
        assert layer.shape.difference(board.outline).area < 0.05, layer.name
        # ...and the layer follows that edge everywhere except the USB bay.
        missing = board.outline.exterior.difference(layer.shape.buffer(0.02))
        assert missing.length < 12.0, layer.name
        if not missing.is_empty:
            minx, _, maxx, _ = missing.bounds
            assert minx > ux - 6 and maxx < ux + 6, layer.name
    assert board.outline.exterior.difference(case.layer("base").shape.buffer(0.02)).is_empty


# --- fasteners ---------------------------------------------------------------

def test_screw_holes_line_up_with_the_pcb_mounting_holes(case, board):
    for layer in case.layers:
        for (x, y) in board.mount_holes:
            hole = Point(x, y).buffer(M3_CLEARANCE / 2 - 0.02)
            assert layer.shape.intersection(hole).area < 1e-3, layer.name
            # ...and there is material all around the hole to clamp on.
            ring = Point(x, y).buffer(4.2).difference(Point(x, y).buffer(3.4))
            assert ring.difference(layer.shape).area < 0.05 * ring.area, layer.name


def test_base_captures_m3_nuts(case, board):
    base = case.layer("base")
    assert base.thickness >= M3_NUT_T
    for (x, y) in board.mount_holes:
        # A nut (inscribed circle = across flats) drops in...
        assert base.shape.intersection(Point(x, y).buffer(M3_NUT_AF / 2)).area < 1e-3
        # ...but cannot spin: the pocket is narrower than the nut's corners.
        corners = Point(x, y).buffer(M3_NUT_AF / 2 / 0.866 + 0.25).boundary
        assert corners.intersection(base.shape).length > 0
    # The frame above closes the pocket so the nut has something to pull on.
    frame = case.layer("bottom-frame")
    for (x, y) in board.mount_holes:
        seat = Point(x, y).buffer(M3_NUT_AF / 2).difference(Point(x, y).buffer(M3_CLEARANCE / 2 + 0.1))
        assert seat.difference(frame.shape).area < 0.05 * seat.area


def test_screw_length_engages_the_nut_without_poking_out(case):
    s = case.screw
    assert s.length in {8, 10, 12, 14, 16, 20}
    assert s.nut_engagement >= 2.0
    assert s.recess_from_bottom >= 0.0


# --- plate -------------------------------------------------------------------

def test_plate_has_a_14mm_cutout_for_each_switch(case, board):
    plate = case.layer("plate").shape
    for (x, y) in board.mx:
        # 14.0 mm flat to flat in both directions. The corners may carry a
        # small radius (Cherry allows 0.3 mm), which keeps acrylic from cracking.
        side, flat = MX_HOLE - 0.02, MX_HOLE - 0.8
        cross = box(x - side / 2, y - flat / 2, x + side / 2, y + flat / 2).union(
            box(x - flat / 2, y - side / 2, x + flat / 2, y + side / 2))
        assert plate.intersection(cross).area < 1e-3
        assert plate.intersection(square(x, y, side)).area < 0.1
        frame = square(x, y, MX_HOLE + 1.2).difference(square(x, y, MX_HOLE + 0.3))
        assert frame.difference(plate).area < 0.02 * frame.area


def test_plate_clears_tact_switch_bodies(case, board):
    plate = case.layer("plate").shape
    for (x, y) in board.tact:
        assert plate.intersection(square(x, y, 6.3)).area < 1e-3
        assert plate.contains(Point(x + 5.0, y)) or plate.contains(Point(x - 5.0, y))


def test_plate_clears_the_usb_receptacle(case, board):
    # HRO TYPE-C-31-M-12: 8.94 mm wide, 7.35 mm deep, 3.26 mm tall. The plate
    # underside is only 2 mm above the PCB, so it must be notched here.
    plate = case.layer("plate")
    assert plate.z0 < 3.26
    ux, uy = board.usb
    body = box(ux - 4.47, uy, ux + 4.47, uy + 7.35)
    assert plate.shape.intersection(body).area < 1e-3


# --- frames ------------------------------------------------------------------

def test_frames_do_not_touch_any_component(case, board):
    top = case.layer("top-frame").shape
    for ref, keepout in board.keepouts_top.items():
        assert top.intersection(keepout).area < 1e-3, f"top-frame hits {ref}"
    bottom = case.layer("bottom-frame").shape
    for ref, keepout in board.keepouts_bottom.items():
        assert bottom.intersection(keepout).area < 1e-3, f"bottom-frame hits {ref}"


def test_frames_keep_a_minimum_wall(case):
    for name in ("top-frame", "bottom-frame"):
        shape = case.layer(name).shape
        core = shape.buffer(-0.9)  # survives only where the wall is >= 1.8 mm
        assert core.geom_type == "Polygon" and not core.is_empty, name


def test_top_frame_is_open_for_the_usb_plug(case, board):
    ux, uy = board.usb
    top = case.layer("top-frame").shape
    assert top.intersection(box(ux - 4.6, uy - 1, ux + 4.6, uy + 7.35)).area < 1e-3


def test_frames_enclose_the_board_except_at_the_usb_bay(case, board):
    # The receptacle's shield legs come through the PCB 0.4 mm from the edge, so
    # neither frame can run a wall past it. That bay is the only opening.
    ux, _ = board.usb
    for name in ("top-frame", "bottom-frame"):
        gap = board.outline.exterior.difference(case.layer(name).shape.buffer(0.02))
        assert 9.0 < gap.length < 12.0, name
        minx, _, maxx, _ = gap.bounds
        assert minx > ux - 6 and maxx < ux + 6, name


def test_base_has_a_reset_access_hole(case, board):
    base = case.layer("base").shape
    x, y = board.reset
    assert not base.contains(Point(x, y))
    assert base.intersection(Point(x, y).buffer(1.4)).area < 1e-3


def test_bottom_cavity_is_deeper_than_the_tallest_bottom_part(case):
    # Kailh hot-swap socket: 1.85 mm; tact switch leads: about 2 mm.
    assert case.layer("bottom-frame").thickness >= 3.0


# --- output files ------------------------------------------------------------

def test_dxf_per_layer_and_cut_sheet(case, tmp_path):
    files = g.write_dxf(case, tmp_path)
    names = sorted(p.name for p in files)
    assert names == [
        "atelier6k-case-all.dxf",
        "atelier6k-case-base-3mm.dxf",
        "atelier6k-case-bottom-frame-5mm.dxf",
        "atelier6k-case-plate-3mm.dxf",
        "atelier6k-case-top-frame-2mm.dxf",
    ]
    doc = ezdxf.readfile(tmp_path / "atelier6k-case-plate-3mm.dxf")
    assert doc.header["$INSUNITS"] == 4  # millimetres
    msp = doc.modelspace()
    polylines = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
    circles = [e for e in msp if e.dxftype() == "CIRCLE"]
    assert all(p.closed for p in polylines)
    # outline (with USB notch) + 6 switch + 3 tact cut-outs; 4 round screw holes
    assert len(polylines) == 10
    assert len(circles) == 4
    assert all(c.dxf.radius == pytest.approx(M3_CLEARANCE / 2) for c in circles)


def test_cut_sheet_parts_do_not_overlap(case, tmp_path):
    g.write_dxf(case, tmp_path)
    doc = ezdxf.readfile(tmp_path / "atelier6k-case-all.dxf")
    outlines = [e for e in doc.modelspace() if e.dxftype() == "LWPOLYLINE" and e.dxf.layer.startswith("CUT-OUTLINE")]
    assert len(outlines) == 4
    boxes = []
    for e in outlines:
        xs = [p[0] for p in e.get_points()]; ys = [p[1] for p in e.get_points()]
        boxes.append(box(min(xs), min(ys), max(xs), max(ys)))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert boxes[i].intersection(boxes[j]).area == 0


def test_model_json_describes_every_layer(case, tmp_path):
    import json
    path = g.write_model(case, tmp_path / "case.json")
    data = json.loads(path.read_text())
    assert [l["name"] for l in data["layers"]] == ["base", "bottom-frame", "top-frame", "plate"]
    for layer in data["layers"]:
        assert layer["outer"] and "holes" in layer and layer["thickness"] > 0
    assert len(data["switches"]) == 6 and len(data["buttons"]) == 3 and len(data["screws"]) == 4
