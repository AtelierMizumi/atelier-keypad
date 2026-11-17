#!/usr/bin/env python3
"""Writes atelier6k-rev1.kicad_sch from circuit.py.

Needs the KiCad symbol libraries, so run it inside the KiCad container
(scripts/rev1.sh does that). Standard library only.

Every pin gets a short wire and a global label carrying its net name, so the
netlist is exactly circuit.py; the drawing is a parts list with named pins
rather than a hand-drawn schematic.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import circuit
from sexpr import Q, dump, find, find_all, parse

HERE = Path(__file__).resolve().parent
OUT = HERE / "atelier6k-rev1.kicad_sch"
PROJECT = "atelier6k-rev1"
NS = uuid.UUID("6f0c8a4e-41a6-4b6b-9d57-a7e1166b0001")
STUB = 2.54


def uid(key: str) -> Q:
    return Q(str(uuid.uuid5(NS, key)))


ROOT = uid("root-sheet")


def symbol_uuid(ref: str) -> str:
    return str(uuid.uuid5(NS, "symbol:" + ref))


# ---------------------------------------------------------------- libraries

def library_file(lib: str, stock: Path) -> Path:
    if lib == "atelier":
        return HERE.parent / "libs" / "local" / "atelier.kicad_sym"
    return stock / f"{lib}.kicad_sym"


_lib_cache: dict[str, list] = {}


def load_symbol(lib_id: str, stock: Path) -> list:
    """The library symbol with any `extends` parent merged in, named `Lib:Name`."""
    lib, name = lib_id.split(":")
    if lib not in _lib_cache:
        _lib_cache[lib] = parse(library_file(lib, stock).read_text())
    symbols = {s[1]: s for s in find_all(_lib_cache[lib], "symbol")}
    sym = symbols[name]
    ext = find(sym, "extends")
    if ext is not None:
        parent = load_symbol(f"{lib}:{ext[1]}", stock)
        parent_name = ext[1]
        merged = [c for c in parent[2:] if not (isinstance(c, list) and c[0] == "property")]
        own_props = {p[1]: p for p in find_all(sym, "property")}
        props = [own_props.pop(p[1], p) for p in find_all(parent, "property")] + list(own_props.values())
        body = []
        for c in merged:
            if isinstance(c, list) and c[0] == "symbol":
                c = ["symbol", Q(name + c[1][len(parent_name):])] + c[2:]
            body.append(c)
        units = [c for c in body if isinstance(c, list) and c[0] == "symbol"]
        rest = [c for c in body if c not in units]
        sym = ["symbol", Q(name)] + rest + props + units
    return ["symbol", Q(lib_id)] + [c for c in sym[2:] if not (isinstance(c, list) and c[0] == "extends")]


def pins_of(sym: list) -> dict[str, tuple[str, float, float, int]]:
    """name-or-number -> (number, x, y, angle) for unit 1 (and the shared unit 0)."""
    table: dict[str, tuple[str, float, float, int]] = {}
    for unit in find_all(sym, "symbol"):
        for pin in find_all(unit, "pin"):
            at = find(pin, "at")
            number = str(find(pin, "number")[1])
            name = str(find(pin, "name")[1])
            entry = (number, float(at[1]), float(at[2]), int(float(at[3])) if len(at) > 3 else 0)
            table[number] = entry
            if name and name != "~":
                table.setdefault(name, entry)
    return table


def pin_names(sym: list) -> dict[str, str]:
    """pin number -> pin name."""
    return {str(find(pin, "number")[1]): str(find(pin, "name")[1])
            for unit in find_all(sym, "symbol") for pin in find_all(unit, "pin")}


# ------------------------------------------------------------------ drawing

FONT = ["effects", ["font", ["size", 1.27, 1.27]]]
OUTWARD = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}  # schematic y points down
LABEL_ANGLE = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}


def wire(a, b, key) -> list:
    return ["wire", ["pts", ["xy", a[0], a[1]], ["xy", b[0], b[1]]],
            ["stroke", ["width", 0], ["type", "default"]], ["uuid", uid("wire:" + key)]]


def label(net: str, at, direction, key) -> list:
    angle = LABEL_ANGLE[direction]
    justify = "right" if angle == 180 else "left"
    return ["global_label", Q(net), ["shape", "passive"], ["at", at[0], at[1], angle],
            ["effects", ["font", ["size", 1.27, 1.27]], ["justify", justify]],
            ["uuid", uid("label:" + key)],
            ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", 0, 0, 0],
             ["effects", ["font", ["size", 1.27, 1.27]], ["hide", "yes"]]]]


def text(s: str, x, y, size=1.8) -> list:
    return ["text", Q(s), ["exclude_from_sim", "no"], ["at", x, y, 0],
            ["effects", ["font", ["size", size, size]], ["justify", "left", "bottom"]], ["uuid", uid("text:" + s)]]


def instance(lib_sym: list, lib_id: str, ref: str, value: str, footprint: str, x: float, y: float, key: str) -> list:
    props = []
    overrides = {"Reference": ref, "Value": value, "Footprint": footprint}
    for p in find_all(lib_sym, "property"):
        name = str(p[1])
        if name.startswith("ki_"):
            continue  # library search metadata, not a field of the placed symbol
        at = find(p, "at")
        new = ["property", Q(name), Q(overrides.get(name, p[2])),
               ["at", x + float(at[1]), y - float(at[2]), 0]]
        hidden = name not in ("Reference", "Value") or ref.startswith("#")
        if hidden:
            new.append(["hide", "yes"])
        new.append(FONT)
        props.append(new)
    pins = [["pin", Q(n), ["uuid", uid(f"pin:{key}:{n}")]]
            for n in sorted({v[0] for v in pins_of(lib_sym).values()})]
    return (["symbol", ["lib_id", Q(lib_id)], ["at", x, y, 0], ["unit", 1],
             ["exclude_from_sim", "no"], ["in_bom", "no" if ref.startswith("#") else "yes"], ["on_board", "yes"],
             ["dnp", "no"], ["uuid", Q(symbol_uuid(ref))]]
            + props + pins
            + [["instances", ["project", Q(PROJECT), ["path", Q("/" + ROOT), ["reference", Q(ref)], ["unit", 1]]]]])


# ------------------------------------------------------------------- layout

def layout() -> dict[str, tuple[float, float]]:
    """Schematic position of every part, on a 2.54 mm grid."""
    pos = {"U1": (71.12, 91.44), "F1": (139.7, 50.8), "C11": (160.02, 53.34),
           "U2": (139.7, 91.44), "C12": (116.84, 91.44), "R1": (175.26, 91.44)}
    for i in range(6):
        pos[f"MX{i + 1}"] = (228.6 + (i % 3) * 43.18, 50.8 + (i // 3) * 20.32)
    for i in range(3):
        pos[f"SW{i + 1}"] = (228.6 + i * 43.18, 96.52)
    for i in range(10):
        x, y = 50.8 + (i % 5) * 68.58, 160.02 + (i // 5) * 50.8
        pos[f"D{i + 1}"] = (x, y)
        pos[f"C{i + 1}"] = (x + 30.48, y)
    return pos


def build(stock: Path) -> list:
    parts = circuit.parts()
    pos = layout()
    lib_ids = sorted({p.symbol for p in parts} | {"power:PWR_FLAG"})
    libs = {lib_id: load_symbol(lib_id, stock) for lib_id in lib_ids}

    items: list = []
    for p in parts:
        sym = libs[p.symbol]
        table = pins_of(sym)
        x, y = pos[p.ref]
        items.append(instance(sym, p.symbol, p.ref, p.value, p.footprint, x, y, p.ref))
        used = set()
        for pin, net in p.pins.items():
            number, px, py, angle = table[pin]
            used.add(number)
            end = (x + px, y - py)
            d = OUTWARD[angle]
            if net is None:
                items.append(["no_connect", ["at", end[0], end[1]], ["uuid", uid(f"nc:{p.ref}:{number}")]])
                continue
            tip = (end[0] + d[0] * STUB, end[1] + d[1] * STUB)
            items.append(wire(end, tip, f"{p.ref}:{number}"))
            items.append(label(net, tip, d, f"{p.ref}:{number}"))
        missing = {v[0] for v in table.values()} - used
        if missing:
            raise SystemExit(f"{p.ref}: circuit.py does not say what pins {sorted(missing)} connect to")

    # The fused rail and ground have no power-output pin; tell ERC they are driven.
    flag = libs["power:PWR_FLAG"]
    for i, (net, fx) in enumerate((("+5V", 177.8), ("GND", 193.04)), start=1):
        fy = 50.8
        items.append(instance(flag, "power:PWR_FLAG", f"#FLG0{i}", "PWR_FLAG", "", fx, fy, f"flag{i}"))
        items.append(wire((fx, fy), (fx, fy + STUB), f"flag{i}"))
        items.append(label(net, (fx, fy + STUB), (0, 1), f"flag{i}"))

    notes = [
        ("Atelier6K rev 1 - generated from hardware/rev1/circuit.py; edit that file, not this sheet", 25.4, 22.86, 2.5),
        ("MCU module: 9 keys on direct pins (switch to GND, internal pull-ups), LED data on one pin", 25.4, 35.56, 1.8),
        ("5 V for the LEDs: polyfuse, then bulk capacitor", 127.0, 35.56, 1.8),
        ("3.3 V -> 5 V LED data", 127.0, 76.2, 1.8),
        ("Keys MX1-MX6 (hot-swap) and buttons SW1-SW3", 215.9, 35.56, 1.8),
        ("LED chain: D1-D6 under the keys (serpentine), D7-D10 underglow; one 100 nF per LED", 25.4, 139.7, 1.8),
    ]
    items += [text(s, x, y, size) for s, x, y, size in notes]

    return (["kicad_sch", ["version", 20260306], ["generator", Q("atelier6k_gen_sch")], ["generator_version", Q("10.0")],
             ["uuid", ROOT], ["paper", Q("A3")],
             ["title_block", ["title", Q("Atelier6K")], ["rev", Q("1")], ["company", Q("AtelierMizumi")],
              ["comment", 1, Q("Generated; not yet built or tested on hardware")]],
             ["lib_symbols"] + [libs[i] for i in lib_ids]]
            + items
            + [["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]])


if __name__ == "__main__":
    stock = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/usr/share/kicad/symbols")
    OUT.write_text(dump(build(stock)) + "\n")
    print("wrote", OUT)
