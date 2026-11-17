#!/usr/bin/env python3
"""Design values for the LMR33630 buck breakout: one source of truth for the
silkscreen table, the BOM and the README.

Equations and limits are from the TI LMR33630 datasheet (SNVSAN3F):
  Eq. 3   RFBB = RFBT / (VOUT / VREF - 1),  VREF = 1.0 V (0.985 .. 1.015 V)
  Eq. 4   L    = (VIN - VOUT) / (fSW * K * IOUTmax) * VOUT / VIN,  K = 0.2..0.4
  Eq. 5   LMIN >= 0.28 * VOUT / fSW          (0.28 for H / Hz, i.e. uH with MHz)
  Eq. 10  RENT = (VON / VEN_H - 1) * RENB,  VOFF = VON * (1 - VEN_HYS / VEN_H)

Run this file to print the tables.
"""
VREF = 1.0
FSW = 400e3          # LMR33630A
IOUT = 3.0
VEN_H, VEN_HYS = 1.231, 0.100
REV = "REV A  2026-11"

# Output options.  r1 = RFBT, r2 + r3 = RFBB in series (kit values, 1 %).
# r2_exact is the single E96 part that replaces r2 + r3 when r1 = 100k.
_ROWS = [
    # label, vout, r1,    r2,    r3,    r2_exact, L uH, typical VIN used for ripple
    ("3V3", 3.3, 100e3, 22e3, 22e3, 43.2e3, 10, 12),
    ("5V",  5.0, 100e3, 22e3, 2.2e3, 24.9e3, 10, 12),
    ("9V",  9.0, 100e3, 10e3, 2.2e3, 12.4e3, 15, 24),
    ("12V", 12.0, 220e3, 10e3, 10e3, 9.09e3, 15, 24),
    ("24V", 24.0, 100e3, 2.2e3, 2.2e3, 4.32e3, 22, 36),
]


def rfmt(r):
    """4k7 style resistor text."""
    for div, ch in ((1e6, "M"), (1e3, "k"), (1, "R")):
        if r >= div:
            v = r / div
            s = f"{v:.2f}".rstrip("0").rstrip(".")
            if "." in s:
                a, b = s.split(".")
                return f"{a}{ch}{b}"
            return f"{s}{ch}"
    return "0R"


def vout(r1, rb):
    return VREF * (1 + r1 / rb)


def ripple(vin, vo, l_uh):
    return (vin - vo) * vo / (vin * FSW * l_uh * 1e-6)


TABLE = []
for label, vo, r1, r2, r3, r2x, l_uh, vin in _ROWS:
    kit = vout(r1, r2 + r3)
    exact = vout(100e3, r2x)
    TABLE.append(dict(
        label=label, vout=vo, r1=rfmt(r1), r2=rfmt(r2), r3=rfmt(r3),
        gets=f"{kit:.2f}" if kit < 10 else f"{kit:.1f}",
        kit_v=kit, exact_v=exact, r2_exact=rfmt(r2x), l=f"{l_uh}u",
        l_uh=l_uh, vin_typ=vin,
        ripple=ripple(vin, vo, l_uh),
        l_ideal=(vin - vo) * vo / (vin * FSW * 0.3 * IOUT) * 1e6,
        l_min=0.28 * vo / FSW * 1e6,
        cout="4x 10u 50V" if vo > 12 else "4x 22u 25V",
    ))


def uvlo(r_top, r_bot):
    von = VEN_H * (1 + r_top / r_bot)
    return von, von * (1 - VEN_HYS / VEN_H)


if __name__ == "__main__":
    print("VOUT   R1    R2    R3    kit V   err    R2(1%)  exact V   L    "
          "ripple@VIN       L(K=0.3)  Lmin")
    for r in TABLE:
        print(f"{r['label']:<5}  {r['r1']:<5} {r['r2']:<5} {r['r3']:<5} "
              f"{r['kit_v']:6.3f} {100 * (r['kit_v'] / r['vout'] - 1):+5.1f}%  "
              f"{r['r2_exact']:<6}  {r['exact_v']:6.3f}   {r['l']:<4} "
              f"{r['ripple']:.2f} A @ {r['vin_typ']:>2} V   "
              f"{r['l_ideal']:5.1f} uH  {r['l_min']:4.1f} uH")
    print("\nUVLO examples (R4 top, R5 bottom):")
    for rt, rb in ((100e3, 22e3), (100e3, 10e3 + 1e3), (100e3, 10e3),
                   (100e3, 4.7e3 + 2.2e3)):
        on, off = uvlo(rt, rb)
        print(f"  R4 {rfmt(rt)}  R5 {rfmt(rb)}:  on {on:5.2f} V  off {off:5.2f} V")
