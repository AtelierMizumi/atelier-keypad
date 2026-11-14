# Atelier6K rev 2 (Hall effect) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A six-key Hall-effect osu! keypad with 8 kHz USB, rapid trigger with a measured floor of 0.05 mm or better on every key, for under 20 USD in parts per unit at 5 units.

**Architecture:** AT32F405 reads six linear Hall sensors on six ADC pins (no multiplexer) and runs a fork of libhmk over USB High Speed. Circuit, PCB and case are generated from code like rev 1 (`hardware/rev1/`), so tests check the design before anything is ordered. Bench measurements replace the model's assumptions before the PCB is drawn.

**Tech Stack:** Python 3 + pytest (model, circuit, case), KiCad 10 via Docker (`kicad/kicad:10.0.8-full`), libhmk (C, PlatformIO, GPL-3.0), hmkconf web configurator.

**Spec:** `docs/hall-effect-plan.md` (decisions, cost) and `docs/hall-effect-how-it-works.md` (principles).

## Global Constraints

- Key positions, outline (81.28 × 73.66 mm) and M3 holes identical to rev 0/rev 1 (`hardware/rev1/circuit.py: OUTLINE, HOLES`).
- One sensor per ADC pin; no analog multiplexer.
- Sensors and ADC share one LP5907 3.3 V rail; LEDs on fused 5 V; polyfuse 500 mA hold.
- Scan 8000 Hz, 16× oversampling, scan time ≤ 125 µs including settling (`he_model.check_scan_fits`).
- Rapid-trigger floor ≤ 0.05 mm on every key, measured, not modelled.
- LED frames start only after a scan completes; a "performance" profile turns LEDs off.
- Parts per unit ≤ 20 USD at 5 units (`hardware/he/bom.csv`).
- No external code runs unread: pin libhmk and every tool to a commit; build in Docker with `--network none` after fetching.

## Review Focus

1. A key resting for an hour while the board warms up must not press itself (temperature drift) → test in Task 4 replays a slow ramp.
2. A key bottomed out hard (deeper than calibration has seen) must still release with rapid trigger → test in Task 4.
3. Pressing one key must not move its neighbours past the RT floor (magnetic crosstalk) → measured gate in Task 2.
4. LED animation at full brightness must not move any key reading by more than 1 count → measured gate in Task 7.
5. USB host that only supports Full Speed must still get a working 1 kHz keyboard → check in Task 7.

---

### Task 0: Confirm prices and order bench parts

**Files:**
- Modify: `hardware/he/bom.csv`

- [ ] **Step 1:** For every row marked `estimate`, find a live listing; set `unit_usd_low_qty`, `source` and `confidence=found`, or replace the part.
- [ ] **Step 2:** Check pinouts of OH49E-S and DRV5056A3 (SOT-23). Record in the `note` column whether one footprint fits both.
- [ ] **Step 3:** Order for the bench: AT32F405 dev board (or the bare chip on an adapter), 10 × OH49E-S, 10 × DRV5056A3, 10 × Gateron Magnetic Jade, scrap 1.6 mm FR4 plate with three cut-outs at 19.05 mm.
- [ ] **Step 4:** Commit: `git commit -m "docs(he): confirm part prices"`

Gate: sum of `unit_usd_low_qty × qty` ≤ 20.

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
- [ ] **Step 3:** Implement `fit.py`. CSV columns: `travel_mm,count` with ≥ 200 samples per travel step. `capture.py` reads lines `count\n` from the dev board's serial port at each travel step set by a micrometer stage (0.1 mm steps, 0 → 4.0 mm).
- [ ] **Step 4:** Tests PASS.
- [ ] **Step 5:** Measure 3 switches × 2 sensors. Copy measured noise into `he_model.SENSORS`; regenerate the plan's sensor table with `python3 tools/he_model/he_model.py`.
- [ ] **Step 6:** Commit: `feat(he): bench capture and curve fit, measured sensor data`

Gate: chosen sensor's measured RT floor ≤ 0.05 mm at the top of the stroke. If neither passes: shorten `rest_gap_mm` (taller sensor pad, thinner PCB) and re-measure before anything else.

### Task 2: Crosstalk between neighbours

**Files:**
- Create: `tools/he_bench/crosstalk.py`, test in `tools/he_bench/tests/test_fit.py`

- [ ] **Step 1: Failing test** `test_crosstalk_is_neighbour_shift_in_mm`: two synthetic CSVs (victim at rest while aggressor sweeps); assert reported shift equals the injected offset divided by the victim's slope.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement `crosstalk.shift_mm(victim_csv, aggressor_csv) -> float`. **Step 4:** PASS.
- [ ] **Step 5:** Measure with keys at 19.05 mm and at 9.525 mm diagonal (the stagger).
- [ ] **Step 6:** Commit.

Gate: shift ≤ 0.05 mm, or a per-key linear compensation (victim −= k × aggressor travel) that brings it under 0.05 mm in the data.

### Task 3: Circuit as code

**Files:**
- Create: `hardware/he/circuit.py`, `hardware/he/tests/test_circuit.py`, `hardware/he/tests/conftest.py`
- Reuse: `hardware/rev1/sexpr.py`, `gen_sch.py`, `gen_lib.py` patterns (copy, then adapt; keep rev 1 untouched)

**Interfaces:**
- Produces: `circuit.parts() -> list[Part]` with the same `Part` dataclass as rev 1; `circuit.ADC_PINS: dict[str, str]` (key → MCU pin).

- [ ] **Step 1: Failing tests:**
  `test_each_key_has_one_sensor_on_its_own_adc_pin` (six distinct pins, all ADC-capable per the AT32F405 datasheet table copied into the test),
  `test_no_multiplexer`,
  `test_sensors_and_vdda_share_the_analog_rail_only` (net `+3V3A` touches only sensors, their caps, VDDA/VREF and the LDO),
  `test_led_rail_is_fused_and_buffered` (as rev 1),
  `test_usb_has_cc_pulldowns_and_esd`,
  `test_hs_usb_pins_are_the_hs_phy` (D+/D− on the HS OTG pins),
  `test_key_positions_match_rev1`.
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

### Task 5: PCB

**Files:**
- Create: `hardware/he/gen_pcb.py`, `hardware/he/route.py` (adapted from rev 1), `hardware/he/tests/test_layout.py`

- [ ] **Step 1: Failing tests:** `test_sensor_on_magnet_axis` (≤ 0.1 mm from each switch centre, top layer), `test_analog_ground_return_does_not_cross_led_current`, `test_crystal_within_5mm_of_mcu`, `test_hs_pair_length_matched_within_0_15mm`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Place and route. **Step 4:** PASS; DRC 0 errors, 0 unconnected.
- [ ] **Step 5:** Commit.

### Task 6: Case with a 6° wedge

**Files:**
- Modify: `case/generate.py` (`Params.wedge_deg`, translucent material names)
- Create: `case/tests/test_case_he.py`

- [ ] **Step 1: Failing tests:** `test_wedge_angle_is_6_degrees`, `test_front_edge_height_under_12mm`, `test_layers_are_stock_thicknesses`, plus the rev 1 plate and frame tests re-run against the HE board.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS (all case tests). **Step 5:** Commit.

### Task 7: Bring-up and measurement

- [ ] **Step 1:** Assemble one board; flash; calibrate.
- [ ] **Step 2:** Log all six keys for 60 s idle with LEDs at full brightness animating, then 60 s with LEDs off. Gate: difference ≤ 1 count per key.
- [ ] **Step 3:** Per-key RT floor with the Task 1 rig. Gate: ≤ 0.05 mm on all six; publish the table in `docs/hall-effect-results.md`.
- [ ] **Step 4:** Plug into a Full-Speed-only hub; gate: works at 1 kHz.
- [ ] **Step 5:** One hour of osu! play; note any phantom or missed inputs.
- [ ] **Step 6:** Commit results; update the site's rev 2 page with measured numbers.
