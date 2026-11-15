#!/usr/bin/env bash
# Regenerates the rev 1 schematic and board from hardware/rev1/circuit.py and
# checks them (unit tests, ERC, netlist against circuit.py, DRC).
#
#   scripts/rev1.sh            schematic, placed and routed board, checks (the board is rebuilt from scratch)
#   scripts/rev1.sh check      checks only, on the files as they are
#
# Everything KiCad runs in the official container without network access.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
IMAGE="${KICAD_IMAGE:-kicad/kicad:10.0.8-full}"
DIR=hardware/rev1
mode="${1:-all}"

kicad() { # runs a command in the KiCad container, with the stock libraries registered
  docker run --rm --network none -u "$(id -u):$(id -g)" -e HOME=/tmp \
    -e KICAD10_3DMODEL_DIR=/usr/share/kicad/3dmodels -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$root":/w -w /w "$IMAGE" bash -c '
      mkdir -p /tmp/.config/kicad/10.0 &&
      cp /usr/share/kicad/template/sym-lib-table /usr/share/kicad/template/fp-lib-table /tmp/.config/kicad/10.0/ &&
      "$@"' _ "$@"
}

echo "==> Circuit tests"
(cd "$DIR" && uv run --quiet --no-project --with pytest pytest -q tests)

mkdir -p docs/reports
if [[ "$mode" == all ]]; then
  echo "==> Library, schematic, board"
  python3 "$DIR/gen_lib.py"
  kicad python3 "$DIR/gen_sch.py"
  kicad python3 "$DIR/route.py"   # places the parts, then routes
fi

echo "==> ERC"
kicad kicad-cli sch erc --format json --severity-all -o docs/reports/rev1-erc.json "$DIR/atelier6k-rev1.kicad_sch" || true
echo "==> Netlist against circuit.py"
kicad bash -c "kicad-cli sch export netlist --format kicadsexpr -o /tmp/rev1.net $DIR/atelier6k-rev1.kicad_sch >/dev/null && python3 $DIR/check_netlist.py /tmp/rev1.net"
echo "==> DRC"
kicad kicad-cli pcb drc --format json --severity-all --schematic-parity -o docs/reports/rev1-drc.json "$DIR/atelier6k-rev1.kicad_pcb" || true
python3 "$DIR/report.py" docs/reports/rev1-erc.json docs/reports/rev1-drc.json

if [[ "$mode" == all ]]; then
  echo "==> Renders, schematic drawing, case, 3D model"
  for side in top bottom; do
    kicad kicad-cli pcb render --quality high --width 1600 --height 1500 --background transparent \
      --side "$side" -o "docs/images/rev1-pcb-$side.png" "$DIR/atelier6k-rev1.kicad_pcb" >/dev/null
  done
  kicad bash -c "mkdir -p /tmp/s && kicad-cli sch export svg --exclude-drawing-sheet -o /tmp/s $DIR/atelier6k-rev1.kicad_sch >/dev/null && cp /tmp/s/*.svg docs/images/rev1-schematic.svg"
  uv run --quiet case/generate.py --rev1
  (cd case && uv run --quiet --no-project --with pytest --with shapely --with ezdxf pytest -q tests)
  origin="$(jq -r '.pcb.kicad_centre | "\(.[0] * 1000 | round / 1000)x\(.[1] * 1000 | round / 1000)mm"' site/assets/case-rev1.json)"
  kicad kicad-cli pcb export glb --force --subst-models --include-tracks --include-pads --include-zones \
    --include-silkscreen --include-soldermask --user-origin "$origin" \
    -o site/assets/atelier6k-rev1.glb "$DIR/atelier6k-rev1.kicad_pcb" >/dev/null
  python3 tools/glb/merge.py site/assets/atelier6k-rev1.glb site/assets/atelier6k-rev1.glb
  python3 tools/glb/quantize.py site/assets/atelier6k-rev1.glb site/assets/atelier6k-rev1.glb
  cp docs/images/rev1-pcb-top.png docs/images/rev1-pcb-bottom.png docs/images/case-rev1-layers.svg \
     docs/images/case-rev1-exploded.png docs/images/rev1-schematic.svg site/assets/
fi
