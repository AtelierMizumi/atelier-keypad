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
    pinout: tuple[str, str, str] = ("VCC", "OUT", "GND")  # SOT-23 pins 1, 2, 3

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
        # A gap below zero means the magnet would pass through the sensor plane: clamp to the face.
        b = field_mT(max(self.geometry.rest_gap_mm - travel, 0.0), self.magnet)
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

    def counts_per_mT(self) -> float:
        s = self.sensor
        v_per_mT = s.mV_per_mT_at_5V / 1000 * (self.vcc / 5.0 if s.ratiometric else 1.0)
        return v_per_mT / self.adc.vref * (1 << self.adc.bits)

    def noise_counts(self, sensor_noise_mT: float, adc_rms_counts: float = 1.5, oversample: int = 32) -> float:
        """RMS noise at the ADC: the filtered sensor noise is correlated across a burst of samples,
        so oversampling only averages the ADC's own noise."""
        return math.hypot(sensor_noise_mT * self.counts_per_mT(), adc_rms_counts / math.sqrt(oversample))

    def span_counts(self) -> int:
        c = self.curve()
        return c[-1][1] - c[0][1]


# ------------------------------------------------- fitting to published flux

def fit_to_flux(rest_mT: float, bottom_mT: float, travel_mm: float,
                radius_mm: float, length_mm: float) -> tuple[Magnet, float]:
    """Magnet remanence and bottom-out gap that reproduce a switch's published rest and
    bottom-out flux, for an assumed magnet shape. Returns (magnet, gap at bottom-out in mm)."""
    unit = Magnet(2 * radius_mm, length_mm, 1.0)
    target = rest_mT / bottom_mT
    lo, hi = 1e-4, 50.0          # the ratio rises monotonically with the gap
    for _ in range(200):
        mid = (lo + hi) / 2
        if field_mT(mid + travel_mm, unit) / field_mT(mid, unit) < target:
            lo = mid
        else:
            hi = mid
    gap = (lo + hi) / 2
    return Magnet(2 * radius_mm, length_mm, bottom_mT / field_mT(gap, unit)), gap


@dataclass(frozen=True)
class Placement:
    """Where the Hall element sits relative to the PCB's top surface (the switch side).

    `package_depth_mm` is the element's distance from the package face that touches the
    PCB; for a SOT-23 the element is near mid-height (~0.5 mm)."""
    side: str            # "top" or "bottom"
    pcb_mm: float
    package_depth_mm: float = 0.5

    def depth_mm(self) -> float:
        """Element below the PCB top surface (negative: above it)."""
        if self.side == "bottom":
            return self.pcb_mm + self.package_depth_mm
        if self.side == "top":
            return -self.package_depth_mm
        raise ValueError(f"side must be top or bottom, not {self.side!r}")

    def offset_from(self, ref: "Placement") -> float:
        """Extra distance from the magnet compared with `ref` (positive: further away)."""
        return self.depth_mm() - ref.depth_mm()


def rc_noise_mT(r_ohm: float, c_farad: float, density_nT: float = 215.0) -> float:
    """RMS input-referred sensor noise through a one-pole RC (noise bandwidth pi/2 * fc).
    215 nT/sqrt(Hz) is the DRV5056 at 3.3 V (TI SBAS644)."""
    fc = 1 / (2 * math.pi * r_ohm * c_farad)
    return density_nT * 1e-6 * math.sqrt(fc * math.pi / 2)


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
    "OH49E": Sensor("OH49E", 14.0, 0.5, True, "bipolar", price_usd=0.23,
                    note="LCSC C85573, SOT-23; 1.4 mV/G at 5 V; 2.3 V minimum supply",
                    pinout=("VCC", "GND", "OUT")),
    # TI DRV5056 (SBAS644): unipolar and ratiometric. Zero field sits at 0.6 V of 5 V,
    # so nearly the whole output range follows the magnet. Range = 79 mT (A3), 158 mT (A4).
    "DRV5056A3": Sensor("DRV5056A3", 50.0, 0.12, True, "unipolar", rail_frac_low=0.12, rail_frac_high=0.91,
                        noise_rms_counts=1.0, price_usd=0.60, note="saturates near bottom-out with this magnet"),
    "DRV5056A4": Sensor("DRV5056A4", 25.0, 0.12, True, "unipolar", rail_frac_low=0.12, rail_frac_high=0.91,
                        noise_rms_counts=1.0, price_usd=0.60, note="price from memory, confirm on LCSC"),
}

KEYS = 3          # analog keys on rev 2 (three-key layout)
OVERSAMPLE = 32   # 3 keys x 32 samples fit the same 48 us as 6 x 16

# Gateron Magnetic Jade: 120 G at rest, 800 G at bottom-out, 3.5 mm travel, measured through
# a 1.2 mm PCB with the sensor on the bottom (docs/research/he-switch-field.md).
JADE = (12.0, 80.0, 3.5)
REF_PLACEMENT = Placement("bottom", 1.2)
ADC = Adc(12, 3.3, 2.0)


def jade_design(placement: Placement, sensor: Sensor, radius_mm: float = 1.5, length_mm: float = 3.5) -> Design:
    """The fitted Jade with its sensor at `placement` instead of the reference."""
    mag, gap = fit_to_flux(*JADE, radius_mm, length_mm)
    rest_gap = gap + JADE[2] + placement.offset_from(REF_PLACEMENT)
    return Design(Geometry(rest_gap, JADE[2]), mag, sensor, ADC, 3.3)


REFERENCE = jade_design(REF_PLACEMENT, SENSORS["DRV5056A4"])


PLACEMENTS = [
    ("Top side, A4", Placement("top", 1.2), "DRV5056A4"),
    ("Bottom, 1.2 mm PCB, A4", Placement("bottom", 1.2), "DRV5056A4"),
    ("Bottom, 1.6 mm PCB, A3", Placement("bottom", 1.6), "DRV5056A3"),
]


def report() -> str:
    lines = ["| Placement | Magnet r/l (mm) | Peak field (mT) | Usable travel (mm) | RT floor 1k/10nF (um) | RT floor 1k/47nF (um) |",
             "|---|---|---|---|---|---|"]
    for name, place, sensor in PLACEMENTS:
        for r, l in ((1.5, 3.5), (2.0, 3.0)):
            d = jade_design(place, SENSORS[sensor], r, l)
            peak = field_mT(max(d.geometry.rest_gap_mm - d.geometry.travel_mm, 0.0), d.magnet)
            usable = d.usable_travel_mm()
            if usable < d.geometry.travel_mm - 0.05:
                rt = ("saturates", "saturates")
            else:
                rt = tuple(f"{d.rt_floor_mm(noise_rms_counts=d.noise_counts(rc_noise_mT(1e3, c)), oversample=1) * 1000:.0f}"
                           for c in (10e-9, 47e-9))
            lines.append(f"| {name} | {r}/{l} | {peak:.0f} | {usable:.2f} | {rt[0]} | {rt[1]} |")
    t = check_scan_fits(KEYS, OVERSAMPLE, 2.0, 8000)
    lines.append("")
    lines.append(f"Scan of {KEYS} keys x {OVERSAMPLE} samples at 2 Msps: {t:.0f} us of a 125 us period.")
    for name, poll in (("Full speed, 1 kHz", 1000), ("High speed, 8 kHz", 8000)):
        b = latency_budget_us(8000, poll)
        lines.append(f"{name}: worst {b['worst']:.0f} us, mean {b['mean']:.0f} us (device side).")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
