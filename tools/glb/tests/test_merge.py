"""Spec for merging a KiCad GLB export into one primitive per material.

KiCad writes every pad, via and silkscreen stroke as its own primitive, so a
small board becomes thousands of draw calls per frame. The merged file must
look identical: same triangles, same place, same materials.

    cd tools/glb && uv run --no-project --with pytest pytest -q
"""
import math
import struct
from pathlib import Path

import pytest

import merge

ROOT = Path(__file__).resolve().parents[3]
REV1 = ROOT / "site" / "assets" / "atelier6k-rev1.glb"


def tiny_glb(tmp_path):
    """Two nodes, each a one-triangle mesh; the child is translated and rotated 90 deg about z."""
    pos = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
    nrm = struct.pack("<9f", 0, 0, 1, 0, 0, 1, 0, 0, 1)
    idx = struct.pack("<3H", 0, 1, 2) + b"\0\0"
    blob = pos + nrm + idx
    views = [{"buffer": 0, "byteOffset": 0, "byteLength": 36},
             {"buffer": 0, "byteOffset": 36, "byteLength": 36},
             {"buffer": 0, "byteOffset": 72, "byteLength": 6}]
    acc = [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3", "min": [0, 0, 0], "max": [1, 1, 0]},
           {"bufferView": 1, "componentType": 5126, "count": 3, "type": "VEC3"},
           {"bufferView": 2, "componentType": 5123, "count": 3, "type": "SCALAR"}]
    prim = lambda mat: {"attributes": {"POSITION": 0, "NORMAL": 1}, "indices": 2, "material": mat, "mode": 4}
    s = math.sqrt(0.5)
    gltf = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0, "children": [1]},
                      {"mesh": 1, "translation": [10, 0, 0], "rotation": [0, 0, s, s]}],
            "meshes": [{"primitives": [prim(0)]}, {"primitives": [prim(0), prim(1)]}],
            "materials": [{"name": "a"}, {"name": "b"}],
            "buffers": [{"byteLength": len(blob)}], "bufferViews": views, "accessors": acc}
    path = tmp_path / "tiny.glb"
    merge.write_glb(path, gltf, blob)
    return path


def test_round_trip_reads_what_was_written(tmp_path):
    gltf, blob = merge.read_glb(tiny_glb(tmp_path))
    assert len(gltf["meshes"]) == 2 and len(blob) >= 78


def test_one_primitive_per_material(tmp_path):
    out = tmp_path / "out.glb"
    merge.merge_file(tiny_glb(tmp_path), out)
    gltf, _ = merge.read_glb(out)
    prims = [p for m in gltf["meshes"] for p in m["primitives"]]
    assert sorted(p["material"] for p in prims) == [0, 1]
    assert len(gltf["nodes"]) == 1 and gltf["scenes"][0]["nodes"] == [0]


def test_triangles_are_kept_and_moved_to_world_space(tmp_path):
    out = tmp_path / "out.glb"
    merge.merge_file(tiny_glb(tmp_path), out)
    tris = merge.world_triangles(out)
    assert len(tris[0]) == 2 and len(tris[1]) == 1
    rotated = tris[1][0]  # child: rotate (1,0,0) -> (0,1,0), then translate by +10 x
    assert rotated[1] == pytest.approx((10, 1, 0), abs=1e-6)
    assert rotated[2] == pytest.approx((9, 0, 0), abs=1e-6)


def test_normals_follow_the_rotation(tmp_path):
    out = tmp_path / "out.glb"
    merge.merge_file(tiny_glb(tmp_path), out)
    gltf, blob = merge.read_glb(out)
    for p in gltf["meshes"][0]["primitives"]:
        for n in merge.read_vec3(gltf, blob, p["attributes"]["NORMAL"]):
            assert math.dist(n, (0, 0, 1)) < 1e-6


@pytest.mark.skipif(not REV1.exists(), reason="rev 1 model not exported")
def test_real_board_keeps_every_triangle_and_its_bounds(tmp_path):
    out = tmp_path / "rev1.glb"
    merge.merge_file(REV1, out)
    before, after = merge.stats(REV1), merge.stats(out)
    assert after["triangles"] == before["triangles"]
    assert after["primitives"] <= before["materials"]
    for a, b in zip(after["bounds"], before["bounds"]):
        assert a == pytest.approx(b, abs=1e-4)
