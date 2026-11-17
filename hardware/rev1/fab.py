#!/usr/bin/env python3
"""BOM, placement, hand-parts list and README for the rev 1 production package.

    python3 fab.py <kicad pos csv> <out dir>      # called by scripts/fab.sh rev1

The assembly house places the SMD parts (circuit.machine_parts); the module,
the hot-swap sockets and the through-hole buttons are soldered by hand and go
in hand-parts.csv instead. Same formats as rev 2.0 (hardware/he/fab.py): the
BOM comes from circuit.py, the placement from KiCad's position file.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import circuit

HAND_SOURCES = {
    "RP2040-Zero": "Waveshare RP2040-Zero (castellated, no headers)",
    "MX hot-swap": "Kailh MX hot-swap socket",
    "6x6 tact": "6x6 mm THT tact, 13 mm",
}


def _ref_key(ref: str):
    head = ref.rstrip("0123456789")
    return head, int(ref[len(head):] or 0)


def _refs(refs) -> str:
    return ",".join(sorted(refs, key=_ref_key))


def write_bom(parts, path: Path) -> Path:
    groups = defaultdict(list)
    for p in circuit.machine_parts(parts):
        groups[(p.value, p.footprint.split(":")[-1], circuit.lcsc(p))].append(p.ref)
    path = Path(path)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC"])
        for (value, fp, lcsc), refs in sorted(groups.items(), key=lambda g: _ref_key(min(g[1], key=_ref_key))):
            w.writerow([value, _refs(refs), fp, lcsc])
    return path


def write_cpl(pos_csv: Path, path: Path, parts) -> Path:
    """KiCad pos CSV (Ref,Val,Package,PosX,PosY,Rot,Side) -> JLCPCB CPL, machine parts only."""
    keep = {p.ref for p in circuit.machine_parts(parts)}
    with open(pos_csv, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["Ref"] in keep]
    path = Path(path)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in sorted(rows, key=lambda r: _ref_key(r["Ref"])):
            w.writerow([r["Ref"], f"{float(r['PosX']):.4f}mm", f"{float(r['PosY']):.4f}mm",
                        "Bottom" if r["Side"].lower() == "bottom" else "Top", f"{float(r['Rot']):g}"])
    return path


def write_hand_parts(parts, path: Path) -> Path:
    groups = defaultdict(list)
    for p in parts:
        if p.ref in circuit.HAND_PLACED:
            groups[p.value].append(p.ref)
    path = Path(path)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Part", "Designator", "Qty", "Source"])
        for value, refs in sorted(groups.items(), key=lambda g: _ref_key(min(g[1], key=_ref_key))):
            w.writerow([value, _refs(refs), len(refs), HAND_SOURCES[value]])
    return path


def write_readme(path: Path) -> Path:
    x0, y0, x1, y1 = circuit.OUTLINE
    top = _refs(p.ref for p in circuit.machine_parts(circuit.parts()) if p.side == "F")
    text = f"""Atelier6K rev 1 (RP2040-Zero) - production package

PCB (gerbers/)
  2 layers, FR-4, {circuit.THICKNESS:g} mm thick, 1 oz copper, lead-free HASL, any mask
  colour, white silkscreen. Size {x1 - x0:g} x {y1 - y0:g} mm, 5 pcs.
  SMT assembly on both sides: {top} on top, every other SMD part on the bottom.
  The board has a notch under the MCU module; it is part of Edge.Cuts.

Switch plate (plate-gerbers/)
  A separate board: 1.6 mm FR-4, no copper, no assembly, same size, 5 pcs.
  Mask on both sides is optional. The MX switches clip into it. The copper
  layers and the drill file are empty on purpose; write "no copper, outline only"
  in the order remark. All holes and cut-outs are milled from Edge.Cuts.

Files
  gerbers/          Gerber X2 + Excellon drill (PTH and NPTH separate)
  plate-gerbers/    switch plate: Edge.Cuts outline with the cut-outs, mask layers
  bom-jlcpcb.csv    Comment, Designator, Footprint, LCSC (SMD parts the fab places)
  cpl-jlcpcb.csv    Designator, Mid X, Mid Y, Layer, Rotation (KiCad origin, Y up)
  hand-parts.csv    parts you buy and solder yourself
  case-dxf/         laser-cut acrylic: top frame 3 mm, bottom frame 5 mm, base 3 mm
  firmware.uf2      QMK build, if one was in firmware/build/

Hand-soldered parts
  U1 RP2040-Zero module (flush, by its castellated edge), MX1-MX6 Kailh hot-swap
  sockets, SW1-SW3 6x6 mm tact switches. See hand-parts.csv.

Check before ordering (docs/rev1-board.md, "Before ordering")
  [ ] Module notch: 11.2 mm wide comes from the pad geometry; measure a real
      RP2040-Zero or check Waveshare's STEP file.
  [ ] LED pinout: compare the SK6812MINI-E footprint with the top-view drawing
      in the datasheet of the exact part bought (LCSC C5149201). D1-D6 are
      mounted from the bottom.
  [ ] Module pinout and size come from Waveshare's drawings; clones can differ.
  [ ] Bottom-side rotations: check every bottom part in JLCPCB's placement preview.
"""
    path = Path(path)
    path.write_text(text)
    return path


def main() -> None:
    pos, out = Path(sys.argv[1]), Path(sys.argv[2])
    parts = circuit.parts()
    write_bom(parts, out / "bom-jlcpcb.csv")
    write_cpl(pos, out / "cpl-jlcpcb.csv", parts)
    write_hand_parts(parts, out / "hand-parts.csv")
    write_readme(out / "README.txt")


if __name__ == "__main__":
    main()
