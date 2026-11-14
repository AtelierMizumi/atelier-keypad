"""Specification of the rev 2 (Hall-effect) circuit, checked against hardware/he/circuit.py.

    cd hardware/he && uv run --no-project --with pytest pytest -q tests

Pin facts are from the AT32F405/402 datasheet v2.02 (LQFP48, Figure 3 and
Table 9) and are copied into AT32F405_LQFP48 below so the tests and the
symbol generator read the same table.
"""
import math
from collections import defaultdict

import pytest

import circuit

ADC_PINS = {f"PA{i}" for i in range(8)} | {"PB0", "PB1"}  # ADC1_IN0..IN9 on LQFP48


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


def mcu_pin(name):
    """LQFP48 pin number of a named MCU pin."""
    return next(n for n, nm in circuit.AT32F405_LQFP48.items() if nm == name)


def mcu_net(parts, name):
    return parts["U1"].pins[str(mcu_pin(name))]


def test_pin_table_is_the_datasheet_lqfp48():
    t = circuit.AT32F405_LQFP48
    assert sorted(t) == list(range(1, 49))
    assert (t[1], t[9], t[8], t[25], t[26], t[27], t[44], t[47], t[48]) == \
        ("VDD", "VDDA", "VSSA", "OTGHS_R", "OTGHS_D-", "OTGHS_D+", "PF11/BOOT0", "VSS", "VDD")
    assert (t[5], t[6], t[7], t[10], t[34], t[37]) == ("PF0", "PF1", "NRST", "PA0", "PA13", "PA14")


def test_every_mcu_pin_is_decided(parts):
    assert set(parts["U1"].pins) == {str(n) for n in range(1, 49)}


def test_three_sensors_each_on_its_own_adc_pin(parts, nets):
    sensors = [p for p in parts.values() if p.symbol.startswith("Sensor_Magnetic:")]
    assert len(sensors) == 3
    pins = set()
    for s in sensors:
        out = s.pins["OUT"]
        # sensor output -> RC -> MCU: find the MCU pin on the far side of the series resistor
        (rref, rpin), = nets[out] - {(s.ref, "OUT")} - {c for c in nets[out] if c[0].startswith("C")}
        other = next(n for pn, n in parts[rref].pins.items() if pn != rpin)
        mcu = [pin for ref, pin in nets[other] if ref == "U1"]
        assert len(mcu) == 1, s.ref
        name = circuit.AT32F405_LQFP48[int(mcu[0])]
        assert name in ADC_PINS, (s.ref, name)
        pins.add(name)
    assert len(pins) == 3


def test_no_multiplexer(parts):
    assert not any("4051" in p.value or "Analog_Switch" in p.symbol for p in parts.values())


def test_sensors_use_the_drv5056_pinout_and_the_analog_rail(parts):
    for s in (p for p in parts.values() if p.symbol.startswith("Sensor_Magnetic:")):
        assert s.value == "DRV5056A4"
        assert s.pins["VCC"] == "+3V3A" and s.pins["GND"] == "GND"
        assert s.footprint.endswith(":SOT-23")


def test_analog_rail_feeds_only_sensors_vdda_and_their_capacitors(parts, nets):
    allowed = set()
    for ref, pin in nets["+3V3A"]:
        p = parts[ref]
        ok = (p.symbol.startswith("Sensor_Magnetic:") or ref.startswith("C") or ref.startswith("FB")
              or (ref == "U1" and circuit.AT32F405_LQFP48[int(pin)] == "VDDA"))
        assert ok, (ref, pin)
        allowed.add(ref)
    fb = [r for r in allowed if r.startswith("FB")]
    assert len(fb) == 1 and set(parts[fb[0]].pins.values()) == {"+3V3", "+3V3A"}


def test_one_ldo_feeds_vdd_and_vdda_is_the_same_potential(parts):
    ldo = [p for p in parts.values() if p.symbol.startswith("Regulator_Linear:LP5907")]
    assert len(ldo) == 1 and ldo[0].pins["OUT"] == "+3V3" and ldo[0].pins["IN"] == "+5V"
    for n, name in circuit.AT32F405_LQFP48.items():
        if name == "VDD":
            assert parts["U1"].pins[str(n)] == "+3V3"
        if name in ("VSS", "VSSA"):
            assert parts["U1"].pins[str(n)] == "GND"


def test_every_vdd_pin_has_its_own_100nF(parts, nets):
    caps = [p for p in parts.values() if p.ref.startswith("C") and p.value == "100nF"
            and set(p.pins.values()) in ({"+3V3", "GND"}, {"+3V3A", "GND"})]
    vdd_pins = [n for n, nm in circuit.AT32F405_LQFP48.items() if nm in ("VDD", "VDDA")]
    assert len(caps) >= len(vdd_pins) + 3  # one per supply pin plus one per sensor


def test_usb_high_speed_with_its_reference_resistor_and_12mhz_crystal(parts, nets):
    j = parts["J1"]
    assert {j.pins["A6"], j.pins["B6"]} == {mcu_net(parts, "OTGHS_D+")}
    assert {j.pins["A7"], j.pins["B7"]} == {mcu_net(parts, "OTGHS_D-")}
    rref = [p for p in parts.values() if mcu_net(parts, "OTGHS_R") in p.pins.values() and p.ref.startswith("R")]
    assert len(rref) == 1 and rref[0].value == "12k 1%" and "GND" in rref[0].pins.values()
    y = parts["Y1"]
    assert y.value == "12MHz"  # the HS PHY only works from a 12 MHz HEXT (datasheet 2.13.6)
    assert {y.pins["1"], y.pins["3"]} == {mcu_net(parts, "PF0"), mcu_net(parts, "PF1")}


def test_usb_has_cc_pulldowns_esd_fuse_and_shield_network(parts, nets):
    j = parts["J1"]
    for cc in ("A5", "B5"):
        others = nets[j.pins[cc]] - {("J1", cc)}
        (r, _), = others
        assert parts[r].value == "5.1k" and "GND" in parts[r].pins.values()
    esd = next(p for p in parts.values() if p.symbol.endswith("USBLC6-2SC6"))
    assert {esd.pins["1"], esd.pins["3"]} == {mcu_net(parts, "OTGHS_D+"), mcu_net(parts, "OTGHS_D-")}
    assert esd.pins["5"] == "VBUS"
    fuse = next(p for p in parts.values() if p.symbol == "Device:Polyfuse")
    assert set(fuse.pins.values()) == {"VBUS", "+5V"}
    shield = j.pins["SH"]
    shunt = {p.value for p in parts.values() if shield in p.pins.values() and p.ref != "J1"}
    assert shunt == {"1M", "4.7nF"}


def test_boot0_pulled_down_with_a_button_to_3v3(parts, nets):
    boot = mcu_net(parts, "PF11/BOOT0")
    vals = {(parts[r].value, tuple(sorted(parts[r].pins.values()))) for r, _ in nets[boot] if r != "U1"}
    assert ("10k", tuple(sorted([boot, "GND"]))) in vals
    assert any(v[0] == "BOOT" for v in vals)


def test_swd_pads_exist(parts):
    pads = {p.pins["1"] for p in parts.values() if p.ref.startswith("TP")}
    assert {mcu_net(parts, "PA13"), mcu_net(parts, "PA14"), "GND", "+3V3"} <= pads


def test_led_chain_is_single_buffered_and_decoupled(parts, nets):
    leds = sorted((p for p in parts.values() if p.symbol == "LED:SK6812MINI-E"), key=lambda p: int(p.ref[1:]))
    assert len(leds) == 7
    for a, b in zip(leds, leds[1:]):
        assert a.pins["DOUT"] == b.pins["DIN"]
    assert leds[-1].pins["DOUT"] is None
    buf = parts["U4"]
    assert buf.symbol == "74xGxx:74AHCT1G125" and buf.pins["VCC"] == "+5V"
    assert circuit.AT32F405_LQFP48[int(next(p for r, p in nets[buf.pins["2"]] if r == "U1"))] == circuit.LED_PIN


def test_keys_follow_the_finger_arc():
    (x1, y1), (x2, y2), (x3, y3) = (circuit.KEYS[k] for k in ("K1", "K2", "K3"))
    assert round(x2 - x1, 3) == 19.05 and round(x3 - x2, 3) == 19.05
    assert y1 == y3 and round(y1 - y2, 3) == 4.76   # middle key further from the wrist (smaller y)
    assert x2 == pytest.approx((circuit.OUTLINE[0] + circuit.OUTLINE[2]) / 2)


def test_sensors_sit_on_their_key_axis(parts):
    for i, key in enumerate(("K1", "K2", "K3"), start=1):
        s = next(p for p in parts.values() if p.symbol.startswith("Sensor_Magnetic:") and p.ref == f"U{9 + i}")
        kx, ky = circuit.KEYS[key]
        assert math.hypot(s.x - kx, s.y - ky) <= 0.1 and s.side == "F"


def test_buttons_are_out_of_the_tapping_path(parts):
    for ref in ("SW1", "SW2"):
        bx, by = parts[ref].x, parts[ref].y
        assert by < min(y for _, y in circuit.KEYS.values()) - 9.5, ref


def test_art_zone_is_free_of_parts(parts):
    x0, y0, x1, y1 = circuit.ART_ZONE
    for p in parts.values():
        assert not (x0 - 2 < p.x < x1 + 2 and y0 - 2 < p.y < y1 + 2), p.ref


def test_board_fits_the_cheap_pcb_size():
    x0, y0, x1, y1 = circuit.OUTLINE
    assert x1 - x0 <= 100 and y1 - y0 <= 100


def test_references_are_unique():
    refs = [p.ref for p in circuit.parts()]
    assert len(refs) == len(set(refs))
