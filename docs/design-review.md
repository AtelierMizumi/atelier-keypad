# Atelier6K rev 0 — design review

**Status of rev 0: unverified.** The board was drawn in KiCad 6 in mid-2022 and
has no recorded bring-up. This review is a desk check done in November 2026
from the schematic netlist, the PCB file, KiCad 10 ERC/DRC and the QMK
sources. Nothing here was measured on hardware, and a desk check cannot
replace building and testing a board.

Raw reports: [`reports/erc.json`](reports/erc.json), [`reports/drc.json`](reports/drc.json).
Regenerate them with `scripts/export.sh`.

## Verdict

Do not order rev 0 as it is. The USB, MCU and key-matrix core looks sound, but
the lighting cannot work as designed with the current firmware, the LED power
budget exceeds what the port is allowed to supply, and there is no overcurrent
protection. The items marked **Blocker** should be fixed in a rev 0.2 first.

## Findings

| # | Severity | Area | Finding |
|---|----------|------|---------|
| 1 | Blocker | Power | No fuse between VBUS and +5V |
| 2 | Blocker | Power | LED current can exceed the USB budget |
| 3 | Blocker | Firmware / LEDs | Underglow chain on PB4 is driven as a PWM backlight |
| 4 | Blocker | LEDs | Per-key LED part is ambiguous; footprint is named after a non-addressable LED |
| 5 | High | Power | No decoupling at any of the 10 addressable LEDs |
| 6 | High | Layout | MCU decoupling capacitors sit in a row at the board edge |
| 7 | Medium | Power | Three 0.1 µF capacitors for five MCU supply pins |
| 8 | Medium | Firmware | `RGBW` defined for RGB LEDs; `BOATLOADER` typo; stale QMK APIs |
| 9 | Medium | Layout | 240 DRC errors against the project's own rules |
| 10 | Low | Clock | Crystal load capacitors not matched to a specific crystal |
| 11 | Low | Schematic | ERC noise: missing power flags, wrong pin type on LED DOUT |
| 12 | Low | Docs | Board is 2-layer, 1.09 mm thick in the file; README promised a fuse |

### 1. No fuse between VBUS and +5V (Blocker)

`USB1.VBUS` connects straight to the `+5V` net that feeds the MCU and all ten
LEDs. The original README lists a fuse in the parts list, but the schematic has
none. A short on the board (a solder bridge on the hand-soldered TQFP-44 or
USB-C pads is the likely one) is then limited only by the host port.

Fix: add a 500 mA hold polyfuse (1206 PTC) in series with VBUS, before
everything else.

### 2. LED current can exceed the USB budget (Blocker)

There are 6 per-key LEDs and 4 underglow LEDs. At full white an SK6812 or
WS2812B draws up to about 60 mA, so the worst case is about 600 mA plus the
MCU. The CC pins carry 5.1 kΩ pull-downs, which identifies the board as a
plain USB device entitled to the default current (500 mA on USB 2.0), and
`config.h` requests exactly 500 mA.

Fix: cap brightness in firmware (`RGBLIGHT_LIMIT_VAL` around 120 of 255), and
size the fuse from finding 1 accordingly.

### 3. Underglow chain is not driven as addressable LEDs (Blocker)

The schematic has two separate data chains:

- `InKeyRGB`: PD0 → R7 (300 Ω) → MX1 … MX6
- `BackRGB`: PB4 → R8 (300 Ω) → D1 … D4

`config.h` sets `RGB_DI_PIN D0` with `RGBLED_NUM 6`, which matches the per-key
chain. It also sets `BACKLIGHT_PIN B4` with `BACKLIGHT_ENABLE = yes`, so PB4
outputs a PWM dimming signal into the data input of D1. Addressable LEDs do
not understand PWM; the four underglow LEDs will stay dark or flicker
randomly. The QMK version this was written for drives a single WS2812 chain.

Fix (hardware, preferred): join the chains, MX6 DOUT → D1 DIN, and drive all
ten from PD0 with `RGBLED_NUM 10`. Fix (firmware only): remove the backlight
feature and accept that the underglow is unused.

### 4. Per-key LED part is ambiguous (Blocker)

The MX footprint is `Cherry-MX_PCB-Mounted_LTST-A683CEGBW_Kailh_Socket`. The
LTST-A683CEGBW is a plain reverse-mount RGB LED with a common anode and three
cathodes. The schematic symbol on the same footprint has `GND`, `DIN`, `DOUT`
and `VCC` pins, which only makes sense for an addressable reverse-mount LED
such as the SK6812MINI-E. The land pattern (3.4 × 3.0 mm cut-out, pads at
±2.6 / ±0.75 mm) is the usual SK6812MINI-E pattern, so that part probably
fits, but the pad-to-pin assignment was not checked against a datasheet.

Fix: decide on the exact LED part, then check each pad number and the
orientation mark against its datasheet before ordering. Fitting an
LTST-A683CEGBW would short data lines to its cathodes.

### 5. No decoupling at the LEDs (High)

Commit `decided to nuke all led capacitor` removed them. WS2812B and SK6812
datasheets call for 100 nF across VDD/VSS at every LED; without it, switching
transients ride on the shared +5V rail that also powers the MCU and USB.

Fix: 100 nF per LED close to its VDD pin, plus one bulk capacitor
(10–47 µF) where the LED supply branches off.

### 6. MCU decoupling placement (High)

C1, C4, C5 and C7 are lined up along the bottom edge next to the crystal,
several millimetres of 0.3 mm trace away from the supply pins they serve
(`UVCC` pin 2, `VCC` pins 14 and 34, `AVCC` pins 24 and 44, on three sides of
the package). A decoupling capacitor only works when its loop to the pin is
short.

Fix: move one 100 nF capacitor directly next to each supply pin and return it
to the ground pour through its own via.

### 7. Decoupling count (Medium)

Three 0.1 µF capacitors (C1, C4, C5) and one 10 µF (C7) cover five supply
pins. `UCAP` has its 1 µF (C6), which is correct. The usual arrangement is one
100 nF per supply pin plus the bulk capacitor.

### 8. Firmware issues (Medium)

- `#define RGBW` tells QMK the LEDs have a fourth white channel. With RGB
  parts every colour after the first LED is shifted. Remove it unless
  SK6812RGBW parts are really fitted.
- `rules.mk` has `BOATLOADER = caterina`; the misspelt variable is ignored. The
  intended setting is `BOOTLOADER = caterina` (or `atmel-dfu` for a blank chip,
  which ships with the Atmel DFU bootloader).
- `config_common.h`, `UNUSED_PINS`, `RGB_DI_PIN`, `DEBOUNCING_DELAY`,
  `RESET` and the USB descriptor macros were removed from QMK after 2022. The
  source needs a port to `keyboard.json` before it builds on current QMK. The
  committed `.hex` is the 2022 build.
- `UNUSED_PINS` lists `C6` twice and omits `C7`. Harmless, but wrong.

Matrix pins were checked and agree with the schematic: rows PD5, PD6, PD7;
columns PD1, PD2, PD3; diodes point from switch to row, matching
`DIODE_DIRECTION COL2ROW`.

### 9. DRC errors (Medium)

KiCad 10 DRC against the rules stored in the project:

| Count | Check | Assessment |
|------:|-------|------------|
| 199 | Track width 0.15 mm < 0.20 mm minimum | Real. Signal tracks are below the project's own minimum. 0.15 mm is within most fabs' capability but leaves no margin; widen to 0.2 mm. |
| 24 | Copper to board edge | Expected. Pads beside the reverse-mount LED cut-outs. |
| 8 | Track to hole clearance 0.20–0.24 mm < 0.25 mm | Real, marginal. Tracks squeezed past switch mounting holes. |
| 7 | Footprint type (SMD / through-hole flag) | Cosmetic. Affects pick-and-place output only. |
| 2 | Pad clearance 0.175 mm on USB1 | From the hand-solder USB-C footprint; acceptable. |

Unconnected items: 0. Connectivity was compared pad by pad between the
schematic netlist and the PCB: 56 of 62 nets match exactly, and the other 6
differ only in the second pair of pins on the three tactile switches, which
are tied together inside the switch.

Power tracks (`+5V`, `GND`) are 0.3 mm. That carries the load, but 0.5 mm or
wider on the LED supply would lower the voltage drop along the chain.

### 10. Crystal load capacitors (Low)

C2 and C3 are 22 pF on a 16 MHz 3225 crystal. That suits a crystal specified
for roughly 16–18 pF load. Many 3225 parts are specified for 8–12 pF, where
22 pF would pull the frequency low. Pick the crystal first and compute
`C = 2 × (CL − Cstray)`.

### 11. ERC noise (Low)

Of 320 ERC items, 7 are errors: two missing `PWR_FLAG`s on `+5V` and `GND`, and
five `DOUT` pins typed as inputs in the Cherry MX RGB symbol. Neither affects
the board. The rest are off-grid wires and library-link warnings from the
KiCad 6 → 10 migration.

### 12. Checked and found correct

- USB-C: CC1 and CC2 each have their own 5.1 kΩ pull-down; both D+/D− pin
  pairs are joined so the plug works in either orientation.
- 22 Ω series resistors on D+ and D−; PRTR5V0U2X ESD protection on the
  connector side.
- ATmega32U4: `UVCC`, `VBUS`, `VCC`, `AVCC` on +5V; `UCAP` 1 µF; `HWB` pulled
  low through 10 kΩ; `RESET` pulled up through 10 kΩ with a push-button to
  ground.
- 300 Ω series resistor at the start of each LED data chain.

## Suggested scope for rev 0.2

1. Polyfuse on VBUS.
2. One LED chain of ten, 100 nF per LED, bulk capacitor on the LED rail.
3. Confirm the per-key LED part and its pinout.
4. Decoupling capacitor at each MCU supply pin.
5. Signal tracks to 0.2 mm, power to 0.5 mm, clear the hole-clearance errors.
6. Port the firmware to current QMK with a brightness cap.
