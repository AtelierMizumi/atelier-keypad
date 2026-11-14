# Rev 2 (Hall effect): the board

Designed, routed and checked; **not built**. Tasks 3, 5 and 6 of the
[build plan](superpowers/plans/2026-11-14-atelier6k-he.md) are done at the
desk; Tasks 1 and 2 (bench measurements) and 4 (firmware) are not.

```sh
scripts/he.sh          # circuit tests, schematic, place + route, ERC, netlist, DRC,
                       # layout tests, renders, case, 3D model
scripts/he.sh check    # checks only, on the files as they are
```

## Results

| Check | Result |
|---|---|
| Circuit tests (`hardware/he/tests/test_circuit.py`) | 19 pass |
| Layout tests on the routed board (`tests/test_layout.py`) | 7 pass |
| ERC | 0 |
| Netlist against `circuit.py` | 34 nets, 178 pins, identical |
| DRC | 0 errors, 0 unconnected, schematic parity 0; 8 silkscreen warnings |
| Routing | 648 track segments, 330 vias (about 260 of them stitch the two ground pours) |
| USB pair, connector to MCU | under 15 mm each, matched within 3 mm |
| Case tests (`case/tests/test_case_he.py`) | 14 pass (50 with rev 0 and rev 1) |

![Rev 2 top](images/rev2-pcb-top.png)

## What the files are

| File | Job |
|---|---|
| `hardware/he/circuit.py` | Every part, net and position; the AT32F405 LQFP48 pin table from the datasheet |
| `hardware/he/gen_lib.py` | AT32F405 symbol (from that table) and the PCB-mount magnetic switch footprint |
| `hardware/he/gen_sch.py` | The schematic (adapted from rev 1) |
| `hardware/he/gen_pcb.py` | Outline, footprints, ground pours, the art keep-out, silkscreen easter eggs |
| `hardware/he/route.py` | Rev 1's maze router tuned for 0.5 mm pitch, plus ground stitching |
| `case/generate_he.py` | The sealed case: DXF in `case/dxf-he/`, model in `site/assets/case-he.json` |
| `tools/pcb_art/` | The four-tone art footprint and its original artwork |

## Decisions made while laying it out

Each of these came from a failed check, not from the plan:

- **One LDO, a ferrite to the analog rail.** The datasheet requires VDDA at the
  same potential as VDD, so the sensors and VDDA hang off the 3.3 V rail
  through a 600 Ω ferrite instead of a second regulator.
- **The USB-C receptacle sits 2.5 mm in from the edge.** Its front shield legs
  were outside the board at the edge.
- **The MCU sits on the 0.25 mm routing grid.** Half a grid step off, its side
  pins became unreachable for the router.
- **ADC channels ordered K1 → PA2, K2 → PA1, K3 → PA0** so the three sensor
  traces fan out from the MCU without crossing.
- **The CC1 pull-down is an 0402 right under its pad.** CC1 is boxed in between
  the left VBUS pad and the USB pair; any other position needed a crossing.
- **The ESD array is beside the connector, not in line.** In line, its VBUS pin
  was trapped between the two data lanes; beside the connector, the branch is
  under 10 mm, and a test keeps it that way.
- **Some decoupling sits on the top side,** directly above its pin and outside
  the switch bodies, where the bottom was too crowded.
- **Ground vias placed before routing under the MCU,** where the fan-out
  otherwise cuts off a ground island.
- **The art moved to the top, into a palm area,** under the clear cover. On the
  bottom it shared the space with the LED chain and the sensor filters.
- **The 6° angle comes from the feet** (1.0 mm front, 7.5 mm rear) instead of a
  wedge layer: cheaper, and swapping feet gives the flat A/B test.

## Before ordering

- Bench Task 1: confirm the field curve and noise of the real switch and
  sensor; the RT floor numbers are from the model.
- Check the magnetic switch's bottom: the footprint assumes no centre post
  (the sensor is there).
- Check pin 1 orientation of the SK6812MINI-E against the part bought (open
  since rev 1).
- Confirm the AT32F405CCT7 price and stock; replace the estimate in `bom.csv`.
- Export Gerbers and the position file (not done yet).
