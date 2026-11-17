#!/usr/bin/env python3
"""Builds atelier-he.kicad_pcb from circuit.py with KiCad's pcbnew API
(adapted from hardware/rev1/gen_pcb.py).

Run inside the KiCad container (scripts/he.sh does that):

    gen_pcb.py place    outline, footprints, nets, ground zones, art; no tracks
    gen_pcb.py fill     refill zones
"""
from __future__ import annotations

import sys
from pathlib import Path

import pcbnew

import circuit
import gen_sch

HERE = Path(__file__).resolve().parent
BOARD = HERE / "atelier-he.kicad_pcb"
LIBS = HERE.parent / "libs"
STOCK_FP = Path("/usr/share/kicad/footprints")
STOCK_SYM = Path("/usr/share/kicad/symbols")
LOCAL_FP = {"local": LIBS / "local", "he_art": HERE / "art"}
ART_FOOTPRINT = "he_art:ART_moon_sea_F"

mm = pcbnew.FromMM


def pt(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def outline_points() -> list[tuple]:
    """Rounded rectangle as ('line', a, b) and ('arc', start, mid, end)."""
    x0, y0, x1, y1 = circuit.OUTLINE
    r = circuit.OUTLINE_RADIUS
    k = r * (1 - 2 ** -0.5)
    return [
        ("line", (x0 + r, y0), (x1 - r, y0)),
        ("arc", (x1 - r, y0), (x1 - k, y0 + k), (x1, y0 + r)),
        ("line", (x1, y0 + r), (x1, y1 - r)),
        ("arc", (x1, y1 - r), (x1 - k, y1 - k), (x1 - r, y1)),
        ("line", (x1 - r, y1), (x0 + r, y1)),
        ("arc", (x0 + r, y1), (x0 + k, y1 - k), (x0, y1 - r)),
        ("line", (x0, y1 - r), (x0, y0 + r)),
        ("arc", (x0, y0 + r), (x0 + k, y0 + k), (x0 + r, y0)),
    ]


def add_outline(board) -> None:
    for kind, *p in outline_points():
        s = pcbnew.PCB_SHAPE(board)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        if kind == "line":
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(pt(*p[0]))
            s.SetEnd(pt(*p[1]))
        else:
            s.SetShape(pcbnew.SHAPE_T_ARC)
            s.SetArcGeometry(pt(*p[0]), pt(*p[1]), pt(*p[2]))
        board.Add(s)


def load_footprint(fpid: str):
    lib, name = fpid.split(":")
    path = LOCAL_FP.get(lib, STOCK_FP / f"{lib}.pretty")
    fp = pcbnew.FootprintLoad(str(path), name)
    if fp is None:
        raise SystemExit(f"footprint not found: {fpid} in {path}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def place_part(board, fp, x, y, rot, side) -> None:
    board.Add(fp)  # must be on a board before Flip, or pcbnew crashes
    fp.SetPosition(pt(x, y))
    if side == "B":
        fp.Flip(pt(x, y), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        rot += 180
    fp.SetOrientationDegrees(rot)


def add_zone(board, net, layer, points, keepout=False, name=""):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    poly = z.Outline()
    poly.NewOutline()
    for x, y in points:
        poly.Append(mm(x), mm(y))
    if keepout:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
    else:
        z.SetNetCode(net.GetNetCode())
        z.SetLocalClearance(mm(0.25))
        z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.25))
        z.SetThermalReliefSpokeWidth(mm(0.3))
    if name:
        z.SetZoneName(name)
    board.Add(z)
    return z


def silk_text(board, s, x, y, layer, size=1.2):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetLayer(layer)
    t.SetPosition(pt(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * 0.15))
    t.SetItalic(True)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)
    return t


def board_only(board, fpid, ref, value, x, y, side="F"):
    fp = load_footprint(fpid)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM
                     | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    fp.Reference().SetVisible(False)
    place_part(board, fp, x, y, 0, side)
    return fp


def place() -> None:
    board = pcbnew.NewBoard(str(BOARD))
    board.GetDesignSettings().SetBoardThickness(mm(circuit.THICKNESS))
    add_outline(board)

    nets = {}

    def net_of(name):
        if name not in nets:
            nets[name] = pcbnew.NETINFO_ITEM(board, name)
            board.Add(nets[name])
        return nets[name]

    for p in circuit.parts():
        fp = load_footprint(p.footprint)
        fp.SetReference(p.ref)
        fp.SetValue(p.value)
        fp.SetPath(pcbnew.KIID_PATH("/" + gen_sch.symbol_uuid(p.ref)))
        symbol = gen_sch.load_symbol(p.symbol, STOCK_SYM)
        table = gen_sch.pins_of(symbol)
        names = gen_sch.pin_names(symbol)
        for prop in gen_sch.find_all(symbol, "property"):
            if prop[1] not in ("Reference", "Value", "Footprint", "private") and not str(prop[1]).startswith("ki_"):
                fp.SetField(str(prop[1]), str(prop[2]))
                fp.GetField(str(prop[1])).SetVisible(False)
        # sensors sit under the switches, where their labels only collide with their own capacitors
        fp.Reference().SetVisible(p.ref.startswith(("U", "J", "SW", "TP")) and not p.symbol.startswith("Sensor_Magnetic:"))
        by_number = {}
        for pin, net in p.pins.items():
            number, name = table[pin][0], names[table[pin][0]]
            label = f"{p.ref}-Pad{number}" if name in ("", "~", number) else f"{p.ref}-{name}-Pad{number}"
            by_number[number] = net or f"unconnected-({label})"
        pad_numbers = {pad.GetNumber() for pad in fp.Pads() if pad.GetNumber()}
        if pad_numbers != set(by_number):
            raise SystemExit(f"{p.ref}: footprint pads {sorted(pad_numbers)} != symbol pins {sorted(by_number)}")
        small = p.footprint.split(":")[1].startswith(("SOT-23", "LQFP"))
        for pad in fp.Pads():
            net = by_number.get(pad.GetNumber())
            if net:
                pad.SetNet(net_of(net))
                if small and net == "GND":
                    # fine-pitch pads have no room for two thermal spokes each
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        place_part(board, fp, p.x, p.y, p.rot, p.side)

    for i, (x, y) in enumerate(circuit.HOLES, start=1):
        board_only(board, circuit.HOLE_FOOTPRINT, f"H{i}", "M3 nylon", x, y)
    for key in circuit.KEY_ORDER:
        board_only(board, circuit.SWITCH_FOOTPRINT, f"SW_{key}", "Gateron Magnetic Jade", *circuit.KEYS[key])

    # Ground on both layers; none on the top in the art zone, so the art copper stays its own.
    x0, y0, x1, y1 = circuit.OUTLINE
    box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        add_zone(board, net_of("GND"), layer, box, name="GND")
    ax0, ay0, ax1, ay1 = circuit.ART_ZONE
    add_zone(board, None, pcbnew.F_Cu, [(ax0, ay0), (ax1, ay0), (ax1, ay1), (ax0, ay1)], keepout=True, name="art")

    art = HERE / "art" / (ART_FOOTPRINT.split(":")[1] + ".kicad_mod")
    if art.exists():
        board_only(board, ART_FOOTPRINT, "ART1", "moon over the sea", (ax0 + ax1) / 2, (ay0 + ay1) / 2)

    labels(board)
    pcbnew.SaveBoard(str(BOARD), board)
    print("wrote", BOARD, "with", len(board.GetFootprints()), "footprints and", len(nets), "nets")


def labels(board) -> None:
    """Board-level silkscreen, kept clear of pads and holes (DRC: silk_over_copper)."""
    silk_text(board, "ATELIER rev 2.0  ·  HE", 100.0, 125.6, pcbnew.F_SilkS, 1.6)
    silk_text(board, "00:00", circuit.KEYS["K2"][0] + 7.6, circuit.KEYS["K2"][1] - 7.9, pcbnew.F_SilkS, 0.8)  # under the keycap rim
    silk_text(board, "26.05.2022", 100.0, 150.2, pcbnew.B_SilkS, 0.8)
    # BOOT hint right under SW3, in the free strip between its pads and C28/Y1.
    sw3 = next(p for p in circuit.parts() if p.ref == "SW3")
    silk_text(board, "BOOT", sw3.x, sw3.y + 5.3, pcbnew.B_SilkS, 1.0)
    silk_text(board, "hold while plugging in", sw3.x, sw3.y + 6.7, pcbnew.B_SilkS, 0.8)
    # Test-point labels stand upright above their pads: side by side at 2.5 mm they overlap.
    for fp in board.GetFootprints():
        if fp.GetReference().startswith("TP"):
            ref = fp.Reference()
            ref.SetTextAngleDegrees(90)
            ref.SetPosition(pt(pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y) - 2.4))


def refill(board) -> None:
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def main(argv: list[str]) -> None:
    if argv[:1] == ["place"]:
        place()
    elif argv[:1] == ["fill"]:
        board = pcbnew.LoadBoard(str(BOARD))
        refill(board)
        pcbnew.SaveBoard(str(BOARD), board)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
