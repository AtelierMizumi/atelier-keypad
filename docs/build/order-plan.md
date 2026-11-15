# Order plan for all three revisions

Written on 16 Nov 2026. **Order rev 2.0.** Do not order rev 0. Order rev 1 only
if you want a mechanical pad to play on while rev 2.0 is being built; its parts
ride along with two of rev 2.0's orders.

| | Rev 0 (2022) | Rev 1 (2026) | Rev 2.0 (Hall effect) |
|---|---|---|---|
| Order it? | **No** | Optional | **Yes** |
| MCU | ATmega32U4 on the board | RP2040-Zero module, hand-soldered | AT32F405CCT7, LQFP-48 |
| Checks | ERC 7 errors, DRC 240 errors | ERC 0, DRC 0 | ERC 0, DRC 0 |
| Blocked by | 4 design blockers ([review](../design-review.md)) | Measure the module notch; check the LED chamfer | The MCU (bought on a WeAct board) |
| PCB | 2 layers; the file says 1.09 mm | 2 layers 1.6 mm + a 1.6 mm FR4 plate | 2 layers **1.2 mm** |
| Assembly | By hand | By hand. JLCPCB two-sided assembly costs about 51 USD setup + 16 USD stencil ([price page](https://jlcpcb.com/help/article/pcb-assembly-price)), more than the parts | By hand, hot air for the MCU |
| Files | 2022 Gerbers | CI artifact `rev1-package` | CI artifact `rev2.0-package` |
| One unit | n/a | about 0.7–0.9 M VND, estimated | **990,500 VND** planned (`hardware/he/bom.csv`) |

The rev 1 figure is an estimate. It reuses rev 2.0's prices for the shared
parts (PCB, acrylic, shipping) and adds the module, the sockets and the
mechanical switches. Rev 1 has no priced BOM yet.

## Sequence and gates

Each gate must pass before money goes to the next step.

| Step | Rev 2.0 | Gate before the next step | Rev 1 rides along |
|---|---|---|---|
| 1 | 2 × WeAct AT32F405CCT7 Core Board (AliExpress): one gives the MCU, one runs libhmk early | The board enumerates at 480M (`lsusb -t`) | |
| 2 | 4 × Gateron Magnetic Jade + 4 keycaps | Compass: north pole faces down | |
| 3 | One China chip order through an agency ([ordering.md](ordering.md) §2–3) | | Its SMD parts (`bom-jlcpcb.csv`) go in the same cart |
| 4 | PCB, 2 layers, 1.2 mm, 5 pcs (CXT or SmartPCB88) | The quote says 1.2 mm | Board + plate (`plate-gerbers/`, "no copper, outline only") in the same order |
| 5 | Acrylic case (5 layers) + 1.5 mm silicone pad | The DXF's 50 mm bar measures 50 mm | 3 acrylic layers at the same shop |
| 6 | Assemble in stages and accept ([rev2-bringup.md](../rev2-bringup.md)) | | Hand parts: RP2040-Zero ([LCSC C5350143](https://www.lcsc.com/product-detail/C5350143.html)), 6 Kailh MX sockets, 3 tact switches, 6 MX switches |

## Why not rev 0

The design review says "Do not order rev 0 as it is". There is no fuse, the
LEDs can draw more than USB allows, the underglow chain is driven as a PWM
light, and the per-key LED part is ambiguous. The rev 0.2 the review proposes
is exactly what rev 1 became. The 2022 files stay as a record.

## Open questions

- Rev 1: build it or not? If not, leave its lines out of the shared orders.
- Does the libhmk build fit in 128 KB? If so, the AT32F405CBT7 (same LQFP-48)
  works too.
- Rev 1 hand parts have no Vietnamese prices yet.
