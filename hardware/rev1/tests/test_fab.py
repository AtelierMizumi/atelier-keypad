"""The rev 1 production package (scripts/fab.sh rev1 -> build/fab/rev1/).

    scripts/fab.sh rev1 && (cd hardware/rev1 && uv run --no-project --with pytest pytest -q tests/test_fab.py)

The BOM checks run on circuit.py alone. The package checks need the package:
they skip when it has not been built, unless FAB_REQUIRED=1 (CI sets it).
"""
import csv
import os
import subprocess
from pathlib import Path

import pytest

import circuit
import fab

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "build" / "fab" / "rev1"
UF2 = ROOT / "firmware" / "build" / "atelier6k_default.uf2"
needs_pkg = pytest.mark.skipif(not PKG.exists() and os.environ.get("FAB_REQUIRED") != "1",
                               reason="package not built (scripts/fab.sh rev1)")


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def designators(rows):
    return sorted(d.strip() for r in rows for d in r["Designator"].split(","))


@pytest.fixture(scope="module")
def bom(tmp_path_factory):
    return read(fab.write_bom(circuit.parts(), tmp_path_factory.mktemp("bom") / "bom-jlcpcb.csv"))


@pytest.fixture(scope="module")
def hand(tmp_path_factory):
    return read(fab.write_hand_parts(circuit.parts(), tmp_path_factory.mktemp("hand") / "hand-parts.csv"))


def test_hand_placed_are_the_module_switches_and_buttons():
    assert circuit.HAND_PLACED == {"U1", *circuit.KEYS, *circuit.BUTTONS}


def test_every_machine_part_has_an_lcsc_number():
    missing = sorted({(p.ref, p.value) for p in circuit.machine_parts(circuit.parts())
                      if not circuit.lcsc(p).startswith("C")})
    assert missing == []


def test_lcsc_numbers_match_rev2_for_the_same_part():
    # rev 1 uses only parts already verified for rev 2.0; same part -> same number
    assert circuit.LCSC[("SK6812MINI-E", "LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount")] == "C5149201"
    assert circuit.LCSC[("74AHCT1G125", "SOT-23-5_HandSoldering")] == "C12494"
    assert circuit.LCSC[("500mA", "Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder")] == "C151162"


def test_bom_has_jlcpcb_columns(bom):
    assert list(bom[0].keys()) == ["Comment", "Designator", "Footprint", "LCSC"]


def test_bom_counts_every_machine_part_and_no_hand_part(bom):
    refs = designators(bom)
    assert refs == sorted(p.ref for p in circuit.machine_parts(circuit.parts()))
    assert not set(refs) & circuit.HAND_PLACED


def test_hand_parts_list_the_module_6_sockets_and_3_buttons(hand):
    assert list(hand[0].keys()) == ["Part", "Designator", "Qty", "Source"]
    qty = {r["Part"]: int(r["Qty"]) for r in hand}
    assert qty == {"RP2040-Zero": 1, "MX hot-swap": 6, "6x6 tact": 3}
    assert designators(hand) == sorted(circuit.HAND_PLACED)


def test_fab_sh_rejects_unknown_revision():
    run = subprocess.run([str(ROOT / "scripts" / "fab.sh"), "rev3"], capture_output=True, text=True)
    assert run.returncode != 0
    assert "unknown revision" in run.stderr
    assert not (ROOT / "build" / "fab" / "rev3").exists()


@needs_pkg
def test_cpl_designators_match_bom():
    cpl = read(PKG / "cpl-jlcpcb.csv")
    assert list(cpl[0].keys()) == ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
    assert sorted(r["Designator"] for r in cpl) == designators(read(PKG / "bom-jlcpcb.csv"))


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
def test_gerber_sets_are_complete():
    names = " ".join(f.name for f in (PKG / "gerbers").iterdir())
    for layer in ("F_Cu", "B_Cu", "F_Mask", "B_Mask", "F_Silkscreen", "B_Silkscreen",
                  "F_Paste", "B_Paste", "Edge_Cuts"):
        assert layer in names, layer
    assert "-PTH.drl" in names and "-NPTH.drl" in names
    plate = " ".join(f.name for f in (PKG / "plate-gerbers").iterdir())
    # Empty copper layers and a drill file too: the fab house reads the layer count
    # from the copper Gerbers and expects a drill file in every order.
    for layer in ("Edge_Cuts", "F_Mask", "B_Mask", "F_Cu", "B_Cu"):
        assert layer in plate, layer
    assert ".drl" in plate
    assert not (PKG / "plate-src").exists()


@needs_pkg
def test_case_dxf_is_the_three_acrylic_layers():
    dxf = sorted(f.name for f in (PKG / "case-dxf").glob("*.dxf"))
    assert len(dxf) == 3
    assert not [n for n in dxf if "plate" in n or "-all" in n]


@needs_pkg
def test_fab_readme_states_board_plate_and_open_checks():
    text = (PKG / "README.txt").read_text()
    for needle in ("1.6 mm", "2 layers", "plate", "notch", "LED pinout", "module",
                   "no copper, outline only"):   # the order remark for the plate
        assert needle in text, needle


@needs_pkg
def test_package_firmware_is_optional():
    assert (PKG / "firmware.uf2").exists() == UF2.exists()
