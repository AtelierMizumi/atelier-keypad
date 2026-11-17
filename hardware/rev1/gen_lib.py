#!/usr/bin/env python3
"""Writes the project-local symbol and footprint for the RP2040-Zero module.

    python3 hardware/rev1/gen_lib.py

Dimensions are from Waveshare's drawing (18.00 x 23.50 mm, pads on a 2.54 mm
pitch, first pad 1.59 mm from the USB end, pad centres 1.38 mm in from the
edges). The footprint is for flush mounting on castellated edges: the module's
back carries the RP2040, so the board needs a notch under it (drawn by
gen_pcb.py, not by this footprint).
"""
from __future__ import annotations

from pathlib import Path

import circuit

LIBS = Path(__file__).resolve().parents[1] / "libs" / "local"

LEFT = ["5V", "GND", "3V3", "GP29", "GP28", "GP27", "GP26", "GP15", "GP14"]
RIGHT = [f"GP{i}" for i in range(9)]
BOTTOM = ["GP13", "GP12", "GP11", "GP10", "GP9"]  # left to right, seen from the component side

W, L = circuit.MODULE_WIDTH, circuit.MODULE_LENGTH
ROW_X = W / 2 - 1.38          # 7.62
FIRST_Y = 1.59
PITCH = 2.54
PAD_LONG, PAD_SHORT = 2.6, 1.6
PAD_SHIFT = 0.6               # pad centre moved outwards so solder can fillet on the edge


def module_pads() -> list[tuple[str, float, float, float, float]]:
    """(name, x, y, size_x, size_y), origin at the middle of the USB end, y towards the far end."""
    pads = []
    for i, name in enumerate(LEFT):
        pads.append((name, -(ROW_X + PAD_SHIFT), FIRST_Y + i * PITCH, PAD_LONG, PAD_SHORT))
    for i, name in enumerate(RIGHT):
        pads.append((name, ROW_X + PAD_SHIFT, FIRST_Y + i * PITCH, PAD_LONG, PAD_SHORT))
    for i, name in enumerate(BOTTOM):
        pads.append((name, (i - 2) * PITCH, L - 1.38 + PAD_SHIFT, PAD_SHORT, PAD_LONG))
    return pads


def footprint() -> str:
    hw = W / 2
    out = [
        '(footprint "RP2040-Zero_Flush"',
        '\t(version 20241229)', '\t(generator "atelier6k_gen_lib")', '\t(layer "F.Cu")',
        '\t(descr "Waveshare RP2040-Zero, flush-mounted on its castellated edges. Needs a board cut-out under the module.")',
        '\t(tags "RP2040 Zero module castellated")',
        f'\t(property "Reference" "REF**" (at 0 {L + 2.2:.2f} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
        f'\t(property "Value" "RP2040-Zero_Flush" (at 0 {L + 3.8:.2f} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
        '\t(attr smd)',
    ]

    def rect(layer: str, x0, y0, x1, y1, width):
        out.append(f'\t(fp_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) '
                   f'(stroke (width {width}) (type solid)) (fill no) (layer "{layer}"))')

    rect("F.Fab", -hw, 0, hw, L, 0.1)
    rect("F.CrtYd", -hw - 0.8, -1.5, hw + 0.8, L + 0.9, 0.05)
    # Silk: corner marks only, the pads take the rest of the outline.
    for sx in (-1, 1):
        out.append(f'\t(fp_line (start {sx * hw:.3f} {L + 0.15:.3f}) (end {sx * (hw - 1.6):.3f} {L + 0.15:.3f}) '
                   '(stroke (width 0.12) (type solid)) (layer "F.SilkS"))')
    out.append('\t(fp_text user "USB" (at 0 -0.9 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))')
    for name, x, y, sx, sy in module_pads():
        out.append(f'\t(pad "{name}" smd roundrect (at {x:.3f} {y:.3f}) (size {sx} {sy}) '
                   '(layers "F.Cu" "F.Mask" "F.Paste") (roundrect_rratio 0.15))')
    out.append(")")
    return "\n".join(out) + "\n"


def symbol_lib() -> str:
    left = LEFT + ["GP13", "GP12", "GP11"]
    right = RIGHT + ["GP9", "GP10"]
    kinds = {"5V": "power_out", "3V3": "power_out", "GND": "power_in"}
    top = (len(left) - 1) * 2.54 / 2

    def prop(key, value, y, hide=False):
        h = " (hide yes)" if hide else ""
        return f'\t\t(property "{key}" "{value}" (at 0 {y:.2f} 0){h} (effects (font (size 1.27 1.27))))'

    out = [
        "(kicad_symbol_lib", "\t(version 20251024)", '\t(generator "atelier6k_gen_lib")', '\t(generator_version "10.0")',
        '\t(symbol "RP2040-Zero"',
        "\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)",
        prop("Reference", "U", top + 5.08),
        prop("Value", "RP2040-Zero", top + 2.54),
        prop("Footprint", "local:RP2040-Zero_Flush", -top - 5.08, hide=True),
        prop("Datasheet", "https://www.waveshare.com/wiki/RP2040-Zero", -top - 7.62, hide=True),
        prop("Description", "Waveshare RP2040-Zero MCU module: RP2040, 2 MB flash, USB-C, 3.3 V regulator", -top - 10.16, hide=True),
        '\t\t(symbol "RP2040-Zero_0_1"',
        f"\t\t\t(rectangle (start -10.16 {top + 1.27:.2f}) (end 10.16 {-top - 1.27:.2f}) "
        "(stroke (width 0.254) (type default)) (fill (type background)))",
        "\t\t)",
        '\t\t(symbol "RP2040-Zero_1_1"',
    ]
    for side, names, x, angle in (("l", left, -12.7, 0), ("r", right, 12.7, 180)):
        for i, name in enumerate(names):
            out.append(f'\t\t\t(pin {kinds.get(name, "bidirectional")} line (at {x} {top - i * 2.54:.2f} {angle}) (length 2.54) '
                       f'(name "{name}" (effects (font (size 1.27 1.27)))) (number "{name}" (effects (font (size 1.27 1.27)))))')
    out += ["\t\t)", "\t)", ")"]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    LIBS.mkdir(parents=True, exist_ok=True)
    (LIBS / "RP2040-Zero_Flush.kicad_mod").write_text(footprint())
    (LIBS / "atelier.kicad_sym").write_text(symbol_lib())
    print("wrote", LIBS / "RP2040-Zero_Flush.kicad_mod", "and", LIBS / "atelier.kicad_sym")
