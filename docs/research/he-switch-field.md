# Magnetic switch field at the sensor: what the published numbers say

Written 14 Nov 2026, instead of a bench measurement (there is no bench). Every
number below has a source; every inference is marked as one.

## Published numbers

| Source | Figure |
|---|---|
| [Wooting, Gateron Magnetic Jade](https://wooting.io/product/gateron-magnetic-jade-switches), [Gateron blog](https://www.gateron.com/blog/detail/elevate-your-typing-experience-with-the-gateron-magnetic-jade-keyboard-switch), [MaxGaming](https://us.maxgaming.com/us/switches/magnetic-jade-linear-switch) | Travel 3.5 ± 0.2 mm; initial flux 120 ± 15 G (12 mT); bottom-out 800 ± 80 G (80 mT) |
| [Gateron, Magic/Magnetic Jade product page](https://www.gateron.com/products/gateron-magic-jade-switch) | Bottom-out 700 ± 80 G (disagrees with the above) |
| [Gateron, Magnetic Jade Gaming](https://www.gateron.com/products/gateron-magnetic-jade-gaming-switch-set?VariantsId=10864) | Travel 3.5 ± 0.1 mm; bottom-out 700 ± 30 G "at PCB 1.2 mm" |
| [Gateron, magnetic switch review](https://www.gateron.com/blog/detail/magnetic-switch-keyboard-review) | Durock Rock HE: 640 ± 60 G on a 1.2 mm PCB, 480 ± 60 G on a 1.6 mm PCB |
| [TI DRV5056 (SBAS644)](https://www.ti.com/lit/gpn/drv5056) | A3 50 mV/mT, 79 mT range; A4 25 mV/mT, 158 mT range (at 5 V, ratiometric); noise density 215 nT/√Hz at 3.3 V; bandwidth 20 kHz |
| [peppapighs/HE60](https://github.com/peppapighs/HE60) | Open-source 8 kHz board: AT32F405, 12 MHz HSE, USB HS; "the components in the BOM are all mounted on the bottom side of the PCB"; sensors tried include DRV5055A3 |
| [libhmk he60-v2 keyboard.json](https://github.com/peppapighs/libhmk/blob/main/keyboards/he60-v2/keyboard.json) | `hse_value 12000000`, `driver at32f405xx`, `port hs`, `initial_rest_value 2400`, `initial_bottom_out_threshold 650`, `invert_adc false` |
| [ebastler/marbastlib](https://github.com/ebastler/marbastlib) `SW_MX_HE_0deg_1u` | Gateron Jade footprint with the SOT-23 sensor on **F.Cu** at the switch centre, NPTH pegs at ±5.08 mm, no centre hole |
| [minipad-firmware](https://github.com/minipadKB/minipad-firmware) | "Rapid Trigger … 0.01 mm resolution": the settings step, not a measured noise floor |

Not found: a Gateron dimension drawing, the magnet size and grade, and where
Gateron's test sensor sits. Gateron's own pages return 403 to scripts; the
figures above come from cached product pages and resellers.

## Inferences

1. **The flux figures are measured through the PCB, with the sensor on the
   bottom.** If the sensor sat on top, PCB thickness could not change the
   reading, yet Durock's 1.2 → 1.6 mm drop is 25 %.
2. **A sensor on the top side sees far more than the published figure.** Fitting
   an on-axis cylinder model to 12 mT at rest and 80 mT at bottom-out, then
   moving the sensor 2.2 mm closer (1.2 mm of PCB plus 0.5 mm package depth on
   each side), predicts 290–525 mT at bottom-out: two to three times the
   DRV5056A4's 158 mT range. The A4 then reads flat over the last 1.2–1.4 mm
   of the 3.5 mm stroke. (An earlier version of this file said 2.2–2.3 mm; that
   came from a sign error in a scratch script, fixed when the model got tests.)
3. **The fitted model predicts the thickness effect on its own.** Moved 0.4 mm
   further away, it drops 22–25 %, against Durock's measured 25 %. This is the
   check that makes the fit worth using.

## Options (DRV5056 at 3.3 V, 12-bit ADC, 1.5 counts ADC noise, 32× oversample)

Output of `python3 tools/he_model/he_model.py`, for both assumed magnet shapes:

| Placement | Peak field | Usable travel of 3.5 mm | RT floor (6σ), 1 k/10 nF | 1 k/47 nF |
|---|---|---|---|---|
| Top side, A4 (rev 2 as routed on 14 Nov) | 290–525 mT | 2.1–2.3 mm | saturates | saturates |
| **Bottom, 1.2 mm PCB, A4 (chosen)** | 80 mT (51 % of range) | 3.5 mm | 43–45 µm | 24–25 µm |
| Bottom, 1.6 mm PCB, A3 | 60–61 mT (76–77 % of range) | 3.5 mm | 51–53 µm | 25–26 µm |

With the +10 % magnet tolerance the bottom 1.2 mm / A4 peak is 88 mT (56 %),
and the 1.6 mm / A3 option creeps to 85 % of its range. That thin margin is
why A4 on 1.2 mm is the choice, even though the A3 floor is about the same.

Two magnet sizes (r 1.5 / l 3.5 mm and r 2.0 / l 3.0 mm) agree closely wherever
the sensor sits through the PCB; they differ only on the top side, where both
saturate. The unknown magnet size does not change the choice.

The floors are far below the 0.1 mm most boards advertise. What limits the
real board is mechanical: ±0.2 mm travel and ±10 % flux from switch to switch,
which libhmk's per-key automatic calibration absorbs.

The script lives in `tools/he_model/` (`fit_to_flux`, `Placement`); its tests
pin the numbers in this file.
