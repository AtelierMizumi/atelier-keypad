"""Back-of-envelope model of a Hall-effect key: magnet -> field -> volts -> ADC counts.

Every number the Hall-effect plan quotes for resolution, rapid-trigger floor
and device latency comes from here, so a changed assumption (a weaker magnet,
a noisier sensor) changes the plan's numbers in one place.

    python3 he_model.py            prints the comparison table used in the plan

Field model: on-axis field of a uniformly magnetised cylinder,
    B(z) = Br/2 * ((z + L) / sqrt(R^2 + (z + L)^2) - z / sqrt(R^2 + z^2)),
z measured from the magnet face nearest the sensor. Real switches differ
(magnet grade, off-axis sensor, steel in the switch), so phase 1 of the plan
replaces these curves with measured ones.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Magnet:
    diameter_mm: float
    length_mm: float
    br_mT: float            # remanence; N35 ~1200 mT, N52 ~1450 mT


@dataclass(frozen=True)
class Geometry:
    rest_gap_mm: float      # magnet face to sensor face with the key up
    travel_mm: float


@dataclass(frozen=True)
class Sensor:
    name: str
    mV_per_mT_at_5V: float  # sensitivity at 5 V; at `vcc` if not ratiometric
    quiescent_frac: float   # zero-field output as a fraction of vcc
    ratiometric: bool
    polarity: str           # "bipolar" or "unipolar"
    rail_frac_low: float = 0.17
    rail_frac_high: float = 0.84
    noise_rms_counts: float = 1.5  # at the ADC, before oversampling; to be measured
    price_usd: float = 0.0
    note: str = ""

    def volts(self, b_mT: float, vcc: float) -> float:
        sens = self.mV_per_mT_at_5V / 1000 * (vcc / 5.0 if self.ratiometric else 1.0)
        v = self.quiescent_frac * vcc + sens * b_mT
        return min(max(v, self.rail_frac_low * vcc), self.rail_frac_high * vcc)


@dataclass(frozen=True)
class Adc:
    bits: int
    vref: float
    msps: float

    @property
    def full(self) -> int:
        return (1 << self.bits) - 1

    def counts_f(self, v: float) -> float:
        return min(max(v / self.vref * (1 << self.bits), 0.0), float(self.full))

    def counts(self, v: float) -> int:
        return int(self.counts_f(v))


def field_mT(z_mm: float, magnet: Magnet) -> float:
    r, l = magnet.diameter_mm / 2, magnet.length_mm
    return magnet.br_mT / 2 * ((z_mm + l) / math.hypot(r, z_mm + l) - z_mm / math.hypot(r, z_mm))


@dataclass(frozen=True)
class Design:
    geometry: Geometry
    magnet: Magnet
    sensor: Sensor
    adc: Adc
    vcc: float

    def _counts_at(self, travel: float) -> float:
        b = field_mT(self.geometry.rest_gap_mm - travel, self.magnet)
        return self.adc.counts_f(self.sensor.volts(b, self.vcc))

    def curve(self, steps: int = 401) -> list[tuple[float, int]]:
        """(travel mm, ADC count) from key up to bottom-out."""
        t = self.geometry.travel_mm
        return [(t * i / (steps - 1), int(self._counts_at(t * i / (steps - 1)))) for i in range(steps)]

    def slopes(self, steps: int = 401) -> list[float]:
        """Counts per mm at each step (forward difference, unquantised)."""
        t = self.geometry.travel_mm
        h = t / (steps - 1)
        xs = [h * i for i in range(steps)]
        out = []
        for x in xs:
            a, b = (x, x + h) if x + h <= t + 1e-12 else (x - h, x)
            out.append((self._counts_at(b) - self._counts_at(a)) / h)
        return out

    def usable_travel_mm(self, steps: int = 401) -> float:
        """Travel until the reading stops changing (sensor or ADC saturates)."""
        curve = [(x, self._counts_at(x)) for x, _ in self.curve(steps)]
        top = max(c for _, c in curve)
        return next(x for x, c in curve if c >= top - 1e-9)

    def rt_floor_mm(self, noise_rms_counts: float | None = None, oversample: int = 16) -> float:
        """Smallest rapid-trigger distance that noise cannot fake: 6 sigma over the worst slope."""
        noise = self.sensor.noise_rms_counts if noise_rms_counts is None else noise_rms_counts
        live = [s for s in self.slopes() if s > 0]
        return 6 * noise / math.sqrt(oversample) / min(live)

    def span_counts(self) -> int:
        c = self.curve()
        return c[-1][1] - c[0][1]


# ----------------------------------------------------------------- timing

def scan_time_us(keys: int, oversample: int, adc_msps: float, settle_us: float = 0.0) -> float:
    return keys * oversample / adc_msps + keys * settle_us


def check_scan_fits(keys: int, oversample: int, adc_msps: float, scan_hz: float, settle_us: float = 0.0) -> float:
    t = scan_time_us(keys, oversample, adc_msps, settle_us)
    period = 1e6 / scan_hz
    if t > period:
        raise ValueError(f"scan takes {t:.1f} us, period is {period:.1f} us")
    return t


def latency_budget_us(scan_hz: float, poll_hz: float, filter_delay_us: float = 0.0) -> dict[str, float]:
    """Device-side delay from a key crossing its threshold to the report leaving the device."""
    scan, poll = 1e6 / scan_hz, 1e6 / poll_hz
    return {"worst": scan + poll + filter_delay_us, "mean": scan / 2 + poll / 2 + filter_delay_us}


def finger_time_ms(distance_mm: float, speed_mm_s: float) -> float:
    return distance_mm / speed_mm_s * 1000


# ----------------------------------------------------------- the candidates

SENSORS = {
    # 49E family: cheap, ratiometric, bipolar, so half the range is unused.
    "OH49E": Sensor("OH49E", 14.0, 0.5, True, "bipolar", price_usd=0.24,
                    note="LCSC C85573, SOT-23; 1.4 mV/G at 5 V"),
    # Unipolar: zero field sits near the bottom rail, so the whole range is usable.
    "DRV5056A3": Sensor("DRV5056A3", 15.0, 0.6 / 3.3, False, "unipolar", rail_frac_low=0.6 / 3.3,
                        rail_frac_high=0.9, noise_rms_counts=1.0, price_usd=0.60,
                        note="TI, 3.3 V figures; price from memory, confirm"),
}

REFERENCE = Design(Geometry(6.1, 4.0), Magnet(2.8, 3.4, 1200), SENSORS["OH49E"], Adc(12, 3.3, 2.0), 3.3)


def report() -> str:
    lines = ["| Sensor | Span (counts) | Worst slope (counts/mm) | RT floor, 16x oversample (mm) | Usable travel (mm) |",
             "|---|---|---|---|---|"]
    for s in SENSORS.values():
        d = Design(REFERENCE.geometry, REFERENCE.magnet, s, REFERENCE.adc, REFERENCE.vcc)
        live = [x for x in d.slopes() if x > 0]
        lines.append(f"| {s.name} | {d.span_counts()} | {min(live):.0f} | {d.rt_floor_mm():.3f} | {d.usable_travel_mm():.2f} |")
    t = check_scan_fits(6, 16, 2.0, 8000)
    lines.append("")
    lines.append(f"Scan of 6 keys x 16 samples at 2 Msps: {t:.0f} us of a 125 us period.")
    for name, poll in (("Full speed, 1 kHz", 1000), ("High speed, 8 kHz", 8000)):
        b = latency_budget_us(8000, poll)
        lines.append(f"{name}: worst {b['worst']:.0f} us, mean {b['mean']:.0f} us (device side).")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
