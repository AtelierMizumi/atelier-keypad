# Atelier rev 2.0: user guide

> Draft. Firmware (plan Task 5) and bring-up (Task 7) are not done yet. Any
> step marked *(to confirm)* is checked during bring-up and then edited here.

## What it is

Three Hall-effect keys for osu! (K1, K2, K3, left to right), plus two small
buttons above them, Esc and Retry. Each key reads its own depth, so a key can
actuate at any depth, and rapid trigger releases it the moment it starts
rising. USB-C, 8 kHz polling, firmware [libhmk](https://github.com/peppapighs/libhmk).

## Default layout *(to confirm)*

| Key | Sends |
|---|---|
| K1 / K2 / K3 | Z / X / C |
| Esc | Esc |
| Retry | `` ` `` (osu! quick retry: hold it) |

## Settings

Settings open in libhmk's web configurator (**hmkconf**) in Chrome or Edge, with
no install. They are saved on the keypad, so they apply on any computer.

| Setting | Start here | What it does |
|---|---|---|
| Actuation point | 1.2 mm | Depth at which the key presses |
| Rapid trigger, press | 0.15 mm | Movement down that presses again |
| Rapid trigger, release | 0.15 mm | Movement up that releases |
| Continuous rapid trigger | On | Rapid trigger stays live until the key is fully up |

Lower the rapid-trigger values in steps of 0.05 mm. Stop when keys start to
chatter while you rest a finger on them. The hardware can resolve about
0.03 mm (`docs/research/he-switch-field.md`). Your fingers resting on a key
are the real limit.

**Calibration is automatic.** After plugging in, press each key all the way
down once, so it learns the bottom of that switch. Do this again after
swapping a switch.

## Updating the firmware *(to confirm)*

1. Unplug. Hold **BOOT** through the hole in the base, plug in, then release.
   The keypad now shows up as a DFU device.
2. Flash `firmware.bin` from the latest Release. hmkconf has an update page;
   from the repo, `pio run --target upload` in `firmware/he/` also works.
3. Unplug and replug.

Nothing can brick it: the bootloader lives in the chip's ROM.

## Swapping switches

The switches have no electrical pins, so nothing is soldered.

1. Remove the four screws and lift the cover.
2. Pull the switch.
3. Press the new one in, **north pole down** (as Gateron ships them; the
   switch only fits one way).
4. Replug, and press each key to the bottom once.

## Care

- The case is sealed against sweat at the top. The board inside is
  conformally coated.
- **Cleaning:** wipe the cover with a damp cloth. No alcohol on acrylic, since
  it crazes.
- **Keep magnets away.** A magnet on the desk shifts the readings until it is
  moved away again.
- **Typing angle:** the 6° comes from the rear feet. Swap them for the 1 mm
  front feet to make it flat.

## If something is wrong

| Symptom | Check |
|---|---|
| A key presses on its own | Raise its rapid-trigger values. Press it to the bottom once to recalibrate. Check for a magnet nearby |
| A key never presses | Is the switch fully seated? Press it to the bottom once |
| Not detected on USB | Try another cable (some are charge-only). In BOOT mode it shows up as DFU |
| Lights off | The LEDs are not driven by libhmk (no RGB support); expected |
