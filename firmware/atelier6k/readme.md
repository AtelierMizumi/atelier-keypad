# Atelier6K

A 6-key osu! keypad with three extra buttons, per-key and underglow RGB.

* Keyboard Maintainer: [thuanc177](https://github.com/AtelierMizumi)
* Hardware Supported: Atelier6K rev 1 (RP2040-Zero module)
* Hardware Availability: open hardware, <https://github.com/AtelierMizumi/atelier-keypad>

Make example for this keyboard (after setting up your build environment):

    make atelier6k:default

Flashing example for this keyboard:

    make atelier6k:default:flash

See the [build environment setup](https://docs.qmk.fm/#/getting_started_build_tools) and the [make instructions](https://docs.qmk.fm/#/getting_started_make_guide) for more information. Brand new to QMK? Start with our [Complete Newbs Guide](https://docs.qmk.fm/#/newbs).

## Bootloader

Enter the bootloader in 3 ways:

* **Bootmagic reset**: hold the top-left key (K1) while plugging in the keypad
* **Physical button**: hold BOOT on the RP2040-Zero module while plugging in, or hold BOOT and tap RESET
* **Keycode in layout**: press the key mapped to `QK_BOOT` if it is assigned

The keypad then appears as a USB drive named `RPI-RP2`; copy the `.uf2` file onto it.
