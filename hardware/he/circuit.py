"""Atelier rev 2 (Hall effect): the circuit and the placement, as data.

Single source for the schematic (gen_sch.py) and the board (gen_pcb.py), in
the style of hardware/rev1/circuit.py. Board millimetres; y grows towards the
wrist. Every electronic part except the sensors sits on the bottom side; the
top carries the sensors (under the switches), the two buttons, the underglow
LEDs (reverse-mounted, shining down) and the art under the clear cover.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# 76 x 70 mm: three keys, the electronics above them, a palm area with the art below.
OUTLINE = (62.0, 82.0, 138.0, 152.0)
OUTLINE_RADIUS = 2.0
HOLES = [(66.0, 86.0), (134.0, 86.0), (66.0, 148.0), (134.0, 148.0)]
HOLE_FOOTPRINT = "MountingHole:MountingHole_3.2mm_M3"
THICKNESS = 1.2   # rev 2.0: Gateron's flux figures are measured through a 1.2 mm PCB
ART_ZONE = (69.0, 129.0, 131.0, 147.0)  # x0, y0, x1, y1: nothing but art in here

# Finger arc: 19.05 mm pitch, middle key 4.76 mm further from the wrist.
KEYS = {"K1": (80.95, 113.0), "K2": (100.0, 108.24), "K3": (119.05, 113.0)}
KEY_ORDER = ["K1", "K2", "K3"]

# AT32F405, LQFP48 (datasheet v2.02, Figure 3 / Table 9).
AT32F405_LQFP48 = {
    1: "VDD", 2: "PC13", 3: "PC14", 4: "PC15", 5: "PF0", 6: "PF1", 7: "NRST", 8: "VSSA",
    9: "VDDA", 10: "PA0", 11: "PA1", 12: "PA2", 13: "PA3", 14: "PA4", 15: "PA5", 16: "PA6",
    17: "PA7", 18: "PB0", 19: "PB1", 20: "PB2", 21: "PB10", 22: "PB12", 23: "VSS", 24: "PB13",
    25: "OTGHS_R", 26: "OTGHS_D-", 27: "OTGHS_D+", 28: "VDD", 29: "PA8", 30: "PA9", 31: "PA10",
    32: "PA11", 33: "PA12", 34: "PA13", 35: "PF6", 36: "PF7", 37: "PA14", 38: "PA15", 39: "PB3",
    40: "PB4", 41: "PB5", 42: "PB6", 43: "PB7", 44: "PF11/BOOT0", 45: "PB8", 46: "PB9", 47: "VSS",
    48: "VDD",
}
SENSOR_ADC = {"K1": "PA2", "K2": "PA1", "K3": "PA0"}   # ADC1_IN2..IN0, ordered so the traces fan out
LED_PIN = "PB0"                                        # TMR3_CH3, for DMA-driven LED data
BUTTON_PINS = {"SW1": "PB12", "SW2": "PB5"}            # Esc (left side), retry (right side); pull-ups

UNDERGLOW = [(66.2, 103.0), (133.8, 103.0), (133.8, 121.0), (66.2, 121.0)]

FP_LED = "LED_SMD:LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount"
FP_C = "Capacitor_SMD:C_0603_1608Metric_Pad1.08x0.95mm_HandSolder"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder"
FP_R = "Resistor_SMD:R_0603_1608Metric_Pad0.98x0.95mm_HandSolder"
FP_TP = "TestPoint:TestPoint_Pad_1.0x1.0mm"


@dataclass
class Part:
    ref: str
    value: str
    symbol: str
    footprint: str
    x: float
    y: float
    rot: float = 0.0
    side: str = "F"
    pins: dict = field(default_factory=dict)


def _pin(name: str) -> str:
    return str(next(n for n, nm in AT32F405_LQFP48.items() if nm == name))


def parts() -> list[Part]:
    out: list[Part] = []
    B = "B"

    def cap(ref, value, x, y, a, b="GND", side=B, fp=FP_C, rot=0):
        out.append(Part(ref, value, "Device:C", fp, x, y, rot, side, {"1": a, "2": b}))

    def res(ref, value, x, y, a, b, side=B, rot=0):
        out.append(Part(ref, value, "Device:R", FP_R, x, y, rot, side, {"1": a, "2": b}))

    # ---------------------------------------------------------------- MCU
    mcu: dict[str, str | None] = {str(n): None for n in AT32F405_LQFP48}
    for n, name in AT32F405_LQFP48.items():
        if name == "VDD":
            mcu[str(n)] = "+3V3"
        elif name in ("VSS", "VSSA"):
            mcu[str(n)] = "GND"
    mcu.update({_pin("VDDA"): "+3V3A", _pin("PF0"): "HEXT_IN", _pin("PF1"): "HEXT_OUT",
                _pin("NRST"): "NRST", _pin("PF11/BOOT0"): "BOOT0",
                _pin("OTGHS_D+"): "USB_DP", _pin("OTGHS_D-"): "USB_DM", _pin("OTGHS_R"): "OTGHS_R",
                _pin("PA13"): "SWDIO", _pin("PA14"): "SWCLK", _pin(LED_PIN): "LED_DATA"})
    for key in KEY_ORDER:
        mcu[_pin(SENSOR_ADC[key])] = f"ADC_{key}"
    for sw, pin in BUTTON_PINS.items():
        mcu[_pin(pin)] = f"BTN_{sw}"
    out.append(Part("U1", "AT32F405CCT7", "atelier_he:AT32F405CxT7", "Package_QFP:LQFP-48_7x7mm_P0.5mm",
                    102.5, 99.0, 270, B, mcu))  # centre on the 0.25 mm routing grid
    cap("C21", "100nF", 101.4, 92.9, "+3V3", side="F", rot=90)  # pin 28, top side right above it
    cap("C22", "100nF", 110.0, 100.4, "+3V3")            # pin 48
    cap("C23", "100nF", 105.25, 99.4, "+3V3", side="F", rot=90)  # pin 1, top side, outside the switch
    cap("C24", "4.7uF", 111.2, 93.3, "+3V3", fp=FP_C0805, rot=90)
    cap("C25", "100nF", 100.6, 99.4, "+3V3A", side="F", rot=90)  # VDDA (pin 9), top side, outside the switch
    cap("C26", "1uF", 97.0, 99.4, "+3V3A", side="F", rot=90)
    cap("C27", "100nF", 102.4, 99.4, "NRST", side="F", rot=90)

    # ------------------------------------------------------- 12 MHz crystal
    out.append(Part("Y1", "12MHz", "Device:Crystal_GND24", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
                    108.6, 105.0, 90, B, {"1": "HEXT_IN", "2": "GND", "3": "HEXT_OUT", "4": "GND"}))
    cap("C28", "18pF", 112.0, 103.9, "HEXT_IN")
    cap("C29", "18pF", 107.75, 108.9, "HEXT_OUT", rot=90)

    # --------------------------------------------------------------- USB-C
    out.append(Part("J1", "USB-C", "Connector:USB_C_Receptacle_USB2.0_16P",
                    "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", 100.0, 84.5, 180, B,
                    {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND",
                     "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
                     "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DM", "B7": "USB_DM",
                     "A8": None, "B8": None, "SH": "USB_SHIELD"}))
    # A5 sits between the left VBUS pad and the USB pair: its pull-down goes straight below it (0402).
    out.append(Part("R1", "5.1k", "Device:R", "Resistor_SMD:R_0402_1005Metric", 98.2, 90.8, 90, B,
                    {"1": "CC1", "2": "GND"}))
    res("R2", "5.1k", 108.0, 87.6, "CC2", "GND")
    res("R3", "1M", 110.4, 85.6, "USB_SHIELD", "GND", rot=90)
    cap("C30", "4.7nF", 112.4, 85.6, "USB_SHIELD", rot=90)
    out.append(Part("U3", "USBLC6-2SC6", "Power_Protection:USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
                    92.2, 88.6, 90, B, {"1": "USB_DP", "6": "USB_DP", "3": "USB_DM", "4": "USB_DM",
                                         "2": "GND", "5": "VBUS"}))
    res("R4", "12k 1%", 99.6, 92.9, "OTGHS_R", "GND", side="F", rot=90)  # top side, above pin 25

    # --------------------------------------------------------------- power
    out.append(Part("F1", "500mA", "Device:Polyfuse", "Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder",
                    86.0, 85.5, 0, B, {"1": "VBUS", "2": "+5V"}))
    cap("C31", "4.7uF", 81.0, 85.5, "+5V", fp=FP_C0805)
    out.append(Part("U2", "LP5907MFX-3.3", "Regulator_Linear:LP5907MFX-3.3", "Package_TO_SOT_SMD:SOT-23-5",
                    84.0, 90.5, 0, B, {"IN": "+5V", "EN": "+5V", "GND": "GND", "NC": None, "OUT": "+3V3"}))
    cap("C32", "1uF", 80.0, 90.5, "+5V", rot=90)
    cap("C33", "1uF", 88.0, 90.5, "+3V3", rot=90)
    out.append(Part("FB1", "600R@100MHz", "Device:FerriteBead_Small", "Inductor_SMD:L_0603_1608Metric",
                    94.0, 104.6, 0, B, {"1": "+3V3", "2": "+3V3A"}))

    # --------------------------------------------- BOOT, SWD pads, buttons
    res("R5", "10k", 109.4, 97.4, "BOOT0", "GND", rot=90)
    out.append(Part("SW3", "BOOT", "Switch:SW_Push", "Button_Switch_SMD:SW_SPST_TL3342",
                    116.5, 95.5, 90, B, {"1": "BOOT0", "2": "+3V3"}))
    for i, (net, x) in enumerate((("SWDIO", 118.5), ("SWCLK", 121.0), ("GND", 123.5), ("+3V3", 126.0)), start=1):
        out.append(Part(f"TP{i}", net, "Connector:TestPoint", FP_TP, x, 87.0, 0, B, {"1": net}))
    for sw, (x, y) in (("SW1", (74.0, 93.0)), ("SW2", (126.0, 93.0))):
        out.append(Part(sw, "Esc" if sw == "SW1" else "Retry", "Switch:SW_Push",
                        "Button_Switch_THT:SW_PUSH_6mm_H7.3mm", x - 3.25, y - 2.25, 0, "F",
                        {"1": f"BTN_{sw}", "2": "GND"}))

    # ------------------------------------------------------------- sensors
    for i, key in enumerate(KEY_ORDER, start=1):
        kx, ky = KEYS[key]
        out.append(Part(f"U{9 + i}", "DRV5056A4", "Sensor_Magnetic:DRV5055A4xDBZxQ1", "Package_TO_SOT_SMD:SOT-23",
                        kx, ky, 0, B, {"VCC": "+3V3A", "OUT": f"SENSE_{key}", "GND": "GND"}))
        # rev 2.0: the sensor reads the magnet through the 1.2 mm board, as Gateron specifies the flux.
        # Around it on the bottom: its decoupling, then the RC filter, between the pegs (+-5.08 mm)
        # and clear of the reverse-mount LED (+5.08 mm).
        cap(f"C{i}", "100nF", kx, ky - 2.6, "+3V3A")
        side_r = -3.0 if key == "K1" else 3.0   # filter on the side facing its route to the MCU
        res(f"R{9 + i}", "1k", kx + side_r, ky + 1.4, f"SENSE_{key}", f"ADC_{key}", rot=90)
        cap(f"C{3 + i}", "47nF", kx - side_r, ky + 1.4, f"ADC_{key}", rot=90)

    # ----------------------------------------------------------------- LEDs
    out.append(Part("U4", "74AHCT1G125", "74xGxx:74AHCT1G125", "Package_TO_SOT_SMD:SOT-23-5",
                    92.0, 99.8, 0, B, {"1": "GND", "2": "LED_DATA", "GND": "GND", "4": "LED_5V", "VCC": "+5V"}))
    cap("C34", "100nF", 88.8, 99.8, "+5V", rot=90)
    res("R6", "330", 92.0, 102.8, "LED_5V", "LED_D1")
    sites = [(KEYS[k][0], KEYS[k][1] + 5.08, B) for k in KEY_ORDER] + [(x, y, "F") for x, y in UNDERGLOW]
    for n, (x, y, side) in enumerate(sites, start=1):
        last = n == len(sites)
        out.append(Part(f"D{n}", "SK6812MINI-E", "LED:SK6812MINI-E", FP_LED, x, y, 0, side,
                        {"VDD": "+5V", "VSS": "GND", "DIN": f"LED_D{n}", "DOUT": None if last else f"LED_D{n + 1}"}))
        cy = y + 2.9 if side == B else y - 2.9
        cap(f"C{40 + n}", "100nF", x, cy, "+5V", side=side)
    return out


# Switch footprints (no electrical pins) placed board-only by gen_pcb.py.
SWITCH_FOOTPRINT = "local:HE_Switch_PCBMount"

# Vias placed before routing: ground under the MCU body, where the pour is cut off by the fan-out.
FIXED_VIAS = [("GND", 100.0, 101.75), ("GND", 104.5, 101.75), ("GND", 102.5, 96.5), ("GND", 102.5, 105.5)]  # clear of the top-side caps

PWR_FLAGS = ["+5V", "GND", "+3V3A", "VBUS"]

NET_CLASSES = {
    "Default": {"track": 0.2, "clearance": 0.15, "nets": []},
    "Power": {"track": 0.3, "clearance": 0.15, "nets": ["VBUS", "+5V", "GND", "+3V3", "+3V3A"]},
}
