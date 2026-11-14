"""The rev 2 budget: one unit, 1,000,000 VND including shipping."""
from pathlib import Path

import budget

BOM = Path(__file__).resolve().parents[3] / "hardware" / "he" / "bom.csv"
CAP_VND = 1_000_000


def test_planned_total_fits_the_cap():
    assert budget.totals(BOM)["plan"] <= CAP_VND


def test_worst_case_is_reported_honestly():
    t = budget.totals(BOM)
    assert t["low"] <= t["plan"] <= t["high"]


def test_every_line_says_how_sure_we_are():
    for row in budget.rows(BOM):
        assert row["confidence"] in {"found", "estimate", "unknown"}, row["item"]


def test_three_sensors_and_three_switches_at_least():
    rows = {r["item"]: int(r["qty"]) for r in budget.rows(BOM)}
    assert rows["TI DRV5056A4QDBZR linear Hall (SOT-23)"] >= 3
    assert rows["Gateron Magnetic Jade PCB-mount"] >= 3
