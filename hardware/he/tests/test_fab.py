"""The production package (scripts/fab.sh -> build/fab/rev2.0/).

    scripts/fab.sh && (cd hardware/he && uv run --no-project --with pytest pytest -q tests/test_fab.py)

The BOM checks run on circuit.py alone. The package checks need the package:
they skip when it has not been built, unless FAB_REQUIRED=1 (CI sets it).
"""
import csv
import os
from pathlib import Path

import pytest

import circuit
import fab

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "build" / "fab" / "rev2.0"
needs_pkg = pytest.mark.skipif(not PKG.exists() and os.environ.get("FAB_REQUIRED") != "1",
                               reason="package not built (scripts/fab.sh)")


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def bom(tmp_path_factory):
    path = tmp_path_factory.mktemp("bom") / "bom-jlcpcb.csv"
    fab.write_bom(circuit.parts(), path)
    return read(path)


def test_bom_has_jlcpcb_columns_and_every_part_has_lcsc(bom):
    assert list(bom[0].keys()) == ["Comment", "Designator", "Footprint", "LCSC"]
    missing = {r["Comment"] for r in bom if not r["LCSC"].startswith("C")}
    # Gate G1: the MCU's LCSC number is filled in once a listing is found.
    assert missing <= set(circuit.LCSC_PENDING) <= {"AT32F405CCT7"}


def test_bom_leaves_out_test_points_and_counts_every_placed_part(bom):
    refs = [d.strip() for r in bom for d in r["Designator"].split(",")]
    placed = [p.ref for p in circuit.parts() if not p.ref.startswith("TP")]
    assert sorted(refs) == sorted(placed)


@needs_pkg
def test_cpl_designators_match_bom():
    bom = read(PKG / "bom-jlcpcb.csv")
    cpl = read(PKG / "cpl-jlcpcb.csv")
    assert list(cpl[0].keys()) == ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
    refs = sorted(d.strip() for r in bom for d in r["Designator"].split(","))
    assert sorted(r["Designator"] for r in cpl) == refs


@needs_pkg
def test_cpl_bottom_parts_are_on_bottom_layer_with_board_coordinates():
    parts = {p.ref: p for p in circuit.parts()}
    for row in read(PKG / "cpl-jlcpcb.csv"):
        p = parts[row["Designator"]]
        assert row["Layer"] == ("Bottom" if p.side == "B" else "Top"), p.ref
        x, y = float(row["Mid X"].removesuffix("mm")), float(row["Mid Y"].removesuffix("mm"))
        # KiCad's placement file has Y pointing up: the same point as the Gerbers, not mirrored.
        assert (x, -y) == pytest.approx((p.x, p.y), abs=0.01), p.ref


@needs_pkg
def test_gerber_set_is_complete():
    names = " ".join(f.name for f in (PKG / "gerbers").iterdir())
    for layer in ("F_Cu", "B_Cu", "F_Mask", "B_Mask", "F_Silkscreen", "B_Silkscreen",
                  "F_Paste", "B_Paste", "Edge_Cuts"):
        assert layer in names, layer
    assert "-PTH.drl" in names and "-NPTH.drl" in names


@needs_pkg
def test_fab_readme_states_1p2_mm_two_layers():
    text = (PKG / "README.txt").read_text()
    assert "1.2 mm" in text and "2 layers" in text
    assert f"{circuit.THICKNESS:g} mm" in text


@needs_pkg
def test_case_dxf_files_are_in_the_package():
    assert len(list((PKG / "case-dxf").glob("*.dxf"))) == 5
