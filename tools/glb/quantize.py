#!/usr/bin/env python3
"""Quantize a merged board GLB with KHR_mesh_quantization.

    python3 quantize.py IN.glb OUT.glb          # IN = output of merge.py

Positions become normalized int16, with the board's centre and half-size moved
onto its node as translation and scale; normals become normalized int8;
indices drop to uint16 where they fit. Viewers decode this natively (no
decoder script), and a board GLB shrinks to about half. Standard library only.
"""
from __future__ import annotations

import sys
from array import array
from pathlib import Path

from merge import read_glb, read_vec3, stats, write_glb, _read_accessor

EXT = "KHR_mesh_quantization"


def quantize(gltf: dict, blob: bytes) -> tuple[dict, bytes]:
    if EXT in gltf.get("extensionsUsed", []):
        raise ValueError("already quantized")
    if len(gltf["nodes"]) != 1 or len(gltf["meshes"]) != 1 or gltf["nodes"][0].keys() - {"name", "mesh"}:
        raise ValueError("expects one untransformed node with one mesh, as merge.py writes")
    prims_in = gltf["meshes"][0]["primitives"]
    points = [read_vec3(gltf, blob, p["attributes"]["POSITION"]) for p in prims_in]
    lo = [min(pt[r] for pts in points for pt in pts) for r in range(3)]
    hi = [max(pt[r] for pts in points for pt in pts) for r in range(3)]
    centre = [(a + b) / 2 for a, b in zip(lo, hi)]
    half = [((b - a) / 2) or 1.0 for a, b in zip(lo, hi)]

    out_blob = bytearray()
    views, accessors, prims = [], [], []

    def view(data: bytes, stride: int | None, target: int) -> int:
        offset = len(out_blob)
        out_blob.extend(data)
        out_blob.extend(b"\0" * (-len(out_blob) % 4))
        v = {"buffer": 0, "byteOffset": offset, "byteLength": len(data), "target": target}
        if stride:
            v["byteStride"] = stride
        views.append(v)
        return len(views) - 1

    def padded(values: array, width: int, pad: int) -> bytes:
        """Each vertex's `width` components, then `pad` zero components (4-byte vertex alignment)."""
        out = array(values.typecode)
        zeros = [0] * pad
        for i in range(0, len(values), width):
            out.extend(values[i: i + width])
            out.extend(zeros)
        if sys.byteorder != "little":
            out.byteswap()
        return out.tobytes()

    for prim, pts in zip(prims_in, points):
        q = array("h", (max(-32767, min(32767, round((pt[r] - centre[r]) / half[r] * 32767)))
                        for pt in pts for r in range(3)))
        pos_acc = {"bufferView": view(padded(q, 3, 1), 8, 34962), "componentType": 5122, "normalized": True,
                   "count": len(pts), "type": "VEC3",
                   "min": [min(q[r::3]) for r in range(3)], "max": [max(q[r::3]) for r in range(3)]}
        accessors.append(pos_acc)
        pos_index = len(accessors) - 1

        nrm = read_vec3(gltf, blob, prim["attributes"]["NORMAL"])
        n = array("b", (max(-127, min(127, round(c * 127))) for v in nrm for c in v))
        accessors.append({"bufferView": view(padded(n, 3, 1), 4, 34962), "componentType": 5120,
                          "normalized": True, "count": len(nrm), "type": "VEC3"})
        nrm_index = len(accessors) - 1

        idx = _read_accessor(gltf, blob, prim["indices"])
        small = max(idx, default=0) < 65535
        ia = array("H" if small else "I", idx)
        if sys.byteorder != "little":
            ia.byteswap()
        accessors.append({"bufferView": view(ia.tobytes(), None, 34963), "componentType": 5123 if small else 5125,
                          "count": len(ia), "type": "SCALAR"})
        p = {"attributes": {"POSITION": pos_index, "NORMAL": nrm_index}, "indices": len(accessors) - 1, "mode": 4}
        if "material" in prim:
            p["material"] = prim["material"]
        prims.append(p)

    node = dict(gltf["nodes"][0], translation=centre, scale=half)
    out = dict(gltf, nodes=[node], meshes=[dict(gltf["meshes"][0], primitives=prims)],
               buffers=[{"byteLength": len(out_blob)}], bufferViews=views, accessors=accessors,
               extensionsUsed=[EXT], extensionsRequired=[EXT])
    out["asset"] = dict(gltf["asset"], generator="atelier6k tools/glb/quantize.py")
    return out, bytes(out_blob)


def quantize_file(src: Path, dst: Path) -> None:
    gltf, blob = read_glb(src)
    write_glb(dst, *quantize(gltf, blob))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    before = src.stat().st_size
    quantize_file(src, dst)
    print(f"{dst}: {before // 1024} KB -> {dst.stat().st_size // 1024} KB, {stats(dst)['triangles']} triangles")
