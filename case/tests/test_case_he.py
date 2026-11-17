"""Spec for the sealed rev 2 (Hall-effect) case, generated from hardware/he/circuit.py.

The PCB sits inside the case: walls run unbroken from base to cover, a 1.2 mm
ledge supports the board edge from below (with a gasket) and another clamps it
from above; the cover is the only top surface. The case sits flat on one
silicone pad cut to its outline (docs/superpowers/specs/2026-11-16-rev2-flat-case-grip.md).
"""

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
        elif layer.material == "silicone":
            assert layer.thickness in {1.0, 1.5, 2.0}, layer.name   # stock self-adhesive sheet
        else:
            assert layer.thickness in ACRYLIC, layer.name


def test_stack_heights(case):
    z = {l.name: (l.z0, l.z0 + l.thickness) for l in case.layers}
    assert z["pcb-ring"] == pytest.approx((-2.0, 0.0))
    # the board's underside sits on the compressed EVA strip that lies on the lower ledge
    assert z["lower-wall"][1] == pytest.approx(-g.circuit.THICKNESS - g.UNDER_GASKET_COMPRESSED)
    assert z["cover"][1] <= 5.0                                 # under the MX plate line
    assert z["pad"] == pytest.approx((z["base"][0] - 1.5, z["base"][0]))
    for a, b in zip(case.layers, case.layers[1:]):
        assert b.z0 == pytest.approx(a.z0 + a.thickness), (a.name, b.name)


def test_board_is_clamped_between_gaskets(case):
    # Lower ledge top to spacer ledge bottom: the board plus the EVA strip under its edge,
    # a 1.0 mm sheet squeezed to 0.8 mm. Too wide and the board rattles; too tight and it bows.
    lower_top = case.layer("lower-wall").z0 + case.layer("lower-wall").thickness
    spacer_bottom = case.layer("spacer").z0
    assert g.UNDER_GASKET == pytest.approx(1.0) and g.UNDER_GASKET_COMPRESSED == pytest.approx(0.8)
    assert spacer_bottom - lower_top == pytest.approx(g.circuit.THICKNESS + 0.8, abs=0.2)


def test_case_is_flat_and_low(tmp_path, case):
    import json
    data = json.loads(g.write_model(case, tmp_path / "case.json").read_text())
    assert data["tilt_deg"] == 0 and case.feet == []
    assert -case.layer("pad").z0 == pytest.approx(11.5, abs=0.01)   # desk to PCB top


def test_pad_covers_the_base_footprint(case):
    from shapely.geometry import Polygon
    pad = case.layer("pad")
    assert pad.material == "silicone" and pad.thickness == pytest.approx(1.5)
    outline = Polygon(case.layer("base").shape.exterior)
    assert pad.shape.area >= 0.9 * outline.area


def test_pad_covers_the_nut_pockets(case):
    from shapely.geometry import Polygon
    pad = Polygon(case.layer("pad").shape.exterior)
    pockets = [Polygon(r) for r in case.layer("base").shape.interiors]
    hexes = [h for h in pockets if len(h.exterior.coords) == 7]
    assert len(hexes) == 4
    for h in hexes:
        assert pad.contains(h) and case.layer("pad").shape.contains(h.buffer(-0.01))


def test_pad_has_a_boot_hole(case):
    pad = case.layer("pad").shape
    assert not pad.contains(Point(case.boot))
    assert not pad.intersects(Point(case.boot).buffer(2.95))     # at least 6 mm across


def test_screws_are_nylon_and_do_not_reach_the_desk(case):
    s = case.screw
    assert s.material == "nylon" and s.length in (10, 12, 14, 16)
    assert s.tip_z > case.layer("pad").z0 + 0.3
    assert s.nut_engagement >= 1.8


def test_model_json_for_the_viewer(tmp_path, case):
    import json
    data = json.loads(g.write_model(case, tmp_path / "case.json").read_text())
    assert data["generic"] is True and data["tilt_deg"] == 0
    assert [l["name"] for l in data["layers"]] == ["pad", "base", "lower-wall", "pcb-ring", "spacer", "gasket", "cover"]
    assert all({"label", "sub", "order"} <= set(l) for l in data["layers"])
    assert data["feet"] == [] and len(data["switches"]) == 3


def test_usb_plug_fits_the_slot(case):
    # A USB-C cable's overmold, up to 12.4 x 6.6 mm, centred on the receptacle. J1 sits
    # under the board (B side), 3.2 mm tall: its centre is 1.6 mm below the board's underside.
    plug_w, plug_h = 12.4, 6.6
    ux, uy = case.usb
    zc = -g.circuit.THICKNESS - 1.6
    outer_edge = case.layer("cover").shape.bounds[1]             # the case's USB-side edge (min y)
    mouth = box(ux - plug_w / 2, outer_edge, ux + plug_w / 2, outer_edge + 2.0)
    cut = [l for l in case.layers if l.material != "eva" and not l.shape.intersects(mouth)]
    assert cut, "no layer is open for the plug"
    lo = min(l.z0 for l in cut)
    hi = max(l.z0 + l.thickness for l in cut)
    assert lo <= zc - plug_h / 2 and hi >= zc + plug_h / 2, (lo, hi, zc)
    # every layer that the plug's height passes through must be open
    for l in case.layers:
        if l.z0 < zc + plug_h / 2 and l.z0 + l.thickness > zc - plug_h / 2 and l.material != "eva":
            assert not l.shape.intersects(mouth), l.name
