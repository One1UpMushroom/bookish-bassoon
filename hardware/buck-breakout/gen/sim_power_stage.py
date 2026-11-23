#!/usr/bin/env python3
"""
Simulate the buck converter's power stage in ngspice, one case per output
option, and compare the results with the design numbers and the LMR33630's
limits.

    python3 gen/sim_power_stage.py            (needs ngspice on the PATH)

What is simulated
-----------------
The parts that carry the power, with the chip's switches modelled as ideal
switches with the datasheet's on-resistance:

    VIN -- input capacitors -- high-side switch --+-- L1 -- output caps -- load
                                                  |
                                       low-side switch to ground

The switches take turns at 400 kHz with a short dead time (a diode carries
the current during it, like the low-side switch's body diode). The duty cycle
is set so the output lands on its target at full load, allowing for the
voltage lost in the switches and the inductor. The chip's control loop is not
modelled: TI doesn't publish its internals, so loop stability can only be
proven on the bench (README, Bring-up). What this does check is everything
the passive parts decide: ripple current, peak current against the chip's
current limit, output ripple, input capacitor current and conduction losses.

Numbers used (TI LMR33630 datasheet SNVSAN3F, DDA package, typical):
  high-side switch 95 mOhm, low-side switch 66 mOhm
  high-side current limit 3.85 A min / 4.5 A typ / 5.05 A max
  low-side (valley) current limit 2.9 A min
  switching frequency 340 / 400 / 460 kHz (min / typ / max, "A" version)
Inductor resistance from Bourns SRP1265A: 10 uH 13 mOhm, 15 uH 23 mOhm,
22 uH 33 mOhm. Ceramic capacitors lose capacitance under DC voltage; the
EFFECTIVE values below are estimates for 1210 X7R parts, not measurements.
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import values  # noqa: E402

RHS, RLS = 0.095, 0.066            # switch on-resistance, ohms
ISC_MIN, ILIM_MIN = 3.85, 2.9      # current limits, amps
IOUT = 3.0
DCR = {10: 0.013, 15: 0.023, 22: 0.033}   # inductor resistance, ohms
DEAD = 10e-9                       # dead time between the switches, s

# Effective capacitance of ONE output capacitor at the output voltage
# (estimates): 22 uF 25 V parts for 3.3-12 V, 10 uF 50 V parts for 24 V.
COUT_EACH = {"3V3": 18e-6, "5V": 16e-6, "9V": 12e-6, "12V": 10e-6, "24V": 5e-6}
CIN_EACH = 5e-6                    # one 10 uF 50 V input capacitor near 12-36 V


def netlist(vin, vout, l_uh, cout_each, fsw):
    """An ngspice deck for one operating point."""
    rl = DCR[l_uh]
    rload = vout / IOUT
    # duty cycle that gives vout at full load once resistive losses are paid
    d = (vout + IOUT * (rl + RLS)) / (vin - IOUT * (RHS - RLS))
    period = 1 / fsw
    ton = d * period
    lf = l_uh * 1e-6
    return f"""* buck power stage, {vin} V -> {vout} V, {l_uh} uH, {fsw/1e3:.0f} kHz
VIN vsrc 0 DC {vin}
* supply leads (about 1 uH) and the board's bulk electrolytic C10 (47 uF):
* the leads make the ceramic capacitors carry the switching current
LSRC vsrc vlead 1u
RSRC vlead vin 0.05
C10 vin c10 47u
R10 c10 0 0.3
VS1 vin s1 0
CIN1 s1 cin1 {CIN_EACH}
RIN1 cin1 0 0.004
VS2 vin s2 0
CIN2 s2 cin2 {CIN_EACH}
RIN2 cin2 0 0.004
CHF vin 0 0.15u
* gate signals: high side on for ton, low side on for the rest minus dead time
VGH gh 0 PULSE(0 1 {DEAD} 1n 1n {ton - 2e-9} {period})
VGL gl 0 PULSE(0 1 {ton + 2 * DEAD} 1n 1n {period - ton - 3 * DEAD - 2e-9} {period})
SHS vin sw gh 0 HSW
SLS sw 0 gl 0 LSW
DBODY 0 sw DB
.model HSW SW(Ron={RHS} Roff=1e6 Vt=0.5 Vh=0.1)
.model LSW SW(Ron={RLS} Roff=1e6 Vt=0.5 Vh=0.1)
.model DB D(Is=1e-12 N=1.2 Rs=0.02)
L1 sw lx {lf} IC={IOUT}
RL lx vout {rl}
""" + "".join(f"C{i} vout c{i} {cout_each} IC={vout}\nRC{i} c{i} 0 0.003\n"
              for i in range(4)) + f"""RLOAD vout 0 {rload}
.options method=gear reltol=1e-4
.tran 2n {500 * period} {460 * period} 2n uic
.control
run
meas tran vavg AVG v(vout)
meas tran vpp PP v(vout)
meas tran ilmax MAX i(L1)
meas tran ilmin MIN i(L1)
meas tran ilavg AVG i(L1)
let pinst = v(vsrc)*(-i(VIN))
meas tran pin AVG pinst
let icin = i(VS1)+i(VS2)
meas tran icinrms RMS icin
.endc
.end
"""


def run(deck):
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as f:
        f.write(deck)
        path = f.name
    try:
        out = subprocess.run(["ngspice", "-b", path], capture_output=True,
                             text=True, timeout=600).stdout
    finally:
        os.unlink(path)
    got = {}
    for key in ("vavg", "vpp", "ilmax", "ilmin", "ilavg", "pin", "icinrms"):
        m = re.search(rf"^{key}\s*=\s*([-\d.eE+]+)", out, re.M)
        got[key] = float(m.group(1)) if m else float("nan")
    return got


def main():
    cases = []
    for row in values.TABLE:          # each output option at its usual input
        cases.append((row["label"], row["vin_typ"], row["vout"], row["l_uh"],
                      400e3, 1.0, "typical"))
    for row in values.TABLE:          # worst case: 36 V in, slow clock, L -20 %
        cases.append((row["label"], 36, row["vout"], row["l_uh"],
                      340e3, 0.8, "worst"))
    print("case        VIN  VOUT(sim)  ripple  ILpeak  ILvalley  Vout p-p  "
          "Cin RMS  loss(cond.)  checks")
    problems = 0
    for label, vin, vout, l_uh, fsw, lscale, kind in cases:
        cout = COUT_EACH[label]
        deck = netlist(vin, vout, l_uh, cout, fsw)
        if lscale != 1.0:             # scale the inductance, keep its resistance
            deck = deck.replace(f"L1 sw lx {l_uh * 1e-6}",
                                f"L1 sw lx {l_uh * 1e-6 * lscale}")
        r = run(deck)
        ripple = r["ilmax"] - r["ilmin"]
        pout = r["vavg"] ** 2 / (vout / IOUT)
        loss = r["pin"] - pout
        checks = []
        if r["ilmax"] >= ISC_MIN:
            checks.append(f"PEAK over {ISC_MIN} A limit")
        if kind == "typical" and abs(r["vavg"] / vout - 1) > 0.01:
            checks.append("VOUT off target")
        if kind == "typical":
            expect = values.ripple(vin, vout, l_uh)
            if abs(ripple / expect - 1) > 0.1:
                checks.append(f"ripple {ripple:.2f} vs {expect:.2f} A designed")
        problems += sum(1 for c in checks if "PEAK" in c or "off target" in c
                        or "designed" in c)
        print(f"{label:<4} {kind:<7} {vin:>3.0f}  {r['vavg']:7.3f} V  {ripple:5.2f} A "
              f"{r['ilmax']:5.2f} A  {r['ilmin']:5.2f} A  {1000 * r['vpp']:6.1f} mV "
              f"{r['icinrms']:5.2f} A   {loss:5.2f} W     "
              + ("; ".join(checks) if checks else "ok"))
    print(f"\n{problems} problem(s). Peak current is checked against the chip's "
          f"MINIMUM high-side limit ({ISC_MIN} A); losses are conduction only "
          "(switching losses add roughly 0.1-0.4 W).")
    return problems


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
