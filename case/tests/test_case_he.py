"""Spec for the sealed rev 2 (Hall-effect) case, generated from hardware/he/circuit.py.

The PCB sits inside the case: walls run unbroken from base to cover, a 1.2 mm
ledge supports the board edge from below (with a gasket) and another clamps it
from above; the cover is the only top surface. A 6 degree typing angle comes
from taller rear feet.
"""
import math

import pytest
from shapely.geometry import Point, box

import generate_he as g

ACRYLIC = {2.0, 3.0, 5.0}


@pytest.fixture(scope="module")
def case():
    return g.design()


def test_pcb_is_inside_the_case(case):
    from shapely.geometry import Polygon
    outer = Polygon(case.layer("cover").shape.exterior)   # the outline, ignoring the holes in it
    assert outer.buffer(-3.9).contains(case.pcb)          # at least a 4 mm wall all round


def test_pcb_ring_holds_the_board_edge_with_clearance(case):
    ring = case.layer("pcb-ring").shape
    assert ring.intersection(case.pcb).area < 1e-3
    assert ring.intersection(case.pcb.buffer(0.35)).area > 0   # 0.25 mm gap, no more


def test_ledges_overlap_the_board_edge_except_at_the_usb(case):
    for name in ("lower-wall", "spacer"):
        layer = case.layer(name).shape
        edge = case.pcb.exterior
        covered = edge.intersection(layer.buffer(0.01)).length / edge.length
        assert covered > 0.85, (name, covered)


def test_lower_wall_and_spacer_have_screw_lugs(case):
    for name in ("lower-wall", "spacer"):
        layer = case.layer(name).shape
        for x, y in case.screws:
            ring = Point(x, y).buffer(3.0).difference(Point(x, y).buffer(1.7))
            assert layer.contains(ring), (name, x, y)


def test_cover_has_only_switch_button_and_screw_holes(case):
    cover = case.layer("cover").shape
    assert len(cover.interiors) == 3 + 2 + 4
    for x, y in case.switches:
        hole = box(x - 7, y - 7, x + 7, y + 7)
        assert cover.intersection(hole.buffer(-0.05)).area < 1e-3
        assert cover.intersection(hole.buffer(0.6)).area > 1.0


def test_cover_is_solid_over_everything_else(case):
    cover = case.layer("cover").shape
    holes = [box(x - 7.2, y - 7.2, x + 7.2, y + 7.2) for x, y in case.switches]
    holes += [box(x - 3.6, y - 3.6, x + 3.6, y + 3.6) for x, y in case.buttons]
    holes += [Point(p).buffer(2.0) for p in case.screws]
    rest = case.pcb
    for h in holes:
        rest = rest.difference(h)
    assert cover.contains(rest.buffer(-0.01))


def test_usb_slot_through_the_walls_only(case):
    ux, uy = case.usb
    plug = box(ux - 6.3, uy - 10, ux + 6.3, uy - 0.5)     # 12.6 mm overmould, in front of the receptacle
    for name in ("lower-wall", "pcb-ring", "spacer"):
        assert case.layer(name).shape.intersection(plug).area < 1e-3, name
    for name in ("base", "cover"):
        assert case.layer(name).shape.intersection(plug).area > 50, name


def test_base_has_the_boot_hole(case):
    bx, by = case.boot
    assert case.layer("base").shape.intersection(Point(bx, by).buffer(1.9)).area < 1e-3


def test_bottom_parts_fit_inside_the_lower_wall(case):
    lower = case.layer("lower-wall").shape
    for ref, (x, y) in case.bottom_parts.items():
        if ref == "J1":
            continue  # its mouth sits in the USB slot
        assert lower.distance(Point(x, y)) > 1.0, ref


def test_layers_are_stock_materials(case):
    for layer in case.layers:
        if layer.material == "eva":
            assert layer.thickness == pytest.approx(0.5)
        else:
            assert layer.thickness in ACRYLIC, layer.name


def test_stack_heights(case):
    z = {l.name: (l.z0, l.z0 + l.thickness) for l in case.layers}
    assert z["pcb-ring"] == pytest.approx((-2.0, 0.0))
    assert z["lower-wall"][1] == pytest.approx(-2.0)            # 0.4 mm gasket under the 1.6 mm PCB
    assert z["cover"][1] <= 5.0                                 # under the MX plate line
    for a, b in zip(case.layers, case.layers[1:]):
        assert b.z0 == pytest.approx(a.z0 + a.thickness), (a.name, b.name)


def test_feet_give_a_6_degree_typing_angle(case):
    front = [f for f in case.feet if f[1] == max(p[1] for p in case.feet)]
    rear = [f for f in case.feet if f[1] == min(p[1] for p in case.feet)]
    dy = front[0][1] - rear[0][1]
    angle = math.degrees(math.atan((rear[0][2] - front[0][2]) / dy))
    assert angle == pytest.approx(6.0, abs=0.05)
    assert front[0][2] >= 1.0


def test_screws_are_nylon_and_do_not_reach_the_desk(case):
    s = case.screw
    assert s.material == "nylon" and s.length in (10, 12, 14, 16)
    assert s.tip_z > case.layer("base").z0 - min(f[2] for f in case.feet) + 0.3
    assert s.nut_engagement >= 1.8


def test_model_json_for_the_viewer(tmp_path, case):
    import json
    data = json.loads(g.write_model(case, tmp_path / "case.json").read_text())
    assert data["generic"] is True and data["tilt_deg"] == 6.0
    assert [l["name"] for l in data["layers"]] == ["base", "lower-wall", "pcb-ring", "spacer", "gasket", "cover"]
    assert all({"label", "sub", "order"} <= set(l) for l in data["layers"])
    assert len(data["feet"]) == 4 and len(data["switches"]) == 3
