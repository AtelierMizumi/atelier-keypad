#!/usr/bin/env bash
# Regenerates the rev 2 (Hall effect) schematic and board from hardware/he/circuit.py and
# checks them (unit tests, ERC, netlist against circuit.py, DRC).
#
#   scripts/he.sh            schematic, placed and routed board, checks (the board is rebuilt from scratch)
#   scripts/he.sh check      checks only, on the files as they are
#
# Everything KiCad runs in the official container without network access.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
IMAGE="${KICAD_IMAGE:-kicad/kicad:10.0.8-full}"
DIR=hardware/he
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
(cd "$DIR" && uv run --quiet --no-project --with pytest pytest -q tests/test_circuit.py)

mkdir -p docs/reports
if [[ "$mode" == all ]]; then
  echo "==> Library, schematic, board"
  python3 "$DIR/gen_lib.py"
  kicad python3 "$DIR/gen_sch.py"
  kicad python3 "$DIR/route.py"   # places the parts, then routes
fi

echo "==> ERC"
kicad kicad-cli sch erc --format json --severity-all -o docs/reports/he-erc.json "$DIR/atelier-he.kicad_sch" || true
echo "==> Netlist against circuit.py"
kicad bash -c "kicad-cli sch export netlist --format kicadsexpr -o /tmp/he.net $DIR/atelier-he.kicad_sch >/dev/null && python3 $DIR/check_netlist.py /tmp/he.net"
echo "==> DRC"
kicad kicad-cli pcb drc --format json --severity-all --schematic-parity -o docs/reports/he-drc.json "$DIR/atelier-he.kicad_pcb" || true
python3 "$DIR/report.py" docs/reports/he-erc.json docs/reports/he-drc.json
echo "==> Layout tests on the routed board"
(cd "$DIR" && uv run --quiet --no-project --with pytest pytest -q tests)

if [[ "$mode" == all ]]; then
  echo "==> Renders, schematic drawing, case, 3D model"
  for side in top bottom; do
    kicad kicad-cli pcb render --quality high --width 1600 --height 1500 --background transparent \
      --side "$side" -o "docs/images/rev2-pcb-$side.png" "$DIR/atelier-he.kicad_pcb" >/dev/null
  done
  kicad bash -c "mkdir -p /tmp/s && kicad-cli sch export svg --exclude-drawing-sheet -o /tmp/s $DIR/atelier-he.kicad_sch >/dev/null && cp /tmp/s/*.svg docs/images/rev2-schematic.svg"
  uv run --quiet case/generate_he.py
  (cd case && uv run --quiet --no-project --with pytest --with shapely --with ezdxf pytest -q tests)
  origin="$(jq -r '.pcb.kicad_centre | "\(.[0] * 1000 | round / 1000)x\(.[1] * 1000 | round / 1000)mm"' site/assets/case-he.json)"
  kicad kicad-cli pcb export glb --force --subst-models --include-tracks --include-pads --include-zones \
    --include-silkscreen --include-soldermask --user-origin "$origin" \
    -o site/assets/atelier6k-he.glb "$DIR/atelier-he.kicad_pcb" >/dev/null
  python3 tools/glb/merge.py site/assets/atelier6k-he.glb site/assets/atelier6k-he.glb
  cp "$DIR/atelier-he.kicad_pcb" "$DIR/atelier-he.kicad_sch" site/kicad/
  cp docs/images/rev2-pcb-top.png docs/images/rev2-pcb-bottom.png docs/images/rev2-schematic.svg \
     docs/images/rev2-art-preview.png site/assets/
fi
