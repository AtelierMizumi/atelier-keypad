"""The rev 1 FR4 plate as a KiCad board with only an Edge.Cuts outline (case/plate_pcb.py).

The plate is ordered as a second PCB, so it needs Gerbers; KiCad makes them from
this file. Positions are checked against hardware/rev1/circuit.py, not retyped.
"""
import importlib.util
import math
import sys
from pathlib import Path

import pytest

import generate as g
from plate_pcb import plate_shape, write_plate_pcb

ROOT = Path(__file__).resolve().parents[2]
# `circuit` in this test session is rev 2.0's (generate_he.py); load rev 1's under its own name.
_spec = importlib.util.spec_from_file_location("rev1_circuit", ROOT / "hardware" / "rev1" / "circuit.py")
assert _spec and _spec.loader
rev1 = sys.modules["rev1_circuit"] = importlib.util.module_from_spec(_spec)  # dataclasses look it up
_spec.loader.exec_module(rev1)


@pytest.fixture(scope="module")
def root(tmp_path_factory):
    path = write_plate_pcb(plate_shape(), tmp_path_factory.mktemp("plate") / "plate.kicad_pcb")
    return g._parse_sexpr(Path(path).read_text())


def _edge(root, kind):
    return [c for c in g._kids(root, kind) if g._kids(c, "layer")[0][1] == "Edge.Cuts"]


def _poly_points(poly):
    return [(float(c[1]), float(c[2])) for c in g._kids(g._kids(poly, "pts")[0], "xy")]


def _bounds(points):
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def test_plate_board_is_edge_cuts_only_and_1p6_mm(root):
    general = g._kids(root, "general")[0]
    assert float(g._kids(general, "thickness")[0][1]) == 1.6
    for kind in ("footprint", "segment", "via", "zone"):
        assert not g._kids(root, kind), kind
    for kind in ("gr_poly", "gr_circle", "gr_line", "gr_arc"):
        assert len(_edge(root, kind)) == len(g._kids(root, kind)), kind


def test_plate_outline_matches_the_board_outline(root):
    outer = max(_edge(root, "gr_poly"), key=lambda p: _bounds(_poly_points(p))[2] - _bounds(_poly_points(p))[0])
    board = g.load_board(g.PCB_FILE_REV1)
    assert _bounds(_poly_points(outer)) == pytest.approx(board.outline.bounds, abs=0.01)


def test_plate_has_four_3p2_mm_screw_holes(root):
    circles = _edge(root, "gr_circle")
    assert len(circles) == 4
    found = []
    for c in circles:
        cx, cy = (float(v) for v in g._kids(c, "center")[0][1:3])
        ex, ey = (float(v) for v in g._kids(c, "end")[0][1:3])
        assert math.hypot(ex - cx, ey - cy) == pytest.approx(1.6, abs=0.01)
        found.append((cx, cy))
    for hole in rev1.HOLES:
        assert any(math.dist(hole, f) < 0.01 for f in found), hole


def test_plate_cutouts_follow_the_rev1_keys(root):
    centres = []
    for poly in _edge(root, "gr_poly"):
        x0, y0, x1, y1 = _bounds(_poly_points(poly))
        if x1 - x0 == pytest.approx(14.0, abs=0.05) and y1 - y0 == pytest.approx(14.0, abs=0.05):
            centres.append(((x0 + x1) / 2, (y0 + y1) / 2))
    assert len(centres) == len(rev1.KEYS)
    for ref, (x, y) in rev1.KEYS.items():
        want = (x, y + rev1.KEY_SHIFT)
        assert any(math.dist(want, c) < 0.05 for c in centres), ref


def test_every_plate_ring_is_written_once(root):
    rings = len(g._kids(root, "gr_poly")) + len(g._kids(root, "gr_circle"))
    assert rings == 1 + len(plate_shape().interiors)
