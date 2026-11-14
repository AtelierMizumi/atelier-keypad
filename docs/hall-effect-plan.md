# Atelier6K rev 2 (HE): design spec

Status: **designed on paper, nothing built.** Branch `plan/hall-effect`,
November 2026. Prices marked *estimate* in `hardware/he/bom.csv` were not
found in a live listing and must be confirmed before ordering.

How Hall sensing and rapid trigger work is explained separately in
[`hall-effect-how-it-works.md`](hall-effect-how-it-works.md). The task-by-task
build plan is
[`superpowers/plans/2026-11-14-atelier6k-he.md`](superpowers/plans/2026-11-14-atelier6k-he.md).
Numbers below marked *model* come from `tools/he_model/he_model.py`
(13 tests; `python3 tools/he_model/he_model.py` prints them).

## What it has to beat

| | Wooting UwU RGB | SayoDevice O3C | Wooting 80HE | **Atelier6K HE target** |
|---|---|---|---|---|
| Analog keys | 3 (+3 digital) | 3 | full board | **6** (+3 digital) |
| USB polling | 1 kHz | 8 kHz | 8 kHz (Tachyon mode) | **8 kHz** |
| Actuation / RT step | 0.1–4.0 mm, 0.05 mm steps (retailer) | down to 0.05 mm (retailer) | 0.1 mm | **0.05 mm worst case, measured** |
| Price | 69.69 USD at launch, ~50 later | ~27–40 USD | keyboard | **~18 USD parts per unit at 5 units** |
| Open hardware / firmware | no | no | no | **yes** |

Sources: [Wooting UwU launch](https://wooting.io/post/uwu-founders-campaign-sneak-peak),
[UwU product page](https://library.wooting.io/Wooting-UwU-8918becd3be045bc95e9d79c8df26628),
[Wooting 80HE polling](https://wooting.io/post/wooting-80he-the-true-polling-rate),
[O3C at CNX Software](https://www.cnx-software.com/2026/03/09/sayodevice-o3c-3-key-hall-effect-keypad-boasts-8000hz-polling-rate-for-playing-rhythm-games/),
[O3C at Notebookcheck](https://www.notebookcheck.net/SayoDevice-O3C-mini-A-Hall-effect-keypad-for-rhythm-games-like-osu-and-Geometry-Dash.1239375.0.html).

Where we can honestly win: six analog keys for less than a three-key UwU,
8 kHz like the expensive boards, a rapid-trigger floor that is **measured and
published per key** rather than claimed, and everything open.

Where we cannot, and should say so: the O3C is mass-produced and costs about
the same as our parts alone; Wooting's software, calibration and build
quality come from years of work. RTINGS reportedly found no measurable
benefit from 8 kHz on the 80HE ([RTINGS review](https://www.rtings.com/keyboard/reviews/wooting/80he)),
and the model agrees that polling is the small term (see *Where the time goes*).

## Decisions

Each one was a grill question; the recommended answer is taken unless
you overrule it. The questions are repeated at the end so they can be
answered in one go.

### MCU: ARTERY AT32F405 (LQFP-48)

| Option | USB | ADC | Firmware | Verdict |
|---|---|---|---|---|
| RP2040 (rev 1's MCU) | Full speed: 1 kHz max | 4 external channels, ~9 effective bits | QMK, minipad | Cannot do 8 kHz; needs a mux for 6 keys |
| WCH CH32V307 | HS PHY built in | 12-bit, 1 Msps | No HE firmware found | Cheap, but we would write everything |
| **AT32F405** | **HS + FS OTG, both PHYs built in** | **12-bit, 2 Msps, 16 external channels** | **libhmk supports it, with 8 kHz** | Chosen |
| STM32F446 | FS only (HS needs an external ULPI PHY) | 3 ADCs | libhmk | No 8 kHz without extra chips |

Sources: [ARTERY AT32F405](https://www.arterychip.com/en/product/AT32F405.jsp),
[AT32F402/405 launch](https://www.prnewswire.com/apac/news-releases/artery-launches-at32f402f405-mcus-designed-with-hs-usb2-0-otg-301917473.html),
[libhmk](https://github.com/peppapighs/libhmk) (`hardware/at32f405xx`, README: "8kHz Polling Rate ... on some microcontrollers (e.g., AT32F405xx)").

Sixteen ADC inputs means **one sensor per pin, no multiplexer**: no mux
settling time, no switching noise, and a scan of six keys with 16×
oversampling takes 48 µs of the 125 µs budget (*model*). LQFP-48 rather than
QFN-32 so it can be soldered by hand.

### Firmware: libhmk, forked, with LED support added

libhmk already has the features that matter for osu!: rapid trigger,
continuous rapid trigger, null bind (SOCD), dynamic keystroke, automatic
calibration, flash storage, 8 kHz on AT32F405 and a web configurator
(hmkconf). It does **not** drive RGB. The fork adds a WS2812 driver that:

- sends LED data by DMA (timer PWM or SPI), so the CPU never waits on it;
- starts a frame only right after a scan, so LED interrupts never land in the
  middle of ADC sampling;
- turns off entirely in a "performance" profile, the same idea as Wooting's
  Tachyon mode.

QMK was the alternative: it has RGB and VIA, but rapid trigger lives in
forks, and its AT32F405 support is an open pull request
([qmk_firmware#25040](https://github.com/qmk/qmk_firmware/pull/25040)).
Licence: libhmk is GPL-3.0, so the fork is too.

### Sensor: OH49E-S as baseline, DRV5056A3 measured alongside

*Model*, TI reference geometry (2.8 × 3.4 mm magnet, 6.1 → 2.1 mm gap,
[TI SLYA093](https://www.ti.com/document-viewer/lit/html/SLYA093/GUID-D139CB2F-A4D9-4F90-891B-C05F7BC0CDF2)),
1.5 counts RMS noise assumed for the 49E and 1.0 for the DRV5056:

| Sensor | Span (counts) | Worst slope (counts/mm) | RT floor, 16× oversample | Price |
|---|---|---|---|---|
| OH49E-S ([LCSC C85573](https://lcsc.com/product-detail/Linear-Hall-Sensors_Nanjing-Ouzhuo-Tech-OH49E-S_C85573.html)) | 843 | 40 | 0.056 mm | 0.23 USD |
| DRV5056A3 ([TI](https://www.ti.com/lit/gpn/drv5056)) | 1367 | 65 | 0.023 mm | ~0.60 USD (estimate) |

Both beat 0.1 mm everywhere in the stroke on paper. The worst point is the
top of the stroke, where the magnet is far away and the field changes
slowly; that is exactly where an osu! player's rapid trigger operates
during streams. The 49E is bipolar, so half its output range is never used;
the unipolar DRV5056 uses all of it. Phase 1 measures both on the real
switch before the PCB is drawn. The noise figures are assumptions until then.

### Switch: Gateron Magnetic Jade

Widely stocked at 0.46–0.80 USD each
([mechanicalkeyboards.com](https://mechanicalkeyboards.com/products/gateron-jade-magnetic-he-30g-linear-plate-mount-switch),
[Milktooth](https://milktooth.com/products/magnetic-jade)), 30 g linear,
plate mount. Magnet polarity and strength differ between HE switch families,
so the sensor orientation is fixed to this switch; other switches are
supported only after their curve is measured.

### Layout and ergonomics

- **Same key positions as rev 0 and rev 1** (3 + 3 stagger, 19.05 mm pitch),
  so muscle memory carries over and `case/generate.py` keeps working.
- **6° typing angle** built into the case: a wedge base layer, inside the
  0–6° range commonly recommended for fast, light taps. Evidence for any
  particular angle is weak (vendor blogs, forum reports), so the plan
  includes a short A/B test instead of trusting a number.
- **Low profile**: switch plate top at 5.0 mm, base 3 mm, so the wrist sits
  low without a rest; an optional detachable palm rest is a later item.
- **Per-finger tuning, not one setting**: actuation and RT sensitivity per key,
  because index and ring fingers press with different force and travel.

### Look: blue, translucent, slanted

The site's palette carried into the object: translucent blue cast acrylic
frames, cyan underglow that lights the frosted bottom frame, white keycaps,
slanted silkscreen lettering. A boot animation and idle effects run only in
the default profile; the performance profile switches every LED off.
Nothing is copied from any game's artwork or logos; the reference is the
mood.

## Electrical architecture

```
USB-C ─ ESD ─ polyfuse ─ 5 V ──────────────► 74AHCT1G125 ─► 10 × SK6812MINI-E
                 │
                 └─ LP5907 3.3 V (analog) ─► 6 × linear Hall ─► 6 ADC pins ┐
                 └─ 3.3 V (digital)  ─────► AT32F405 (HS USB, 12 MHz xtal) ◄┘
                                              ▲
                                3 tact buttons┘
```

- **Quiet analog rail.** The sensors and the ADC reference share one LDO. The
  49E is ratiometric and the ADC measures against the same rail, so supply
  ripple cancels instead of showing up as key movement.
- **LED current stays away.** 5 V LED return current gets its own path to the
  USB ground; nothing analog shares it.
- **One RC per sensor output** (e.g. 1 kΩ / 10 nF, 16 kHz) as an anti-alias
  filter; its delay (~10 µs) is part of the latency budget.
- **Sensor placement** on the top layer, centred on the switch's magnet axis,
  within 0.1 mm; the footprint carries the switch outline so this is checked
  by DRC.

## Where the time goes

*Model*, device side, threshold crossing to report sent:

| | Worst | Mean |
|---|---|---|
| Full speed, 1 kHz (rev 1, UwU) | 1125 µs | 562 µs |
| High speed, 8 kHz (this board) | 250 µs | 125 µs |

The finger is slower than either: releasing 0.1 mm at 150 mm/s takes
0.67 ms, and climbing back 1.0 mm to a fixed reset point takes 6.7 ms. Rapid
trigger saves several milliseconds per release; 8 kHz saves about 0.4 ms on
average. Both are worth having, in that order of importance.

## Cost

Per unit, at 5 units, parts only, from `hardware/he/bom.csv`:

| Group | USD |
|---|---|
| Electronics (MCU, sensors, power, LEDs, passives) | ~5.4 |
| Six switches | ~2.8 |
| PCB and FR4 plate | ~0.8 |
| Acrylic case, screws | ~6.4 |
| Keycaps | ~2.1 |
| **Total** | **~17.5** |

Not included: shipping, LCSC minimum quantities, a stencil, and any PCBA fee
if the MCU is machine-placed. With DRV5056 sensors add ~2.2 USD.

## Open questions for you

Each has a recommended answer that the plan already follows.

❓ **Q1 — MCU**: AT32F405 (8 kHz, libhmk, a new toolchain) or stay on RP2040 (cheaper module, 1 kHz, shared with rev 1)?
➡️ **Recommendation**: AT32F405. 8 kHz is the point of a performance board, and there is no multiplexer.

❓ **Q2 — Firmware**: libhmk fork with RGB added, or QMK with a rapid-trigger fork?
➡️ **Recommendation**: libhmk. Rapid trigger and calibration already work there; RGB is the smaller job.

❓ **Q3 — Sensor**: commit to the 0.23 USD OH49E, or pay ~2 USD more per board for DRV5056?
➡️ **Recommendation**: buy both, decide after phase 1 measures them on the real switch.

❓ **Q4 — Layout**: keep the rev 0 key positions, or redesign for ergonomics (splayed columns)?
➡️ **Recommendation**: keep them; add the 6° wedge and per-key tuning; revisit only if play-testing finds a problem.

❓ **Q5 — Price target**: under 20 USD in parts at 5 units, or allow more for nicer materials?
➡️ **Recommendation**: under 20 USD; the look comes from colour and light, not expensive materials.
