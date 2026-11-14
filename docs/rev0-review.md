# Rev 0, looked at again

Rev 0 is kept exactly as it was drawn in 2022: the KiCad files in
`hardware/atelier6k/` are the originals, byte for byte, and only moved into
the new folder layout. This page is a look back at what that board is, how it
was made, and how well it holds up, written in November 2026. The defect list
with every detail is in [`design-review.md`](design-review.md); this page is
the story around it.

## How it was made

The whole board went from first commit to Gerbers and firmware in **eleven
days**, 26 May to 5 June 2022, in 34 commits. The history shows the shape of
learning by doing:

| Date | What happened (from the commit messages) |
|---|---|
| 26 May | First commit, footprint libraries added as submodules, schematic drawn, then **redrawn**, and a first trial routing finished |
| 27 May | **Third redraw** "with a few more features", ideas taken from the VCL6K board, essentials added, footprints updated and the board re-routed "with far fewer vias", first Gerbers exported for printing |
| 28 May | Mounting holes added |
| 29 May | Rework; Gerbers exported again, matched to the case |
| 1 Jun | Case drawing finished (DWG/DXF, Blender model) |
| 3 Jun | All LED capacitors removed; notes written |
| 5 Jun | QMK firmware added and compiled; final PCB update |

Three full redraws in two days, then a routing pass that cut the via count,
is how people get good at this. The finished board has **47 footprints, 533
track segments and only 28 vias** on two layers, which is a tidy result for a
first board with a TQFP-44 MCU, a USB-C connector and ten LEDs.

## What it is

- ATmega32U4 at 16 MHz with its own crystal, USB-C, QMK firmware.
- Six hot-swap MX switches and three tactile buttons in a 3 × 3 matrix with a
  diode per switch.
- Six reverse-mount RGB LEDs shining up through the switches and four
  underglow LEDs lighting the case.
- 81 × 74 mm, 2 layers, a stacked acrylic case with four M3 screws.

## Grading it as a first board

| Area | Grade | Why |
|---|---|---|
| USB-C | **A** | Both CC pins have their own 5.1 kΩ pull-down (a mistake many commercial boards made in 2022), both D+/D− pairs joined, 22 Ω series resistors, a proper ESD array. |
| MCU core | **B+** | Correct UCAP, HWB strap, reset pull-up and button, crystal with load caps. Decoupling capacitors are present but placed along the edge, far from the pins they serve. |
| Key matrix | **A** | Diode per key, correct direction for the firmware, every combination of keys registers. For osu! that matters. |
| Hot-swap and layout | **A−** | Kailh sockets and the 3 + 3 stagger are what good keypads use; the layout is still used unchanged by rev 1 and the planned rev 2. |
| Lighting | **C** | The idea is right (per-key and underglow), but the underglow chain is on a pin the firmware drives as PWM, no LED has a decoupling capacitor, and the per-key footprint is named after a non-addressable LED. |
| Power safety | **D** | No fuse, and ten LEDs at full white can draw more than USB allows. Easy to fix, but a real risk as drawn. |
| Routing | **B** | Few vias and clean paths; signal tracks are 0.15 mm, below the project's own 0.2 mm rule. |
| Case | **B+** | A working layered design with real CAD drawings, a Blender model and a sketch of the stack. The parametric case generator built in 2026 reproduces its layers from the PCB file. |
| Firmware | **B−** | It compiled in 2022. It carries an `RGBW` define for RGB parts and a `BOATLOADER` typo, and current QMK no longer builds it as is. |
| Documentation | **B** | A readme, a note on how to compile, sketches and a parts list; the parts list promised a fuse the schematic never got. |

**Overall: a solid B for a self-taught first board.** The hard parts
(USB-C, the MCU, the matrix) are right. What it gets wrong are the parts that
only show up when a board is built and lit at full brightness: power budget,
LED decoupling and the second LED chain. Those are exactly the things rev 1
was designed around.

## What carried forward

- The outline, the four screw holes and the key positions: rev 1 and the
  planned rev 2 keep them, so the cases stay compatible.
- The stacked acrylic case: rebuilt as a generator that reads the PCB.
- The idea of per-key plus underglow lighting, now on one chain with a
  capacitor per LED and a fused, capped supply.

## Files from 2022

- Schematic and PCB: `hardware/atelier6k/` (also browsable on the project site).
- Gerbers as sent for printing: `hardware/gerbers/rev0/`.
- Case drawings and the Blender model: `case/legacy/`.
- Firmware as compiled in 2022: `firmware/legacy-2022/` (with the original
  `.hex`).
