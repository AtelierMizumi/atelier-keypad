"""The rev 1 production package (scripts/fab.sh rev1 -> build/fab/rev1/).

    scripts/fab.sh rev1 && (cd hardware/rev1 && uv run --no-project --with pytest pytest -q tests/test_fab.py)

The BOM checks run on circuit.py alone. The package checks need the package:
they skip when it has not been built, unless FAB_REQUIRED=1 (CI sets it).
"""
import circuit


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
