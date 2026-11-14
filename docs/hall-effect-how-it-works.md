# How a Hall-effect key works

Written for anyone building or tuning Atelier6K rev 2. The design decisions
are in [`hall-effect-plan.md`](hall-effect-plan.md).

## 1. From a key press to a number

A magnetic switch has no electrical contacts. Its stem carries a small
permanent magnet. Under each switch, on the PCB, sits a **linear Hall
sensor**: a chip whose output voltage is proportional to the magnetic field
passing through it.

```
   key up                key down
  ┌──────┐              ┌──────┐
  │ stem │              │      │
  │ [N]  │ magnet       │      │
  │      │              │ stem │
  └──────┘  6.1 mm      │ [N]  │  2.1 mm
  ════════ PCB          ════════
    [H]   sensor          [H]
```

As the key goes down, the magnet approaches the sensor and the field rises,
fast at first close in and slowly far away. For the reference geometry
(2.8 × 3.4 mm magnet, 6.1 mm gap at rest, 4.0 mm travel) the field goes from
about 9 mT to 82 mT.

The sensor turns that into a voltage; the microcontroller's 12-bit ADC turns
the voltage into a number between 0 and 4095. One key is then a stream of
numbers, 8000 times a second, that says where the key is.

## 2. Calibration: numbers to millimetres

Every switch, magnet and sensor is slightly different, so the firmware learns
two numbers per key:

- **rest**: the reading with the key up, averaged at power-on;
- **bottom**: the deepest reading seen so far, updated whenever the key goes
  further than before.

The field is not linear with distance, so the reading is mapped to travel
through a curve: either a table measured once for the switch model (phase 1
of the plan), or a fitted function. After that, every key reports travel in
hundredths of a millimetre, and all settings are in millimetres.

Temperature moves the magnet's strength by about 0.1 % per °C. The firmware
follows slow drift by re-learning **rest** whenever a key has been still and
up for a while.

## 3. Noise and resolution

The reading jitters by a count or two even when nothing moves. Two tools
reduce that:

- **Oversampling**: take 32 readings and average them. Random noise falls by
  √32 ≈ 5.7; on this MCU the 3 keys × 32 samples take 48 µs.
- **Filtering**: a light exponential filter. Every filter adds delay, so its
  strength is a setting with its cost shown in microseconds.

What matters is how many counts one millimetre is worth **at the worst point
of the stroke**, which is the top, where the magnet is far away. The model
gives 40 counts/mm there for a 49E-type sensor. Six standard deviations of
the remaining noise must fit inside the smallest movement we want to detect,
which gives the **rapid-trigger floor**: about 0.040 mm for the 49E and
0.015 mm for the DRV5056A4, on paper. Phase 1 replaces both with measurements.

## 4. Actuation and rapid trigger

**Fixed actuation**, like a mechanical switch: pressed below a depth, released
above a slightly shallower depth (the gap prevents chatter). The finger must
lift all the way back above that line before the next press can start.

**Rapid trigger** ignores fixed lines and watches direction:

```
state RELEASED: track the highest point (lowest travel) since release.
                pressed  when travel > that point + press_sensitivity
state PRESSED:  track the deepest point since press.
                released when travel < that point − release_sensitivity
                (or the key is fully up)
```

So during a stream, a finger that bounces between 2.3 mm and 3.6 mm deep
produces a press and a release every cycle, even though it never comes back
above a 2.0 mm reset line. The interactive chart on the project site shows
this with the same rules.

**Continuous rapid trigger** keeps this behaviour until the key is fully up,
instead of switching it on only below the first actuation point.

Settings per key: actuation depth (first press), press sensitivity, release
sensitivity, and whether rapid trigger is continuous.

## 5. Getting the press to the computer

1. The ADC scan finishes (every 125 µs at 8 kHz).
2. Filter, calibrate, run the rapid-trigger state machine: a few
   microseconds on a 216 MHz Cortex-M4.
3. The new key state is written into the next USB report.
4. The host collects reports every 125 µs on USB High Speed (every 1 ms on
   Full Speed, which is what RP2040 boards are limited to).

Worst case from a key crossing its threshold to a report leaving the device:
250 µs at 8 kHz versus 1125 µs at 1 kHz. The finger's own motion is still
slower: rapid trigger saves milliseconds, polling saves fractions of one.

## 6. The LEDs must not disturb the keys

Addressable LEDs draw current in short pulses. If that current shares a
ground path with the sensors, or if LED data interrupts land during an ADC
sample, keys appear to move. The board avoids both: the sensors have their
own 3.3 V regulator and ground return, LED data goes out by DMA right after
a scan, and the performance profile turns the LEDs off.

## 7. Things that go wrong, and what they look like

| Symptom | Likely cause | Check |
|---|---|---|
| A key presses by itself | Bottom calibration too shallow, or noise above the RT setting | Raise sensitivity; log raw readings |
| A key never reaches full depth | Sensor saturating close to the magnet (the DRV5056A3 does with this magnet) | Usable travel in the model; use the A4 |
| Neighbour keys move together | Magnetic crosstalk between switches | Press one key, log its neighbours; compensate in calibration |
| Readings drift over an hour | Temperature | Rest re-learning interval |
| Readings wander on a humid day or after long play | Sweat or moisture film on the board (leakage on the analog outputs) | Coating intact? Gasket seated? Open and dry the case |
| Keys twitch when LEDs change | Shared ground or supply | Performance profile on; compare logs |
