"""Spec for the case generated from the rev 1 board (RP2040-Zero under the PCB).

Differences from the rev 0 case, each checked below:
  - the switch plate is a 1.6 mm FR4 board, so MX switches clip into it;
  - a 3 mm acrylic frame plus a 0.5 mm M3 washer per screw put the plate top
    5.1 mm above the PCB;
  - nothing pokes through the plate at the USB end: the module hangs under the
    PCB and the bottom frame opens for it;
  - the base has two holes to reach the module's BOOT and RESET buttons.
"""
from pathlib import Path

import pytest
from shapely.geometry import Point, box

import generate as g

ROOT = Path(__file__).resolve().parents[2]
PCB = ROOT / "hardware" / "rev1" / "atelier6k-rev1.kicad_pcb"

MODULE_W, MODULE_L = 18.0, 23.5
MODULE_HEIGHT = 1.0 + 3.3     # module PCB + USB-C receptacle, below our PCB
ACRYLIC = {2.0, 3.0, 5.0}


@pytest.fixture(scope="module")
def board():
    return g.load_board(PCB)


@pytest.fixture(scope="module")
def case(board):
    return g.design(board, g.params_for(board))


def test_board_is_read(board):
    assert len(board.mx) == 6 and len(board.tact) == 3 and len(board.mount_holes) == 4
    assert board.usb is None and board.reset is None, "no USB receptacle or reset switch on this board"
    assert board.thickness == pytest.approx(1.6)
    minx, miny, maxx, maxy = board.outline.bounds
    assert (round(maxx - minx, 2), round(maxy - miny, 2)) == (81.28, 73.66)


def test_module_is_found_on_the_top_edge(board):
    x, y = board.module
    minx, miny, maxx, _ = board.outline.bounds
    assert x == pytest.approx((minx + maxx) / 2, abs=0.01)
    assert y == pytest.approx(miny, abs=0.01)


def test_module_buttons_are_under_the_module(board):
    x, y = board.module
    assert len(board.module_buttons) == 2
    for bx, by in board.module_buttons:
        assert abs(abs(bx - x) - 5.0) < 0.01 and by == pytest.approx(y + 16.2, abs=0.01)


def test_plate_is_fr4_and_the_rest_is_stock_acrylic(case):
    plate = case.layer("plate")
    assert plate.material == "fr4" and plate.thickness == pytest.approx(1.6)
    for name in ("base", "bottom-frame", "top-frame"):
        assert case.layer(name).thickness in ACRYLIC, name
        assert case.layer(name).material != "fr4"


def test_plate_top_is_at_the_mx_height(case):
    plate = case.layer("plate")
    assert plate.z0 + plate.thickness == pytest.approx(5.1, abs=0.11)  # MX: 5.0 mm
    gap = plate.z0 - (case.layer("top-frame").z0 + case.layer("top-frame").thickness)
    assert gap == pytest.approx(case.washer) and case.washer == pytest.approx(0.5)


def test_plate_holds_switches_and_clears_buttons(case, board):
    plate = case.layer("plate").shape
    for x, y in board.mx:
        hole = box(x - 7, y - 7, x + 7, y + 7)
        assert plate.intersection(hole.buffer(-0.35)).area < 1e-3
        assert plate.intersection(hole.buffer(0.6)).area > 1.0, "plate grips the switch on every side"
    for x, y in board.tact:
        assert plate.intersection(box(x - 3.1, y - 3.1, x + 3.1, y + 3.1)).area < 1e-3


def test_plate_webs_are_wide_enough_for_fr4(case):
    core = case.layer("plate").shape.buffer(-0.4)  # survives where material is >= 0.8 mm wide
    assert core.geom_type == "Polygon" and not core.is_empty


def test_plate_and_top_frame_are_closed_at_the_usb_end(case, board):
    x, y = board.module
    assert case.layer("plate").shape.contains(box(x - 6, y + 0.5, x + 6, y + 10))
    for name in ("plate", "top-frame"):
        gap = board.outline.exterior.difference(case.layer(name).shape.buffer(0.02))
        assert gap.length < 0.1, name


def test_bottom_frame_opens_for_the_module_only(case, board):
    x, y = board.module
    bottom = case.layer("bottom-frame").shape
    module = box(x - MODULE_W / 2, y - 1, x + MODULE_W / 2, y + MODULE_L)
    assert bottom.intersection(module.buffer(0.3)).area < 1e-3
    gap = board.outline.exterior.difference(bottom.buffer(0.02))
    assert MODULE_W < gap.length < MODULE_W + 6
    minx, _, maxx, _ = gap.bounds
    assert minx > x - MODULE_W / 2 - 3 and maxx < x + MODULE_W / 2 + 3


def test_bottom_cavity_is_deeper_than_the_module(case):
    assert case.layer("bottom-frame").thickness >= MODULE_HEIGHT + 0.5


def test_frames_do_not_touch_any_component(case, board):
    top = case.layer("top-frame").shape
    for ref, keepout in board.keepouts_top.items():
        assert top.intersection(keepout).area < 1e-3, f"top-frame hits {ref}"
    bottom = case.layer("bottom-frame").shape
    for ref, keepout in board.keepouts_bottom.items():
        assert bottom.intersection(keepout).area < 1e-3, f"bottom-frame hits {ref}"


def test_frames_keep_a_minimum_wall(case):
    for name in ("top-frame", "bottom-frame"):
        core = case.layer(name).shape.buffer(-0.9)
        assert not core.is_empty, name
        if name == "top-frame":
            assert core.geom_type == "Polygon", "top frame is one closed ring"


def test_base_has_holes_for_boot_and_reset_and_is_solid_under_the_usb(case, board):
    base = case.layer("base").shape
    for bx, by in board.module_buttons:
        assert base.intersection(Point(bx, by).buffer(1.4)).area < 1e-3
    x, y = board.module
    assert base.contains(box(x - 4.5, y + 0.5, x + 4.5, y + 8))


def test_screw_reaches_the_nut_and_stays_inside(case):
    assert case.screw.nut_engagement >= 2.0
    assert case.screw.recess_from_bottom >= 0


def test_model_json_carries_the_rev1_details(case, tmp_path):
    import json
    data = json.loads(g.write_model(case, tmp_path / "case.json").read_text())
    assert data["usb"] is None and len(data["module_buttons"]) == 2 and data["washer"] == 0.5
    assert {l["name"]: l["material"] for l in data["layers"]}["plate"] == "fr4"
