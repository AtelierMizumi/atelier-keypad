# Atelier rev 2.0 Production Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the routed rev 2 into rev 2.0: sensors on the bottom of a 1.2 mm board, CI-built production package, libhmk firmware, acceptance procedure, updated preview.

**Architecture:** Everything stays generated from `hardware/he/circuit.py`. The field model in `tools/he_model` argues the sensor choice. `scripts/fab.sh` turns the checked board into the package. CI runs the same scripts as a laptop.

**Tech Stack:** Python 3.12 + pytest (uv), KiCad 10.0.8 in Docker (`kicad/kicad:10.0.8-full`, `--network none` locally), shapely/ezdxf, libhmk + PlatformIO, GitHub Actions, three.js site.

**Spec:** `docs/superpowers/specs/2026-11-14-atelier-rev2-production.md` (field data: `docs/research/he-switch-field.md`)

## Global Constraints

- Branch `plan/hall-effect`. Never push or merge to `main`. Commit only when the owner asks.
- Never commit `*.zip, *.pdf, *.docx, *.xlsx, *.pptx` or secrets. The package is a CI artifact or Release asset only.
- Test first: write the test, run it red for the right reason, then the code. Never loosen an assertion to pass.
- A test whose subject changed by decision D2 (top → bottom sensors) is rewritten to the new decision, and the commit message says so.
- Pin versions: the KiCad image tag, the libhmk commit SHA, the PlatformIO platform version, and the action versions (`@v4`-style tags already in `pages.yml`).
- Board: 2 layers, `THICKNESS = 1.2`, DRV5056A4 on B.Cu, filter 1 kΩ / 47 nF, silkscreen `rev 2.0`.
- Budget test (`tools/he_model/tests/test_budget.py`) must stay green: total ≤ 1,000,000 VND.

## Review Focus

1. **Bottom sensor vs reverse-mount LED.** Each key's SK6812MINI-E sits at ky + 5.08 on the bottom. Its body must not overlap the sensor or its RC parts. Test: `test_bottom_parts_under_a_key_do_not_collide` (Task 2).
2. **Sensor pin 1 after flipping.** On B.Cu the SOT-23 is mirrored. Net-to-pad must still be 1 VCC / 2 OUT / 3 GND. Test: `test_sensor_pads_carry_vcc_out_gnd` (Task 2).
3. **CPL rotation and coordinates for bottom parts.** JLCPCB expects bottom-side rotations as KiCad exports them, with Y not flipped. Test: `test_cpl_bottom_parts_are_on_bottom_layer_with_board_coordinates` (Task 4).
4. **Firmware ADC pins drifting from the board.** A pin swapped in `circuit.py` must fail the firmware test, not the user. Test: `test_keyboard_json_adc_pins_match_circuit` (Task 5).
5. **Thinner board in the case.** At 1.2 mm the clamp could leave the board loose. Test: `test_board_is_clamped_between_gaskets` (Task 3).

---

### Task 1: Field model fitted to published flux

**Files:**
- Modify: `tools/he_model/he_model.py`
- Test: `tools/he_model/tests/test_he_model.py`

**Interfaces:**
- Produces:
  - `fit_to_flux(rest_mT: float, bottom_mT: float, travel_mm: float, radius_mm: float, length_mm: float) -> tuple[Magnet, float]`. Returns the magnet with fitted `br_mT` and the bottom-out gap at the reference plane.
  - `@dataclass(frozen=True) Placement(side: str, pcb_mm: float, package_depth_mm: float = 0.5)` with `offset_from(self, ref: "Placement") -> float`, in mm. Positive means further from the magnet.
  - `rc_noise_mT(r_ohm: float, c_farad: float, density_nT: float = 215.0) -> float`. RMS over the RC noise bandwidth, π/2 · fc.
  - `JADE = (12.0, 80.0, 3.5)`, `REF_PLACEMENT = Placement("bottom", 1.2)`.
  - `REFERENCE` becomes the fitted Jade + DRV5056A4 + bottom placement at 1.2 mm.

- [ ] **Step 1: Write failing tests**
  - `test_fit_reproduces_the_published_rest_and_bottom_flux`: the fitted design gives 12.0 ± 0.1 mT at rest and 80.0 ± 0.1 mT at bottom.
  - `test_thicker_pcb_drops_bottom_flux_like_durock`: moving from a 1.2 to a 1.6 mm bottom placement drops the bottom flux by 20–28 %. Durock measured 25 %.
  - `test_top_placement_saturates_drv5056a4`: `usable_travel_mm() < 2.0` at `Placement("top", 1.2)`, for both magnet shapes (1.5, 3.5) and (2.0, 3.0).
  - `test_bottom_1p2_uses_half_the_a4_range`: peak / 158 mT is between 0.45 and 0.60.
  - `test_47nF_filter_gives_rt_floor_under_30_um`: with sensor noise `rc_noise_mT(1e3, 47e-9)` and 1.5 counts ADC noise at 32× oversampling, `rt_floor_mm` < 0.030.
  - Also update `test_drv5056a3_saturates_before_bottom_out_but_a4_does_not` to the fitted reference: it must still hold at 88 mT (the +10 % magnet).
- [ ] **Step 2: Run red.** `cd tools/he_model && uv run --no-project --with pytest --with scipy pytest -q`. Expect `AttributeError: fit_to_flux`.
- [ ] **Step 3: Implement.** Fit the gap with a bracketed root find on the rest/bottom ratio. `scipy.optimize.brentq` is fine; add `scipy` to the uv command in the docstring. Then scale `br_mT` to match the bottom flux.
- [ ] **Step 4: Run green.** Same command, all pass. `python3 he_model.py` prints the table in `docs/research/he-switch-field.md`, to within the rounding shown there.
- [ ] **Step 5: Commit** `feat(he_model): fit the field model to Gateron Jade flux and model sensor placement`.

### Task 2: Board rev 2.0: bottom sensors, 1.2 mm, 47 nF

**Files:**
- Modify: `hardware/he/circuit.py`, `hardware/he/gen_pcb.py` (silkscreen `rev 2.0`, stackup thickness)
- Modify: `hardware/he/bom.csv` (PCB row 1.2 mm)
- Test: `hardware/he/tests/test_circuit.py`, `hardware/he/tests/test_layout.py`
- Regenerate: `atelier-he.kicad_sch`, `atelier-he.kicad_pcb`, `docs/reports/he-*.json`, renders, GLB (via `scripts/he.sh`)

**Interfaces:**
- Consumes: Task 1's conclusion only (no import).
- Produces: `circuit.THICKNESS == 1.2`. U10–U12 have `side == "B"` at `KEYS[k]`. C4–C6 are `"47nF"`.

- [ ] **Step 1: Write failing tests**
  - In `test_circuit.py`:
    - `test_sensors_are_on_the_bottom_at_each_key`
    - `test_sensor_filter_is_1k_47nF`
    - `test_board_is_1p2_mm`
  - In `test_layout.py`, replace `test_sensors_are_on_top_under_each_magnet` with `test_sensors_are_on_bottom_under_each_magnet`. This is decision D2; say so in the commit.
  - Add `test_sensor_pads_carry_vcc_out_gnd`: pad 1 is +3V3A, pad 2 is SENSE_Kn, pad 3 is GND, on B.Cu.
  - Add `test_bottom_parts_under_a_key_do_not_collide`: no B.Cu courtyard overlaps within 9.5 mm of a key centre.
  - Add `test_silkscreen_says_rev_2_0`.
- [ ] **Step 2: Run red.** `cd hardware/he && uv run --no-project --with pytest pytest -q tests/test_circuit.py`. Expect the three new tests to fail on side, value and thickness.
- [ ] **Step 3: Implement.**
  - Move the sensors to B.
  - Re-place their 100 nF and RC parts on B inside the peg span, clear of the LED body at ky + 5.08.
  - Change the filter value and `THICKNESS`.
  - Change the silk text in `gen_pcb.py`.
- [ ] **Step 4: Regenerate and check.** Run `scripts/he.sh`. Expect ERC 0, DRC 0 errors, 0 unconnected, parity 0, and all layout tests green. If routing fails, adjust placement, not the tests.
- [ ] **Step 5: Commit** `feat(he): rev 2.0 — sensors on the bottom of a 1.2 mm board, 47 nF filter`.

### Task 3: Case follows the 1.2 mm board

**Files:**
- Modify: `case/generate_he.py`
- Test: `case/tests/test_case_he.py`

**Interfaces:**
- Consumes: `circuit.THICKNESS`.
- Produces: an `UNDER_GASKET = 1.0` EVA strip (compressed to 0.8) carrying the board; regenerated `case/dxf-he/` and `site/assets/case-he.json`.

- [ ] **Step 1: Write failing test** `test_board_is_clamped_between_gaskets`. The gap from the lower ledge top to the spacer ledge bottom equals `THICKNESS + 0.8`, ± 0.2 mm. Update `test_stack_heights` to read `circuit.THICKNESS` instead of a literal 1.6.
- [ ] **Step 2: Run red.** `cd case && uv run --quiet --no-project --with pytest --with shapely --with ezdxf pytest -q tests`.
- [ ] **Step 3: Implement** by deriving the stack z-values from `circuit.THICKNESS` and `UNDER_GASKET`.
- [ ] **Step 4: Run green.** 50+ tests pass. Then `uv run case/generate_he.py`.
- [ ] **Step 5: Commit** `fix(case): stack follows the 1.2 mm board with an EVA strip under its edge`.

### Task 4: Production package

**Files:**
- Modify: `hardware/he/circuit.py` (an `lcsc` field on every placed part, from the LCSC catalogue; AT32F405CCT7 left as `""` if not listed)
- Create: `scripts/fab.sh`, `hardware/he/fab.py` (BOM/CPL writers)
- Test: `hardware/he/tests/test_fab.py`

**Interfaces:**
- Consumes: the `.kicad_pcb` from Task 2.
- Produces: `build/fab/rev2.0/` containing:
  - `gerbers/*.g*` and drill files;
  - `bom-jlcpcb.csv` and `cpl-jlcpcb.csv`;
  - `case-dxf/*.dxf`;
  - `README.txt`.
  - `fab.py` exposes `write_bom(parts, path)` and `write_cpl(pcb_pos_csv, path)`.
  - `build/` is git-ignored.

- [ ] **Step 1: Write failing tests**
  - `test_bom_has_jlcpcb_columns_and_every_part_has_lcsc`. `AT32F405CCT7` is allowed as `""` only while `docs/hall-effect-task0.md` marks gate D5 open.
  - `test_cpl_designators_match_bom`
  - `test_cpl_bottom_parts_are_on_bottom_layer_with_board_coordinates`
  - `test_gerber_set_is_complete`: F/B Cu, F/B Mask, F/B Silk, F/B Paste, Edge.Cuts, PTH and NPTH drill.
  - `test_fab_readme_states_1p2_mm_two_layers`
- [ ] **Step 2: Run red.** `cd hardware/he && uv run --no-project --with pytest pytest -q tests/test_fab.py`.
- [ ] **Step 3: Implement.**
  - `fab.sh` runs `kicad-cli pcb export gerbers|drill|pos` in the pinned image.
  - `fab.py` writes the BOM from `circuit.parts()` and reformats the pos file.
  - Copy the DXF files and write `README.txt`.
- [ ] **Step 4: Run green.** `scripts/fab.sh && pytest tests/test_fab.py`.
- [ ] **Step 5: Commit** `feat(he): production package — Gerber, drill, JLCPCB BOM and CPL, case DXF`.

### Task 5: Firmware on libhmk

**Files:**
- Create:
  - `firmware/he/libhmk`: git submodule pinned to a SHA and recorded in `firmware/he/README.md`.
  - `firmware/he/keyboards/atelier-he/keyboard.json`
  - `firmware/he/build.sh`
  - `firmware/he/LICENSE` (GPL-3.0)
- Test: `firmware/he/tests/test_keyboard_json.py`

**Interfaces:**
- Consumes:
  - `circuit.SENSOR_ADC`, `circuit.KEY_ORDER`, `circuit.BUTTON_PINS`, `circuit.LED_PIN`;
  - `he_model.REFERENCE` for the calibration numbers.
- Produces: `build/fw/atelier-he.bin`.

- [ ] **Step 1: Write failing tests**
  - `test_keyboard_json_adc_pins_match_circuit`
  - `test_keyboard_json_is_at32f405_hs_12mhz_three_keys`
  - `test_initial_calibration_matches_model`: the rest value is within ±10 % of the model's rest counts. The bottom-out threshold is ≤ 70 % of the model's span, so the weakest switch (−10 % flux) still bottoms out.
  - `test_invert_adc_matches_sensor_polarity`: compare against how libhmk's `invert_adc` is defined in the pinned source. Read it, don't assume.
- [ ] **Step 2: Run red.** `cd firmware/he && uv run --no-project --with pytest pytest -q`.
- [ ] **Step 3: Implement.**
  - Add the submodule.
  - Write `keyboard.json` following the pinned libhmk schema; `keyboards/he60-v2/keyboard.json` is the template.
  - Write `build.sh`, which calls `pio run` with the pinned platform.
- [ ] **Step 4: Run green and build.** `firmware/he/build.sh` produces the `.bin`. If PlatformIO needs the network, it runs in CI only (Task 6), and that is stated in `firmware/he/README.md`.
- [ ] **Step 5: Commit** `feat(firmware): libhmk config for Atelier rev 2.0`.

### Task 6: CI and Release

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `.gitignore` (`build/`)

**Interfaces:**
- Consumes: the commands from Tasks 1–5.
- Produces:
  - Job `test`: all pytest suites through uv.
  - Job `kicad`: `scripts/he.sh check` plus `scripts/fab.sh` in `kicad/kicad:10.0.8-full`.
  - Job `firmware`: `firmware/he/build.sh`.
  - The `rev2.0-package` artifact.
  - On tag `rev2.0`, a Release with the package attached.

- [ ] **Step 1: Write the workflow.** It runs on push to `plan/hall-effect` and `revamp`, and on tags `rev*`. Permissions are `contents: write` only for the release job.
- [ ] **Step 2: Verify locally** with `act` if installed. Otherwise run each job's commands in sequence, then let the first push be the check. The owner pushes.
- [ ] **Step 3: Commit** `ci: tests, KiCad checks, production package and firmware build`.

### Task 7: Acceptance procedure and preview

**Files:**
- Create: `docs/rev2-bringup.md`
- Modify:
  - `docs/rev2-board.md`, `docs/hall-effect-plan.md`, `README.md`
  - Site: `site/index.html` rev 2 section, with `site/assets/*` regenerated by `scripts/he.sh`
- Test: `scripts/check-assets.sh`

- [ ] **Step 1: Write `docs/rev2-bringup.md`.**
  - Power-on, before the MCU is fitted, then after: 3V3 and 3V3A within ±3 %, idle current under 60 mA.
  - DFU flash.
  - Raw counts per key against the model band from Task 1, with a table to fill in.
  - RT at 0.1 mm and at 0.05 mm.
  - Sealing check.
- [ ] **Step 2: Update the site.**
  - The rev 2 text says rev 2.0, sensors on the bottom, 1.2 mm.
  - Add a link to the latest Release.
  - Run `scripts/check-assets.sh`, then check desktop and mobile in Playwright with no console errors.
- [ ] **Step 3: Merge `plan/hall-effect` into `revamp`.** Pages deploys after the owner says push.
- [ ] **Step 4: Commit** `docs(he): rev 2.0 bring-up and acceptance; site shows rev 2.0`.

### Human gates (GitHub Issues assigned to the owner)

- **G1, before Task 4 is closed:**
  - AT32F405CCT7 on LCSC: stock and price. Fill `bom.csv` and the `lcsc` field.
  - If there is no stock, stop and open the Plan B spec.
- **G2, after Task 6:** the JLCPCB quote at 1.2 mm, with shipping to Vietnam. Budget test green.
- **G3, ordering:** 5 PCBs plus stencil, LCSC parts, 4 Gateron Magnetic Jade, the case at a laser shop.
- **G4, acceptance:** fill `docs/rev2-bringup.md`, then tag `rev2.0`. Then open the PR `revamp` → `main`.
