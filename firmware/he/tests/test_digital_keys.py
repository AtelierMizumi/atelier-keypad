"""Esc and Retry (issue #12): two tact switches to GND on PB12 and PB5, read as libhmk keys 4 and 5.

libhmk v1.8.1 only scans analog keys, so each button is turned into the ADC value of a key
at rest or at bottom-out. The debounce logic is plain C in ext/include/digital_debounce.h and
is compiled and run on the host here; the GPIO side is checked by the firmware build.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import circuit

HE = Path(__file__).resolve().parents[1]
INC = HE / "ext" / "include"
KB = json.loads((HE / "keyboards" / "atelier-he" / "keyboard.json").read_text())

HARNESS = r"""
#include <stdio.h>
#include "digital_debounce.h"
int main(void) {
  /* each line of stdin: "<raw 0|1> <now ms>"; prints the debounced state */
  debounce_t d = {0};
  int raw; unsigned now;
  while (scanf("%d %u", &raw, &now) == 2) printf("%d", debounce_update(&d, raw != 0, now));
  printf(" %u %u\n", digital_key_value(false, 790, 4095), digital_key_value(true, 790, 4095));
  return 0;
}
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc")
    if not cc:
        pytest.skip("no host C compiler")
    tmp = tmp_path_factory.mktemp("debounce")
    (tmp / "t.c").write_text(HARNESS)
    exe = tmp / "t"
    subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-I", str(INC), str(tmp / "t.c"), "-o", str(exe)],
                   check=True)

    def go(samples):
        out = subprocess.run([str(exe)], input="".join(f"{r} {t}\n" for r, t in samples),
                             capture_output=True, text=True, check=True).stdout.split()
        return out[0] if samples else "", tuple(int(x) for x in out[-2:])
    return go


def test_press_is_reported_on_the_first_sample(run):
    states, _ = run([(0, 0), (1, 1)])
    assert states == "01"


def test_bounce_after_a_press_is_ignored_for_5_ms(run):
    states, _ = run([(1, 0), (0, 1), (1, 2), (0, 3), (0, 4), (0, 6)])
    assert states == "111110"


def test_release_is_reported_at_once_when_the_lockout_is_over(run):
    states, _ = run([(1, 0), (1, 10), (0, 11)])
    assert states == "110"


def test_bounce_after_a_release_is_ignored_too(run):
    states, _ = run([(1, 0), (0, 10), (1, 11), (0, 12), (1, 16)])
    assert states == "10001"


def test_timer_wraparound_does_not_lock_the_key(run):
    states, _ = run([(1, 4294967294), (0, 4294967295), (0, 4)])
    assert states == "110"


def test_buttons_read_as_rest_or_full_scale(run):
    _, (released, pressed) = run([])
    assert (released, pressed) == (790, 4095)


def test_keyboard_json_has_five_keys_with_esc_and_retry():
    assert KB["keyboard"]["num_keys"] == 5
    assert KB["keymap"][0] == ["KC_Z", "KC_X", "KC_C", "KC_ESC", "KC_GRV"]
    assert sorted(k["key"] for row in KB["layout"]["keymap"] for k in row) == [0, 1, 2, 3, 4]
    # the buttons are not ADC inputs
    assert sorted(KB["analog"]["raw"]["vector"]) == [1, 2, 3]


def test_button_pins_match_circuit():
    cfg = (HE / "keyboards" / "atelier-he" / "digital_keys_config.h").read_text()
    pins = re.findall(r"\{\s*GPIO([A-Z]),\s*GPIO_PINS_(\d+)\s*\}", cfg)
    assert [f"P{port}{n}" for port, n in pins] == [circuit.BUTTON_PINS["SW1"], circuit.BUTTON_PINS["SW2"]]
    assert re.search(r"#define\s+DIGITAL_KEYS_FIRST\s+3\b", cfg)


def test_patch_applies_to_the_pinned_libhmk():
    patch = HE / "ext" / "libhmk-digital-keys.patch"
    subprocess.run(["git", "-C", str(HE / "libhmk"), "apply", "--check", str(patch)], check=True)
