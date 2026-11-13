#!/usr/bin/env python3
"""Summarises kicad-cli ERC/DRC JSON reports; exits 1 if any has an error."""
import collections
import json
import sys

failed = False
for path in sys.argv[1:]:
    d = json.load(open(path))
    groups = {"violations": [v for s in d.get("sheets", []) for v in s["violations"]] + d.get("violations", []),
              "unconnected": d.get("unconnected_items", []), "parity": d.get("schematic_parity", [])}
    print(f"   {path}")
    for group, items in groups.items():
        count = collections.Counter((v["severity"], v["type"]) for v in items)
        if any(sev == "error" for sev, _ in count):
            failed = True
        print(f"     {group}: {len(items)}", dict(count) if items else "")
        if "-v" in sys.argv[0:1] or len(items) <= 6:
            for v in items:
                print("       -", v["description"], "|", "; ".join(i["description"] for i in v["items"]))
sys.exit(1 if failed else 0)
