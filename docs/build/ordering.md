# Rev 2.0: ordering, step by step

Where to buy, and why: [sourcing-vn.md](sourcing-vn.md). Budget:
`hardware/he/bom.csv` (`python3 tools/he_model/budget.py hardware/he/bom.csv`).

Order in this sequence. Each step only spends money once the step before it
has passed.

## 0. Gate G1: is the MCU buyable? (no money)

1. Search **AT32F405CCT7** on Taobao (an agency's app or website shows it) and
   on szlcsc.com.
2. Write the cheapest shop that also sells the other chips in step 2 into
   `hardware/he/bom.csv`.
3. **If no shop has it, stop.** Rev 2.0 then becomes Plan B (RP2040, 1 kHz),
   which needs its own board.

## 1. Files

Take the latest `rev2.0-package` from CI (Actions → latest run → Artifacts, or
the GitHub Release). Until CI exists, build it locally with `scripts/fab.sh`
(plan Task 4). Inside:

| File | For |
|---|---|
| `gerbers/` + drill files, zipped by you | PCB fab |
| `bom-jlcpcb.csv`, `cpl-jlcpcb.csv` | Only if you ever pay for assembly |
| `case-dxf/*.dxf` | Laser shop |
| `firmware.bin` | Flashing (see [user-guide.md](user-guide.md)) |

## 2. Chips: one China order through an agency

Put all of these in one cart at one shop. Buy spares of the small parts: they
are cheap, and easy to lose under hot air.

| Part | Qty (incl. spares) | Package |
|---|---|---|
| AT32F405CCT7 | 1 (2 if cheap) | LQFP-48 |
| DRV5056A4QDBZR (LCSC C2152902) | 4 | SOT-23. Not the QDBZT (obsolete), not the TO-92 QLPG |
| LP5907MFX-3.3 | 2 | SOT-23-5 |
| USBLC6-2SC6 | 2 | SOT-23-6 |
| 74AHCT1G125 | 2 | SOT-23-5 |
| SK6812MINI-E | 10 | 3.2 × 2.8 mm reverse-mount |
| Crystal 12 MHz, 3225, 20 pF load (LCSC C9002) | 2 | 3.2 × 2.5 mm, 4 pads |
| USB-C 16-pin receptacle HRO TYPE-C-31-M-12 | 2 | |
| Polyfuse 500 mA | 2 | 1206 |
| Ferrite 600 Ω @ 100 MHz | 2 | 0603 |

Ask the agency for the cheapest consolidated shipping, and to hold the parcel
until everything has arrived at their warehouse.

## 3. Passives and buttons (local shop or the same China order)

All 0603 unless noted. Quantities include about 50 % spares.

| Value | Used | Buy |
|---|---|---|
| 100 nF | 16 | 25 |
| 1 µF | 3 | 5 |
| 4.7 µF (0805) | 2 | 5 |
| 47 nF | 3 | 5 |
| 33 pF (C0G) | 2 | 5 |
| 4.7 nF | 1 | 5 |
| 1 kΩ | 3 | 5 |
| 5.1 kΩ (one 0603, one **0402**) | 2 | 5 + 5 |
| 10 kΩ | 1 | 5 |
| 12 kΩ **1 %** | 1 | 5 |
| 1 MΩ | 1 | 5 |
| 330 Ω | 1 | 5 |

Buttons:
- 2 × tact switch 6 × 6 mm THT, 7.3 mm tall (Esc and Retry).
- 1 × TL3342 SMD (BOOT).

## 4. PCB (CXT or SmartPCB88)

Send the zipped Gerbers with this message:

> Chào shop, em đặt mạch 2 lớp, kích thước 76 × 70 mm, số lượng 5, **độ dày
> 1.2 mm**, phủ xanh hoặc đen, chữ trắng, HASL không chì, đồng 1 oz, đi đường
> bộ. Mạch có lỗ khoan không mạ (NPTH) 1.75 mm và có linh kiện cả 2 mặt. Shop
> báo giá giúp em, và cho em hỏi có làm kèm stencil (khung thép) không ạ?

(In English: 2 layers, 76 × 70 mm, 5 pcs, **1.2 mm thick**, green or black
mask, white silk, lead-free HASL, 1 oz copper, road shipping; the board has
1.75 mm NPTH holes and parts on both sides; please quote, and do you also make
a stencil?)

Check the quote says 1.2 mm before paying. If it says 1.6 mm, ask them to fix
it. At 1.6 mm the field model and the case no longer match.

## 5. Switches and keycaps

- 4 × Gateron Magnetic Jade (original, PCB mount) from TechSpace. Three go on
  the board, one is a spare.
- 4 × 1u keycaps, any MX-stem set.
- When the switches arrive, before ordering the chips if you can, do the
  compass check in `docs/rev2-bringup.md` step 0. If the magnets face
  south-down, buy DRV5055A4 instead of DRV5056A4.

## 6. Acrylic

Send the five DXF files to two or three shops with:

> Chào shop, em cần cắt laser mica theo 5 file DXF đính kèm (đơn vị mm,
> 1 bộ): đế 3 mm trong suốt; vách dưới 5 mm, vòng bo mạch 2 mm, đệm 2 mm,
> nắp 2 mm, tất cả xanh dương trong (translucent blue). Shop báo giá trọn
> gói gồm vật liệu và phí ship giúp em.

(In English: laser-cut acrylic from the 5 attached DXF files, units mm, one
set: a 3 mm clear base; 5 mm lower wall, 2 mm board ring, 2 mm spacer and 2 mm
cover, all translucent blue; please quote everything including material and
shipping.)

The file names say the thickness and colour of each layer.

## 7. Small things (Shopee or a hardware street)

- **EVA foam**, 0.5 mm and 1.0 mm sheets. The cover gasket is cut from the
  spacer outline; the 1.0 mm strips go under the board edge.
- **Hardware:** 4 × nylon M3 × 14 screws plus nuts.
- **Grip pad:** one self-adhesive silicone sheet, 1.5 mm, at least 85 × 80 mm.
  Cut it to `atelier-he-pad-1.5mm-silicone.dxf` (laser or a sharp knife over a
  print); it replaces the rubber feet.
- **Soldering supplies:** acrylic conformal coating, flux, solder paste or
  0.5 mm solder, wick.

## 8. After it all arrives

Assemble and accept with `docs/rev2-bringup.md` (plan Task 7). Then write the
real prices into `bom.csv`, so the next person's budget is real too.
