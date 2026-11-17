#!/usr/bin/env bash
# Builds the Atelier rev 2.0 firmware from the pinned libhmk submodule.
#   firmware/he/build.sh     -> build/fw/atelier-he.bin
# PLATFORMIO_CORE_DIR may point at a roomy disk (the toolchain is a few hundred MB).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
out="$root/build/fw"
src="$out/src"

[[ -f "$here/libhmk/setup.py" ]] || git -C "$root" submodule update --init firmware/he/libhmk

# Fresh copy of the pinned library, only ever inside build/fw.
case "$src" in "$root"/build/fw/src) rm -rf -- "$src" ;; *) echo "refusing to clean $src" >&2; exit 1 ;; esac
mkdir -p "$src"
(cd "$here/libhmk" && git archive HEAD) | tar -x -C "$src"
cp -r "$here/keyboards/atelier-he" "$src/keyboards/"
# Esc and Retry as keys (issue #12): our module plus a small patch to libhmk's matrix.c
cp "$here"/ext/include/*.h "$src/include/"
cp "$here"/ext/src/*.c "$src/src/"
patch -p1 --forward --silent -d "$src" < "$here/ext/libhmk-digital-keys.patch"

pio=(pio)
# libhmk's build scripts import pydantic inside PlatformIO's own Python
command -v pio >/dev/null || pio=(uvx --from "platformio==6.1.18" --with "pydantic~=2.11" pio)
cd "$src"
uv run --quiet --no-project --with "pydantic~=2.11" python setup.py -k atelier-he
"${pio[@]}" run -e atelier-he
cp ".pio/build/atelier-he/firmware.bin" "$out/atelier-he.bin"
echo "built $out/atelier-he.bin"
