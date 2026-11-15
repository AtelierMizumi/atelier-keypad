"""Every laser-cut DXF carries a 50 mm scale bar, so a shop can check the scale
before cutting. tokaku's keypad case came back tiny from an export at the wrong
scale (docs/superpowers/specs/2026-11-16-rev2-flat-case-grip.md, D4)."""
import math
from pathlib import Path

import ezdxf
import pytest

ROOT = Path(__file__).resolve().parents[2]
DXF = sorted(p for d in ("dxf", "dxf-rev1", "dxf-he") for p in (ROOT / "case" / d).glob("*.dxf"))


def test_there_are_dxf_files():
    assert len(DXF) >= 15


@pytest.mark.parametrize("path", DXF, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_dxf_is_in_mm_with_a_50_mm_scale_bar(path):
    doc = ezdxf.readfile(path)
    assert doc.header.get("$INSUNITS") == 4, "units must be millimetres"
    bars = [e for e in doc.modelspace().query("LINE") if e.dxf.layer == "NOTES"]
    assert len(bars) == 1
    s, e = bars[0].dxf.start, bars[0].dxf.end
    assert math.dist((s.x, s.y), (e.x, e.y)) == pytest.approx(50.0, abs=1e-6)
    texts = [t.dxf.text for t in doc.modelspace().query("TEXT") if t.dxf.layer == "NOTES"]
    assert any("50 mm, check before cutting" in t for t in texts)


@pytest.mark.parametrize("path", DXF, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_scale_bar_is_on_a_notes_layer(path):
    # Nothing that would be cut may sit on NOTES, and the bar is the only LINE there.
    doc = ezdxf.readfile(path)
    on_notes = {e.dxftype() for e in doc.modelspace() if e.dxf.layer == "NOTES"}
    assert on_notes <= {"LINE", "TEXT"}
