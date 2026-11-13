"""Specification of the rev 1 circuit, checked against hardware/rev1/circuit.py.

    cd hardware/rev1 && uv run --no-project --with pytest pytest -q tests
"""
import json
from collections import defaultdict
from pathlib import Path

import pytest

import circuit

REPO = Path(__file__).resolve().parents[3]
KEYBOARD_JSON = REPO / "firmware" / "atelier6k" / "keyboard.json"

GPIO_3V3_MAX_NETS = {"VBUS", "+5V"}
# 74x1G125 in SOT-23-5; the KiCad symbol leaves these three pins unnamed.
OE, A, Y = "1", "2", "4"


@pytest.fixture(scope="module")
def parts():
    return {p.ref: p for p in circuit.parts()}


@pytest.fixture(scope="module")
def nets(parts):
    table = defaultdict(set)
    for p in parts.values():
        for pin, net in p.pins.items():
            if net is not None:
                table[net].add((p.ref, pin))
    return table


def refs(parts, prefix):
    return sorted((r for r in parts if r.rstrip("0123456789") == prefix), key=lambda r: int(r[len(prefix):]))


def test_has_the_agreed_parts(parts):
    assert refs(parts, "MX") == [f"MX{i}" for i in range(1, 7)]
    assert refs(parts, "SW") == ["SW1", "SW2", "SW3"]
    assert refs(parts, "D") == [f"D{i}" for i in range(1, 11)]
    assert len(refs(parts, "F")) == 1
    assert parts["U1"].footprint.endswith("RP2040-Zero_Flush")
    assert not any(r.startswith("Y") for r in parts), "no crystal: it is on the module"


def test_every_switch_is_one_gpio_to_ground(parts, nets):
    for ref in refs(parts, "MX") + refs(parts, "SW"):
        a, b = parts[ref].pins["1"], parts[ref].pins["2"]
        assert "GND" in (a, b), ref
        signal = a if b == "GND" else b
        others = nets[signal] - {(ref, "1"), (ref, "2")}
        assert len(others) == 1, f"{ref}: {signal} must reach exactly one MCU pin, got {others}"
        (mcu, pin), = others
        assert mcu == "U1" and pin.startswith("GP"), (ref, mcu, pin)


def test_no_matrix_diodes(parts):
    assert all(p.footprint.find("SOD") < 0 for p in parts.values())


def test_led_chain_is_single_and_ordered(parts, nets):
    leds = refs(parts, "D")
    for prev, nxt in zip(leds, leds[1:]):
        assert parts[prev].pins["DOUT"] == parts[nxt].pins["DIN"], (prev, nxt)
        assert nets[parts[prev].pins["DOUT"]] == {(prev, "DOUT"), (nxt, "DIN")}
    assert parts[leds[-1]].pins["DOUT"] is None, "end of chain is left open"
    for d in leds:
        assert parts[d].pins["VDD"] == "+5V" and parts[d].pins["VSS"] == "GND"
        assert parts[d].footprint.endswith("LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount")


def test_each_led_has_its_own_decoupling_capacitor(parts):
    caps = [p for p in parts.values() if p.ref.startswith("C") and p.value == "100nF"
            and set(p.pins.values()) == {"+5V", "GND"}]
    leds = [parts[r] for r in refs(parts, "D")]
    assert len(caps) >= len(leds)
    for led in leds:
        nearest = min(caps, key=lambda c: (c.x - led.x) ** 2 + (c.y - led.y) ** 2)
        dist = ((nearest.x - led.x) ** 2 + (nearest.y - led.y) ** 2) ** 0.5
        assert dist <= 4.0, f"{led.ref}: nearest 100 nF is {dist:.1f} mm away"


def test_led_rail_is_fused(parts, nets):
    fuse = parts[refs(parts, "F")[0]]
    assert set(fuse.pins.values()) == {"VBUS", "+5V"}
    assert nets["VBUS"] == {("U1", "5V"), (fuse.ref, "1")} or nets["VBUS"] == {("U1", "5V"), (fuse.ref, "2")}, \
        "nothing but the fuse hangs on the module's 5 V pin"


def test_led_data_goes_through_a_5v_level_shifter(parts, nets):
    shifter = parts["U2"]
    assert shifter.symbol == "74xGxx:74AHCT1G125"
    assert shifter.pins["VCC"] == "+5V" and shifter.pins["GND"] == "GND"
    assert shifter.pins[OE] == "GND", "output always enabled"
    in_net, out_net = shifter.pins[A], shifter.pins[Y]
    (mcu, pin), = nets[in_net] - {("U2", A)}
    assert mcu == "U1" and pin.startswith("GP")
    # shifter output -> series resistor -> first LED
    (rref, rpin), = nets[out_net] - {("U2", Y)}
    assert rref.startswith("R")
    other = [n for p, n in parts[rref].pins.items() if p != rpin][0]
    assert other == parts["D1"].pins["DIN"]


def test_no_5v_net_touches_a_gpio(parts):
    for pin, net in parts["U1"].pins.items():
        if pin.startswith("GP"):
            assert net not in GPIO_3V3_MAX_NETS, pin


def test_pin_map_matches_the_firmware(parts, nets):
    kb = json.loads(KEYBOARD_JSON.read_text())
    order = [["MX1", "MX2", "MX3"], ["MX4", "MX5", "MX6"], ["SW1", "SW2", "SW3"]]
    for row, pins in zip(order, kb["matrix_pins"]["direct"]):
        for ref, gpio in zip(row, pins):
            signal = next(n for n in parts[ref].pins.values() if n != "GND")
            assert ("U1", gpio) in nets[signal], f"{ref} should be on {gpio}"
    assert ("U1", kb["ws2812"]["pin"]) in nets[parts["U2"].pins[A]]


def test_firmware_led_order_follows_the_chain(parts):
    """LED n in the firmware is D(n+1) on the board; key LEDs sit under their key."""
    kb = json.loads(KEYBOARD_JSON.read_text())
    layout = kb["rgb_matrix"]["layout"]
    assert len(layout) == 10
    keys = {(0, 0): "MX1", (0, 1): "MX2", (0, 2): "MX3", (1, 0): "MX4", (1, 1): "MX5", (1, 2): "MX6"}
    for i, entry in enumerate(layout):
        led = parts[f"D{i + 1}"]
        if "matrix" in entry:
            key = parts[keys[tuple(entry["matrix"])]]
            assert abs(led.x - key.x) < 0.01 and abs(abs(led.y - key.y) - 5.08) < 0.01, (i, led.ref, key.ref)
        else:
            assert entry["flags"] == 2
            assert led.side == "F", "underglow LEDs are reverse-mounted on the top so they shine down"


def test_key_layout_is_the_rev0_3_plus_3_stagger(parts):
    mx = [parts[f"MX{i}"] for i in range(1, 7)]
    assert [round(b.x - a.x, 3) for a, b in zip(mx[:3], mx[1:3])] == [19.05, 19.05]
    assert [round(b.x - a.x, 3) for a, b in zip(mx[3:], mx[4:])] == [19.05, 19.05]
    assert round(mx[3].x - mx[0].x, 3) == 9.525
    assert round(mx[3].y - mx[0].y, 3) == 19.685  # rev 0 row pitch
    assert len({m.y for m in mx[:3]}) == 1 and len({m.y for m in mx[3:]}) == 1


def test_outline_and_holes_are_unchanged_from_rev0():
    assert circuit.OUTLINE == (116.84, 60.96, 198.12, 134.62)
    assert circuit.OUTLINE_RADIUS == 1.27
    assert sorted(circuit.HOLES) == [(121.92, 66.04), (121.92, 129.54), (193.04, 66.04), (193.04, 129.54)]


def test_everything_is_inside_the_board(parts):
    x0, y0, x1, y1 = circuit.OUTLINE
    for p in parts.values():
        assert x0 + 1 < p.x < x1 - 1 and y0 - 0.01 <= p.y < y1 - 1, p.ref


def test_module_sits_at_the_top_edge_and_clears_the_keys(parts):
    u1 = parts["U1"]
    assert u1.side == "B", "module hangs under the board; nothing tall under the plate"
    assert u1.y == circuit.OUTLINE[1], "USB end flush with the top edge"
    module_end = u1.y + 23.5 + 0.6  # pads overhang the module by about 0.5 mm
    socket_top = min(parts[f"MX{i}"].y for i in (1, 2, 3)) - 5.08 - 1.25
    assert socket_top - module_end >= 1.0


def test_references_are_unique_and_pins_named():
    seen = set()
    for p in circuit.parts():
        assert p.ref not in seen
        seen.add(p.ref)
        assert p.symbol and p.footprint and p.pins
