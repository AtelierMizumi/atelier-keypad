# Atelier rev 2.0 firmware (libhmk)

GPL-3.0, like [libhmk](https://github.com/peppapighs/libhmk), which it builds on.
The rest of the repository keeps its own licence.

| | |
|---|---|
| libhmk | git submodule `libhmk/`, pinned to **v1.8.1** (`1d2b2e2101fa4509700a24152d33335ddfda8240`) |
| Config | `keyboards/atelier-he/keyboard.json`: AT32F405, 12 MHz HSE, USB HS (8 kHz), 3 analog keys on PA2/PA1/PA0 |
| Build | `./build.sh` → `build/fw/atelier-he.bin` (repository root) |
| Tests | `uv run --no-project --with pytest pytest -q` (config against `circuit.py` and the field model) |

`build.sh` copies the pinned libhmk into `build/fw/src/`, adds the Atelier
config, and runs PlatformIO there. The submodule itself is never modified.
PlatformIO downloads its toolchain and TinyUSB on the first build, so the
first build needs network access (CI always has it).

## Known gaps (rev 2.0)

- **Esc and Retry buttons (PB12, PB5) are not read.** libhmk v1.8.1 scans
  analog keys only. They need a small digital-key extension. This is tracked as
  an issue; until then the three Hall keys work and the buttons do nothing.
- **No LEDs.** libhmk has no RGB support; the SK6812 chain on PB0 stays dark.
- **USB ID 0x1209:0x0001** is pid.codes' test PID. Register a PID at
  pid.codes before sharing builds.

## Flashing

Hold BOOT, plug in, then release: the AT32F405 ROM bootloader shows up as a
DFU device on the USB HS port. Flash `atelier-he.bin` with
[WebUSB DFU](https://devanlai.github.io/webdfu/dfu-util/) (libhmk's
recommendation), or `dfu-util -a 0 -s 0x08000000:leave -D atelier-he.bin`.
