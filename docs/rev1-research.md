# Atelier6K rev 1 — research and proposal

Goal: a more complete, safer and cheaper keypad that keeps every function of
rev 0 (6 MX hot-swap keys, 3 buttons, per-key and underglow RGB) and adds
1000 Hz polling, adjustable debounce and current VIA support.

Scope of this document: parts, schematic-level changes and firmware. Component
placement and routing are left to the board designer. Researched in November
2026. **Prices marked ~ are from memory and were not confirmed online; check
LCSC or a local shop before ordering.** Nothing here has been built.

Related: [rev 0 design review](design-review.md), [case notes](case.md).

## Summary

| Area | Rev 0 | Proposed rev 1 | Why |
|------|-------|----------------|-----|
| MCU | ATmega32U4, TQFP-44, 16 MHz crystal | RP2040 (module for hand builds, bare chip for factory assembly) | Cheaper, UF2 drag-and-drop flashing, cannot be bricked, room for firmware features, shared with the Hall-effect variant |
| Key wiring | 3 × 3 matrix, 9 diodes | 9 direct pins, no diodes | Fewer parts, no ghosting analysis, lowest scan latency |
| LEDs | 6 per-key on PD0, 4 underglow on PB4 | One chain of 10 on one pin | Fixes the dead underglow chain; one driver |
| LED parts | Per-key part undefined, 4 × WS2812B 5050 | 10 × SK6812MINI-E (same part everywhere) | One LED part number; reverse-mount part is hand-solderable |
| Protection | ESD diodes only | 500 mA polyfuse, ESD diodes, firmware brightness cap | Rev 0 had no over-current protection |
| Decoupling | 3 × 100 nF far from the MCU, none at LEDs | Per the MCU reference design; 100 nF per LED; bulk cap on the LED rail | Rev 0 findings 5–7 |
| Firmware | QMK 2022, does not build today | Current QMK, data-driven `keyboard.json`, VIA v3 with a custom menu | Requested features |
| PCB | 2-layer, 1.0 mm in the file | 2-layer, 1.6 mm, same outline and hole positions | Standard and cheapest; the new case still fits |

## Decisions

Agreed with the owner on 2026-11-14:

| Topic | Decision |
|-------|----------|
| Assembly | Hand-soldered, small quantity |
| MCU | RP2040-Zero module; the ATmega32U4 is dropped |
| Keys | 9 direct pins, no matrix diodes |
| LEDs | 10 × SK6812MINI-E in one chain (6 per-key, 4 underglow) |
| Debounce | Runtime-adjustable through a VIA v3 custom menu (definition loaded by hand); eager on press, deferred on release |
| Layout | Keep the 3 + 3 staggered keys, outline and hole positions |
| Plate | 1.5 mm FR4, so the switches clip in |
| Default keymap | osu! standard on layer 0, plus taiko and mania layers; side buttons Esc, quick retry, layer switch |
| Who does what | Schematic, placement, routing, firmware and case are all done in this repository with scripted tools |
| Order of work | Firmware first, then schematic and PCB |

## 1. MCU choice

Requirements: QMK support, full-speed USB at 1000 Hz, enough flash for VIA and
RGB, available in small quantities, solderable by the intended builder.

| Option | Cost per board | Extra parts it needs | Hand-solderable | Flashing | Notes |
|--------|----------------|----------------------|-----------------|----------|-------|
| **ATmega32U4-AU** (rev 0) | $3.50–6.80 on LCSC depending on quantity | 16 MHz crystal, 2 load caps, UCAP cap | Yes, TQFP-44 0.8 mm | DFU over USB; a blank chip ships with DFU | 32 KB flash is tight with VIA, RGB and a custom menu. 5 V logic drives the LEDs directly |
| **RP2040, bare** | ~$1 chip + ~$0.50 for flash, crystal, LDO | W25Q-series QSPI flash, 12 MHz crystal, 3.3 V LDO, BOOT button | No: QFN-56 at 0.4 mm pitch needs hot air or factory assembly | UF2 mass storage from ROM | Cheapest per board when a factory assembles it |
| **RP2040-Zero module** | $3.99–4.99 from Waveshare; clones are sold for less | None: USB-C, flash, crystal, LDO, BOOT and RESET are on the module | Yes, castellated edges at 2.54 mm | UF2 mass storage | Removes the USB-C connector, crystal and fine-pitch soldering from the board. 20 GPIO on the edge, enough for 9 keys + 1 LED pin |
| **STM32F072CBT6** | ~$2–3 | 3.3 V LDO only (crystal-less USB) | Yes, LQFP-48 0.5 mm | DFU from ROM, BOOT0 button | Smallest bare-chip BOM. No upgrade path for analog sensing beyond its ADC |

Not considered further: CH552 and CH32V203 (very cheap, but not supported by
mainline QMK at the time of writing), nRF52840 (wireless is out of scope).

**Recommendation: design rev 1 around the RP2040.**

- For a board that is hand-soldered in small numbers, use the **RP2040-Zero
  module**. It costs about the same as a bare ATmega32U4 and replaces the MCU,
  crystal, USB-C receptacle, regulator and reset circuit, which are the parts
  rev 0 got wrong or that are hardest to solder.
- For a batch assembled by a PCB factory, use the **bare RP2040** with the
  Raspberry Pi minimal reference design.

Either way the firmware is the same, the bootloader is in ROM so a bad flash
cannot brick the board, and the Hall-effect variant
(`plan/hall-effect` branch) can use the same MCU and ADC.

Consequences to design for:

- **3.3 V logic into 5 V LEDs.** SK6812 inputs want 0.7 × VDD = 3.5 V. Many
  RP2040 boards drive them directly and it usually works, but it is outside
  the datasheet. Add a single-gate level shifter (74AHCT1G125, a few cents) on
  the data line, or leave its footprint with a solder-jumper bypass.
- **GPIOs are not 5 V tolerant.** Nothing on this board feeds 5 V into a GPIO
  once the LED data line is shifted.
- **Settings storage.** The RP2040 has no EEPROM; QMK emulates it in the
  external flash with wear levelling. VIA works on top of it.
- **Module on a USB edge.** With the RP2040-Zero the USB-C port is the
  module's, so the module must sit at the board edge where rev 0 has its
  receptacle. The case's USB bay needs re-checking for the module's height.

## 2. Electrical changes

### Safety

1. **Polyfuse on VBUS**, 500 mA hold, before anything else. With the
   RP2040-Zero, VBUS reaches the board on the module's 5 V pin; fuse the LED
   rail there, since the module itself has no fuse.
2. **Cap LED current in firmware.** Ten LEDs at full white draw about 600 mA.
   `RGBLIGHT_LIMIT_VAL` (or the RGB Matrix equivalent) at about 120 of 255
   keeps the board under 300 mA.
3. **ESD protection** on D+/D− stays (bare-chip build). The module build
   relies on the module's own USB circuit.
4. **CC resistors**: 5.1 kΩ on each CC pin, as in rev 0 (bare-chip build).

### Function

5. **One LED chain**: MCU → level shifter → 6 per-key → 4 underglow. One
   series resistor (220–470 Ω) at the start.
6. **100 nF at every LED**, plus 10–47 µF where the LED rail starts.
7. **Direct key pins**: each of the 9 switches between a GPIO and ground,
   using the internal pull-ups. Remove D11–D33.
8. **Decoupling per the reference design**, each capacitor beside its pin.
9. **Reset and boot**: BOOT button reachable through the case base (bare
   chip), or the module's own buttons.

### Part count

| | Rev 0 | Rev 1, module | Rev 1, bare RP2040 |
|---|---:|---:|---:|
| Diodes | 9 | 0 | 0 |
| Crystal + load caps | 3 | 0 | 3 |
| USB-C receptacle, CC and series resistors, ESD | 6 | 0 | 6 |
| MCU and support | MCU + 6 passives | 1 module | MCU, flash, LDO, ~12 passives |
| LED part numbers | 2 | 1 | 1 |
| Added for safety | — | fuse, 10 × 100 nF, bulk cap, level shifter | same |

## 3. Firmware

| Feature | How |
|---------|-----|
| 1000 Hz | Full-speed USB at a 1 ms interval (`usb.polling_interval: 1`). This is the ceiling for the RP2040, ATmega32U4 and STM32F072; 8000 Hz needs a high-speed USB PHY and is out of scope |
| Current VIA | Data-driven `keyboard.json` plus a VIA v3 definition. Until the definition is accepted into the VIA repository it is loaded through VIA's Design tab |
| Adjustable debounce | Not a stock QMK or VIA feature: `DEBOUNCE` is a compile-time constant. Implement a custom debounce routine (`DEBOUNCE_TYPE = custom`) that reads its time from a variable stored in emulated EEPROM, and expose it as a slider in a VIA v3 custom menu. Community firmware has done the same for other boards |
| Debounce algorithm | Eager on press, deferred on release, per key. A press is reported on the first scan that sees it, and the debounce time only delays the release. This suits osu! |
| Lighting | One 10-LED chain; per-key and underglow as separate ranges; brightness cap |
| Bootloader entry | Bootmagic on one key, plus the BOOT button |

Latency budget with direct pins and eager debounce: one scan (well under
1 ms on an RP2040) plus up to 1 ms waiting for the next USB poll.

## 4. Cost

Rough per-unit parts cost for a hand-built board, excluding switches, keycaps
and shipping. Treat these as an order of magnitude, not a quote.

| Item | Rev 0 | Rev 1 (module) |
|------|------:|---------------:|
| MCU and its support parts | ~$5.50 | ~$4 (less with a clone module) |
| USB-C, ESD, CC parts | ~$0.80 | $0 |
| Diodes | ~$0.20 | $0 |
| LEDs (10) | ~$1 | ~$0.80 |
| Hot-swap sockets (6) | ~$0.90 | ~$0.90 |
| Fuse, level shifter, extra capacitors | $0 | ~$0.40 |
| PCB (5 pcs minimum, per board) | ~$1 | ~$1 |
| Acrylic and screws | local | local |

The saving in parts is modest. The larger gains are fewer hand-soldered
fine-pitch joints, no bricking risk, and a board that passes the review.

## 5. Tuning for osu!

What a keypad can actually improve is the time from finger contact to the USB
report, its consistency from press to press, and how it behaves under fast
alternating taps. In order of effect:

| # | Measure | Effect | Where |
|---|---------|--------|-------|
| 1 | Eager per-key debounce: report a press on the first scan that sees it | Removes the debounce time (5 ms in rev 0) from every press | Firmware |
| 2 | Direct pins instead of a matrix | A scan is one port read; scan rate in the tens of kHz on an RP2040 | Schematic |
| 3 | 1 ms USB polling | Average wait for the next poll is 0.5 ms; this is the remaining floor | Firmware |
| 4 | No tap-hold on the main keys | `LT()`/`MT()` keys wait for the tapping term before reporting. Rev 0 uses `LT()` on the three side buttons only, which is acceptable; never on the six keys | Keymap |
| 5 | Non-blocking LED driver | On AVR the WS2812 bit-bang disables interrupts while it writes. The RP2040 PIO driver does not stall the scan | MCU choice |
| 6 | Light effects that do not slow the scan | Prefer static or key-reactive lighting; measure the scan rate with effects on (`DEBUG_MATRIX_SCAN_RATE`) and drop any effect that lowers it noticeably | Firmware |
| 7 | Release debounce adjustable at runtime | Lets each player and switch type find the lowest value without double taps; a worn switch needs more | Firmware + VIA menu |

Expected result with 1–3: worst case about 1 ms from contact to report,
against roughly 6 ms worst case for rev 0 as configured (5 ms debounce +
1 ms poll). The Hall-effect variant goes further only through rapid trigger,
which removes the need to travel back past a fixed reset point.

**Keymap.** Ship layers for the modes people play, selectable from a side
button and shown by underglow colour:

| Layer | Six keys | Notes |
|-------|----------|-------|
| osu! standard | `Z` `X` on two adjacent keys, the rest free for mods or a second pair | Default |
| osu!taiko | `Z` `X` `C` `V` (or `D` `F` `J` `K`) | Four keys |
| osu!mania 4K / 6K | `D` `F` `J` `K` / `S` `D` `F` `J` `K` `L` | The 3 + 3 staggered layout is less natural for mania than one row |
| Side buttons | `Esc`, quick retry (`` ` ``), layer switch | Editable in VIA |

**Mechanical.**

- The case weighs little, so it must not slide under fast tapping: use wide,
  soft feet, and consider a steel or FR4 base in place of the acrylic one for
  mass.
- With a 3 mm acrylic plate the switches are held only by the hot-swap
  sockets. That is fine for play, but pulling a tight keycap can lift the
  switch. A 1.5 mm FR4 plate (ordered with the PCB) lets the switches clip
  in; the case generator takes the plate thickness as a parameter.
- Switch choice matters more than any of the above for feel: light linear
  switches with short pre-travel are the usual pick, and the hot-swap
  sockets let each player choose.

**Not worth doing.** 8000 Hz polling needs a different MCU with a high-speed
USB PHY and saves under 0.5 ms on average. N-key rollover is irrelevant with
nine keys. Raising the MCU clock or overclocking gains nothing once the scan
is far faster than the USB poll.

## 6. What was not checked

- The latency figures above are derived from the configuration, not measured.
  Measure on the first board (scan rate from QMK's debug output; end-to-end
  with a high-speed camera or a latency tester).

- Unit prices other than the ATmega32U4 and the Waveshare module.
- Whether a specific SK6812MINI-E batch accepts 3.3 V data.
- Current QMK support status of each alternative MCU; confirm against the
  QMK compatible-microcontrollers page before committing.
- RP2040-Zero pin assignment and module height against the case.

## Sources

- QMK: [compatible microcontrollers](https://docs.qmk.fm/compatible_microcontrollers), [RP2040 platform notes](https://docs.qmk.fm/platformdev_rp2040)
- VIA: [v3 changes](https://caniusevia.com/docs/v3_changes), [custom UI](https://caniusevia.com/docs/custom_ui)
- Raspberry Pi: [Hardware design with RP2040](https://pip-assets.raspberrypi.com/categories/814-rp2040/documents/RP-008279-DS-2-hardware-design-with-rp2040.pdf)
- LCSC: [ATmega32U4-AU](https://www.lcsc.com/product-detail/C44854.html)
- Waveshare: [RP2040-Zero](https://www.waveshare.com/product/rp2040-zero.htm)
- Example of a keyboard-oriented RP2040 board: [RP Micro](https://github.com/siderakb/rp-micro)
