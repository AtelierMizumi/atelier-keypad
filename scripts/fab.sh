#!/usr/bin/env bash
# Builds the rev 2.0 production package from the routed, checked board:
#   build/fab/rev2.0/{gerbers/, bom-jlcpcb.csv, cpl-jlcpcb.csv, case-dxf/, README.txt, firmware.bin?}
# Run scripts/he.sh first (it regenerates and checks the board). Nothing here is committed:
# build/ is ignored; CI uploads the folder as an artifact and attaches a zip to Releases.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
IMAGE="${KICAD_IMAGE:-kicad/kicad:10.0.8-full}"
NETWORK="${KICAD_NETWORK:-none}"   # CI pulls the image first, then runs without network too
PCB=hardware/he/atelier-he.kicad_pcb
OUT=build/fab/rev2.0

kicad() {
  docker run --rm --network "$NETWORK" -u "$(id -u):$(id -g)" -e HOME=/tmp \
    -v "$root":/w -w /w "$IMAGE" "$@"
}

# Start clean, but only ever inside build/fab.
case "$OUT" in build/fab/*) rm -rf -- "$OUT" ;; *) echo "refusing to clean $OUT" >&2; exit 1 ;; esac
mkdir -p "$OUT/gerbers" "$OUT/case-dxf"

echo "==> Gerbers and drill"
kicad kicad-cli pcb export gerbers \
  --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask -o "$OUT/gerbers/" "$PCB" >/dev/null
kicad kicad-cli pcb export drill --format excellon --excellon-separate-th \
  --excellon-units mm -o "$OUT/gerbers/" "$PCB" >/dev/null

echo "==> Placement, BOM, README"
kicad kicad-cli pcb export pos --format csv --units mm --side both -o "$OUT/kicad-pos.csv" "$PCB" >/dev/null
python3 hardware/he/fab.py "$OUT/kicad-pos.csv" "$OUT"
rm -f -- "$OUT/kicad-pos.csv"

echo "==> Case and firmware"
cp case/dxf-he/*.dxf "$OUT/case-dxf/"
if [[ -f build/fw/atelier-he.bin ]]; then cp build/fw/atelier-he.bin "$OUT/firmware.bin"; fi

ls -R "$OUT"
