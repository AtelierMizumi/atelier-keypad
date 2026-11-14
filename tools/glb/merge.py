#!/usr/bin/env python3
"""Merge a KiCad GLB export into one primitive per material.

KiCad exports every pad, via and silkscreen stroke as its own primitive:
17,775 for the rev 0 board. A browser issues one draw call per primitive per
frame, which is what made the site's 3D views stutter. This bakes every node
transform into world-space vertices and concatenates triangles by material,
so the same board draws in a few dozen calls.

    python3 merge.py IN.glb OUT.glb

Standard library only. Handles what KiCad writes: triangle lists with
POSITION and NORMAL, indexed, nodes with translation/rotation/scale/matrix.
"""
from __future__ import annotations

import json
import math
import struct
import sys
from array import array
from pathlib import Path

GLB_MAGIC, JSON_CHUNK, BIN_CHUNK = 0x46546C67, 0x4E4F534A, 0x004E4942
COMPONENT = {5121: "B", 5123: "H", 5125: "I", 5126: "f"}


# ------------------------------------------------------------------ file I/O

def read_glb(path: Path) -> tuple[dict, bytes]:
    data = Path(path).read_bytes()
    magic, _version, _length = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC:
        raise ValueError(f"{path}: not a GLB file")
    offset, gltf, blob = 12, None, b""
    while offset < len(data):
        size, kind = struct.unpack_from("<II", data, offset)
        chunk = data[offset + 8: offset + 8 + size]
        if kind == JSON_CHUNK:
            gltf = json.loads(chunk)
        elif kind == BIN_CHUNK:
            blob = chunk
        offset += 8 + size
    if gltf is None:
        raise ValueError(f"{path}: no JSON chunk")
    return gltf, blob


def write_glb(path: Path, gltf: dict, blob: bytes) -> None:
    text = json.dumps(gltf, separators=(",", ":")).encode()
    text += b" " * (-len(text) % 4)
    blob = bytes(blob) + b"\0" * (-len(blob) % 4)
    total = 12 + 8 + len(text) + 8 + len(blob)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", GLB_MAGIC, 2, total))
        f.write(struct.pack("<II", len(text), JSON_CHUNK) + text)
        f.write(struct.pack("<II", len(blob), BIN_CHUNK) + blob)


def _read_accessor(gltf: dict, blob: bytes, index: int) -> array:
    acc = gltf["accessors"][index]
    view = gltf["bufferViews"][acc["bufferView"]]
    code = COMPONENT[acc["componentType"]]
    width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[acc["type"]]
    item = struct.calcsize(code)
    stride = view.get("byteStride", 0)
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    if stride and stride != item * width:
        out = array(code)
        for i in range(acc["count"]):
            out.extend(struct.unpack_from(f"<{width}{code}", blob, start + i * stride))
        return out
    out = array(code)
    out.frombytes(blob[start: start + acc["count"] * width * item])
    if sys.byteorder != "little":
        out.byteswap()
    return out


def read_vec3(gltf: dict, blob: bytes, index: int) -> list[tuple[float, float, float]]:
    a = _read_accessor(gltf, blob, index)
    return [tuple(a[i: i + 3]) for i in range(0, len(a), 3)]


# ------------------------------------------------------------------ transforms

Mat = list[float]  # 4x4, column-major like glTF


def _mul(a: Mat, b: Mat) -> Mat:
    return [sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4)) for c in range(4) for r in range(4)]


def _local(node: dict) -> Mat:
    if "matrix" in node:
        return list(node["matrix"])
    tx, ty, tz = node.get("translation", (0, 0, 0))
    x, y, z, w = node.get("rotation", (0, 0, 0, 1))
    sx, sy, sz = node.get("scale", (1, 1, 1))
    r = [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w),
         2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w),
         2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)]
    return [r[0] * sx, r[1] * sx, r[2] * sx, 0,
            r[3] * sy, r[4] * sy, r[5] * sy, 0,
            r[6] * sz, r[7] * sz, r[8] * sz, 0,
            tx, ty, tz, 1]


def _normal_matrix(m: Mat) -> list[float]:
    """Inverse transpose of the upper 3x3, row-major."""
    a, b, c = m[0], m[4], m[8]
    d, e, f = m[1], m[5], m[9]
    g, h, i = m[2], m[6], m[10]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-20:
        return [1, 0, 0, 0, 1, 0, 0, 0, 1]
    inv = [(e * i - f * h), -(b * i - c * h), (b * f - c * e),
           -(d * i - f * g), (a * i - c * g), -(a * f - c * d),
           (d * h - e * g), -(a * h - b * g), (a * e - b * d)]
    inv = [v / det for v in inv]
    return [inv[0], inv[3], inv[6], inv[1], inv[4], inv[7], inv[2], inv[5], inv[8]]


def _instances(gltf: dict):
    """(mesh index, world matrix) for every node that draws a mesh."""
    identity: Mat = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    scene = gltf["scenes"][gltf.get("scene", 0)]
    stack: list[tuple[int, Mat]] = [(n, identity) for n in scene["nodes"]]
    while stack:
        index, parent = stack.pop()
        node = gltf["nodes"][index]
        world = _mul(parent, _local(node))
        if "mesh" in node:
            yield node["mesh"], world
        stack.extend((c, world) for c in node.get("children", []))


# ------------------------------------------------------------------ merge

def merge(gltf: dict, blob: bytes) -> tuple[dict, bytes]:
    groups: dict[int, dict] = {}
    for mesh_index, world in _instances(gltf):
        nm = _normal_matrix(world)
        for prim in gltf["meshes"][mesh_index]["primitives"]:
            if prim.get("mode", 4) != 4:
                raise ValueError("only triangle lists are supported")
            g = groups.setdefault(prim.get("material", -1), {"pos": array("f"), "nrm": array("f"), "idx": array("I")})
            base = len(g["pos"]) // 3
            pos = _read_accessor(gltf, blob, prim["attributes"]["POSITION"])
            nrm = _read_accessor(gltf, blob, prim["attributes"]["NORMAL"]) if "NORMAL" in prim["attributes"] else None
            for i in range(0, len(pos), 3):
                x, y, z = pos[i], pos[i + 1], pos[i + 2]
                g["pos"].extend((world[0] * x + world[4] * y + world[8] * z + world[12],
                                 world[1] * x + world[5] * y + world[9] * z + world[13],
                                 world[2] * x + world[6] * y + world[10] * z + world[14]))
                if nrm is not None:
                    a, b, c = nrm[i], nrm[i + 1], nrm[i + 2]
                    nx, ny, nz = nm[0] * a + nm[1] * b + nm[2] * c, nm[3] * a + nm[4] * b + nm[5] * c, nm[6] * a + nm[7] * b + nm[8] * c
                    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                    g["nrm"].extend((nx / length, ny / length, nz / length))
                else:
                    g["nrm"].extend((0.0, 0.0, 1.0))
            if "indices" in prim:
                g["idx"].extend(v + base for v in _read_accessor(gltf, blob, prim["indices"]))
            else:
                g["idx"].extend(range(base, base + len(pos) // 3))

    out_blob = bytearray()
    views, accessors, prims = [], [], []

    def add(data: array, kind: str, ctype: int, target: int, bounds: bool = False) -> int:
        offset = len(out_blob)
        if sys.byteorder != "little":
            data = array(data.typecode, data)
            data.byteswap()
        out_blob.extend(data.tobytes())
        out_blob.extend(b"\0" * (-len(out_blob) % 4))
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data) * data.itemsize, "target": target})
        width = 3 if kind == "VEC3" else 1
        acc = {"bufferView": len(views) - 1, "componentType": ctype, "count": len(data) // width, "type": kind}
        if bounds:
            acc["min"] = [min(data[i::3]) for i in range(3)]
            acc["max"] = [max(data[i::3]) for i in range(3)]
        accessors.append(acc)
        return len(accessors) - 1

    for material, g in sorted(groups.items()):
        p = {"attributes": {"POSITION": add(g["pos"], "VEC3", 5126, 34962, True),
                            "NORMAL": add(g["nrm"], "VEC3", 5126, 34962)},
             "indices": add(g["idx"], "SCALAR", 5125, 34963), "mode": 4}
        if material >= 0:
            p["material"] = material
        prims.append(p)

    out = {"asset": {"version": "2.0", "generator": "atelier6k tools/glb/merge.py"},
           "scene": 0, "scenes": [{"nodes": [0]}],
           "nodes": [{"name": "board", "mesh": 0}],
           "meshes": [{"name": "board", "primitives": prims}],
           "materials": gltf.get("materials", []),
           "buffers": [{"byteLength": len(out_blob)}],
           "bufferViews": views, "accessors": accessors}
    return out, bytes(out_blob)


def merge_file(src: Path, dst: Path) -> None:
    gltf, blob = read_glb(src)
    out, out_blob = merge(gltf, blob)
    write_glb(dst, out, out_blob)


# ------------------------------------------------------------------ inspection

def world_triangles(path: Path) -> dict[int, list[tuple]]:
    """material -> list of triangles, each three world-space points."""
    gltf, blob = read_glb(path)
    out: dict[int, list[tuple]] = {}
    for mesh_index, world in _instances(gltf):
        for prim in gltf["meshes"][mesh_index]["primitives"]:
            pts = read_vec3(gltf, blob, prim["attributes"]["POSITION"])
            pts = [tuple(world[r] * x + world[4 + r] * y + world[8 + r] * z + world[12 + r] for r in range(3))
                   for x, y, z in pts]
            idx = _read_accessor(gltf, blob, prim["indices"])
            tris = out.setdefault(prim.get("material", -1), [])
            tris.extend((pts[idx[i]], pts[idx[i + 1]], pts[idx[i + 2]]) for i in range(0, len(idx), 3))
    return out


def stats(path: Path) -> dict:
    gltf, blob = read_glb(path)
    tris = prims = 0
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for mesh_index, world in _instances(gltf):
        for prim in gltf["meshes"][mesh_index]["primitives"]:
            prims += 1
            tris += gltf["accessors"][prim["indices"]]["count"] // 3
            for x, y, z in read_vec3(gltf, blob, prim["attributes"]["POSITION"]):
                for r in range(3):
                    v = world[r] * x + world[4 + r] * y + world[8 + r] * z + world[12 + r]
                    lo[r], hi[r] = min(lo[r], v), max(hi[r], v)
    return {"triangles": tris, "primitives": prims, "materials": len(gltf.get("materials", [])),
            "bounds": lo + hi}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    merge_file(Path(sys.argv[1]), Path(sys.argv[2]))
    a, b = stats(Path(sys.argv[1])), stats(Path(sys.argv[2]))
    print(f"{sys.argv[2]}: {a['primitives']} -> {b['primitives']} primitives, {b['triangles']} triangles")
