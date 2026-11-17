"""Totals for hardware/he/bom.csv (prices in VND).

    python3 budget.py ../../hardware/he/bom.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path


def rows(path: Path) -> list[dict[str, str]]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def totals(path: Path) -> dict[str, int]:
    out = {"low": 0, "high": 0, "plan": 0}
    for r in rows(path):
        q = int(r["qty"])
        out["low"] += q * int(r["unit_vnd_low"])
        out["high"] += q * int(r["unit_vnd_high"])
        out["plan"] += q * int(r["plan_vnd"])
    return out


if __name__ == "__main__":
    t = totals(Path(sys.argv[1]))
    print(" ".join(f"{k}={v:,} VND" for k, v in t.items()))
