#!/usr/bin/env python3
"""Fails unless a KiCad netlist export of the schematic equals circuit.py."""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import circuit
import gen_sch
from sexpr import find, find_all, parse


def expected(stock: Path) -> dict[str, set]:
    nets = defaultdict(set)
    for p in circuit.parts():
        table = gen_sch.pins_of(gen_sch.load_symbol(p.symbol, stock))
        for pin, net in p.pins.items():
            if net:
                nets[net].add((p.ref, table[pin][0]))
    return dict(nets)


def exported(path: str) -> dict[str, set]:
    nets = {}
    for net in find_all(find(parse(Path(path).read_text()), "nets"), "net"):
        nodes = {(str(find(n, "ref")[1]), str(find(n, "pin")[1])) for n in find_all(net, "node")}
        nodes = {n for n in nodes if not n[0].startswith("#")}
        if len(nodes) > 1 or not str(find(net, "name")[1]).startswith("unconnected-"):
            nets[str(find(net, "name")[1])] = nodes
    return nets


if __name__ == "__main__":
    want = expected(Path("/usr/share/kicad/symbols"))
    got = exported(sys.argv[1])
    if want != got:
        for name in sorted(set(want) | set(got)):
            if want.get(name) != got.get(name):
                print(f"  {name}: circuit.py {sorted(want.get(name, []))} != schematic {sorted(got.get(name, []))}")
        raise SystemExit("netlist mismatch")
    print(f"   netlist matches circuit.py: {len(got)} nets, {sum(map(len, got.values()))} pins")
