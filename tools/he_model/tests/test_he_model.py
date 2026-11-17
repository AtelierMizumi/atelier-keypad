"""Spec for the Hall-effect design model.

    cd tools/he_model && uv run --no-project --with pytest pytest -q

The model turns a switch geometry, a magnet, a sensor and an ADC into the
numbers the plan argues from: counts per millimetre of travel, the smallest
rapid-trigger sensitivity that noise allows, and the device-side latency.
"""
import math

import pytest

import he_model as m

# TI SLYA093 reference geometry: 2.8 mm x 3.4 mm cylinder magnet, its bottom
# 6.1 mm above the sensor at rest and 2.1 mm at bottom-out (4.0 mm of travel).
GEO = m.Geometry(rest_gap_mm=6.1, travel_mm=4.0)
MAG = m.Magnet(diameter_mm=2.8, length_mm=3.4, br_mT=1200)


# ------------------------------------------------------------- magnet field

def test_field_at_the_magnet_face_matches_the_closed_form():
    r, l = 1.4, 3.4
    assert m.field_mT(0.0, MAG) == pytest.approx(1200 / 2 * l / math.hypot(r, l), rel=1e-9)


def test_field_falls_with_distance():
    values = [m.field_mT(z / 10, MAG) for z in range(0, 100)]
    assert all(a > b for a, b in zip(values, values[1:]))


def test_reference_geometry_spans_about_9_to_82_mT():
    assert m.field_mT(6.1, MAG) == pytest.approx(8.8, abs=0.3)
    assert m.field_mT(2.1, MAG) == pytest.approx(82.3, abs=0.5)


# ------------------------------------------------------------------ sensor

def test_ratiometric_sensor_output_scales_with_supply_and_clamps():
    s = m.Sensor(name="49E", mV_per_mT_at_5V=14.0, quiescent_frac=0.5, ratiometric=True, polarity="bipolar")
    assert s.volts(0.0, vcc=3.3) == pytest.approx(1.65)
    assert s.volts(10.0, vcc=3.3) == pytest.approx(1.65 + 0.140 * 3.3 / 5.0)
    assert s.volts(1e6, vcc=3.3) == pytest.approx(3.3 * s.rail_frac_high)
    assert s.volts(-1e6, vcc=3.3) == pytest.approx(3.3 * s.rail_frac_low)


def test_adc_counts_round_down_and_stay_in_range():
    adc = m.Adc(bits=12, vref=3.3, msps=2.0)
    assert adc.counts(0.0) == 0
    assert adc.counts(3.3) == 4095
    assert adc.counts(1.65) == 2048


# ----------------------------------------------------------- the travel curve

@pytest.fixture
def design():
    return m.Design(GEO, MAG, m.SENSORS["OH49E"], m.Adc(bits=12, vref=3.3, msps=2.0), vcc=3.3)


def test_counts_rise_monotonically_with_travel(design):
    curve = design.curve(steps=401)
    assert curve[0][0] == 0.0 and curve[-1][0] == pytest.approx(4.0)
    counts = [c for _, c in curve]
    assert all(b >= a for a, b in zip(counts, counts[1:]))
    assert counts[-1] - counts[0] > 600


def test_the_shallow_end_is_the_worst_resolution(design):
    slopes = design.slopes(steps=401)  # counts per mm along the travel
    assert slopes[0] == min(slopes)
    assert slopes[-1] == max(slopes)


def test_rapid_trigger_floor_is_six_sigma_noise_over_the_worst_slope(design):
    noise = 1.5
    expected = 6 * noise / math.sqrt(16) / min(design.slopes(steps=401))
    assert design.rt_floor_mm(noise_rms_counts=noise, oversample=16) == pytest.approx(expected, rel=1e-6)


def test_saturating_sensor_loses_the_bottom_of_the_stroke():
    tight = m.Sensor(name="tight", mV_per_mT_at_5V=80.0, quiescent_frac=0.1, ratiometric=False, polarity="unipolar")
    d = m.Design(GEO, MAG, tight, m.Adc(bits=12, vref=3.3, msps=2.0), vcc=3.3)
    assert d.usable_travel_mm() < 3.0


# --------------------------------------------------------------- latency

def test_scan_time_is_conversions_over_sample_rate():
    t = m.scan_time_us(keys=6, oversample=16, adc_msps=2.0, settle_us=0.0)
    assert t == pytest.approx(48.0)


def test_latency_budget_full_speed_vs_high_speed():
    fs = m.latency_budget_us(scan_hz=8000, poll_hz=1000, filter_delay_us=0)
    hs = m.latency_budget_us(scan_hz=8000, poll_hz=8000, filter_delay_us=0)
    assert fs["worst"] == pytest.approx(125 + 1000)
    assert hs["worst"] == pytest.approx(125 + 125)
    assert hs["mean"] == pytest.approx(62.5 + 62.5)


def test_scan_must_fit_in_its_period():
    with pytest.raises(ValueError):
        m.check_scan_fits(keys=6, oversample=64, adc_msps=2.0, scan_hz=8000)


def test_finger_travel_dwarfs_usb_polling():
    # Releasing after 0.1 mm at 150 mm/s takes 0.67 ms; climbing 1.0 mm back to
    # a fixed reset point takes ten times as long, far more than one USB frame.
    assert m.finger_time_ms(0.1, 150) == pytest.approx(0.6667, rel=1e-3)
    assert m.finger_time_ms(1.0, 150) / m.finger_time_ms(0.1, 150) == pytest.approx(10)


# ------------------------------------------------- catalogue vs. datasheets

def test_drv5056_variants_are_ratiometric_with_datasheet_sensitivity():
    # TI SBAS644, at VCC = 5 V: A3 50 mV/mT (79 mT range), A4 25 mV/mT (158 mT range).
    a3, a4 = m.SENSORS["DRV5056A3"], m.SENSORS["DRV5056A4"]
    assert a3.ratiometric and a4.ratiometric
    assert a3.mV_per_mT_at_5V == 50.0 and a4.mV_per_mT_at_5V == 25.0


def test_drv5056a3_saturates_before_bottom_out_but_a4_does_not():
    # Fitted Jade through a 1.2 mm PCB: 80 mT at bottom-out against the A3's 79 mT range,
    # and 88 mT with a +10 % magnet. The A4 (158 mT) keeps the full stroke either way.
    ref = m.REFERENCE
    a3 = m.Design(ref.geometry, ref.magnet, m.SENSORS["DRV5056A3"], ref.adc, 3.3)
    assert a3.usable_travel_mm() < ref.geometry.travel_mm
    strong = m.Magnet(ref.magnet.diameter_mm, ref.magnet.length_mm, ref.magnet.br_mT * 1.1)
    assert m.Design(ref.geometry, strong, m.SENSORS["DRV5056A3"], ref.adc, 3.3).usable_travel_mm() < ref.geometry.travel_mm
    assert m.Design(ref.geometry, strong, m.SENSORS["DRV5056A4"], ref.adc, 3.3).usable_travel_mm() == pytest.approx(ref.geometry.travel_mm)
    assert ref.usable_travel_mm() == pytest.approx(ref.geometry.travel_mm)


def test_pinouts_are_recorded_and_differ():
    # Ouzhuo OH49E datasheet: 1 VCC, 2 GND, 3 OUT. TI DRV5056 SOT-23: 1 VCC, 2 OUT, 3 GND.
    assert m.SENSORS["OH49E"].pinout == ("VCC", "GND", "OUT")
    assert m.SENSORS["DRV5056A4"].pinout == ("VCC", "OUT", "GND")


# ------------------------------------- fitted to Gateron Jade (docs/research/he-switch-field.md)

SHAPES = [(1.5, 3.5), (2.0, 3.0)]   # magnet radius, length (mm): the Jade's is not published


@pytest.mark.parametrize("r,l", SHAPES)
def test_fit_reproduces_the_published_rest_and_bottom_flux(r, l):
    rest, bottom, travel = m.JADE
    mag, gap = m.fit_to_flux(rest, bottom, travel, r, l)
    assert m.field_mT(gap, mag) == pytest.approx(bottom, abs=0.1)
    assert m.field_mT(gap + travel, mag) == pytest.approx(rest, abs=0.1)


@pytest.mark.parametrize("r,l", SHAPES)
def test_thicker_pcb_drops_bottom_flux_like_durock(r, l):
    # Durock Rock HE: 640 G on 1.2 mm, 480 G on 1.6 mm (-25 %).
    mag, gap = m.fit_to_flux(*m.JADE, r, l)
    shift = m.Placement("bottom", 1.6).offset_from(m.REF_PLACEMENT)
    assert shift == pytest.approx(0.4)
    drop = 1 - m.field_mT(gap + shift, mag) / m.field_mT(gap, mag)
    assert 0.20 <= drop <= 0.28


@pytest.mark.parametrize("r,l", SHAPES)
def test_top_placement_saturates_drv5056a4(r, l):
    # More than a millimetre of the 3.5 mm stroke reads flat at the top of the sensor's range.
    d = m.jade_design(m.Placement("top", 1.2), m.SENSORS["DRV5056A4"], r, l)
    assert d.usable_travel_mm() < 2.5


@pytest.mark.parametrize("r,l", SHAPES)
def test_bottom_1p2_uses_half_the_a4_range(r, l):
    mag, gap = m.fit_to_flux(*m.JADE, r, l)
    assert 0.45 <= m.field_mT(gap, mag) / 158.0 <= 0.60


def test_rc_noise_follows_the_noise_bandwidth():
    fc = 1 / (2 * math.pi * 1e3 * 47e-9)
    assert m.rc_noise_mT(1e3, 47e-9) == pytest.approx(215e-6 * math.sqrt(fc * math.pi / 2), rel=1e-9)
    assert m.rc_noise_mT(1e3, 10e-9) > m.rc_noise_mT(1e3, 47e-9)


def test_47nF_filter_gives_rt_floor_under_30_um():
    d = m.REFERENCE
    noise = d.noise_counts(m.rc_noise_mT(1e3, 47e-9), adc_rms_counts=1.5, oversample=32)
    assert d.rt_floor_mm(noise_rms_counts=noise, oversample=1) < 0.030
    noise_10n = d.noise_counts(m.rc_noise_mT(1e3, 10e-9), adc_rms_counts=1.5, oversample=32)
    assert d.rt_floor_mm(noise_rms_counts=noise_10n, oversample=1) > 0.035


def test_reference_is_the_fitted_jade_on_the_bottom_of_a_1p2_mm_board():
    assert m.REF_PLACEMENT == m.Placement("bottom", 1.2)
    assert m.REFERENCE.sensor.name == "DRV5056A4"
    assert m.REFERENCE.geometry.travel_mm == 3.5


def test_reversed_magnet_gives_a_flat_reading_on_a_unipolar_sensor():
    # The DRV5056 only answers one pole. If the switch's magnet faced the other way, the output
    # would sit at its zero-field level for the whole stroke: no flag in firmware can recover it.
    ref = m.REFERENCE
    reversed_mag = m.Magnet(ref.magnet.diameter_mm, ref.magnet.length_mm, -ref.magnet.br_mT)
    d = m.Design(ref.geometry, reversed_mag, ref.sensor, ref.adc, ref.vcc)
    counts = {c for _, c in d.curve()}
    assert counts == {int(ref.adc.counts_f(ref.sensor.volts(0.0, ref.vcc)))}
