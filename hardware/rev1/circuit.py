"""Atelier6K rev 1: the circuit and the placement, as data.

This file is the single source for the schematic (gen_sch.py) and the board
(gen_pcb.py). Coordinates are KiCad board millimetres, same frame as rev 0.
Pins are given by pin *name* where the library symbol has names (LEDs, the
level shifter, the module) and by number otherwise; the generators resolve
names to pad numbers from the KiCad libraries, so no pinout is retyped here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Board outline and screw holes, unchanged from rev 0.
OUTLINE = (116.84, 60.96, 198.12, 134.62)  # x0, y0, x1, y1
OUTLINE_RADIUS = 1.27
HOLES = [(121.92, 66.04), (193.04, 66.04), (121.92, 129.54), (193.04, 129.54)]
HOLE_FOOTPRINT = "MountingHole:MountingHole_3.2mm_M3"
THICKNESS = 1.6

# Rev 0 key positions, moved down so the MCU module fits above the top row.
KEY_SHIFT = 12.7
BUTTON_SHIFT = 8.0
KEYS = {
    "MX1": (133.985, 80.645), "MX2": (153.035, 80.645), "MX3": (172.085, 80.645),
    "MX4": (143.51, 100.33), "MX5": (162.56, 100.33), "MX6": (181.61, 100.33),
}
BUTTONS = {"SW1": (122.48, 94.429), "SW2": (122.48, 103.16), "SW3": (122.48, 111.891)}

# RP2040-Zero, flush-mounted under the board, USB end on the top edge.
MODULE_X = (OUTLINE[0] + OUTLINE[2]) / 2
MODULE_LENGTH = 23.5
MODULE_WIDTH = 18.0
# Notch in the board under the module: its back carries the RP2040 and flash.
MODULE_NOTCH = (11.2, 20.4)  # width, depth from the top edge

GPIO = {  # signal -> module pin; chosen for short routes, mirrored in keyboard.json
    "K1": "GP8", "K2": "GP10", "K3": "GP14",
    "K4": "GP9", "K5": "GP12", "K6": "GP15",
    "B1": "GP7", "B2": "GP6", "B3": "GP5",
    "LED_DATA": "GP3",
}
MODULE_PINS = ["5V", "GND", "3V3", "GP29", "GP28", "GP27", "GP26", "GP15", "GP14",
               "GP0", "GP1", "GP2", "GP3", "GP4", "GP5", "GP6", "GP7", "GP8",
               "GP13", "GP12", "GP11", "GP10", "GP9"]

# LED chain order: key LEDs in a serpentine, then the four underglow LEDs.
KEY_LED_ORDER = ["MX1", "MX2", "MX3", "MX6", "MX5", "MX4"]
UNDERGLOW = [(136.0, 127.5), (179.0, 127.5), (184.0, 68.0), (131.0, 68.0)]

FP_LED = "LED_SMD:LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount"
FP_C0603 = "Capacitor_SMD:C_0603_1608Metric_Pad1.08x0.95mm_HandSolder"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder"
FP_R0603 = "Resistor_SMD:R_0603_1608Metric_Pad0.98x0.95mm_HandSolder"


@dataclass
class Part:
    ref: str
    value: str
    symbol: str      # "Library:Name"
    footprint: str   # "Library:Name"
    x: float
    y: float
    rot: float = 0.0
    side: str = "F"  # "F" top, "B" bottom
    pins: dict = field(default_factory=dict)  # pin name or number -> net, None = unconnected


def parts() -> list[Part]:
    out: list[Part] = []

    module_nets: dict[str, str | None] = {p: None for p in MODULE_PINS}
    module_nets.update({"5V": "VBUS", "GND": "GND"})
    for signal, pin in GPIO.items():
        module_nets[pin] = signal
    out.append(Part("U1", "RP2040-Zero", "atelier:RP2040-Zero", "local:RP2040-Zero_Flush",
                    MODULE_X, OUTLINE[1], side="B", pins=module_nets))

    # Over-current protection for everything this board adds to the module.
    out.append(Part("F1", "500mA", "Device:Polyfuse", "Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder",
                    171.5, 63.6, side="B", pins={"1": "VBUS", "2": "+5V"}))
    out.append(Part("C11", "4.7uF", "Device:C", FP_C0805, 171.5, 66.9, side="B", pins={"1": "+5V", "2": "GND"}))

    # 3.3 V GPIO -> 5 V LED data.
    out.append(Part("U2", "74AHCT1G125", "74xGxx:74AHCT1G125", "Package_TO_SOT_SMD:SOT-23-5_HandSoldering",
                    142.0, 70.2, rot=90, side="B",
                    # SOT-23-5 1G125: 1 = /OE, 2 = A, 4 = Y (unnamed in the KiCad symbol)
                    pins={"1": "GND", "2": "LED_DATA", "GND": "GND", "4": "LED_5V", "VCC": "+5V"}))
    out.append(Part("C12", "100nF", "Device:C", FP_C0603, 142.0, 65.6, side="B", pins={"1": "+5V", "2": "GND"}))
    out.append(Part("R1", "330", "Device:R", FP_R0603, 142.0, 75.2, side="B", pins={"1": "LED_5V", "2": "LED_D1"}))

    for i, (ref, (x, y)) in enumerate(KEYS.items(), start=1):
        out.append(Part(ref, "MX hot-swap", "Switch:SW_Push", "MX_Only:MXOnly-1U-Hotswap",
                        x, y + KEY_SHIFT, pins={"1": f"K{i}", "2": "GND"}))
    for i, (ref, (x, y)) in enumerate(BUTTONS.items(), start=1):
        out.append(Part(ref, "6x6 tact", "Switch:SW_Push", "Button_Switch_THT:SW_PUSH_6mm_H13mm",
                        x, y + BUTTON_SHIFT, pins={"1": f"B{i}", "2": "GND"}))

    led_sites = [(KEYS[k][0], KEYS[k][1] + KEY_SHIFT + 5.08, "B") for k in KEY_LED_ORDER]
    led_sites += [(x, y, "F") for x, y in UNDERGLOW]
    for n, (x, y, side) in enumerate(led_sites, start=1):
        last = n == len(led_sites)
        out.append(Part(f"D{n}", "SK6812MINI-E", "LED:SK6812MINI-E", FP_LED, x, y, side=side,
                        pins={"VDD": "+5V", "VSS": "GND", "DIN": f"LED_D{n}",
                              "DOUT": None if last else f"LED_D{n + 1}"}))
        out.append(Part(f"C{n}", "100nF", "Device:C", FP_C0603, x, y + 2.9, side=side,
                        pins={"1": "+5V", "2": "GND"}))
    return out


# Net classes for routing: (track width, clearance) in mm.
NET_CLASSES = {
    "Default": {"track": 0.25, "clearance": 0.2, "nets": []},
    "Power": {"track": 0.5, "clearance": 0.2, "nets": ["VBUS", "+5V", "GND"]},
}


# --- production --------------------------------------------------------------

# LCSC numbers for the JLCPCB BOM, keyed by value and footprint name. Each one is
# the rev 2.0 number for the same part (hardware/he/circuit.py), which was checked
# against its LCSC product page; see docs/build/sourcing-vn.md.
LCSC: dict[tuple[str, str], str] = {
    ("SK6812MINI-E", FP_LED.split(":")[-1]): "C5149201",
    ("74AHCT1G125", "SOT-23-5_HandSoldering"): "C12494",
    ("500mA", "Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder"): "C151162",
    ("100nF", FP_C0603.split(":")[-1]): "C14663",
    ("4.7uF", FP_C0805.split(":")[-1]): "C1779",
    ("330", FP_R0603.split(":")[-1]): "C23138",
}

# Soldered by hand, not by the assembly house: the MCU module, the hot-swap
# sockets and the through-hole buttons.
HAND_PLACED = frozenset({"U1", *KEYS, *BUTTONS})


def lcsc(p: Part) -> str:
    return LCSC.get((p.value, p.footprint.split(":")[-1]), "")


def machine_parts(parts: list[Part]) -> list[Part]:
    """Parts the assembly house places: everything not in HAND_PLACED."""
    return [p for p in parts if p.ref not in HAND_PLACED]
