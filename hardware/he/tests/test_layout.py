"""Checks on the placed and routed board file (atelier-he.kicad_pcb), read as plain s-expressions.

These complement KiCad's DRC with the rules this design adds: short USB pair,
crystal next to the MCU, sensors on the magnet axes, nothing routed through the art.
"""
import math
from collections import defaultdict
from pathlib import Path

import pytest

import circuit
from sexpr import find, find_all, parse

BOARD = Path(__file__).resolve().parents[1] / "atelier-he.kicad_pcb"
pytestmark = pytest.mark.skipif(not BOARD.exists(), reason="board not generated (scripts/he.sh)")


@pytest.fixture(scope="module")
def pcb():
    return parse(BOARD.read_text())


def xy(node):
    return float(node[1]), float(node[2])


def tracks(pcb):
    """net name -> list of segments; KiCad 10 names the net directly in each segment."""
    out = defaultdict(list)
    for seg in find_all(pcb, "segment"):
        out[str(find(seg, "net")[1])].append((xy(find(seg, "start")), xy(find(seg, "end"))))
    return out


def length(segs):
    return sum(math.dist(a, b) for a, b in segs)


def footprint(pcb, ref):
    for fp in find_all(pcb, "footprint"):
        for prop in find_all(fp, "property"):
            if prop[1] == "Reference" and prop[2] == ref:
                return fp, xy(find(fp, "at")), str(find(fp, "layer")[1])
    raise KeyError(ref)


def signal_path(segs, starts, end):
    """Shortest copper path (mm) from any of `starts` to `end`, through tracks and vias."""
    import heapq
    key = lambda p: (round(p[0] * 20), round(p[1] * 20))  # 0.05 mm: pad centres sit at x.xx5
    adj = defaultdict(list)
    for a, b in segs:
        d = math.dist(a, b)
        adj[key(a)].append((key(b), d))
        adj[key(b)].append((key(a), d))
    dist = {key(s): 0.0 for s in starts}
    heap = [(0.0, key(s)) for s in starts]
    while heap:
        d, n = heapq.heappop(heap)
        if n == key(end):
            return d
        if d > dist.get(n, 1e9):
            continue
        for m, w in adj[n]:
            if d + w < dist.get(m, 1e9):
                dist[m] = d + w
                heapq.heappush(heap, (d + w, m))
    return math.inf


def mcu_pad(pin: int) -> tuple[float, float]:
    """Board position of an LQFP48 pin, for the placement in circuit.py (bottom side, 270 deg)."""
    u1 = next(p for p in circuit.parts() if p.ref == "U1")
    cx, cy = u1.x, u1.y
    assert (u1.side, u1.rot) == ("B", 270)
    if 25 <= pin <= 36:
        return cx - 2.75 + (pin - 25) * 0.5, cy - 4.1625
    raise NotImplementedError(pin)


def test_esd_stub_is_short(pcb):
    """The ESD array hangs off the pair: keep the branch to it short."""
    _, (x, y), _ = footprint(pcb, "U3")
    assert math.dist((x, y), (100.0, 88.545)) < 10


def test_usb_pair_is_short_and_matched(pcb):
    """Connector-to-MCU signal path: short, and the two lines within 3 mm of each other.

    USB-C has two pads per line (A6/B6, A7/B7); the bridge between them is a stub,
    not part of the path, so the path starts at whichever pad is nearer.
    """
    t = tracks(pcb)
    j1 = {"A6": (99.75, 88.545), "B6": (100.75, 88.545), "A7": (100.25, 88.545), "B7": (99.25, 88.545)}
    dp = signal_path(t["USB_DP"], [j1["A6"], j1["B6"]], mcu_pad(27))
    dm = signal_path(t["USB_DM"], [j1["A7"], j1["B7"]], mcu_pad(26))
    assert dp < 15 and dm < 15, (dp, dm)       # far below the ~70 mm where a 480 Mb/s edge sees a line
    assert abs(dp - dm) < 3.0, (dp, dm)


def test_crystal_is_close_to_the_mcu(pcb):
    _, (yx, yy), _ = footprint(pcb, "Y1")
    _, (ux, uy), _ = footprint(pcb, "U1")
    assert math.dist((yx, yy), (ux, uy)) < 12
    t = tracks(pcb)
    assert length(t["HEXT_IN"]) < 15 and length(t["HEXT_OUT"]) < 15


def test_sensors_are_on_bottom_under_each_magnet(pcb):
    # Decision D2 (rev 2.0): through the PCB, as Gateron measures the flux. Was "on top" in rev 2.
    for i, key in enumerate(circuit.KEY_ORDER, start=1):
        _, (x, y), layer = footprint(pcb, f"U{9 + i}")
        kx, ky = circuit.KEYS[key]
        assert layer == "B.Cu" and math.hypot(x - kx, y - ky) <= 0.1


def test_sensor_pads_carry_vcc_out_gnd(pcb):
    # Flipped to the bottom, the SOT-23 is mirrored; the pad numbers must still carry the DRV5056 pinout.
    for i, key in enumerate(circuit.KEY_ORDER, start=1):
        fp, _, _ = footprint(pcb, f"U{9 + i}")
        pads = {str(p[1]): (str(find(p, "net")[1]), [str(l) for l in find(p, "layers")[1:]]) for p in find_all(fp, "pad")}
        assert pads["1"][0] == "+3V3A" and pads["2"][0] == f"SENSE_{key}" and pads["3"][0] == "GND"
        assert all("B.Cu" in layers for _, layers in pads.values())


def test_bottom_parts_under_a_key_do_not_collide():
    # KiCad's DRC checks courtyards; the report must carry no overlap anywhere.
    import json
    report = json.loads((BOARD.parents[2] / "docs" / "reports" / "he-drc.json").read_text())
    assert not [v for v in report["violations"] if v["type"] == "courtyards_overlap"]


def test_silkscreen_is_readable_and_clear_of_pads():
    # Labels must not sit on pads or holes (the fab clips them), on each other, or below
    # the 0.8 mm minimum text height. Clipping by the board edge (J1's outline) is allowed.
    import json
    report = json.loads((BOARD.parents[2] / "docs" / "reports" / "he-drc.json").read_text())
    bad = [(v["type"], [i["description"] for i in v["items"]]) for v in report["violations"]
           if v["type"] in ("silk_over_copper", "silk_overlap", "text_height")]
    assert bad == []


def test_boot_label_sits_under_the_boot_button(pcb):
    # The BOOT hint belongs next to SW3 on the bottom, where a finger finds the button.
    _, (sx, sy), _ = footprint(pcb, "SW3")
    labels = [t for t in find_all(pcb, "gr_text") if "BOOT" in str(t[1])]
    assert labels, "no BOOT label"
    for t in labels:
        x, y = xy(find(t, "at"))
        assert abs(x - sx) < 3.0 and 0 < y - sy < 8.0, (x, y)


def test_silkscreen_says_rev_2_0(pcb):
    texts = [str(t[2]) for t in find_all(pcb, "gr_text")] + [str(t[1]) for t in find_all(pcb, "gr_text")]
    assert any("rev 2.0" in t for t in texts)


def test_switch_footprints_at_the_keys(pcb):
    for key in circuit.KEY_ORDER:
        _, (x, y), _ = footprint(pcb, f"SW_{key}")
        assert (x, y) == pytest.approx(circuit.KEYS[key])


def test_nothing_is_routed_through_the_art(pcb):
    x0, y0, x1, y1 = circuit.ART_ZONE
    inside = lambda p: x0 < p[0] < x1 and y0 < p[1] < y1
    for segs in tracks(pcb).values():
        for a, b in segs:
            assert not (inside(a) or inside(b))
    for via in find_all(pcb, "via"):
        assert not inside(xy(find(via, "at")))


def test_art_is_on_the_board(pcb):
    fp, (x, y), layer = footprint(pcb, "ART1")
    x0, y0, x1, y1 = circuit.ART_ZONE
    assert layer == "F.Cu" and x0 < x < x1 and y0 < y < y1
