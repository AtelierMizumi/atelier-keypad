# Rev 2.0: where to buy everything in Vietnam

Researched 14 Nov 2026. Prices are what shops list publicly. Confirm them
before paying: listings go stale, and several pages carry old dates. Since
February 2025 Vietnam no longer exempts small imported parcels from duty
([ParcelPath](https://parcelpath.com/international-shipping/destinations/asia/shipping-to-vietnam/)),
so an overseas order may cost a little more than its checkout total.

The rule used below: **buy in Vietnam when it exists here at a sane price.
Otherwise make one single order from China, not several.** Each extra overseas
shop adds its own shipping fee.

## The short answer

| What | Buy from | Why this one | Backup |
|---|---|---|---|
| PCB, 5 boards, 2 layers, 1.2 mm | **CXT** ([machin.cxtvn.com](https://machin.cxtvn.com/)) or **SmartPCB88** ([smartpcb88.com](https://smartpcb88.com/)), road shipping | 5 boards under 10 × 10 cm for 110,000 đ delivered, 8–10 days. JLCPCB alone is 2 USD plus 130–320k shipping | JLCPCB direct, if you need fast air shipping or a stencil from them |
| AT32F405CCT7, DRV5056A4, LP5907, USBLC6, 74AHCT1G125, crystal, USB-C, fuse | **One Taobao component shop, through a Vietnamese order agency** | Artery is a Chinese brand with no Vietnamese distributor found. The SOT-23 DRV5056 is not sold here (only TO-92, 43k each at Inobon) | Thegioiic "đặt hàng theo yêu cầu" (custom order); LCSC direct |
| SK6812MINI-E | Same Taobao shop | Rarely stocked in Vietnam | Shopee search "SK6812 mini-e" |
| 0603/0402 resistors, capacitors, ferrite | Same Taobao shop, or a local shop (IC Đây Rồi, Linh Kiện Thủ Đức, Thegioiic) | A sample book or a few strips from a local shop is fine | Shopee |
| Tact switches 6 × 6 × 7.3, TL3342 | Local shop or Shopee | Common parts | Taobao |
| Gateron Magnetic Jade (PCB mount) | **TechSpace** (original Jade, 21,000 đ each) | The field model is fitted to the original Jade's 12 → 80 mT figures | Soigear, MokbStore or TheBabuStore (Jade **Pro**, 18,000 đ). See the note below |
| Keycaps 1u × 4 | Shopee | | Any local keyboard shop |
| Acrylic, 5 layers from the DXF files | **TP.HCM:** MicaTrong, or Xưởng Hy Huy (catkhaclaser.com). **Hà Nội:** MTV Plastic, or Mica Hà Nội | They accept DXF and single pieces, and quote in minutes | Any laser shop; send the same files to 2–3 and compare |
| 0.5 mm and 1.0 mm EVA foam sheet | Shopee ("xốp EVA 0.5mm", "xốp EVA 1mm") | | Stationery or craft shop |
| Nylon M3 × 14 screws and nuts, rubber feet | Shopee or a hardware street (Nguyễn Văn Trỗi in HN, Nhật Tảo / Lê Hồng Phong in HCM) | | |
| Conformal coating, flux, solder paste, solder wick | Local electronics shop or Shopee | | |

## Details and sources

### PCB

| Fab | Listed price | Notes |
|---|---|---|
| [CXT](https://machin.cxtvn.com/) | 5 pcs 110,000 đ / 10 pcs 130,000 đ (road); 310,000 / 340,000 đ (air) | Under 10 × 10 cm, 2 layers, default specs. Ask whether 1.2 mm and a stencil are available |
| [SmartPCB88](https://smartpcb88.com/) (Hà Nội) | 5 pcs 110,000 đ / 10 pcs 130,000 đ, 8–10 days | Same price grid as CXT |
| [Hatakey](https://hatakey.com.vn/) | "From 99,000 đ for 10 pcs 10 × 10 cm" | Advertised floor price; check the options |
| [Mạch in Tuấn Cường](https://machintuancuong.com/) | 180,000 đ for 2 layers 10 × 10 | |
| JLCPCB direct | 2 USD for 5 boards plus shipping seen at checkout | [JLCPCB shipping help](https://jlcpcb.com/help/article/how-much-does-shipping-cost); a [forum post](http://www.dientuvietnam.net/forums/forum/c%C6%A1-s%E1%BB%9F-%C4%90i%E1%BB%87n-%C4%90i%E1%BB%87n-t%E1%BB%AD/%C4%90i%E1%BB%87n-t%E1%BB%AD-d%C3%A0nh-cho-ng%C6%B0%E1%BB%9Di-m%E1%BB%9Bi-b%E1%BA%AFt-%C4%91%E1%BA%A7u/1706354-h%E1%BB%8Fi-v%E1%BB%81-m%E1%BA%A1ch-in-pcb) reports about 20 USD for DHL |

The board is 76 × 70 mm, so it fits the "under 10 × 10 cm" price. The thing
to ask about is **1.2 mm**, since the default is 1.6 mm. Decision D2 needs
1.2 mm.

### Chips and parts from China

- **No Vietnamese distributor for Artery was found.** A Chinese distributor
  table ([Manduic](https://www.manduic.com/cpzx/4911/AT32F405RCT7-7)) lists the
  AT32F405CCT7 with stock "暂无" (none yet). szlcsc (LCSC's Chinese site)
  turned up no page for it, and JLCPCB's part search returns "0 Found". **This is gate G1:** search "AT32F405CCT7" on
  Taobao and szlcsc, and only order if a shop has it. If no shop has it, see
  Plan B in `docs/hall-effect-task0.md`. Checked again on 16 Nov 2026: there is
  still no LQFP-48 listing, but LCSC stocks the LQFP-64 **AT32F405RCT7-7**
  (C19674180), which would mean a rev 2.1 board
  ([order gates](../research/order-gates-2026-11.md)). **The fastest source of
  a genuine CCT7 is the WeAct AT32F405CCT7 Core Board on AliExpress** (about
  72,000 VND): buy 2–3, keep one for firmware bring-up, desolder the chip
  from the others.
- **The DRV5056A4QDBZR is LCSC C2152902**
  ([LCSC](https://www.lcsc.com/product-image/C2152902.html)), about 0.60 USD,
  stock unclear. Arrow lists the reel suffix QDBZT as obsolete; **QDBZR** is
  the one to buy. In Vietnam, Inobon sells only the TO-92 (QLPG) at about
  42,768 đ ([Inobon](https://inobon.com.vn/DRV5056A4QLPG-pe265902.html)). That
  package does not fit this board.
- **Order agencies** charge 1–3 % of the order plus CN → VN freight at about
  8,000–40,000 đ/kg, depending on the agency
  ([Thương Đô](https://www.thuongdo.com/dat-hang-taobao),
  [Yến China](https://yenchina.vn/cach-tinh-phi-ship-taobao/)). The whole
  order is well under 1 kg. What adds up is each Taobao shop's own domestic
  shipping, so **buy every chip from one shop**.
- **Thegioiic custom order** takes a 30 % deposit and 7–10 working days
  ([Thegioiic](https://www.thegioiic.com/cong-ty/dat-mua-linh-kien-dien-tu)).
  It suits the parts it already stocks. Ask for the AT32F405 first.

### Switches

| Shop | Switch | Price |
|---|---|---|
| [TechSpace](https://techspace.vn/switch-ban-phim-he-gateron-magnetic-jade-le-1-switch) | Magnetic Jade (original), sold singly | 21,000 đ |
| [Soigear](https://soigear.vn/switch-gateron-magnetic-jade-pro-1), [MokbStore](https://mokbstore.com/gateron-magnetic-jade-pro-switch), [TheBabuStore](https://thebabustore.vn/product/gateron-magnetic-jade-pro-switch) | Magnetic Jade **Pro** | 18,000 đ |

The Jade Pro is listed at 3.5 ± 0.1 mm travel and 36 ± 5 gf. One comparison
page gives it the same 120/800 G flux as the original
([kbd.news](https://kbd.news/switch-comparison/Gateron-Magnetic-Jade-Pro-vs-gateron-magnetic-jade-135-58.html)),
but that is not confirmed. **Buy the original Jade**, so the board matches the
numbers the model was fitted to. Make sure the listing says PCB mount (5-pin)
and HE/magnetic. MokbStore notes these are not compatible with Akko HE boards;
that is irrelevant here.

### Acrylic

| Shop | City | How they charge |
|---|---|---|
| [MicaTrong](https://micatrong.com/gia-cong-mica/) | TP.HCM | Laser cut 2–10 mm at 2,000–12,000 đ per metre of cut; small orders accepted; ships nationwide |
| [Xưởng Hy Huy](https://catkhaclaser.com/cat-laser-mica-tphcm/) | TP.HCM | Takes DXF, AI, CDR, PDF |
| [MTV Plastic](https://mtvplastic.com/cat-nhua-mica-theo-yeu-cau-ha-noi/) | Hà Nội | From one sheet; takes DWG/DXF; same-day delivery inside the city |
| [Mica Hà Nội](https://micahanoi.com.vn/cat-mica.html) | Hà Nội | 90,000–130,000 đ per hour of machine time, measured on your file |

The five layers have about 2–3 m of cut in total, so expect the material to
cost more than the cutting. Ask whether they stock **translucent blue** in
2 mm and 5 mm, and clear in 3 mm.

## What has no Vietnamese source

| Part | Easiest route |
|---|---|
| AT32F405CCT7 | Taobao or szlcsc through an order agency (gate G1) |
| DRV5056A4QDBZR (SOT-23) | Same order |
| SK6812MINI-E, LP5907, USBLC6-2SC6, 74AHCT1G125, 12 MHz 3225 crystal | Same order, unless a local shop happens to stock them |

Everything else is in Vietnam.

## LCSC numbers

Every other part's LCSC number is in `hardware/he/circuit.py` (`LCSC`), and
from there in `bom-jlcpcb.csv`. Each number was checked against its
jlcpcb.com/lcsc.com product page on 14 Nov 2026. Stock was not visible there,
so check it in the cart. Two were noted as possibly low or out of stock: the
74AHCT1G125 (C12494) and the TL3342 (C2886898).
