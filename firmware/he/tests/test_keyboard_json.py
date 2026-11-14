"""The libhmk configuration must describe the board circuit.py generates.

    cd firmware/he && uv run --no-project --with pytest pytest -q
"""
import json
from pathlib import Path

import pytest

import circuit
import he_model

KB = Path(__file__).resolve().parents[1] / "keyboards" / "atelier-he" / "keyboard.json"


@pytest.fixture(scope="module")
def kb():
    return json.loads(KB.read_text())


def gpio(pin: str) -> str:
    """circuit.py names pins PA2; libhmk names them A2."""
    assert pin.startswith("P")
    return pin[1:]


def test_keyboard_json_is_at32f405_hs_12mhz_three_keys(kb):
    assert kb["hardware"] == {"hse_value": 12_000_000, "driver": "at32f405xx"}
    assert kb["usb"]["port"] == "hs"
    assert kb["keyboard"]["num_keys"] == 3


def test_keyboard_json_adc_pins_match_circuit(kb):
    raw = kb["analog"]["raw"]
    assert "mux" not in kb["analog"]
    # key index k (1-based, left to right) reads the sensor under circuit.KEY_ORDER[k - 1]
    pins = {key: raw["input"][raw["vector"].index(i)] for i, key in enumerate(circuit.KEY_ORDER, start=1)}
    assert pins == {key: gpio(circuit.SENSOR_ADC[key]) for key in circuit.KEY_ORDER}


def test_initial_calibration_matches_model(kb):
    curve = he_model.REFERENCE.curve()
    rest, span = curve[0][1], curve[-1][1] - curve[0][1]
    cal = kb["calibration"]
    assert cal["initial_rest_value"] == pytest.approx(rest, rel=0.10)
    # libhmk takes the bottom-out at rest + max(this, learned): small enough that the weakest
    # switch (-10 % flux) still reaches it, so every key learns its own bottom on the first press.
    assert 0.3 * span <= cal["initial_bottom_out_threshold"] <= 0.7 * span


def test_invert_adc_matches_sensor_polarity(kb):
    # libhmk (scripts/schema/keyboard.py): invert_adc is "true if the ADC value is inversely
    # proportional to the travel distance". The DRV5056 rises with a south pole at its branded
    # face. Mounted on the bottom, branded face down, with the switch magnet's north pole facing
    # the board from above (Gateron), the field points out through the branded face: the same
    # sign. So the reading rises with travel.
    assert he_model.REFERENCE.curve()[-1][1] > he_model.REFERENCE.curve()[0][1]
    assert kb["analog"].get("invert_adc", False) is False


def test_default_keymap_is_osu_three_keys(kb):
    assert kb["keymap"][0] == ["KC_Z", "KC_X", "KC_C"]
    assert len(kb["layout"]["keymap"]) == 1 and len(kb["layout"]["keymap"][0]) == 3


def test_libhmk_is_pinned():
    import subprocess
    root = Path(__file__).resolve().parents[1]
    sha = subprocess.run(["git", "-C", str(root / "libhmk"), "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    assert sha in (root / "README.md").read_text()


def test_initial_rest_value_sits_above_every_switch_at_rest(kb):
    # libhmk only ever lowers a key's rest value. Start above the strongest switch's rest
    # (Gateron +15 G, +5 % sensor gain), or that key sits part-way into its travel forever.
    ref = he_model.REFERENCE
    strongest_rest_mT = 13.5
    v = ref.sensor.volts(strongest_rest_mT * 1.05, ref.vcc)
    assert kb["calibration"]["initial_rest_value"] >= ref.adc.counts_f(v)
