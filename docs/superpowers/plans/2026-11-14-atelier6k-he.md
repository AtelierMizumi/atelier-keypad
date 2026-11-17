# Atelier6K rev 2 (Hall effect) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One three-key Hall-effect osu! keypad with 8 kHz USB, rapid trigger with a measured floor of 0.05 mm or better on every key, in a sealed case, for at most 1,000,000 VND including shipping.

**Architecture:** AT32F405 reads three linear Hall sensors (DRV5056A4) on three ADC pins (no multiplexer) and runs a fork of libhmk over USB High Speed. Circuit, PCB and case are generated from code like rev 1 (`hardware/rev1/`), so tests check the design before anything is ordered. Bench measurements replace the model's assumptions before the PCB is drawn.

**Tech Stack:** Python 3 + pytest (model, circuit, case), KiCad 10 via Docker (`kicad/kicad:10.0.8-full`), libhmk (C, PlatformIO, GPL-3.0), hmkconf web configurator.

**Spec:** `docs/hall-effect-plan.md` (decisions, cost) and `docs/hall-effect-how-it-works.md` (principles).

## Global Constraints

- Three analog keys at x = −19.05, 0, +19.05 mm; middle key 4.76 mm further from the wrist; two tact buttons (Esc, retry) at the far corners.
- The PCB sits inside the case walls (never a layer of the sandwich); nylon M3 screws; NPTH holes with 1 mm copper keep-out.
- Planned total in `hardware/he/bom.csv` ≤ 1,000,000 VND (`tools/he_model/tests/test_budget.py`).
- One sensor per ADC pin; no analog multiplexer.
- Sensors and ADC share one LP5907 3.3 V rail; LEDs on fused 5 V; polyfuse 500 mA hold.
- Scan 8000 Hz, 32× oversampling, scan time ≤ 125 µs including settling (`he_model.check_scan_fits`).
- Rapid-trigger floor ≤ 0.05 mm on every key, measured, not modelled.
- LED frames start only after a scan completes; a "performance" profile turns LEDs off.
- No external code runs unread: pin libhmk and every tool to a commit; build in Docker with `--network none` after fetching.

## Review Focus

1. A key resting for an hour while the board warms up must not press itself (temperature drift) → test in Task 4 replays a slow ramp.
2. A key bottomed out hard (deeper than calibration has seen) must still release with rapid trigger → test in Task 4.
3. Pressing one key must not move its neighbours past the RT floor (magnetic crosstalk) → measured gate in Task 2.
6. Sweat on the case must not reach copper: a drop of salt water at the switch hole and at every seam → check in Task 7.
4. LED animation at full brightness must not move any key reading by more than 1 count → measured gate in Task 7.
5. USB host that only supports Full Speed must still get a working 1 kHz keyboard → check in Task 7.

---

### Task 0: Confirm prices and buy the bench parts

Details and results: `docs/hall-effect-task0.md`.

- [x] **Step 1:** Pinouts and sensitivities from datasheets; choose DRV5056A4 (model test proves A3 saturates).
- [x] **Step 2:** One-unit BOM in VND with low/high/plan columns; budget test (`tools/he_model/tests/test_budget.py`).
- [ ] **Step 3 (you):** JLCPCB and LCSC shipping to Vietnam, Shopee switch price, laser-shop quote → `plan_vnd`.
- [ ] **Step 4:** `cd tools/he_model && uv run --no-project --with pytest pytest -q` → PASS (plan ≤ 1,000,000 VND), or switch to Plan B.
- [ ] **Step 5 (you):** Buy the bench parts listed in the Task 0 doc.

Gate: budget test passes with real quotes.

### Task 1: Bench curve of one key

**Files:**
- Create: `tools/he_bench/capture.py`, `tools/he_bench/fit.py`, `tools/he_bench/tests/test_fit.py`
- Create: `tools/he_bench/data/<sensor>-jade-<n>.csv` (measured)
- Modify: `tools/he_model/he_model.py` (`SENSORS[...]` noise and measured curves)

**Interfaces:**
- Produces: `fit.load(path) -> list[tuple[float, float]]` (travel mm, mean counts); `fit.noise_rms(path) -> float`; `fit.rt_floor_mm(path, oversample: int) -> float`.

- [ ] **Step 1: Write the failing tests** in `test_fit.py`:
  `test_load_sorts_by_travel`, `test_noise_rms_of_constant_column_is_zero`,
  `test_rt_floor_matches_model_for_synthetic_data` (build a CSV from `he_model.REFERENCE.curve()` with added Gaussian noise of σ = 1.5, seed 1; assert `fit.rt_floor_mm(..., 16)` is within 20 % of `REFERENCE.rt_floor_mm()`).
- [ ] **Step 2:** `cd tools/he_bench && uv run --no-project --with pytest pytest -q` → FAIL (module missing).
- [ ] **Step 3:** Implement `fit.py`. CSV columns: `travel_mm,count` with ≥ 200 samples per travel step. `capture.py` reads lines `count\n` from any ADC board you own over USB serial (sketch in `tools/he_bench/firmware/`), one batch per depth set with a digital caliper (0.25 mm steps, 0 → 3.5 mm; the Jade's travel is 3.5 mm).
- [ ] **Step 4:** Tests PASS.
- [ ] **Step 5:** Measure one switch with the TO-92 49E at three sensor heights; scale to the DRV5056 by datasheet sensitivity. Copy measured noise into `he_model.SENSORS`; regenerate the plan's sensor table with `python3 tools/he_model/he_model.py`.
- [ ] **Step 6:** Commit: `feat(he): bench capture and curve fit, measured sensor data`

Gate: chosen sensor's measured RT floor ≤ 0.05 mm at the top of the stroke. If neither passes: shorten `rest_gap_mm` (taller sensor pad, thinner PCB) and re-measure before anything else.

### Task 2: Crosstalk between neighbours

**Files:**
- Create: `tools/he_bench/crosstalk.py`, test in `tools/he_bench/tests/test_fit.py`

- [ ] **Step 1: Failing test** `test_crosstalk_is_neighbour_shift_in_mm`: two synthetic CSVs (victim at rest while aggressor sweeps); assert reported shift equals the injected offset divided by the victim's slope.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement `crosstalk.shift_mm(victim_csv, aggressor_csv) -> float`. **Step 4:** PASS.
- [ ] **Step 5:** Measure with the neighbour at 19.05 mm across and 4.76 mm forward (the arc).
- [ ] **Step 6:** Commit.

Gate: shift ≤ 0.05 mm, or a per-key linear compensation (victim −= k × aggressor travel) that brings it under 0.05 mm in the data.

### Task 3: Circuit as code — done 14 Nov 2026 (19 tests, ERC 0; see docs/rev2-board.md)

**Files:**
- Create: `hardware/he/circuit.py`, `hardware/he/tests/test_circuit.py`, `hardware/he/tests/conftest.py`
- Reuse: `hardware/rev1/sexpr.py`, `gen_sch.py`, `gen_lib.py` patterns (copy, then adapt; keep rev 1 untouched)

**Interfaces:**
- Produces: `circuit.parts() -> list[Part]` with the same `Part` dataclass as rev 1; `circuit.ADC_PINS: dict[str, str]` (key → MCU pin).

- [ ] **Step 1: Failing tests:**
  `test_each_key_has_one_sensor_on_its_own_adc_pin` (three distinct pins, all ADC-capable per the AT32F405 datasheet table copied into the test),
  `test_no_multiplexer`,
  `test_sensors_and_vdda_share_the_analog_rail_only` (net `+3V3A` touches only sensors, their caps, VDDA/VREF and the LDO),
  `test_led_rail_is_fused_and_buffered` (as rev 1),
  `test_usb_has_cc_pulldowns_and_esd`,
  `test_hs_usb_pins_are_the_hs_phy` (D+/D− on the HS OTG pins),
  `test_keys_follow_the_arc` (x = −19.05, 0, 19.05; middle 4.76 mm forward),
  `test_usb_shell_to_ground_through_1M_and_4n7`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Write `circuit.py`. **Step 4:** PASS, then ERC 0 through the generated schematic.
- [ ] **Step 5:** Commit: `feat(he): circuit as code`

### Task 4: Firmware fork

**Files:**
- Fork: `firmware/he/libhmk` (git submodule pinned to a reviewed commit)
- Create: `firmware/he/keyboards/atelier6k_he/` (board config: ADC pins from `circuit.ADC_PINS`, LED pin, buttons)
- Create: `firmware/he/test/test_rapid_trigger.c` (host build with `gcc`, plain asserts)
- Create: `firmware/he/drivers/ws2812_dma.c`

- [ ] **Step 1: Failing host tests** replaying recorded traces through libhmk's key state code:
  `stream_bounce_releases_every_cycle` (2.3 ↔ 3.6 mm trace → 4 presses, 4 releases at 0.2 mm),
  `deeper_than_calibrated_still_releases`,
  `slow_thermal_ramp_never_presses` (rest drifts 0.3 mm over 3600 s),
  `noise_at_floor_never_presses` (σ from Task 1 at sensitivity = measured floor).
- [ ] **Step 2:** `make -C firmware/he/test` → FAIL.
- [ ] **Step 3:** Add the board, calibration curve from Task 1, rest re-learning; fix any test the upstream code fails.
- [ ] **Step 4:** PASS. Build the firmware in Docker with `--network none`.
- [ ] **Step 5:** WS2812 by DMA, triggered from the end-of-scan hook; "performance" profile disables it.
- [ ] **Step 6:** Commit: `feat(he): libhmk board, LED driver, host tests`

### Task 5: PCB — done 14 Nov 2026 (7 layout tests, DRC 0, 0 unconnected)

**Files:**
- Create: `hardware/he/gen_pcb.py`, `hardware/he/route.py` (adapted from rev 1), `hardware/he/tests/test_layout.py`

- [ ] **Step 1: Failing tests:** `test_sensor_on_magnet_axis` (≤ 0.1 mm from each switch centre, top layer), `test_analog_ground_return_does_not_cross_led_current`, `test_crystal_within_5mm_of_mcu`, `test_hs_pair_length_matched_within_0_15mm`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Place and route. **Step 4:** PASS; DRC 0 errors, 0 unconnected.
- [ ] **Step 5:** Commit.

### Task 6: Sealed case with a 6° wedge — done 14 Nov 2026 (14 tests; the wedge became taller rear feet)

**Files:**
- Create: `case/generate_he.py` (reuses `case/generate.py` geometry helpers), `case/tests/test_case_he.py`

- [ ] **Step 1: Failing tests:**
  `test_pcb_is_inside_the_walls` (PCB outline buffered by 1.0 mm lies inside every wall layer's inner opening, and the walls are closed rings),
  `test_top_cover_has_only_switch_holes` (holes = 3 × 14.0 mm squares + USB opening; nothing else),
  `test_gasket_ring_overlaps_the_wall_seam_by_2mm`,
  `test_wedge_angle_is_6_degrees_and_front_edge_under_12mm`,
  `test_layers_are_stock_thicknesses` (2, 3, 5 mm),
  `test_screws_are_nylon_and_holes_clear_copper_by_1mm`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS (all case tests). **Step 5:** Commit.

### Task 7: Bring-up and measurement

- [ ] **Step 1:** Assemble one board; flash; calibrate.
- [ ] **Step 2:** Log all three keys for 60 s idle with LEDs at full brightness animating, then 60 s with LEDs off. Gate: difference ≤ 1 count per key.
- [ ] **Step 3:** Per-key RT floor with the Task 1 rig. Gate: ≤ 0.05 mm on all three; publish the table in `docs/hall-effect-results.md`.
- [ ] **Step 4:** Plug into a Full-Speed-only hub; gate: works at 1 kHz.
- [ ] **Step 5:** One hour of osu! play; note any phantom or missed inputs. A/B the 0° and 6° wedge.
- [ ] **Step 6:** Sweat test: a drop of salt water (1 % NaCl) at each switch hole and seam, wipe after 10 min, open the case; gate: no liquid on the PCB, no change in readings.
- [ ] **Step 7:** Commit results; update the site's rev 2 page with measured numbers.
