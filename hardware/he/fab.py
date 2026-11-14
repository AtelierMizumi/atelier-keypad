#!/usr/bin/env python3
"""BOM, placement and README for the rev 2.0 production package, in JLCPCB's formats.

    python3 fab.py <kicad pos csv> <out dir>      # called by scripts/fab.sh

The BOM comes from circuit.py (the source of truth), the placement from KiCad's
position file (where the parts really are on the routed board).
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import circuit


def bom_parts(parts):
    """Parts that get soldered: everything placed except test points (bare pads)."""
    return [p for p in parts if not p.ref.startswith("TP")]


def _ref_key(ref: str):
    head = ref.rstrip("0123456789")
    return head, int(ref[len(head):] or 0)


def write_bom(parts, path: Path) -> Path:
    groups = defaultdict(list)
    for p in bom_parts(parts):
        groups[(p.value, p.footprint.split(":")[-1], circuit.lcsc(p))].append(p.ref)
    path = Path(path)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC"])
        for (value, fp, lcsc), refs in sorted(groups.items(), key=lambda g: _ref_key(min(g[1], key=_ref_key))):
            w.writerow([value, ",".join(sorted(refs, key=_ref_key)), fp, lcsc])
    return path


def write_cpl(pos_csv: Path, path: Path, parts) -> Path:
    """KiCad pos CSV (Ref,Val,Package,PosX,PosY,Rot,Side) -> JLCPCB CPL, BOM parts only."""
    keep = {p.ref for p in bom_parts(parts)}
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


def write_readme(path: Path) -> Path:
    x0, y0, x1, y1 = circuit.OUTLINE
    text = f"""Atelier rev 2.0 (Hall effect) - production package

PCB
  2 layers, FR-4, {circuit.THICKNESS:g} mm thick ({circuit.THICKNESS:g} mm is required: the Hall sensors
  read the switch magnets through the board), 1 oz copper, lead-free HASL,
  any mask colour, white silkscreen. Size {x1 - x0:g} x {y1 - y0:g} mm, 5 pcs.
  Parts on both sides; 1.75 mm NPTH switch pegs, 3.2 mm NPTH screw holes.

Files
  gerbers/          Gerber X2 + Excellon drill (PTH and NPTH separate)
  bom-jlcpcb.csv    Comment, Designator, Footprint, LCSC
  cpl-jlcpcb.csv    Designator, Mid X, Mid Y, Layer, Rotation (KiCad origin, Y up)
  case-dxf/         laser-cut acrylic, one file per layer (thickness and colour in the name)
  firmware.bin      libhmk build, if the firmware job ran

Ordering and sourcing: docs/build/ordering.md in the repository.
"""
    path = Path(path)
    path.write_text(text)
    return path


def main() -> None:
    pos, out = Path(sys.argv[1]), Path(sys.argv[2])
    parts = circuit.parts()
    write_bom(parts, out / "bom-jlcpcb.csv")
    write_cpl(pos, out / "cpl-jlcpcb.csv", parts)
    write_readme(out / "README.txt")


if __name__ == "__main__":
    main()
