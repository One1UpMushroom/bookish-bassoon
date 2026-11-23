"""What every themed board says, whatever it looks like: the output table,
the part notes and the limits. The numbers come from values.py, the single
source of truth for the design."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import values  # noqa: E402

# kit table: output, R1, R2, R3, L1 (R2 and R3 in series)
KIT_HEAD = ("VOUT", "R1", "R2", "R3", "L1")
KIT = [(r["label"], r["r1"], r["r2"], r["r3"], r["l"]) for r in values.TABLE]
# what the kit values give, and the single 1 % part for R2 (with R1 = 100k,
# R3 = a wire link)
GETS = [(r["label"], r["gets"]) for r in values.TABLE]
EXACT = [(r["label"], r["r2_exact"]) for r in values.TABLE]

# Inductor: TI says its saturation current should ideally reach the chip's
# high-side current limit, which can be as high as 5.05 A (SNVSAN3F 9.2.2.4).
L_SAT = "L1 SAT >= 5.1A"
REV = values.REV


def kit_value(s):
    """Upper-case form for fonts without lower case (the pixel font)."""
    return s.upper()
