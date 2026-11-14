# Atelier rev 2 (HE): design spec

Status: **schematic, board and case designed and checked (ERC 0, DRC 0); nothing built.** See [`rev2-board.md`](rev2-board.md). Branch `plan/hall-effect`,
November 2026. One unit, for one player, on a budget of **1,000,000 VND**
(about 38 USD) all-in. Prices marked *estimate* in `hardware/he/bom.csv` were not found in a live listing.

How Hall sensing and rapid trigger work: [`hall-effect-how-it-works.md`](hall-effect-how-it-works.md).
Build plan: [`superpowers/plans/2026-11-14-atelier6k-he.md`](superpowers/plans/2026-11-14-atelier6k-he.md).
Task 0 (prices, pinouts, what to order): [`hall-effect-task0.md`](hall-effect-task0.md).
PCB art and easter eggs: [`pcb-art.md`](pcb-art.md).
Numbers marked *model* come from `tools/he_model/he_model.py` (20 tests with the budget).

## What changed after the first review

| Before | Now | Why |
|---|---|---|
| 6 analog keys in the rev 0 3 + 3 stagger | **3 analog keys on a finger arc**, 2 small buttons | osu! standard needs two or three keys; six keys put the hand off-centre |
| Rev 0 outline and holes | New, smaller outline, centred on the keys | Ergonomics first; also a cheaper PCB and case |
| PCB edge exposed between acrylic layers | **Closed tub**: the PCB sits inside the case, coated, behind a gasket | Sweaty hands: no touchable copper, no path for sweat |
| 5 units, ~18 USD each | **1 unit, ≤ 1,000,000 VND including shipping** | Your budget |
| OH49E baseline | **DRV5056A4** primary | With three keys the better sensor costs ~1.1 USD more in total; the A3 variant saturates (see *Sensor*) |

## What it has to beat

| | Wooting UwU RGB | SayoDevice O3C | **Atelier rev 2 target** |
|---|---|---|---|
| Analog keys | 3 (+3 digital) | 3 | **3** (+2 digital) |
| USB polling | 1 kHz | 8 kHz | **8 kHz** |
| Actuation / RT step | 0.1–4.0 mm, 0.05 mm steps (retailer) | down to 0.05 mm (retailer) | **≤ 0.02 mm floor on the model; measured per key** |
| Price | 69.69 USD at launch | ~27–40 USD | **≤ 38 USD for one unit, shipping included** |
| Open | no | no | **yes** |

Sources: [Wooting UwU launch](https://wooting.io/post/uwu-founders-campaign-sneak-peak),
[UwU product page](https://library.wooting.io/Wooting-UwU-8918becd3be045bc95e9d79c8df26628),
[Wooting 80HE polling](https://wooting.io/post/wooting-80he-the-true-polling-rate),
[O3C at CNX Software](https://www.cnx-software.com/2026/03/09/sayodevice-o3c-3-key-hall-effect-keypad-boasts-8000hz-polling-rate-for-playing-rhythm-games/),
[RTINGS 80HE](https://www.rtings.com/keyboard/reviews/wooting/80he).

Honest position: a mass-made O3C costs about what our single unit costs. This
board wins on a finer measured rapid-trigger floor, a layout fitted to one
hand, a sealed case, and being open; not on price.

## Layout and ergonomics

```
        ┌──────────────────────────────────────────┐
        │  (esc)                           (retry) │   small buttons, far edge,
        │              ┌──────┐                    │   out of the tapping path
        │   ┌──────┐   │  K2  │   ┌──────┐         │
        │   │  K1  │   │middle│   │  K3  │         │   middle key 4.76 mm further
        │   │      │   └──────┘   │      │         │   away: the middle finger is
        │   └──────┘              └──────┘         │   the longest
        │                                          │
        └──────────────── wrist side ──────────────┘   6° wedge, front edge low
```

- **Three keys, 19.05 mm apart, middle key 4.76 mm (¼ u) forward.** The arc
  follows the fingertips of index, middle and ring when the hand rests flat.
  It is symmetric, so it works for either hand and the board is not lopsided.
- **Centred.** The board outline is centred on the middle key; the cable exits
  at the far edge, behind the middle key.
- **6° typing angle from the feet** (1.0 mm front, 7.5 mm rear), front edge as low as the stack allows. Evidence for any exact
  angle is weak (vendor blogs, forum reports), so the case generator takes the
  angle as a parameter and Task 7 A/B-tests 0° and 6°.
- **Esc and retry** on two 6 × 6 mm tact buttons at the far corners, where a
  tapping finger never lands.
- **Per-finger settings**: actuation and RT sensitivity per key.

## Case: a sealed tub for sweaty hands

What the risks really are:

- **Electric shock: none.** USB supplies 5 V; a person cannot feel 5 V. What
  you can feel, and what can reset or damage a board, is **static discharge**
  from your own body into exposed copper.
- **Sweat** is salty water. On bare pads and traces it corrodes copper and
  forms leakage paths. On this board leakage matters twice: the sensor outputs
  are analog, so a damp film shifts the reading and looks like key movement.

How the case answers them:

1. **The PCB is inside, not a layer of the sandwich.** The acrylic walls are
   continuous from base to top cover; the PCB rests on a ledge inside them, so
   its edge is never on the outside.
2. **Top cover over the whole board.** A 3 mm acrylic cover with 14.0 mm holes
   for the switches is the only top surface. Gateron Magnetic Jade come in a
   PCB-mount version, so the switches are held by the PCB and the cover does
   not need a clip-thickness plate (no FR4 plate to order).
3. **Gasket.** A 1 mm EVA or silicone foam strip between the cover and the
   wall ring closes the seam. The only openings left are the switch holes and
   the USB port.
4. **Conformal coating.** Magnetic switches have no electrical contacts, so the
   **whole** PCB can be coated, sensors included, except the USB-C receptacle
   and the programming pads (masked with tape). Sweat that runs down a switch
   lands on lacquer, not copper.
5. **Nylon M3 screws.** No metal path from the outside to anything, and they do
   not rust. Screw holes are non-plated with a 1 mm copper keep-out.
6. **ESD at the only metal you can touch.** The USB-C shell goes to ground
   through 1 MΩ in parallel with 4.7 nF; a USBLC6 array protects the data and
   supply lines.

## Decisions (answered "OK" on 14 Nov 2026)

### MCU: ARTERY AT32F405 (LQFP-48)

| Option | USB | ADC | Firmware | Verdict |
|---|---|---|---|---|
| RP2040 (rev 1) | Full speed: 1 kHz max | 4 external channels | QMK, minipad | No 8 kHz |
| WCH CH32V307 | HS PHY built in | 12-bit, 1 Msps | No HE firmware found | We would write everything |
| **AT32F405** | **HS + FS OTG, both PHYs built in** | **12-bit, 2 Msps, 16 channels** | **libhmk, with 8 kHz** | Chosen |

Sources: [ARTERY AT32F405](https://www.arterychip.com/en/product/AT32F405.jsp),
[libhmk](https://github.com/peppapighs/libhmk) (`hardware/at32f405xx`; README: "8kHz Polling Rate ... (e.g., AT32F405xx)").
With three keys, each sensor has its own ADC pin and the scan reads each key
32 times in 48 µs of the 125 µs budget (*model*).

### Firmware: libhmk fork, LED support added

Rapid trigger, continuous rapid trigger, null bind, dynamic keystroke,
automatic calibration and the hmkconf web configurator already exist in
libhmk; it has no RGB. The fork adds WS2812 output by DMA, started right after
a scan, and a performance profile with all LEDs off. Licence GPL-3.0.

### Sensor: DRV5056A4

*Model*, TI reference geometry ([SLYA093](https://www.ti.com/document-viewer/lit/html/SLYA093/GUID-D139CB2F-A4D9-4F90-891B-C05F7BC0CDF2)),
3 keys × 32 samples:

| Sensor | Span (counts) | Worst slope (counts/mm) | RT floor | Usable travel |
|---|---|---|---|---|
| OH49E-S | 843 | 40 | 0.040 mm | 4.00 mm |
| DRV5056A3 | 2876 | 94 | 0.011 mm | **3.96 mm (saturates)** |
| **DRV5056A4** | 1504 | 71 | **0.015 mm** | 4.00 mm |

The DRV5056 is unipolar and ratiometric: 25 mV/mT at 5 V for the A4, 50 mV/mT
for the A3 ([TI DRV5056](https://www.ti.com/lit/gpn/drv5056)). The A3's 79 mT
range ends just below the 82 mT this magnet gives at bottom-out, and an
N52-grade magnet would lose more than 0.2 mm; the A4 (158 mT) keeps the full
stroke. **Pinouts differ**: OH49E is 1 VCC, 2 GND, 3 OUT
([Ouzhuo datasheet](https://datasheetspdf.com/datasheet/OH49E.html)); DRV5056
is 1 VCC, 2 OUT, 3 GND. The PCB uses the DRV5056 pinout. Noise figures are
assumptions until the bench measures them.

### Switch: Gateron Magnetic Jade, PCB-mount

30 g linear, 3.5 mm travel, widely stocked
([mechanicalkeyboards.com](https://mechanicalkeyboards.com/products/gateron-jade-magnetic-he-30g-linear-plate-mount-switch)).
PCB-mount so no switch plate is needed. Sensor orientation is fixed to this
switch's magnet polarity.

### Look

Translucent blue acrylic walls and cover, art in the palm area under the clear
cover, cyan underglow, white keycaps. LEDs: one under each key and four
underglow (7 in total). Details and easter eggs in [`pcb-art.md`](pcb-art.md).

## Electrical architecture

```
USB-C ─ USBLC6 ─ polyfuse ─ 5 V ───────────► 74AHCT1G125 ─► 7 × SK6812MINI-E
  shell ─ 1 MΩ ∥ 4.7 nF ─ GND
                 └─ LP5907 3.3 V ─► AT32F405 VDD (HS USB, 12 MHz crystal) ◄─┐
                                 └─ ferrite ─► +3V3A: VDDA, 3 × DRV5056A4 ─► 3 ADC pins
                                              ▲
                                 2 tact buttons┘ + BOOT pad underneath
```

- One LDO; a ferrite bead separates the analog rail (sensors and VDDA). The
  datasheet requires VDDA at VDD's potential, which rules out a second
  regulator. The sensors are ratiometric, so supply ripple cancels.
- LED current returns to the USB ground on its own path.
- One RC (1 kΩ / 10 nF) per sensor output; ~10 µs, inside the budget.
- Sensors on the top layer, centred on each switch's magnet axis within 0.1 mm.

## Where the time goes

*Model*, device side, threshold crossing to report sent: 1125 µs worst at
1 kHz (rev 1, UwU), 250 µs worst at 8 kHz (this board). The finger is slower:
releasing 0.1 mm at 150 mm/s takes 0.67 ms, climbing 1 mm back to a fixed reset
point takes 6.7 ms. Rapid trigger saves milliseconds; 8 kHz saves about 0.4 ms
on average.

## Budget

`hardware/he/bom.csv`, totals by `python3 tools/he_model/budget.py hardware/he/bom.csv`
(a test fails if the planned total passes 1,000,000 VND):

| | VND |
|---|---|
| Planned | **894,500** |
| Best case | 627,400 |
| Worst case (LCSC and JLCPCB ship separately, high local prices) | 1,746,500 |

It fits only if the LCSC parts travel in the JLCPCB parcel and the case is cut
locally. Shipping is the largest unknown, so Task 0 checks it before anything
is bought. If it cannot fit, Plan B in [`hall-effect-task0.md`](hall-effect-task0.md)
drops LCSC entirely.
