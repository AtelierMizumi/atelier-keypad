#!/usr/bin/env python3
"""Writes the rev 2 project-local library: the AT32F405 (LQFP48) symbol and the
footprint of a PCB-mount magnetic switch.

    python3 hardware/he/gen_lib.py

The symbol's pins come from circuit.AT32F405_LQFP48 (datasheet v2.02), so the
circuit, the tests and the symbol share one table. The footprint uses the
stock Package_QFP:LQFP-48_7x7mm_P0.5mm.

Switch footprint: two 1.75 mm plastic pegs at +-5.08 mm like a PCB-mount MX
switch, no electrical pins, nothing at the centre where the sensor sits.
Check against the drawing of the exact switch bought (Task 1): if its housing
has a centre post, the sensor must move.
"""
from __future__ import annotations

from pathlib import Path

import circuit

LIBS = Path(__file__).resolve().parents[1] / "libs" / "local"
SYMBOL_LIB = LIBS / "atelier_he.kicad_sym"
SWITCH_FP = LIBS / "HE_Switch_PCBMount.kicad_mod"

POWER = {"VDD", "VSS", "VDDA", "VSSA"}


def _kind(name: str) -> str:
    if name in POWER:
        return "power_in"
    if name == "NRST":
        return "input"
    if name == "OTGHS_R":
        return "passive"
    return "bidirectional"


def symbol_lib() -> str:
    pins = circuit.AT32F405_LQFP48
    # Left: supplies, clock, reset, boot. Right: every GPIO and USB, in pin order.
    left = [n for n, nm in pins.items() if nm in POWER | {"NRST", "PF0", "PF1", "PF11/BOOT0"}]
    right = [n for n in pins if n not in left]
    rows = max(len(left), len(right))
    top = (rows - 1) * 2.54 / 2
    w = 15.24

    def prop(key, value, y, hide=False):
        h = " (hide yes)" if hide else ""
        return f'\t\t(property "{key}" "{value}" (at 0 {y:.2f} 0){h} (effects (font (size 1.27 1.27))))'

    out = [
        "(kicad_symbol_lib", "\t(version 20251024)", '\t(generator "atelier_he_gen_lib")', '\t(generator_version "10.0")',
        '\t(symbol "AT32F405CxT7"',
        "\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)",
        prop("Reference", "U", top + 5.08),
        prop("Value", "AT32F405CxT7", top + 2.54),
        prop("Footprint", "Package_QFP:LQFP-48_7x7mm_P0.5mm", -top - 5.08, hide=True),
        prop("Datasheet", "https://www.arterychip.com/en/product/AT32F405.jsp", -top - 7.62, hide=True),
        prop("Description", "ARTERY AT32F405 Cortex-M4F, 216 MHz, OTGHS with PHY, LQFP48", -top - 10.16, hide=True),
        '\t\t(symbol "AT32F405CxT7_0_1"',
        f"\t\t\t(rectangle (start {-w:.2f} {top + 1.27:.2f}) (end {w:.2f} {-top - 1.27:.2f}) "
        "(stroke (width 0.254) (type default)) (fill (type background)))",
        "\t\t)",
        '\t\t(symbol "AT32F405CxT7_1_1"',
    ]
    for numbers, x, angle in ((left, -w - 2.54, 0), (right, w + 2.54, 180)):
        for i, n in enumerate(numbers):
            name = pins[n]
            out.append(f'\t\t\t(pin {_kind(name)} line (at {x:.2f} {top - i * 2.54:.2f} {angle}) (length 2.54) '
                       f'(name "{name}" (effects (font (size 1.27 1.27)))) (number "{n}" (effects (font (size 1.27 1.27)))))')
    out += ["\t\t)", "\t)", ")"]
    return "\n".join(out) + "\n"


def switch_footprint() -> str:
    lines = [
        '(footprint "HE_Switch_PCBMount"', '\t(version 20241229)', '\t(generator "atelier_he_gen_lib")',
        '\t(layer "F.Cu")',
        '\t(descr "PCB-mount magnetic (Hall effect) switch, MX-style pegs, no electrical pins; sensor goes at the centre")',
        '\t(property "Reference" "KEY**" (at 0 -8.2 0) (layer "F.SilkS") (hide yes) (effects (font (size 1 1) (thickness 0.15))))',
        '\t(property "Value" "HE switch" (at 0 8.2 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
        '\t(attr board_only exclude_from_pos_files exclude_from_bom)',
        '\t(fp_rect (start -7 -7) (end 7 7) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))',
        '\t(fp_line (start -7 -7) (end -6 -7) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
        '\t(fp_line (start -7 -7) (end -7 -6) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
        '\t(fp_line (start 7 7) (end 6 7) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
        '\t(fp_line (start 7 7) (end 7 6) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
    ]
    for x in (-5.08, 5.08):
        lines.append(f'\t(pad "" np_thru_hole circle (at {x} 0) (size 1.75 1.75) (drill 1.75) (layers "*.Cu" "*.Mask"))')
    lines.append(")")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    LIBS.mkdir(parents=True, exist_ok=True)
    SYMBOL_LIB.write_text(symbol_lib())
    SWITCH_FP.write_text(switch_footprint())
    print("wrote", SYMBOL_LIB, "and", SWITCH_FP)
