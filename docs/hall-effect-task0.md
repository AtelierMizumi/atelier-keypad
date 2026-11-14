# Rev 2, Task 0: prices, pinouts, what to buy

Task 0 of the [build plan](superpowers/plans/2026-11-14-atelier6k-he.md).
Goal: know the real total before spending anything, and buy only what Task 1
(the bench test) needs first.

## Done at the desk (14 Nov 2026)

| Check | Result | Source |
|---|---|---|
| DRV5056 pinout (SOT-23) | 1 VCC, 2 OUT, 3 GND | [TI DRV5056](https://www.ti.com/lit/gpn/drv5056) |
| OH49E pinout | 1 VCC, 2 GND, 3 OUT; **not** interchangeable with the DRV5056 | [Ouzhuo OH49E](https://datasheetspdf.com/datasheet/OH49E.html) |
| DRV5056 sensitivity | 25 mV/mT (A4), 50 mV/mT (A3) at 5 V, ratiometric | TI datasheet |
| Which variant | **A4**: A3 saturates at 79 mT, this magnet gives 82 mT at bottom-out | `tools/he_model`, test `test_drv5056a3_saturates_before_bottom_out_but_a4_does_not` |
| OH49E at 3.3 V | Allowed (2.3 V minimum) but only characterised at 5 V | Ouzhuo datasheet |
| AT32F405 dev board | None found for sale (WeAct sells AT32F403A, not F405) | search, Nov 2026 |
| AT32F405 price | Not found; estimated 45–80k VND from the AT32F407 (2.95 USD) | [LCSC AT32F407RCT7](https://lcsc.com/product-detail/Microcontrollers-MCU-MPU-SOC_ARTERY-AT32F407RCT7_C528443.html) |
| JLCPCB, 5 boards ≤ 100 × 100 mm | 2 USD; shipping depends on address, seen only at checkout | [JLCPCB shipping](https://jlcpcb.com/help/article/how-much-does-shipping-cost) |
| Budget | Planned 884,000 VND; best 627,500; worst 1,726,500 | `hardware/he/bom.csv` |

## Needs you (10 minutes, no money spent)

These prices depend on your address and account, so only you can see them.
Write the numbers into the `plan_vnd` column of `hardware/he/bom.csv` and
run `python3 tools/he_model/budget.py hardware/he/bom.csv`; the test suite
fails if the total passes 1,000,000 VND.

1. **JLCPCB quote**: 2 layers, 80 × 50 mm, 5 pcs, 1.6 mm, any colour,
   country Vietnam. Note the cheapest shipping option and its price.
2. **LCSC cart**: put in the `lcsc` rows of the BOM (search the part names).
   At checkout, check whether it offers to ship together with a JLCPCB order,
   and what LCSC alone would cost to ship.
3. **Shopee**: search "Gateron Magnetic Jade" and "switch từ tính Gateron
   Jade". Make sure the listing says **5-pin / PCB mount** and **HE /
   magnetic**. Note price per switch.
4. **Laser shop**: ask for a quote on three 3 mm acrylic layers about
   90 × 60 mm (the DXF comes later; the size is enough for a quote).

Stop rule: if 1 + 2 together are over 450,000 VND, use Plan B.

## Buy first (for Task 1, the bench)

Only what proves the sensor works with the switch, before any PCB:

| Item | Why | About |
|---|---|---|
| 4 × Gateron Magnetic Jade (PCB mount) | 3 for the board, 1 for the bench | 60–100k |
| 2 × SS49E or OH49E in **TO-92** from a local shop | Breadboard-friendly stand-in to measure the field curve | 10k |
| Any board with an ADC you already own (Arduino, ESP32, RP2040) | Logs readings over USB serial | 0 |
| A digital caliper, if you have none | Sets the key depth for each reading | 100–150k |

The TO-92 49E reads the same field as the SOT-23 part on the PCB will (its
sensing element sits slightly deeper, which the bench measures). The DRV5056
itself comes with the LCSC order in Task 3, after the bench confirms the curve.

## Plan B: no LCSC order

If shipping breaks the budget:

- **RP2040-Zero** from a local shop (~100–120k VND) instead of the AT32F405:
  **1 kHz, not 8 kHz**, otherwise the same design. Its 4 ADC inputs are
  enough for 3 keys.
- **49E in TO-92**, bought locally, laid flat in a slot under each switch
  instead of the SOT-23 DRV5056. The model gives a 0.040 mm rapid-trigger
  floor for the 49E with 32× oversampling: still finer than the 0.1 mm most
  boards advertise.
- Only one overseas order remains: the PCB from JLCPCB.

Plan B loses the 8 kHz claim and keeps everything else (sealed case,
three-key arc, rapid trigger, art).
