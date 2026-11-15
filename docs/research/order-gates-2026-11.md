# Order gates: what was checked on 16 Nov 2026

Rev 2.0 had three questions that ERC and DRC cannot answer. Rev 1 shares one of
them (the LED). This note records what desk research settled, what it did not,
and where each answer comes from. None of it replaces looking at the real part
on the bench.

| Gate | Question | Answer | Confidence |
|---|---|---|---|
| Magnet pole | Which pole of a Gateron Magnetic Jade magnet faces the PCB? | **North, facing down to the PCB** | High: Gateron's own product pages |
| LED pinout | Does KiCad's SK6812MINI-E reverse-mount footprint put each signal on the right corner? | **Yes** | High: three OPSCO datasheets agree, and the footprint matches their bottom view |
| G1, MCU | Can the AT32F405**C**CT7 (LQFP-48) be bought? | **Still open.** LCSC and JLCPCB list no LQFP-48 part. LCSC does stock the LQFP-64 AT32F405**R**CT7-7 | Medium: the search pages render prices and stock with JavaScript |

## Magnet pole: north down

Gateron's Magnetic Jade product pages (Pro, Ultra, Delta) state that "the
magnetic switches N-pole faces down to the PCB board". A retailer's listing of
the plain Jade 30 g switch gives "Magnetic North Direction: downward". The one
exception found is the dual-rail *Jade Mini E*, an "E version" with the north
pole towards the LED, made for boards such as the Boog75. It is not the switch
this board uses.

This is what the firmware and the unipolar DRV5056A4 assume, so **keep the
DRV5056A4**. The compass check in `docs/rev2-bringup.md` step 0 is still worth
the minute it takes: it costs nothing, and it catches a mislabelled batch.

gateron.com refuses automated fetches (HTTP 403). The quote above comes from the
search engine's copy of the page. Open one product page in a browser before
ordering, to see that it still says the same thing.

## LED pinout: the footprint is right

The datasheets number the pins differently from KiCad, but the signal at each
corner is the same in both. Only the corners matter.

- OPSCO SK6812MINI-E-012 (the maker of LCSC C5149201), the SK6812 MINI-EA
  (A/0, 2022) and the Adafruit-hosted SK6812MINI-E Rev.02 all use
  **1 VDD, 2 DOUT, 3 GND, 4 DIN**.
- The OPSCO drawing, **top view** (lens up): VDD top left, DIN top right,
  DOUT bottom left, GND bottom right. The chamfer is on the GND corner.
- **Bottom view** (mirrored): DIN top left, VDD top right, GND bottom left,
  DOUT bottom right.
- KiCad's `LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount`, with the KiCad
  `SK6812MINI-E` symbol (1 VSS, 2 DIN, 3 VDD, 4 DOUT):
  pad 2 DIN at (−2.725, −0.75) top left, pad 3 VDD at (+2.725, −0.75) top
  right, pad 1 GND at (−2.725, +0.75) bottom left, pad 4 DOUT at
  (+2.725, +0.75) bottom right.

A reverse-mount LED is soldered on its back, lens through the board, so the
footprint must match the **bottom view**, and it does, corner for corner. The
footprint's own description links to the LCSC C5149201 datasheet. Mirrored,
VDD and DIN would trade places and 5 V would land on the data pin; this check
rules that out.

Still to check on the bench: the chamfer and polarity mark on the reel's parts,
against the silkscreen. Datasheet revisions have disagreed before.

## G1: the MCU

- **AT32F405CCT7 (LQFP-48, the part on the board): no listing found.** LCSC and
  szlcsc show no product page. JLCPCB's parts search for "AT32F405" returns
  "0 Found". One Chinese distributor (Manduic) lists it as out of stock.
- **AT32F405RCT7-7 (LQFP-64, 7 × 7 mm): LCSC C19674180.** The search engine's
  copy showed "from $1.6985, 129 in stock". The live page did not render stock
  when fetched, so treat that figure as dated. It is not in JLCPCB's assembly
  library, so it would be hand-soldered or shipped to JLCPCB as a consigned
  part.
- Artery's datasheet (V2.02, January 2025) lists the AT32F405 in LQFP64
  10 × 10, LQFP64 7 × 7, LQFP48 7 × 7, QFN48 6 × 6 and QFN32 4 × 4. Only the
  AT32F405 has the High Speed USB PHY; the AT32F402 does not, so it is no
  substitute.

What to do, in order:

1. Search **AT32F405CCT7** on Taobao through an order agency, as
   `docs/build/ordering.md` already says. If a shop has it, nothing changes.
2. If none does: **rev 2.1 on the AT32F405RCT7-7.** The body is the same
   7 × 7 mm, but it has 64 pins at 0.4 mm pitch instead of 48 at 0.5 mm. The
   footprint, the pin map and the routing around the MCU change, and the
   firmware's pin map follows. That is a board revision, not a BOM swap. Plan
   it with the usual tests, since a 0.4 mm-pitch LQFP is harder to hand-solder.

## Sources

- Gateron Magnetic Jade Pro: https://www.gateron.com/products/gateron-magnetic-jade-pro-switch-set
- Gateron Magnetic Jade Ultra: https://www.gateron.com/products/gateron-magnetic-jade-ultra-switch-set
- Gateron Magnetic Jade Delta: https://www.gateron.com/products/gateron-magnetic-jade-delta-switch
- Jade 30 g listing: https://mechanicalkeyboards.com/products/gateron-jade-magnetic-he-30g-linear-pcb-mount
- Jade Mini E exception: https://mechanicalkeyboard.net/best-hall-effect-switches/
- LCSC C5149201 (OPSCO SK6812MINI-E): https://www.lcsc.com/product-detail/C5149201.html
- OPSCO SK6812MINI-E-012 datasheet: https://atta.szlcsc.com/upload/public/pdf/source/20240708/7577C013CD62BC7D192EAA1AF5B38052.pdf
- OPSCO SK6812 MINI-EA datasheet: https://atta.szlcsc.com/upload/public/pdf/source/20260416/06649CDD3352A94368C5FAB79FAACA32.pdf
- SK6812MINI-E Rev.02 (Adafruit): https://cdn-shop.adafruit.com/product-files/4960/4960_SK6812MINI-E_REV02_EN.pdf
- LCSC C19674180 (AT32F405RCT7-7): https://www.lcsc.com/product-detail/C19674180.html
- JLCPCB parts search: https://jlcpcb.com/parts/componentSearch?searchTxt=AT32F405
- Manduic (Artery distributor): https://www.manduic.com/cpzx/4911/AT32F405RCT7-7
- Artery AT32F405 product page: https://www.arterychip.com/en/product/AT32F405.jsp
- AT32F405/402 datasheet V2.02: https://datasheet.lcsc.com/lcsc/2504231454_ARTERY-AT32F402CCT7_C21714350.pdf
