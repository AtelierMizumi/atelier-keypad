#!/usr/bin/env bash
# Runs the debounce unit tests and builds the Atelier6K firmware with the
# official QMK container.
#
#   scripts/firmware.sh test     unit tests only
#   scripts/firmware.sh build    compile the .uf2 into firmware/build/
#   scripts/firmware.sh          both
#
# QMK_HOME must point at a qmk_firmware checkout (with submodules) at the tag
# below. The keyboard and its tests are copied into that checkout; nothing
# else in it is modified apart from registering the test.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QMK_HOME="${QMK_HOME:-/mnt/500GBext4/qmk-build/qmk_firmware}"
QMK_TAG="0.34.8"
IMAGE="${QMK_IMAGE:-qmkfm/qmk_cli:1.2.0}"
KB=atelier6k
KM="${KEYMAP:-default}"
what="${1:-all}"

[[ -d "$QMK_HOME/quantum" ]] || { echo "QMK_HOME=$QMK_HOME is not a qmk_firmware checkout (expected tag $QMK_TAG)" >&2; exit 1; }

qmk() {
  docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp \
    -v "$QMK_HOME":/qmk -w /qmk "$IMAGE" \
    sh -c 'git config --global --add safe.directory "*"; "$@"' sh "$@"
}

echo "==> Copy keyboard into $QMK_HOME/keyboards/$KB"
dest="$QMK_HOME/keyboards/$KB"
[[ "$dest" == */keyboards/atelier6k ]] || { echo "refusing to sync to $dest" >&2; exit 1; }
mkdir -p "$dest"
rsync -a --delete --exclude tests "$root/firmware/$KB/" "$dest/"

if [[ "$what" == test || "$what" == all ]]; then
  echo "==> Unit tests"
  tests="$QMK_HOME/quantum/debounce/tests"
  cp "$root/firmware/$KB/tests/debounce_runtime_tests.cpp" "$tests/atelier_runtime_tests.cpp"
  if ! grep -q debounce_atelier_runtime "$tests/testlist.mk"; then
    printf '\nTEST_LIST += debounce_atelier_runtime\n' >> "$tests/testlist.mk"
    cat >> "$tests/rules.mk" <<'MK'

debounce_atelier_runtime_DEFS := $(DEBOUNCE_COMMON_DEFS)
debounce_atelier_runtime_INC := keyboards/atelier6k
debounce_atelier_runtime_SRC := $(DEBOUNCE_COMMON_SRC) \
	keyboards/atelier6k/debounce_runtime.c \
	$(QUANTUM_PATH)/debounce/tests/atelier_runtime_tests.cpp
MK
  fi
  qmk make test:debounce_atelier_runtime
fi

if [[ "$what" == build || "$what" == all ]]; then
  echo "==> Lint and compile $KB:$KM"
  qmk qmk lint -kb "$KB" || true
  qmk qmk compile -kb "$KB" -km "$KM"
  mkdir -p "$root/firmware/build"
  cp "$QMK_HOME/${KB}_${KM}.uf2" "$root/firmware/build/"
  ls -la "$root/firmware/build/${KB}_${KM}.uf2"
fi
