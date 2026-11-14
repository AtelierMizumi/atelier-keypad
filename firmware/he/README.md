# Atelier rev 2.0 firmware (libhmk)

GPL-3.0, like [libhmk](https://github.com/peppapighs/libhmk), which it builds on.
The rest of the repository keeps its own licence.

| | |
|---|---|
| libhmk | git submodule `libhmk/`, pinned to **v1.8.1** (`1d2b2e2101fa4509700a24152d33335ddfda8240`) |
| Config | `keyboards/atelier-he/keyboard.json`: AT32F405, 12 MHz HSE, USB HS (8 kHz), 3 analog keys on PA2/PA1/PA0, Esc and Retry on PB12/PB5 |
| Buttons | `ext/`: `digital_keys.c` + a small patch to libhmk's `matrix.c` (issue #12) |
| Build | `./build.sh` → `build/fw/atelier-he.bin` (repository root) |
| Tests | `uv run --no-project --with pytest pytest -q` (config against `circuit.py` and the field model) |

`build.sh` copies the pinned libhmk into `build/fw/src/`, adds the Atelier
config, and runs PlatformIO there. The submodule itself is never modified.
PlatformIO downloads its toolchain and TinyUSB on the first build, so the
first build needs network access (CI always has it).

## Esc and Retry

libhmk v1.8.1 scans analog keys only. `ext/` adds the two tact switches as
keys 4 and 5:

- `ext/src/digital_keys.c` reads PB12 and PB5 (internal pull-up, button to GND).
- It hands `matrix.c` the ADC value of a key at rest or fully pressed, so the
  keymap, layers and the configurator treat them like any other key.
- `ext/include/digital_debounce.h` is an eager debounce: a press is reported
  on the first sample, then the key is locked for 5 ms. It is plain C and
  tested on the host by `tests/test_digital_keys.py`.
- `ext/libhmk-digital-keys.patch` hooks the module into `matrix.c`. It only
  takes effect for a keyboard that ships `digital_keys_config.h`.
  `build.sh` applies it to the build copy, never to the submodule.

## Known gaps (rev 2.0)

- **No LEDs.** libhmk has no RGB support; the SK6812 chain on PB0 stays dark.
- **USB ID 0x1209:0x0001** is pid.codes' test PID. Register a PID at
  pid.codes before sharing builds.

## Flashing

Hold BOOT, plug in, then release: the AT32F405 ROM bootloader shows up as a
DFU device on the USB HS port. Flash `atelier-he.bin` with
[WebUSB DFU](https://devanlai.github.io/webdfu/dfu-util/) (libhmk's
recommendation), or `dfu-util -a 0 -s 0x08000000:leave -D atelier-he.bin`.
