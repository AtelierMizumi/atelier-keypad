# Rev 2 case: flat, low, and a full silicone pad

Decided on 16 Nov 2026, after reviewing three videos and the rev 2 case geometry.

## Problem

The rev 2 case got its 6° angle from flat rubber discs: 1.0 mm at the front and
7.5 mm at the rear, under a base that is itself tilted 6°.

- Each disc meets the desk on **one edge only**, with the other edge 0.84 mm
  up. That gives little contact area, and the case rocks.
- The front edge of the base is **0.58 mm** above the desk. The front feet sit
  8 mm in from that edge, so once the rubber compresses under a hard press, the
  case itself touches the desk.
- Keycap tops sit about 33 mm above the desk.

Evidence from the videos:
- Hugofrost, a keypad player since 2017, taps faster on a lower keypad. He says
  he does not know why, so this is an anecdote, not a measurement.
- BTMC tests grip by pushing hard sideways with the wrist. A light keypad's grip
  comes almost entirely from the hand pressing down on it, so contact area and
  the pad material decide whether it slides.
- tokaku built a keypad and reviewed LotusPro's failures. Two lessons apply to
  the case files: a laser-cut file exported at the **wrong scale**, and a
  **board rattling** in its case.

## Decisions

| # | Decision | Value |
|---|---|---|
| D1 | No tilt. The case sits flat | `TILT_DEG` removed; the model JSON has `tilt_deg: 0` |
| D2 | One silicone pad cut to the base outline replaces the four feet | 1.5 mm self-adhesive silicone, inset 0.5 mm from the case edge, with a hole at BOOT. It covers the nut pockets, so the nuts stay captive |
| D3 | No added mass for now | Re-test after the first build with BTMC's sideways push. Only if it slides, cut the base from 2 mm steel |
| D4 | Every DXF carries a 50 mm scale bar | On a `NOTES` layer that is not cut, labelled "50 mm, check before cutting". DXF units are mm (`$INSUNITS` = 4) |
| D5 | A USB-C plug fits through the slot, and the slot does not loosen the board | The slot clears a 12.4 × 6.6 mm plug overmold centred on J1. The ledges still carry ≥ 85 % of the board edge (existing test) |
| D6 | The site shows the flat case, the pad, and the lessons | After tests pass and the owner has seen a preview |

## Height budget (flat)

| Item | mm |
|---|---|
| Pad | 1.5 |
| Base to PCB top (base 3 + lower wall 5 + EVA strip 0.8 + PCB 1.2) | 10.0 |
| Desk to PCB top | **11.5** |

That is 2 mm lower at the PCB than the old front feet gave, and about 5 mm
lower at the middle key than the old tilt.

## Out of scope

- Rev 0 and rev 1 geometry. They only get the scale bar in their DXF.
- A tilt accessory, such as a 3D-printed TPU wedge with a flat bottom. Revisit
  after play-testing flat.
- Socket orientation marks on rev 1 silkscreen.
