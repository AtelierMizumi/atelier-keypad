# Rev 2.0: assembly, bring-up and acceptance

The first batch of five boards is the prototype (spec decision D4). This
procedure decides whether rev 2.0 is accepted, or what rev 2.1 must change.
Fill in the tables with real numbers and commit them. They are the bench data
the field model never had.

Tools: a multimeter, a USB power meter (or a bench supply with a current
display), hot air or a fine iron, flux, a caliper, and a magnifier for the
LQFP.

## 1. Assemble in stages

Solder, then measure, then add the next stage. A short found on stage 1 costs
one LDO, not the MCU.

| Stage | Parts | Check before going on |
|---|---|---|
| 1. Power | J1, F1, U3, R1/R2 (CC), U2 (LP5907), its caps, FB1, C30/R3 | Plug into the USB power meter: **under 5 mA**. TP +3V3 reads **3.30 V ± 3 %**. The analog rail (C1 pad) is the same within 20 mV |
| 2. MCU | U1, Y1, C28/C29 (33 pF), R4 (12 k 1 %), BOOT0 network, every 100 nF | Idle current **under 60 mA** with no firmware. No part warm to the touch |
| 3. Sensors | U10–U12 on the bottom (dot = pin 1, see silkscreen), C1–C3, R10–R12, C4–C6 (47 nF) | Analog rail still 3.30 V |
| 4. LEDs and buttons | U4, R6, C34, D1–D7, C41–C47, SW1–SW3 | none until firmware |

Coat the board (acrylic conformal coating) only after the acceptance below
passes. Mask the USB-C receptacle and the switch peg holes.

## 2. Flash

1. Hold **SW3 (BOOT)**, plug in, then release.
2. The PC shows a DFU device with the Artery bootloader's VID/PID. If it
   doesn't: check Y1 and its caps, and R4.
3. Flash `firmware.bin` from the Release package (see
   `firmware/he/README.md`), then replug.
4. Expected: a USB **High Speed** HID device, 0x1209:0x0001. On Linux,
   `lsusb -t` shows `480M` for it. 12M means the board fell back to Full Speed,
   so check R4 (12 k 1 %) and the USB pair.

## 3. Raw readings against the model

Open hmkconf, and read each key's raw ADC value at rest and pressed fully
down. The model band comes from Gateron's 120 ± 15 G and 800 ± 80 G through a
1.2 mm board (`docs/research/he-switch-field.md`). It adds ±5 % for the
DRV5056's own sensitivity tolerance.

| Key | Rest, model band | Rest, measured | Bottom, model band | Bottom, measured | Bottom > rest? |
|---|---|---|---|---|---|
| K1 | 700–775 | | 1,900–2,350 | | |
| K2 | 700–775 | | 1,900–2,350 | | |
| K3 | 700–775 | | 1,900–2,350 | | |

How to read the result:

- **All inside the bands:** the model holds. Go to step 4.
- **Bottom lower than rest:** the polarity is reversed. Set `invert_adc: true`
  in `keyboard.json`. The switch magnet then faces south-down, or the sensor
  is rotated.
- **Bottom near 3,700 (rail):** the sensor saturates. Rev 2.1 needs a thicker
  board, or the A3 → A4 reasoning is wrong.
- **Rest outside its band, bottom inside:** the sensor's zero-field offset is
  off. Harmless, because calibration absorbs it.
- **Span (bottom − rest) under 1,000 counts:** the magnet is weaker than
  Gateron states. The RT floor rises in proportion; note it.

Noise: with a key at rest, note the raw value's peak-to-peak over 10 seconds
in hmkconf. The model expects about **±2 counts**.

| Key | Peak-to-peak at rest |
|---|---|
| K1 | |
| K2 | |
| K3 | |

## 4. Rapid trigger

Set actuation at 1.2 mm and rapid trigger at 0.10 mm on all keys.

| Test | Pass when | K1 | K2 | K3 |
|---|---|---|---|---|
| Tap 20 times quickly in a key tester | 20 presses, 20 releases | | | |
| Rest a finger on a pressed key for 10 s | no extra presses | | | |
| Repeat at 0.05 mm | 20/20, no chatter | | | |

## 5. Case and sealing

| Check | Pass when |
|---|---|
| Board in the case, screws tight | the board does not rattle; nothing bows visibly |
| Look along the cover around each switch | the gasket closes the seam, with no gap visible |
| Feet | 6° front-to-back on a phone inclinometer |

## Accepting

Every table filled in and passing:

1. Commit this file with the numbers.
2. Close issue G4.
3. Tag `rev2.0`. CI attaches the package to the Release.
4. Open the PR `revamp` → `main`.

Anything failing becomes an issue labelled `rev2`, and the fix goes into rev 2.1.
