# Rev 2 Flat Case and Grip Pad Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The rev 2 case sits flat on a full silicone pad. Every case DXF carries a 50 mm scale bar. A test proves a USB-C plug fits the slot. The site shows all of it.

**Architecture:** `case/generate_he.py` drops the feet and the tilt, and adds a `pad` layer to the bottom of the stack. That layer flows through the existing DXF and model-JSON writers. A shared helper `case/scale_bar.py` draws the bar into each DXF from both generators. `site/case.js` stops drawing feet and gets a style for the silicone layer.

**Tech Stack:** Python, shapely, ezdxf, pytest via `uv run --no-project`, three.js viewer.

**Spec:** `docs/superpowers/specs/2026-11-16-rev2-flat-case-grip.md`

## Global Constraints
- Pad: 1.5 mm silicone, inset 0.5 mm, a BOOT hole of Ø 6 mm. The pad layer's material string is `"silicone"`.
- Desk to PCB top: 11.5 mm. `tilt_deg` is 0.
- Scale bar: a 50.0 mm line plus the text "50 mm, check before cutting", on DXF layer `NOTES`. `$INSUNITS` is 4.
- USB plug envelope: 12.4 × 6.6 mm, centred on J1 in x, and in z on the receptacle centre.

## Review Focus
1. Nut pockets must stay covered by the pad, so nuts cannot drop out: `test_pad_covers_the_nut_pockets`.
2. The pad must not cover the BOOT hole: `test_pad_has_a_boot_hole`.
3. The scale bar must not end up on a cut layer: `test_scale_bar_is_on_a_notes_layer`.
4. Rev 0 and rev 1 DXF geometry must not change, only gain the bar: the existing case tests stay green.
5. The viewer must not break when `feet` is empty: checked in the browser preview.

---

### Task 1: Flat case with a silicone pad (`case/generate_he.py`)
- [ ] Tests in `case/tests/test_case_he.py`:
  - Replace `test_feet_give_a_6_degree_typing_angle` with `test_case_is_flat_and_low`: `data["tilt_deg"] == 0`, `case.feet == []`, and desk to PCB top (`-pad.z0`) == 11.5 ± 0.01.
  - Add `test_pad_covers_the_base_footprint`: pad area ≥ 0.9 × the area of the base outline.
  - Add `test_pad_covers_the_nut_pockets`: every hexagonal nut pocket is fully inside the pad.
  - Add `test_pad_has_a_boot_hole`: the pad does not contain `Point(boot)`, and the hole is at least 6 mm across.
  - Update `test_model_json_for_the_viewer`: names start `["pad", "base", …]`.
  - Update `test_stack_heights`: the pad has thickness 1.5 and sits under the base.
  - The screw test checks the tip is above the pad bottom.
- [ ] Red, then implement: constants `PAD_T = 1.5`, `PAD_INSET = 0.5`, `PAD_BOOT_HOLE = 6.0`. Remove the feet from the stack, `TILT_DEG` and `FRONT_FOOT`. The model `order` becomes `i - 3 if i < 3 else i - 2`. Update the module docstring.
- [ ] Green: `cd case && uv run --no-project --with pytest --with shapely --with ezdxf pytest -q tests`.

### Task 2: 50 mm scale bar in every DXF
- [ ] `case/scale_bar.py`: `add_scale_bar(doc, msp, origin=(0, -12)) -> None`. Adds a `NOTES` layer if it is missing, a 50 mm line, and the text.
- [ ] Test `case/tests/test_scale_bar.py`: for every `.dxf` in `case/dxf`, `case/dxf-rev1` and `case/dxf-he`, after regeneration, check `$INSUNITS == 4`, exactly one `LINE` on `NOTES` of length 50.0 ± 1e-6, and no cut entity on `NOTES` (`test_scale_bar_is_on_a_notes_layer`).
- [ ] Call it from `generate.write_dxf` (each layer file and the overview) and from `generate_he.write_dxf`. Regenerate with `uv run case/generate.py`, `uv run case/generate.py --rev1` and `uv run case/generate_he.py`.

### Task 3: USB plug fits the slot
- [ ] `test_usb_plug_fits_the_slot` in `test_case_he.py`. The slot opening, taken as the union over the walls cut by the slot, must contain a 12.4 mm wide rectangle centred on J1 x, in plan view. The walls cut must span z from −2.8 − 3.3 to −2.8 + 3.3 (receptacle centre at −1.2 − 1.6).
- [ ] If red, widen `USB_SLOT` or extend the cut walls. Otherwise the test pins the current geometry.

### Task 4: Viewer, site and docs
- [ ] `site/case.js`: add a `silicone` style (near-black, opaque). Skip the feet group when `data.feet` is empty, and skip the tilt when it is 0.
- [ ] `site/index.html`, rev 2:
  - Fix the "Hand" item: no wedge.
  - The case `sub` text describes the flat stack and the pad.
  - Add a "Lessons from other keypads" section, built from the spec's evidence.
- [ ] Docs: `docs/rev2-board.md` (feet line), `docs/build/ordering.md` (hardware line: a silicone sheet instead of feet).
- [ ] Preview in a browser and show the owner. Commit, deploy only after their OK.
