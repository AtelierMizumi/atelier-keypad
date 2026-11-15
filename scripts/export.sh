#!/usr/bin/env bash
# Regenerates every derived artefact (renders, 3D model, schematic SVG, BOM,
# ERC/DRC reports, interactive BOM) from the KiCad sources.
#
# Uses a local `kicad-cli` (KiCad >= 10) when present, otherwise the official
# KiCad Docker image. Run it again after any change to hardware/atelier6k/.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

IMAGE="${KICAD_IMAGE:-kicad/kicad:10.0.8-full}"
IBOM_REF="${IBOM_REF:-v2.10.0}"
PRJ=hardware/atelier6k
SCH="$PRJ/atelier6k.kicad_sch"
PCB="$PRJ/atelier6k.kicad_pcb"

if command -v kicad-cli >/dev/null 2>&1 && [[ -z "${KICAD_FORCE_DOCKER:-}" ]]; then
  kicad() { kicad-cli "$@"; }
  have_docker=0
else
  command -v docker >/dev/null 2>&1 || { echo "need kicad-cli or docker" >&2; exit 1; }
  kicad() {
    docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp \
      -e KICAD10_3DMODEL_DIR=/usr/share/kicad/3dmodels \
      -v "$root":/w -w /w "$IMAGE" kicad-cli "$@"
  }
  have_docker=1
fi

mkdir -p docs/images docs/reports site/assets site/kicad

echo "==> ERC / DRC"
kicad sch erc --format json --severity-all -o docs/reports/erc.json "$SCH" || true
kicad pcb drc --format json --severity-all --schematic-parity -o docs/reports/drc.json "$PCB" || true

echo "==> Schematic SVG, BOM"
tmp="$(mktemp -d "$root/build.XXXXXX")"; trap 'rm -rf "$tmp"' EXIT
kicad sch export svg --exclude-drawing-sheet -o "${tmp#"$root"/}/sch" "$SCH"
cp "$tmp"/sch/*.svg docs/images/schematic.svg
kicad sch export bom \
  --fields 'Reference,Value,Footprint,${QUANTITY}' --labels 'Refs,Value,Footprint,Qty' \
  --group-by 'Value,Footprint' --ref-range-delimiter '' \
  -o hardware/bom.csv "$SCH"

echo "==> 3D renders"
render() { # name, extra args...
  local name="$1"; shift
  kicad pcb render --quality high --width 2000 --height 1500 --background transparent \
    "$@" -o "docs/images/$name.png" "$PCB"
}
render pcb-top    --side top
render pcb-bottom --side bottom
render pcb-iso        --side top    --perspective --rotate '-40,0,25'  --zoom 0.72
render pcb-iso-bottom --side bottom --perspective --rotate '-40,0,-25' --zoom 0.72

echo "==> Acrylic case (DXF, drawing, 3D viewer data)"
if command -v uv >/dev/null 2>&1; then
  uv run --quiet case/generate.py
else
  echo "   skipped (needs uv); case files left as is"
fi

echo "==> GLB model"
# Origin at the board centre so the case viewer can place the PCB inside the case.
origin="$(jq -r '.pcb.kicad_centre | "\(.[0] * 1000 | round / 1000)x\(.[1] * 1000 | round / 1000)mm"' site/assets/case.json)"
kicad pcb export glb --force --subst-models --include-tracks --include-pads \
  --include-zones --include-silkscreen --include-soldermask \
  --user-origin "$origin" \
  -o site/assets/atelier6k.glb "$PCB"
# One primitive per material: KiCad writes ~18k, which stalls browsers.
# Bump MODEL_VERSION in site/case.js and site/app.js when the model changes.
python3 tools/glb/merge.py site/assets/atelier6k.glb site/assets/atelier6k.glb
python3 tools/glb/quantize.py site/assets/atelier6k.glb site/assets/atelier6k.glb

echo "==> Rev 0 KiCad 6 sources for the in-browser viewer"
# KiCanvas reads the original KiCad 6 files, taken from the rev0 tag.
git show rev0-kicad6:atelier-alter/atelier-alter.kicad_sch > site/kicad/atelier6k.kicad_sch
git show rev0-kicad6:atelier-alter/atelier-alter.kicad_pcb > site/kicad/atelier6k.kicad_pcb

echo "==> Interactive BOM"
if [[ "${WITH_IBOM:-0}" != 1 ]]; then
  echo "   skipped (opt in with WITH_IBOM=1; downloads and runs InteractiveHtmlBom)"
elif (( have_docker )); then
  ibom="$tmp/ibom"
  git clone -q --depth 1 --branch "$IBOM_REF" https://github.com/openscopeproject/InteractiveHtmlBom.git "$ibom"
  mkdir -p "$tmp/out"
  # Third-party code: no network, sources mounted read-only, writes only to a scratch dir.
  docker run --rm --network none -u "$(id -u):$(id -g)" -e HOME=/tmp \
    -e INTERACTIVE_HTML_BOM_NO_DISPLAY=1 \
    -v "$root/hardware":/hw:ro -v "$ibom":/ibom:ro -v "$tmp/out":/out \
    "$IMAGE" python3 /ibom/InteractiveHtmlBom/generate_interactive_bom.py \
      --no-browser --dark-mode --include-tracks --include-nets \
      --dest-dir /out --name-format ibom /hw/atelier6k/atelier6k.kicad_pcb
  cp "$tmp/out/ibom.html" site/ibom.html
else
  echo "   skipped (needs docker); site/ibom.html left as is"
fi

echo "==> Copy shared images into the site"
cp docs/images/pcb-top.png docs/images/pcb-bottom.png docs/images/pcb-iso.png \
   docs/images/pcb-iso-bottom.png docs/images/schematic.svg \
   docs/images/case-layers.svg docs/images/case-exploded.png docs/images/case-assembled.png site/assets/

echo "Done. The case renders (docs/images/case-*.png) are screenshots of site/case.html; see docs/case.md."
