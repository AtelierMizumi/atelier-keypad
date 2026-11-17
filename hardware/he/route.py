#!/usr/bin/env python3
"""Routes atelier-he.kicad_pcb: the rev 1 grid maze router, tuned for 0.5 mm pitch.

Run inside the KiCad container (scripts/rev1.sh does that):

    route.py            place the parts afresh, route every net, refill zones, save

This is not a general autorouter. It handles this board: two layers, a 0.25 mm
grid, 45-degree moves, through vias, one track width per net class. Obstacles
are grown by clearance + half the widest track, which is conservative for the
thin signal tracks. KiCad's DRC is the judge of the result, not this script.
"""
from __future__ import annotations

import heapq
import math
import sys

import pcbnew

import circuit
import gen_pcb

GRID = 0.25
CLEARANCE = 0.15
HALF_MAX = 0.15                    # half of the widest track (0.3 mm power)
GROW = CLEARANCE + HALF_MAX        # obstacle growth seen by a track centre line
EDGE_GROW = 0.3 + HALF_MAX         # board edge and cut-outs
HOLE_GROW = 0.25 + HALF_MAX        # unplated holes
VIA_DIAMETER, VIA_DRILL = 0.6, 0.3
VIA_COST = 24                      # in grid steps
FREE, BLOCKED = 0, -1
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
X0, Y0, X1, Y1 = circuit.OUTLINE
NX = int(round((X1 - X0) / GRID)) + 1
NY = int(round((Y1 - Y0) / GRID)) + 1
MOVES = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]

to_mm = pcbnew.ToMM
mm = pcbnew.FromMM


class Grid:
    """owner[layer][cell]: FREE, BLOCKED, or the id of the only net allowed there."""

    def __init__(self):
        self.owner = [[FREE] * (NX * NY) for _ in LAYERS]

    @staticmethod
    def cell(x: float, y: float) -> tuple[int, int]:
        return int(round((x - X0) / GRID)), int(round((y - Y0) / GRID))

    def claim(self, layer: int, ix: int, iy: int, net: int) -> None:
        if 0 <= ix < NX and 0 <= iy < NY:
            o = self.owner[layer]
            i = iy * NX + ix
            if o[i] == FREE:
                o[i] = net
            elif o[i] != net:
                o[i] = BLOCKED

    def rect(self, layer: int, x0, y0, x1, y1, net: int) -> None:
        ax, ay = self.cell(x0, y0)
        bx, by = self.cell(x1, y1)
        # cell() rounds to nearest; widen so the whole grown shape is covered
        for iy in range(ay - 1, by + 2):
            for ix in range(ax - 1, bx + 2):
                cx, cy = X0 + ix * GRID, Y0 + iy * GRID
                if x0 - 1e-6 <= cx <= x1 + 1e-6 and y0 - 1e-6 <= cy <= y1 + 1e-6:
                    self.claim(layer, ix, iy, net)

    def disc(self, layer: int, x, y, r, net: int) -> None:
        ax, ay = self.cell(x - r, y - r)
        bx, by = self.cell(x + r, y + r)
        for iy in range(ay - 1, by + 2):
            for ix in range(ax - 1, bx + 2):
                if math.hypot(X0 + ix * GRID - x, Y0 + iy * GRID - y) <= r + 1e-6:
                    self.claim(layer, ix, iy, net)

    def line(self, layer: int, a, b, r, net: int) -> None:
        n = max(1, int(math.dist(a, b) / (GRID / 2)))
        for i in range(n + 1):
            t = i / n
            self.disc(layer, a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, r, net)

    def usable(self, layer: int, ix: int, iy: int, net: int) -> bool:
        if not (0 <= ix < NX and 0 <= iy < NY):
            return False
        o = self.owner[layer][iy * NX + ix]
        return o == FREE or o == net


def box_mm(item):
    b = item.GetBoundingBox()
    return to_mm(b.GetLeft()), to_mm(b.GetTop()), to_mm(b.GetRight()), to_mm(b.GetBottom())


def build_obstacles(board, net_ids: dict[str, int]) -> Grid:
    g = Grid()
    both = (0, 1)

    # Board edge and everything outside the outline.
    for kind, *p in gen_pcb.outline_points():
        for layer in both:
            g.line(layer, p[0], p[-1], EDGE_GROW, BLOCKED)
    for layer in both:
        r = circuit.OUTLINE_RADIUS  # square off the rounded corners
        for cx, cy in ((X0, Y0), (X1, Y0), (X0, Y1), (X1, Y1)):
            g.rect(layer, cx - r, cy - r, cx + r, cy + r, BLOCKED)

    for fp in board.GetFootprints():
        # Cut-outs drawn in footprints (the reverse-mount LEDs).
        cuts = [box_mm(s) for s in fp.GraphicalItems() if s.GetLayer() == pcbnew.Edge_Cuts]
        if cuts:
            x0, y0 = min(c[0] for c in cuts), min(c[1] for c in cuts)
            x1, y1 = max(c[2] for c in cuts), max(c[3] for c in cuts)
            for layer in both:
                g.rect(layer, x0 - EDGE_GROW, y0 - EDGE_GROW, x1 + EDGE_GROW, y1 + EDGE_GROW, BLOCKED)
        for pad in fp.Pads():
            x0, y0, x1, y1 = box_mm(pad)
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                c = pad.GetPosition()
                for layer in both:
                    g.disc(layer, to_mm(c.x), to_mm(c.y), to_mm(pad.GetDrillSize().x) / 2 + HOLE_GROW, BLOCKED)
                continue
            net = net_ids.get(pad.GetNetname(), BLOCKED)
            for layer in both:
                if pad.IsOnLayer(LAYERS[layer]):
                    g.rect(layer, x0 - GROW, y0 - GROW, x1 + GROW, y1 + GROW, net)

    for zone in board.Zones():
        if zone.GetIsRuleArea():
            x0, y0, x1, y1 = box_mm(zone)
            for layer in both:
                if zone.IsOnLayer(LAYERS[layer]):
                    g.rect(layer, x0 - HALF_MAX, y0 - HALF_MAX, x1 + HALF_MAX, y1 + HALF_MAX, BLOCKED)
    return g


def via_fits(g: Grid, ix: int, iy: int, net: int) -> bool:
    # Obstacles are grown for a 0.15 mm half-width; a via is 0.15 mm wider, so ask for one more cell.
    return all(g.usable(layer, ix + dx, iy + dy, net)
               for layer in (0, 1) for dx in (-1, 0, 1) for dy in (-1, 0, 1))


TURN_COST = 0.6                    # discourages staircase tracks


def search(g: Grid, net: int, sources: set, targets: set):
    """Cheapest path from any source to any target; nodes are (layer, ix, iy).

    The search state also carries the direction of travel so that turns can be charged for.
    """
    tx = sum(t[1] for t in targets) / len(targets)
    ty = sum(t[2] for t in targets) / len(targets)
    slack = max(math.hypot(t[1] - tx, t[2] - ty) for t in targets)

    def h(n):
        return max(0.0, math.hypot(n[1] - tx, n[2] - ty) - slack)

    start = [(s[0], s[1], s[2], -1) for s in sources]
    best = {s: 0.0 for s in start}
    prev = {}
    heap = [(h(s), 0.0, s) for s in start]
    heapq.heapify(heap)
    while heap:
        _, cost, state = heapq.heappop(heap)
        if cost > best.get(state, 1e18):
            continue
        layer, ix, iy, heading = state
        if (layer, ix, iy) in targets:
            path = [state]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return [p[:3] for p in path[::-1]]
        steps = []
        for d, (dx, dy, c) in enumerate(MOVES):
            jx, jy = ix + dx, iy + dy
            if not g.usable(layer, jx, jy, net):
                continue
            if dx and dy and not (g.usable(layer, jx, iy, net) and g.usable(layer, ix, jy, net)):
                continue
            steps.append(((layer, jx, jy, d), c + (TURN_COST if heading not in (-1, d) else 0.0)))
        if via_fits(g, ix, iy, net):
            steps.append(((1 - layer, ix, iy, -1), VIA_COST))
        for nxt, c in steps:
            nc = cost + c
            if nc < best.get(nxt, 1e18):
                best[nxt] = nc
                prev[nxt] = state
                heapq.heappush(heap, (nc + h(nxt), nc, nxt))
    return None


def xy(node) -> tuple[float, float]:
    return X0 + node[1] * GRID, Y0 + node[2] * GRID


def add_track(board, net, layer, a, b, width) -> None:
    if math.dist(a, b) < 1e-4:
        return
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(gen_pcb.pt(*a))
    t.SetEnd(gen_pcb.pt(*b))
    t.SetWidth(mm(width))
    t.SetLayer(LAYERS[layer])
    t.SetNet(net)
    board.Add(t)


def add_via(board, net, at) -> None:
    v = pcbnew.PCB_VIA(board)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetPosition(gen_pcb.pt(*at))
    v.SetWidth(pcbnew.F_Cu, mm(VIA_DIAMETER))
    v.SetDrill(mm(VIA_DRILL))
    v.SetNet(net)
    board.Add(v)


def emit(board, g: Grid, net, net_id: int, path: list, width: float) -> None:
    """Turns a cell path into tracks and vias and claims the copper in the grid."""
    grow = width / 2 + GROW
    run = [path[0]]
    for node in path[1:] + [None]:
        if node is not None and node[0] == run[-1][0]:
            run.append(node)
            continue
        # flush a same-layer run, merging collinear steps
        start = run[0]
        for i in range(1, len(run)):
            last = i == len(run) - 1
            if last or (run[i + 1][1] - run[i][1], run[i + 1][2] - run[i][2]) != (run[i][1] - run[i - 1][1], run[i][2] - run[i - 1][2]):
                add_track(board, net, start[0], xy(start), xy(run[i]), width)
                g.line(start[0], xy(start), xy(run[i]), grow, net_id)
                start = run[i]
        if node is not None:
            add_via(board, net, xy(node))
            for layer in (0, 1):
                g.disc(layer, *xy(node), VIA_DIAMETER / 2 + GROW, net_id)
            run = [node]


def pad_nodes(pad) -> set:
    c = pad.GetPosition()
    ix, iy = Grid.cell(to_mm(c.x), to_mm(c.y))
    return {(layer, ix, iy) for layer in (0, 1) if pad.IsOnLayer(LAYERS[layer])}


def route_net(board, g: Grid, name: str, net_id: int, width: float) -> list[str]:
    net = board.FindNet(name)
    pads = [p for fp in board.GetFootprints() for p in fp.Pads() if p.GetNetname() == name]
    failed = []
    # Pads of one footprint that share a number (tact switch legs) still each get a connection.
    remaining = sorted(pads, key=lambda p: (p.GetPosition().x, p.GetPosition().y))
    first = remaining.pop(0)
    tree = set(pad_nodes(first))
    done = [first]
    while remaining:
        nxt = min(remaining, key=lambda p: min(math.dist((p.GetPosition().x, p.GetPosition().y),
                                                         (d.GetPosition().x, d.GetPosition().y)) for d in done))
        remaining.remove(nxt)
        targets = pad_nodes(nxt)
        path = search(g, net_id, tree, targets)
        if path is None:
            failed.append(f"{name}: {nxt.GetParentFootprint().GetReference()} pad {nxt.GetNumber()}")
            continue
        emit(board, g, net, net_id, path, width)
        # exact pad centres are rarely on the grid: bridge the last fraction of a millimetre
        for pad, node in ((nxt, path[-1]),) + tuple((d, path[0]) for d in done if path[0] in pad_nodes(d)):
            c = pad.GetPosition()
            add_track(board, net, node[0], xy(node), (to_mm(c.x), to_mm(c.y)), width)
        tree.update(path)
        tree.update(targets)
        done.append(nxt)
    return failed


STITCH_PITCH = 3.0                 # mm between candidate ground vias


def stitch_ground(board, g: Grid, gnd: int) -> int:
    """Ground vias on a lattice wherever there is room, so the two pours are one ground."""
    net = board.FindNet("GND")
    ax0, ay0, ax1, ay1 = circuit.ART_ZONE
    count = 0
    vias = [(to_mm(t.GetPosition().x), to_mm(t.GetPosition().y)) for t in board.GetTracks()
            if t.Type() == pcbnew.PCB_VIA_T]
    # keep drilled holes apart too: through-hole pads and unplated holes count like vias
    vias += [(to_mm(p.GetPosition().x), to_mm(p.GetPosition().y)) for fp in board.GetFootprints()
             for p in fp.Pads() if p.GetDrillSize().x > 0]
    steps = int(STITCH_PITCH / GRID)
    for iy in range(steps // 2, NY, steps):
        for ix in range(steps // 2, NX, steps):
            x, y = X0 + ix * GRID, Y0 + iy * GRID
            if ax0 - 1 < x < ax1 + 1 and ay0 - 1 < y < ay1 + 1:
                continue
            if via_fits(g, ix, iy, gnd) and all(math.dist((x, y), v) >= 1.2 for v in vias):
                vias.append((x, y))
                add_via(board, net, (x, y))
                for layer in (0, 1):
                    g.disc(layer, x, y, VIA_DIAMETER / 2 + GROW, gnd)
                count += 1
    return count


def stitch_islands(board, g: Grid, gnd: int) -> int:
    """After a fill, give every ground island without a via one, if any spot in it fits."""
    net = board.FindNet("GND")
    vias = [t.GetPosition() for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == "GND"]
    added = 0
    for zone in board.Zones():
        if zone.GetIsRuleArea() or zone.GetNetname() != "GND":
            continue
        for layer in LAYERS:
            if not zone.IsOnLayer(layer):
                continue
            polys = zone.GetFilledPolysList(layer)
            for i in range(polys.OutlineCount()):
                outline = polys.Outline(i)
                if any(outline.PointInside(v) for v in vias):
                    continue
                bb = outline.BBox()
                ax, ay = Grid.cell(to_mm(bb.GetLeft()), to_mm(bb.GetTop()))
                bx, by = Grid.cell(to_mm(bb.GetRight()), to_mm(bb.GetBottom()))
                spot = next(((ix, iy) for iy in range(ay, by + 1) for ix in range(ax, bx + 1)
                             if via_fits(g, ix, iy, gnd)
                             and outline.PointInside(gen_pcb.pt(*xy((0, ix, iy))))), None)
                if spot:
                    at = xy((0, *spot))
                    add_via(board, net, at)
                    vias.append(gen_pcb.pt(*at))
                    for lyr in (0, 1):
                        g.disc(lyr, *at, VIA_DIAMETER / 2 + GROW, gnd)
                    added += 1
    return added


def net_order(names: list[str]) -> list[str]:
    def rank(n: str) -> tuple:
        # Power to the LEDs first: those pads are boxed in by the LED cut-outs.
        # Ground last; whatever it cannot reach with a track is left to the pours.
        if n == "GND":
            return (4, n)
        if n in ("USB_DP", "USB_DM"):
            return (-1, n)  # shortest, straightest: the high-speed pair first
        if n == "VBUS":
            return (-0.8, n)  # the right-hand VBUS pad has to cross the USB pair
        if n in ("CC1", "CC2"):
            return (-0.5, n)  # after VBUS: its resistor sits right under the pad
        if n in ("HEXT_IN", "HEXT_OUT", "OTGHS_R"):
            return (0, n)
        if n.startswith("ADC_K"):
            return (0.2, {"ADC_K3": 0, "ADC_K1": 1, "ADC_K2": 2}[n])  # outside-in, so they nest
        if n.startswith("BTN_") or n in ("LED_DATA", "BOOT0", "SWDIO", "SWCLK", "NRST"):
            return (0.3, n)  # MCU side pins before the 3.3 V rails can wall them in
        if n in ("+5V", "+3V3", "+3V3A"):
            return (0.5, n)
        if n.startswith("LED_D") and n[5:].isdigit():
            return (1, int(n[5:]))
        return (2, n)
    return sorted(names, key=rank)


def main() -> None:
    gen_pcb.place()  # always start from a freshly placed, unrouted board
    board = pcbnew.LoadBoard(str(gen_pcb.BOARD))
    names = sorted({p.GetNetname() for fp in board.GetFootprints() for p in fp.Pads()
                    if p.GetNetname() and not p.GetNetname().startswith("unconnected-")})
    net_ids = {n: i + 1 for i, n in enumerate(names)}
    g = build_obstacles(board, net_ids)
    for name, x, y in circuit.FIXED_VIAS:
        add_via(board, board.FindNet(name), (x, y))
        for layer in (0, 1):
            g.disc(layer, x, y, VIA_DIAMETER / 2 + GROW, net_ids[name])
    power = set(circuit.NET_CLASSES["Power"]["nets"])
    failed = []
    for name in net_order(names):
        width = circuit.NET_CLASSES["Power" if name in power else "Default"]["track"]
        failed += route_net(board, g, name, net_ids[name], width)
    stitched = stitch_ground(board, g, net_ids["GND"])
    gen_pcb.refill(board)
    stitched += stitch_islands(board, g, net_ids["GND"])
    gen_pcb.refill(board)
    pcbnew.SaveBoard(str(gen_pcb.BOARD), board)
    print(f"ground stitching vias: {stitched}")
    tracks = [t for t in board.GetTracks()]
    vias = sum(1 for t in tracks if t.Type() == pcbnew.PCB_VIA_T)
    print(f"routed {len(names)} nets: {len(tracks) - vias} track segments, {vias} vias")
    if failed:
        print("no track found for (ground may still connect through the pours; DRC decides):\n  " + "\n  ".join(failed))
        if any(not f.startswith("GND:") for f in failed):
            sys.exit(1)


if __name__ == "__main__":
    main()
