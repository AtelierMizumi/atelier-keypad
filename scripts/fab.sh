#!/usr/bin/env bash
# Builds a production package from the routed, checked board:
#
#   scripts/fab.sh [rev2.0]   build/fab/rev2.0/{gerbers/, bom-jlcpcb.csv, cpl-jlcpcb.csv, case-dxf/, README.txt, firmware.bin?}
#   scripts/fab.sh rev1       build/fab/rev1/{gerbers/, plate-gerbers/, bom-jlcpcb.csv, cpl-jlcpcb.csv,
#                                             hand-parts.csv, case-dxf/, README.txt, firmware.uf2?}
#
# Run scripts/he.sh (or scripts/rev1.sh) first: it regenerates and checks the board.
# Nothing here is committed: build/ is ignored; CI uploads each folder as an artifact
# and attaches the rev 2.0 zip to Releases.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
IMAGE="${KICAD_IMAGE:-kicad/kicad:10.0.8-full}"
NETWORK="${KICAD_NETWORK:-none}"   # CI pulls the image first, then runs without network too

rev="${1:-rev2.0}"
case "$rev" in
  rev2.0)
    PCB=hardware/he/atelier-he.kicad_pcb
    FAB_PY=hardware/he/fab.py
    DXF=(case/dxf-he/*.dxf)
    FW=build/fw/atelier-he.bin
    FW_NAME=firmware.bin
    ;;
  rev1)
    PCB=hardware/rev1/atelier6k-rev1.kicad_pcb
    FAB_PY=hardware/rev1/fab.py
    # Acrylic only: the plate is FR4 and goes out as plate-gerbers/.
    DXF=(case/dxf-rev1/atelier6k-case-{top-frame-3mm,bottom-frame-5mm,base-3mm}.dxf)
    FW=firmware/build/atelier6k_default.uf2
    FW_NAME=firmware.uf2
    ;;
  *)
    echo "unknown revision: $rev (expected rev2.0 or rev1)" >&2
    exit 2
    ;;
esac
OUT=build/fab/$rev

kicad() {
  docker run --rm --network "$NETWORK" -u "$(id -u):$(id -g)" -e HOME=/tmp \
    -v "$root":/w -w /w "$IMAGE" "$@"
}

# Start clean, but only ever inside build/fab.
case "$OUT" in build/fab/?*) rm -rf -- "$OUT" ;; *) echo "refusing to clean $OUT" >&2; exit 1 ;; esac
mkdir -p "$OUT/gerbers" "$OUT/case-dxf"

echo "==> Gerbers and drill"
kicad kicad-cli pcb export gerbers \
  --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask -o "$OUT/gerbers/" "$PCB" >/dev/null
kicad kicad-cli pcb export drill --format excellon --excellon-separate-th \
  --excellon-units mm -o "$OUT/gerbers/" "$PCB" >/dev/null

if [[ "$rev" == rev1 ]]; then
  echo "==> Switch plate (FR4, no copper)"
  mkdir -p "$OUT/plate-gerbers"
  uv run --quiet --no-project --with shapely --with ezdxf case/plate_pcb.py "$OUT/plate-src/atelier6k-plate.kicad_pcb" >/dev/null
  # Empty copper layers and a drill file as well: the fab house reads the layer count
  # from the copper Gerbers and expects a drill file in every order.
  kicad kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Mask,B.Mask,Edge.Cuts \
    -o "$OUT/plate-gerbers/" "$OUT/plate-src/atelier6k-plate.kicad_pcb" >/dev/null
  kicad kicad-cli pcb export drill --format excellon --excellon-units mm \
    -o "$OUT/plate-gerbers/" "$OUT/plate-src/atelier6k-plate.kicad_pcb" >/dev/null
  rm -rf -- "$OUT/plate-src"
fi

echo "==> Placement, BOM, README"
kicad kicad-cli pcb export pos --format csv --units mm --side both -o "$OUT/kicad-pos.csv" "$PCB" >/dev/null
python3 "$FAB_PY" "$OUT/kicad-pos.csv" "$OUT"
rm -f -- "$OUT/kicad-pos.csv"

echo "==> Case and firmware"
cp "${DXF[@]}" "$OUT/case-dxf/"
if [[ -f "$FW" ]]; then cp "$FW" "$OUT/$FW_NAME"; fi

ls -R "$OUT"
