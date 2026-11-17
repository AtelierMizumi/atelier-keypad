# Atelier6K Rev 1 Production Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `scripts/fab.sh rev1` builds `build/fab/rev1/`, an order-ready package for the rev 1 board (Gerber + drill, JLCPCB BOM/CPL for the SMD parts, a hand-parts list, FR4 plate Gerbers, acrylic DXF, firmware). CI builds and checks it next to rev 2.0.

**Architecture:** This follows the rev 2.0 package (`hardware/he/fab.py`, `scripts/fab.sh`, `hardware/he/tests/test_fab.py`). Rev 1 gets its own `hardware/rev1/fab.py` because the repo keeps one copy of each tool per revision (`sexpr.py` and `route.py` already work this way). `circuit.py` is the source of truth for the BOM, and KiCad's position file is the source of truth for placement. The FR4 plate becomes a second, Edge.Cuts-only KiCad board, generated from the case model's plate polygon (`case/generate.py`), so its Gerbers come out of the same `kicad-cli` call path. `scripts/fab.sh` takes a revision argument and defaults to `rev2.0`, so the CI step that exists today keeps working.

**Tech Stack:** Python 3 (stdlib for fab.py; shapely + ezdxf for the plate), pytest via `uv run --no-project`, KiCad 10 `kicad-cli` in `kicad/kicad:10.0.8-full` (Docker, `--network none`), GitHub Actions.

**Spec:** `docs/rev1-board.md` § "Before ordering" (item 8: the plate has no Gerbers) and `docs/rev1-assessment.md` § "What is still open" ("No fabrication package yet (Gerbers, drill, position file, plate)"). There is no separate spec document. This plan cites those two sections.

## Global Constraints

- KiCad image: `${KICAD_IMAGE:-kicad/kicad:10.0.8-full}`, run with `--network none`, `-u "$(id -u):$(id -g)" -e HOME=/tmp`, as `scripts/fab.sh` does today.
- Board: 2 layers, FR-4, **1.6 mm** (`circuit.THICKNESS`), outline `circuit.OUTLINE` = 81.28 × 73.66 mm, 4 × 3.2 mm M3 holes.
- Plate: FR4, **1.6 mm**, ordered as a separate PCB with no copper. Its outline comes from the case model (`params_for(board)` gives `t_plate=1.6`, `plate_material="fr4"`).
- JLCPCB formats are copied exactly from rev 2.0. BOM columns are `Comment, Designator, Footprint, LCSC`. CPL columns are `Designator, Mid X, Mid Y, Layer, Rotation`, with values in `mm` and KiCad origin, Y up.
- LCSC numbers: reuse only the numbers already verified in `hardware/he/circuit.py` for the same part. Rev 1's machine-assembled parts are all in that table, so no new number gets invented.
- Hand-placed parts (not in the JLCPCB BOM/CPL): `U1` (RP2040-Zero module), `MX1`–`MX6` (Kailh MX hot-swap sockets), `SW1`–`SW3` (6 × 6 mm THT tact, 13 mm).
- `build/` is never committed (`.gitignore` has `/build/`). Generated plate sources live under `build/fab/rev1/`.
- `scripts/fab.sh` with no argument must keep producing `build/fab/rev2.0/` exactly as before.
- Commit messages follow the repo's Conventional Commit style (`feat(rev1): …`, `ci: …`, `docs(rev1): …`).

## Review Focus

1. **Bottom-side CPL rotation.** D1–D6, U2, F1 and most of the passives are on `B`. JLCPCB's preview often shows bottom parts rotated wrongly. Expected: Layer is `Bottom` and the coordinates are the unmirrored board coordinates. Pinned by `test_cpl_bottom_parts_are_on_bottom_layer_with_board_coordinates` (Task 3).
2. **Plate cut-outs drift from the shifted keys.** Rev 1 moved the keys down by `KEY_SHIFT = 12.7`. The plate PCB must cut every MX hole at `KEYS[ref] + (0, KEY_SHIFT)`, not at the rev 0 position. Pinned by `test_plate_cutouts_follow_the_rev1_keys` (Task 2).
3. **Unknown revision argument.** `scripts/fab.sh rev3` must exit non-zero without deleting anything. Pinned by `test_fab_sh_rejects_unknown_revision` (Task 3).
4. **No firmware build present.** The package must still build without the `.uf2`, and then contain no `firmware.uf2`. Pinned by `test_package_firmware_is_optional` (Task 3).
5. **A part with no LCSC number gets into the SMD BOM silently** (for example a new resistor value added to `circuit.py`). Expected: a test fails and names it. Pinned by `test_every_machine_part_has_an_lcsc_number` (Task 1).

---

## File Structure

| File | Responsibility |
|---|---|
| `hardware/rev1/circuit.py` (modify) | Add `LCSC` table, `HAND_PLACED` set, `lcsc(p)` and `machine_parts(parts)` |
| `hardware/rev1/fab.py` (create) | Writes `bom-jlcpcb.csv`, `cpl-jlcpcb.csv`, `hand-parts.csv`, `README.txt` |
| `hardware/rev1/tests/test_fab.py` (create) | BOM tests run on `circuit.py`; package tests skip unless built or `FAB_REQUIRED=1` |
| `case/plate_pcb.py` (create) | Turns the rev 1 plate polygon into an Edge.Cuts-only `.kicad_pcb` |
| `case/tests/test_plate_pcb.py` (create) | Plate board geometry tests |
| `scripts/fab.sh` (modify) | `rev2.0` (default) or `rev1` |
| `.github/workflows/ci.yml` (modify) | rev 1 unit tests, `scripts/rev1.sh check`, rev 1 package + tests + artifact |
| `docs/rev1-board.md`, `README.md` (modify) | "How to order rev 1", status row |

---

### Task 1: LCSC table and hand-placed parts in `circuit.py`

**Files:**
- Modify: `hardware/rev1/circuit.py` (append after `NET_CLASSES`)
- Test: `hardware/rev1/tests/test_fab.py` (create; Task 3 adds more tests to it)

**Interfaces:**
- Produces:
  - `LCSC: dict[tuple[str, str], str]`, keyed by `(value, footprint name after ":")`
  - `HAND_PLACED: frozenset[str]` = `{"U1", "MX1", …, "MX6", "SW1", "SW2", "SW3"}`, built from `KEYS`, `BUTTONS` and `"U1"`
  - `lcsc(p: Part) -> str` returns `""` when there is no entry
  - `machine_parts(parts: list[Part]) -> list[Part]` returns the parts not in `HAND_PLACED`

- [ ] **Step 1: Write the failing tests** in `hardware/rev1/tests/test_fab.py`:

```python
import circuit

def test_hand_placed_are_the_module_switches_and_buttons():
    assert circuit.HAND_PLACED == {"U1", *circuit.KEYS, *circuit.BUTTONS}

def test_every_machine_part_has_an_lcsc_number():
    missing = sorted({(p.ref, p.value) for p in circuit.machine_parts(circuit.parts())
                      if not circuit.lcsc(p).startswith("C")})
    assert missing == []

def test_lcsc_numbers_match_rev2_for_the_same_part():
    # rev 1 uses only parts already verified for rev 2.0; same part -> same number
    assert circuit.LCSC[("SK6812MINI-E", "LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount")] == "C5149201"
    assert circuit.LCSC[("74AHCT1G125", "SOT-23-5_HandSoldering")] == "C12494"
    assert circuit.LCSC[("500mA", "Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder")] == "C151162"
```

- [ ] **Step 2: Run red.** `cd hardware/rev1 && uv run --no-project --with pytest pytest -q tests/test_fab.py`. Expected: 3 failures with `AttributeError: module 'circuit' has no attribute 'HAND_PLACED'` (and `machine_parts`, `LCSC`).

- [ ] **Step 3: Implement** in `circuit.py`. The `LCSC` entries are: `("100nF", FP_C0603)` → `C14663`; `("4.7uF", FP_C0805)` → `C1779`; `("330", FP_R0603)` → `C23138`, plus the three from the test (key = footprint name after `:`). Copy the rev 2.0 comment that each number was checked against its LCSC product page, and say these are the rev 2.0 numbers.

- [ ] **Step 4: Run green.** Same command: 3 passed. Then run `uv run --no-project --with pytest pytest -q tests`: 18 passed (15 old + 3).

- [ ] **Step 5: Commit** `feat(rev1): LCSC numbers and hand-placed parts for the production BOM`.

---

### Task 2: FR4 plate as an Edge.Cuts-only KiCad board

**Files:**
- Create: `case/plate_pcb.py`
- Test: `case/tests/test_plate_pcb.py`

**Interfaces:**
- Consumes: `generate.load_board(generate.PCB_FILE_REV1)`, `generate.params_for(board)`, `generate.design(board, p).layer("plate").shape` (shapely `Polygon`, KiCad board coordinates, Y down), `generate._is_circle(coords)`
- Produces:
  - `plate_shape() -> Polygon`, the rev 1 plate in board coordinates
  - `write_plate_pcb(shape: Polygon, path: Path, thickness: float = 1.6) -> Path`
  - CLI: `uv run --quiet --no-project --with shapely --with ezdxf case/plate_pcb.py <out.kicad_pcb>`

- [ ] **Step 1: Write the failing tests** in `case/tests/test_plate_pcb.py`. Parse the written file with `generate._parse_sexpr` and `generate._kids`, and keep only items on `Edge.Cuts`:

```python
def test_plate_board_is_edge_cuts_only_and_1p6_mm(tmp_path):
    root = parse(write_plate_pcb(plate_shape(), tmp_path / "p.kicad_pcb"))
    assert thickness(root) == 1.6
    assert not kids(root, "footprint") and not kids(root, "segment") and not kids(root, "zone")

def test_plate_outline_matches_the_board_outline(tmp_path):
    # outer gr_poly bounds == board.outline.bounds within 0.01 mm
def test_plate_has_four_3p2_mm_screw_holes(tmp_path):
    # exactly 4 gr_circle on Edge.Cuts, radius 1.6 ± 0.01, centres == circuit HOLES ± 0.01
def test_plate_cutouts_follow_the_rev1_keys(tmp_path):
    # one 14 mm square-ish gr_poly centred within 0.05 mm of KEYS[ref] + (0, KEY_SHIFT) for each MX
def test_every_plate_ring_is_written_once(tmp_path):
    # count(gr_poly) + count(gr_circle) == 1 + len(plate_shape().interiors)
```

Import `circuit` from `hardware/rev1` the same way `case/tests/test_case_rev1.py` gets its board data. Do not hardcode the coordinates.

- [ ] **Step 2: Run red.** `cd case && uv run --no-project --with pytest --with shapely --with ezdxf pytest -q tests/test_plate_pcb.py`. Expected: `ModuleNotFoundError: No module named 'plate_pcb'`.

- [ ] **Step 3: Implement `case/plate_pcb.py`.** Write the s-expression as text. Take the header from `hardware/rev1/atelier6k-rev1.kicad_pcb`: `(version 20260206)`, `(generator "pcbnew")`, `(generator_version "10.0")`, the `(general (thickness …))` block, and the `(layers …)` block copied verbatim. Write the exterior as one `gr_poly` on `Edge.Cuts` (stroke width 0.05, no fill). Write each interior as a `gr_circle` (center + end point at radius) when `_is_circle` matches, otherwise as a `gr_poly`. Do not add any copper, footprints or zones.

- [ ] **Step 4: Run green.** Same command: 5 passed. Then run the whole case suite, `pytest -q tests`: 56 passed (51 + 5). In the container, `kicad-cli pcb drc` on the written plate must report 0 errors. Run it through the same `docker run` line that `scripts/fab.sh` uses.

- [ ] **Step 5: Commit** `feat(case): FR4 plate for rev 1 as an Edge.Cuts-only KiCad board`.

---

### Task 3: `hardware/rev1/fab.py` and `scripts/fab.sh rev1`

**Files:**
- Create: `hardware/rev1/fab.py`
- Modify: `scripts/fab.sh`
- Test: `hardware/rev1/tests/test_fab.py` (extend)

**Interfaces:**
- Consumes: Task 1 (`circuit.machine_parts`, `circuit.lcsc`, `circuit.HAND_PLACED`), Task 2 (the `case/plate_pcb.py` CLI)
- Produces:
  - `write_bom(parts, path) -> Path`: machine parts only, grouped by `(value, footprint, lcsc)`, sorted the way `hardware/he/fab.py` sorts (`_ref_key`)
  - `write_cpl(pos_csv, path, parts) -> Path`: machine parts only, same row format as rev 2.0
  - `write_hand_parts(parts, path) -> Path` with columns `Part, Designator, Qty, Source`. Sources: `RP2040-Zero` → `Waveshare RP2040-Zero (castellated, no headers)`; MX → `Kailh MX hot-swap socket`; SW → `6x6 mm THT tact, 13 mm`
  - `write_readme(path) -> Path`
  - Package layout `build/fab/rev1/`: `gerbers/`, `plate-gerbers/`, `bom-jlcpcb.csv`, `cpl-jlcpcb.csv`, `hand-parts.csv`, `case-dxf/` (the three acrylic layers from `case/dxf-rev1/`: top-frame 3 mm, bottom-frame 5 mm, base 3 mm; not the plate or `-all`), `README.txt`, `firmware.uf2` (only if `firmware/build/atelier6k_default.uf2` exists)

- [ ] **Step 1: Write the failing tests.** Append them to `hardware/rev1/tests/test_fab.py`. Use the same `PKG`/`needs_pkg` skip pattern as `hardware/he/tests/test_fab.py`, with `PKG = ROOT / "build" / "fab" / "rev1"`.
  - `test_bom_has_jlcpcb_columns` (columns == `["Comment","Designator","Footprint","LCSC"]`)
  - `test_bom_counts_every_machine_part_and_no_hand_part`: BOM designators == `machine_parts` refs, and they are disjoint from `HAND_PLACED`
  - `test_hand_parts_list_the_module_6_sockets_and_3_buttons`: Qty 1 / 6 / 3
  - `@needs_pkg test_cpl_designators_match_bom`
  - `@needs_pkg test_cpl_bottom_parts_are_on_bottom_layer_with_board_coordinates`: Layer comes from `p.side`, and `(x, -y) == (p.x, p.y)` ± 0.01
  - `@needs_pkg test_gerber_sets_are_complete`: `gerbers/` has the 9 layers + `-PTH.drl` + `-NPTH.drl`; `plate-gerbers/` has `Edge_Cuts`, `F_Mask` and `B_Mask`
  - `@needs_pkg test_case_dxf_is_the_three_acrylic_layers`: exactly 3 `.dxf` files, none with `plate` in the name
  - `@needs_pkg test_fab_readme_states_board_plate_and_open_checks`: contains `"1.6 mm"`, `"2 layers"`, `"plate"`, and each of `"notch"`, `"LED pinout"`, `"module"` (the open items 1–3 of rev1-board.md, copied as a checklist)
  - `@needs_pkg test_package_firmware_is_optional`: `firmware.uf2` exists if and only if `ROOT/firmware/build/atelier6k_default.uf2` exists
  - `test_fab_sh_rejects_unknown_revision`: `subprocess.run([ROOT/"scripts/fab.sh", "rev3"])` returns non-zero, and `build/fab/rev3` does not exist afterwards. This runs before any docker call, so it needs no KiCad.

- [ ] **Step 2: Run red.** `cd hardware/rev1 && uv run --no-project --with pytest pytest -q tests/test_fab.py`. Expected: `ModuleNotFoundError: No module named 'fab'`. The unknown-revision test fails because the current `fab.sh` ignores its argument and builds rev 2.0. The package tests skip.

- [ ] **Step 3: Implement `fab.py`** by adapting `hardware/he/fab.py`. Use `machine_parts` instead of the `TP` filter. The README states: 2 layers, FR-4, 1.6 mm, size from `OUTLINE`, 5 pcs, SMD parts on both sides (D7–D10 and C7–C10 on top, the rest on the bottom). It describes the plate as a separate 1.6 mm FR4 board with no copper, sent from `plate-gerbers/`. It lists the hand parts and the "Check before ordering" items (notch, LED pinout, module) from `docs/rev1-board.md`. `main()` takes `<kicad pos csv> <out dir>`, as rev 2.0 does.

- [ ] **Step 4: Implement `scripts/fab.sh [rev2.0|rev1]`.** Add `rev="${1:-rev2.0}"`, then a `case` block that sets `PCB`, `OUT=build/fab/$rev`, the fab.py path, the DXF glob and the firmware source/name. Any other value prints `unknown revision: $rev` to stderr and exits 2 before the clean step. For `rev1` only, add one more step after the drill export: generate `$OUT/plate-src/atelier6k-plate.kicad_pcb` with `case/plate_pcb.py`, run `kicad-cli pcb export gerbers --layers F.Mask,B.Mask,Edge.Cuts` into `$OUT/plate-gerbers/`, then `rm -rf -- "$OUT/plate-src"`. Keep the `build/fab/*` guard on the clean step. Do not change what the `rev2.0` branch outputs.

- [ ] **Step 5: Run green.**
  - `scripts/fab.sh rev1 && (cd hardware/rev1 && FAB_REQUIRED=1 uv run --no-project --with pytest pytest -q tests/test_fab.py)`: all 13 pass, none skipped.
  - Regression: `scripts/fab.sh && (cd hardware/he && FAB_REQUIRED=1 uv run --no-project --with pytest pytest -q tests/test_fab.py)`: 7 passed, the same as before this task.

- [ ] **Step 6: Commit** `feat(rev1): production package — Gerber, drill, JLCPCB BOM and CPL, FR4 plate, case DXF`.

---

### Task 4: CI and docs

**Files:**
- Modify: `.github/workflows/ci.yml`, `docs/rev1-board.md`, `README.md`

**Interfaces:**
- Consumes: `scripts/rev1.sh check`, `scripts/fab.sh rev1`, the Task 3 tests

- [ ] **Step 1: CI.**
  - In the `test` job, add a step `cd hardware/rev1 && uv run --no-project --with pytest pytest -q tests`. It does not run in CI today.
  - In the `kicad` job, after the rev 2.0 package steps, add `scripts/rev1.sh check`, `scripts/fab.sh rev1`, `cd hardware/rev1 && FAB_REQUIRED=1 uv run --no-project --with pytest pytest -q tests/test_fab.py`, and `actions/upload-artifact@v4` with `name: rev1-package`, `path: build/fab/rev1`.
  - Leave the `release` job unchanged; rev 1 is not tagged.
- [ ] **Step 2: Docs.**
  - `docs/rev1-board.md`: item 8 becomes "Done: `plate-gerbers/` in the rev 1 package". Add a short "How to order" section: run `scripts/fab.sh rev1`, or download the `rev1-package` CI artifact; upload `gerbers/` + BOM + CPL to JLCPCB as 1.6 mm, 2 layers, two-sided SMT; order `plate-gerbers/` as a separate 1.6 mm board with no assembly; buy the parts in `hand-parts.csv`. Items 1–3 stay open.
  - `README.md` rev 1 row: "Order files ready (ERC 0, DRC 0); not built".
- [ ] **Step 3: Verify.** `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"` succeeds (or use `uv run --with pyyaml`). `scripts/check-assets.sh` passes. After the push, the `Rev 2.0 checks and production package` workflow is green, and its run page lists a `rev1-package` artifact (`gh run view --log` / `gh run view <id>`).
- [ ] **Step 4: Commit** `ci: rev 1 tests, KiCad checks and production package`, plus `docs(rev1): how to order rev 1`.

---

## Self-review notes

- Coverage: item 8 of "Before ordering" → Tasks 2–3. "No fabrication package" → Task 3. Items 1–3 (notch, LED pinout, module) need a real part or datasheet, so they are not code. They go into the README checklist (Task 3) and stay open in the docs (Task 4). Items 4–7 and 9 need no change before ordering.
- Names used across tasks: `HAND_PLACED`, `machine_parts`, `lcsc`, `plate_shape`, `write_plate_pcb`, `build/fab/rev1`, `plate-gerbers/`, `hand-parts.csv`.
