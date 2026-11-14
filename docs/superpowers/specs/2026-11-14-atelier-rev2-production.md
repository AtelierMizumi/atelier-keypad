# Atelier rev 2.0 (Hall effect): from routed design to an orderable product

Decided in the grilling of 14 Nov 2026. Builds on the routed rev 2 in
`docs/rev2-board.md` and the field study in `docs/research/he-switch-field.md`.

## Goal

Anyone who clones the repo can order, assemble, flash and accept one working
Atelier rev 2.0 for under 1,000,000 VND, from files that CI generated and
checked. The web preview shows exactly that board.

"Production" here means reproducible single units, not a sales run. Hand
assembly with a stencil; the BOM carries LCSC numbers so JLCPCB assembly stays
possible later.

## Decisions

| # | Decision | Why |
|---|---|---|
| D1 | Keep the routed rev 2 as the base; change only what a check forces | ERC/DRC and layout tests already pass |
| D2 | Hall sensors move to the **bottom** side, under each switch, on a **1.2 mm** PCB, still **DRV5056A4** | Gateron's flux figures are measured through a 1.2 mm PCB; on top the A4 saturates over 2.2 mm of the stroke |
| D3 | Sensor filter **1 kΩ / 47 nF** (fc ≈ 3.4 kHz) | RT floor ≈ 25 µm instead of 45 µm, for ≈ 47 µs of delay |
| D4 | No bench: the first JLCPCB batch (5 boards) is the prototype, marked `rev 2.0` | Acceptance compares measured curves with the model; a miss becomes rev 2.1 |
| D5 | MCU stays AT32F405 (8 kHz) behind a gate: confirm AT32F405CCT7 stock before ordering, else Plan B (RP2040, 1 kHz) | No price or stock found on 14 Nov |
| D6 | Firmware: libhmk as a git submodule pinned to one commit; Atelier's `keyboard.json` in `firmware/he/` (GPL-3.0); built with PlatformIO | Reproducible, no fork to maintain |
| D7 | GitHub Actions run every test, ERC/DRC, and build the production package (Gerber, drill, JLCPCB BOM + CPL, case DXF, firmware `.bin`) as a CI artifact and a Release asset on tag `rev2.0`; no archives committed | Anyone gets the checked package |
| D8 | Pages keeps deploying from `revamp`; a PR `revamp` → `main` opens after acceptance, merged by the owner | Preview stays current; main changes only by the owner |
| D9 | Work is tracked as GitHub Issues with blocking links | Visible remotely; human steps get ticked off there |

## Requirements

### Field model (`tools/he_model`)
- Fit the cylinder model to a published rest/bottom-out flux pair.
- Express sensor placement as side + PCB thickness + package depth.
- Reproduce the table in `docs/research/he-switch-field.md`.

### Board (`hardware/he`)
- U10–U12 on B.Cu at the key centres. Their 100 nF and RC parts stay on the
  bottom within the switch peg span.
- Filter caps 47 nF.
- `THICKNESS = 1.2`, written into the board stackup and the fab notes.
- Silkscreen reads `rev 2.0`.
- ERC 0, DRC 0 errors, 0 unconnected, parity 0. Every existing layout test
  still passes, with "sensors on top" replaced by "sensors on bottom".

### Case (`case/generate_he.py`)
- Follows `circuit.THICKNESS`.
- The board is carried on a 1.0 mm EVA strip compressed to 0.8 mm. The clamp
  gap closes to within 0.2 mm of the gasket thickness.

### Production package (`scripts/fab.sh`)
- Gerbers for F/B Cu, Mask, Silk, Paste, Edge.Cuts.
- Excellon drill (PTH and NPTH).
- `bom-jlcpcb.csv` with columns `Comment,Designator,Footprint,LCSC`, every
  placed part carrying an LCSC number.
- `cpl-jlcpcb.csv` with columns `Designator,Mid X,Mid Y,Layer,Rotation`, the
  same designators as the BOM.
- Case DXF and `firmware.bin`.
- A `README.txt` stating 2 layers, 1.2 mm, HASL lead-free, both sides SMT.

### Firmware (`firmware/he`)
- `keyboard.json` uses the 12 MHz HSE, `at32f405xx`, USB HS and 3 keys.
- ADC pins match `circuit.SENSOR_ADC`.
- Initial rest value and bottom-out threshold come from the model, with
  `invert_adc` set from the sensor's polarity (DRV5056 output rises with
  field).
- Raw ADC readout is available for acceptance.

### Acceptance (`docs/rev2-bringup.md`)
- Power-on checks: 3V3 and 3V3A, idle current.
- DFU flash over USB HS with BOOT.
- Per key, compare raw rest/bottom counts with the model's band.
- RT works at 0.1 mm.
- Sealing: no gap visible around the switches.

### Site
- Rev 2 section shows rev 2.0 (bottom sensors, 1.2 mm) and the regenerated
  renders and GLB.
- It links the latest Release package.

## Out of scope
- Sales run.
- JLCPCB assembly order.
- RGB effects in firmware (libhmk has none).
- A rev 2.1. Plan B (RP2040) gets designed only if gate D5 fails.

## Human steps
- Check AT32F405CCT7 stock and price on LCSC (gate D5).
- Get the JLCPCB quote at 1.2 mm.
- Buy switches.
- Order, assemble and run the acceptance.
