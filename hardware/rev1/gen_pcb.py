#!/usr/bin/env python3
"""Builds atelier6k-rev1.kicad_pcb from circuit.py with KiCad's pcbnew API.

Run inside the KiCad container (scripts/rev1.sh does that):

    gen_pcb.py place            outline, footprints, nets, ground zones; no tracks
    gen_pcb.py dsn  OUT.dsn     export for the autorouter
    gen_pcb.py ses  IN.ses      import the routed session, refill zones
"""
from __future__ import annotations

import sys
from pathlib import Path

import pcbnew

import circuit
import gen_sch

HERE = Path(__file__).resolve().parent
BOARD = HERE / "atelier6k-rev1.kicad_pcb"
LIBS = HERE.parent / "libs"
STOCK_FP = Path("/usr/share/kicad/footprints")
STOCK_SYM = Path("/usr/share/kicad/symbols")
LOCAL_FP = {"local": LIBS / "local", "MX_Only": LIBS / "MX_Alps_Hybrid" / "MX_Only.pretty"}

mm = pcbnew.FromMM


def pt(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def outline_points() -> list[tuple]:
    """Board edge as ('line', a, b) and ('arc', start, mid, end), with the notch under the module."""
    x0, y0, x1, y1 = circuit.OUTLINE
    r = circuit.OUTLINE_RADIUS
    k = r * (1 - 2 ** -0.5)  # arc midpoint offset from the corner
    nw, nd = circuit.MODULE_NOTCH
    nl, nr = circuit.MODULE_X - nw / 2, circuit.MODULE_X + nw / 2
    return [
        ("line", (x0 + r, y0), (nl, y0)), ("line", (nl, y0), (nl, y0 + nd)),
        ("line", (nl, y0 + nd), (nr, y0 + nd)), ("line", (nr, y0 + nd), (nr, y0)),
        ("line", (nr, y0), (x1 - r, y0)),
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
        # pcbnew's bottom-side footprint at 0 degrees is the top view mirrored in y.
        # This design wants parts mirrored in x (as if the board were turned over
        # sideways), which is the same thing rotated by 180 degrees.
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
        z.SetLocalClearance(mm(0.3))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.5))
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
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


def place() -> None:
    board = pcbnew.NewBoard(str(BOARD))
    board.GetDesignSettings().SetBoardThickness(mm(circuit.THICKNESS))
    add_outline(board)

    nets = {}
    for p in circuit.parts():
        for net in p.pins.values():
            if net and net not in nets:
                nets[net] = pcbnew.NETINFO_ITEM(board, net)
                board.Add(nets[net])

    for p in circuit.parts():
        fp = load_footprint(p.footprint)
        fp.SetReference(p.ref)
        fp.SetValue(p.value)
        fp.SetPath(pcbnew.KIID_PATH("/" + gen_sch.symbol_uuid(p.ref)))
        symbol = gen_sch.load_symbol(p.symbol, STOCK_SYM)
        table = gen_sch.pins_of(symbol)
        names = gen_sch.pin_names(symbol)
        for prop in gen_sch.find_all(symbol, "property"):
            if prop[1] in ("Datasheet", "Description"):  # keep the parity check quiet
                fp.SetField(str(prop[1]), str(prop[2]))
                fp.GetField(str(prop[1])).SetVisible(False)
        if p.ref.startswith("C") and p.value == "100nF":
            fp.Reference().SetVisible(False)  # no room for it next to the LED cut-out
        by_number = {}
        for pin, net in p.pins.items():
            number, name = table[pin][0], names[table[pin][0]]
            # KiCad's name for the net of an unconnected pin, so the parity check agrees.
            label = f"{p.ref}-Pad{number}" if name in ("", "~", number) else f"{p.ref}-{name}-Pad{number}"
            by_number[number] = net or f"unconnected-({label})"
        pad_numbers = {pad.GetNumber() for pad in fp.Pads() if pad.GetNumber()}
        if pad_numbers != set(by_number):
            raise SystemExit(f"{p.ref}: footprint pads {sorted(pad_numbers)} != symbol pins {sorted(by_number)}")
        for pad in fp.Pads():
            net = by_number.get(pad.GetNumber())
            if net:
                if net not in nets:
                    nets[net] = pcbnew.NETINFO_ITEM(board, net)
                    board.Add(nets[net])
                pad.SetNet(nets[net])
                if p.ref == "U2" and net == "GND":
                    # SOT-23-5 pads are too close together for two thermal spokes each
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        place_part(board, fp, p.x, p.y, p.rot, p.side)

    for i, (x, y) in enumerate(circuit.HOLES, start=1):
        fp = load_footprint(circuit.HOLE_FOOTPRINT)
        fp.SetReference(f"H{i}")
        fp.SetValue("M3")
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM
                         | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        fp.Reference().SetVisible(False)
        place_part(board, fp, x, y, 0, "F")

    # Ground on both layers.
    x0, y0, x1, y1 = circuit.OUTLINE
    box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        add_zone(board, nets["GND"], layer, box, name="GND")

    # No copper where the module's underside test pads rest on this board.
    nw, nd = circuit.MODULE_NOTCH
    inner = circuit.MODULE_WIDTH / 2 - 1.38 - 0.6 - 1.3 - 0.25  # just inside the edge pads
    for sign in (-1, 1):
        a, b = circuit.MODULE_X + sign * nw / 2, circuit.MODULE_X + sign * inner
        add_zone(board, None, pcbnew.B_Cu, [(a, y0), (b, y0), (b, y0 + nd), (a, y0 + nd)],
                 keepout=True, name="module underside pads")

    check_module(board)
    silk_text(board, "Atelier6K rev 1", 157.48, 131.6, pcbnew.F_SilkS, 1.5)
    silk_text(board, "Atelier6K rev 1", 157.48, 131.6, pcbnew.B_SilkS, 1.5)
    silk_text(board, "RP2040-Zero", 174.0, 74.0, pcbnew.B_SilkS, 1.0)
    pcbnew.SaveBoard(str(BOARD), board)
    print("wrote", BOARD, "with", len(board.GetFootprints()), "footprints and", len(nets), "nets")


def check_module(board) -> None:
    """The module is under the board: seen from the top its GP0 column is on the left, 5V top right."""
    pads = {p.GetNumber(): p.GetPosition() for p in board.FindFootprintByReference("U1").Pads()}
    top = circuit.OUTLINE[1]
    ok = (pcbnew.ToMM(pads["GP0"].x) < circuit.MODULE_X < pcbnew.ToMM(pads["5V"].x)
          and abs(pcbnew.ToMM(pads["5V"].y) - (top + 1.59)) < 0.01
          and abs(pcbnew.ToMM(pads["GP9"].x) - (circuit.MODULE_X - 5.08)) < 0.01
          and pcbnew.ToMM(pads["GP11"].y) > top + 21)
    if not ok:
        raise SystemExit("module pads are not where a bottom-mounted RP2040-Zero needs them")


def refill(board) -> None:
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def main(argv: list[str]) -> None:
    if argv[:1] == ["place"]:
        place()
    elif argv[:1] == ["dsn"]:
        board = pcbnew.LoadBoard(str(BOARD))
        if not pcbnew.ExportSpecctraDSN(board, argv[1]):
            raise SystemExit("DSN export failed")
    elif argv[:1] == ["ses"]:
        board = pcbnew.LoadBoard(str(BOARD))
        if not pcbnew.ImportSpecctraSES(board, argv[1]):
            raise SystemExit("SES import failed")
        refill(board)
        pcbnew.SaveBoard(str(BOARD), board)
    elif argv[:1] == ["fill"]:
        board = pcbnew.LoadBoard(str(BOARD))
        refill(board)
        pcbnew.SaveBoard(str(BOARD), board)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
