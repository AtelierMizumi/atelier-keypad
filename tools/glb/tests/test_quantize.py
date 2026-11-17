"""Spec for quantizing a merged board GLB (KHR_mesh_quantization).

Float positions and normals are most of a board's GLB. Stored as normalized
int16 positions (offset and scale on the node) and int8 normals, the file
shrinks by about half and needs no decoder: model-viewer and three.js read
the extension natively. The board must still look the same: every vertex
within a micron, every normal within a degree or so.

    cd tools/glb && uv run --no-project --with pytest pytest -q
"""
import math
from pathlib import Path

import pytest

import merge
import quantize
from test_merge import tiny_glb

ROOT = Path(__file__).resolve().parents[3]
REV1 = ROOT / "site" / "assets" / "atelier6k-rev1.glb"


@pytest.fixture
def merged(tmp_path):
    src = tiny_glb(tmp_path)
    out = tmp_path / "merged.glb"
    merge.merge_file(src, out)
    return out


@pytest.fixture
def quantized(tmp_path, merged):
    out = tmp_path / "q.glb"
    quantize.quantize_file(merged, out)
    return out


def test_declares_the_extension_and_the_compact_types(quantized):
    gltf, _ = merge.read_glb(quantized)
    assert "KHR_mesh_quantization" in gltf["extensionsUsed"]
    assert "KHR_mesh_quantization" in gltf["extensionsRequired"]
    for prim in gltf["meshes"][0]["primitives"]:
        pos = gltf["accessors"][prim["attributes"]["POSITION"]]
        nrm = gltf["accessors"][prim["attributes"]["NORMAL"]]
        assert (pos["componentType"], pos.get("normalized")) == (5122, True)
        assert (nrm["componentType"], nrm.get("normalized")) == (5120, True)
        assert "min" in pos and "max" in pos
        # vertex attributes must be 4-byte aligned per vertex
        assert gltf["bufferViews"][pos["bufferView"]]["byteStride"] == 8
        assert gltf["bufferViews"][nrm["bufferView"]]["byteStride"] == 4


def _max_vertex_error(a_path, b_path):
    a, b = merge.world_triangles(a_path), merge.world_triangles(b_path)
    assert a.keys() == b.keys()
    worst = 0.0
    for mat in a:
        assert len(a[mat]) == len(b[mat])
        for ta, tb in zip(a[mat], b[mat]):
            worst = max(worst, *(math.dist(pa, pb) for pa, pb in zip(ta, tb)))
    return worst


def test_every_vertex_stays_within_one_quantization_step(merged, quantized):
    lo_hi = merge.stats(merged)["bounds"]
    step = max(lo_hi[3 + r] - lo_hi[r] for r in range(3)) / 65534   # int16 spans the board
    assert _max_vertex_error(merged, quantized) <= step


def test_normals_keep_their_direction(merged, quantized):
    for path_a, path_b in ((merged, quantized),):
        ga, ba = merge.read_glb(path_a)
        gb, bb = merge.read_glb(path_b)
        for pa, pb in zip(ga["meshes"][0]["primitives"], gb["meshes"][0]["primitives"]):
            na = merge.read_vec3(ga, ba, pa["attributes"]["NORMAL"])
            nb = merge.read_vec3(gb, bb, pb["attributes"]["NORMAL"])
            for u, v in zip(na, nb):
                dot = sum(x * y for x, y in zip(u, v)) / (math.hypot(*v) or 1)
                assert dot > math.cos(math.radians(1.5))


def test_real_board_halves_and_keeps_its_shape(tmp_path):
    if not REV1.exists():
        pytest.skip("rev 1 GLB not exported")
    # The site's copy is already quantized: merge it back to plain floats first.
    floats = tmp_path / "rev1-float.glb"
    merge.merge_file(REV1, floats)
    out = tmp_path / "rev1-q.glb"
    quantize.quantize_file(floats, out)
    a, b = merge.stats(floats), merge.stats(out)
    assert b["triangles"] == a["triangles"] and b["primitives"] == a["primitives"]
    for x, y in zip(a["bounds"], b["bounds"]):
        assert y == pytest.approx(x, abs=1e-5)                 # metres: 10 µm
    assert out.stat().st_size < 0.6 * floats.stat().st_size
    assert _max_vertex_error(floats, out) < 1e-6               # metres: under a micron


def test_merge_reads_a_quantized_file_back_to_the_same_place(tmp_path, quantized):
    back = tmp_path / "back.glb"
    merge.merge_file(quantized, back)
    assert _max_vertex_error(quantized, back) < 1e-6


def test_quantizing_twice_is_refused(tmp_path, quantized):
    with pytest.raises(ValueError, match="already quantized"):
        quantize.quantize_file(quantized, tmp_path / "again.glb")
