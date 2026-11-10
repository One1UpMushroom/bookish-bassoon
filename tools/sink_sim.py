"""Time-domain model of the op-amp + MOSFET LED current sink under PWM.

Compares the revision 1 sink (2.5 ohm sense, millivolt reference) with the
revision 2 sink in docs/driver-build.html (50 ohm sense, reference in volts).
It is a model, not a measurement: use it for the size of the turn-on delay,
then calibrate Min duty on the real lamp.

    python3 tools/sink_sim.py


Op-amp: single-pole integrator (GBW) with slew limit and output saturation
        (LM324: GBW ~1 MHz, SR ~0.4 V/us, swing ~20 mV .. Vcc-1.5 V).
Feedback: Rf from sense node to IN-, Cf from OUT to IN-, Roff from Vcc to IN-.
MOSFET: square law in saturation, gate fed through Rg into Ciss.
"""
import math, sys

def simulate(vref_hi, rs, rf=1e3, cf=1e-9, roff=1e6, vcc=12.0, rg=100.0,
             vth=1.9, kfet=10.0, ciss=1.1e-9, gbw=1.0e6, sr=0.4e6,
             t_on=100e-6, t_total=200e-6, dt=2e-9, vdrain_avail=8.0, rballast=0.0):
    wt = 2 * math.pi * gbw
    vout = 0.02; vg = 0.02; vminus = None
    # state for Cf: voltage across cap vc = vout - vminus
    vs = 0.0
    # initial IN-: DC solution with cap open: vminus = vs + (vcc - vs) * rf/(rf+roff)
    vminus = vs + (vcc - vs) * rf / (rf + roff)
    vc = vout - vminus
    t = 0.0
    q = 0.0  # integral of current
    t_first = None; t_90 = None; t_off10 = None
    i_peak = 0.0
    n = int(t_total / dt)
    trace = []
    for k in range(n):
        t = k * dt
        vplus = vref_hi if t < t_on else 0.0
        # MOSFET current (saturation, limited by available drain headroom / ballast)
        # source follower with degeneration: solve i_d = K*(vg - i_d*rs - vth)^2 exactly
        x = vg - vth
        if x > 0:
            kr = kfet * rs
            vov = (-1.0 + math.sqrt(1.0 + 4.0 * kr * x)) / (2.0 * kr) if kr > 0 else x
            i_d = kfet * vov * vov
        else:
            i_d = 0.0
        # headroom limit: Vds must stay >= 0
        i_max = max(0.0, vdrain_avail / (rs + rballast)) if (rs + rballast) > 0 else 1e9
        if i_d > i_max: i_d = i_max
        vs_new = i_d * rs
        # relax vs (source node has no storage in this model; mild smoothing for stability)
        vs = vs_new
        # IN- node: KCL with capacitor current ic = cf*d(vc)/dt ; solve vminus algebraically
        # (vs - vm)/rf + (vcc - vm)/roff + ic = 0, with ic = cf * d(vout - vm)/dt
        # op-amp
        dv = wt * (vplus - vminus)
        if dv > sr: dv = sr
        if dv < -sr * 1.25: dv = -sr * 1.25   # LM324 slews a bit faster downward
        vout_new = vout + dv * dt
        vout_new = min(max(vout_new, 0.02), vcc - 1.5)
        dvout = vout_new - vout
        # implicit step for vminus: cf*(dvout - dvm)/dt = (vm_new - vs)/rf + (vm_new - vcc)/roff
        a = cf / dt
        g = 1.0 / rf + 1.0 / roff
        vm_new = (a * (dvout + vminus) + vs / rf + vcc / roff) / (a + g)
        vminus = vm_new
        vout = vout_new
        # gate RC
        vg += (vout - vg) * dt / (rg * ciss)
        q += i_d * dt
        if i_d > i_peak: i_peak = i_d
        i_set = max(0.0, (vref_hi - vcc * rf / (rf + roff))) / rs
        if t_first is None and i_d > 0.02 * i_set: t_first = t
        if t_90 is None and i_d > 0.9 * i_set: t_90 = t
        if t >= t_on and t_off10 is None and i_d < 0.1 * i_set: t_off10 = t - t_on
        if k % 500 == 0: trace.append((t, vplus, vout, vg, vs, i_d))
    i_set = max(0.0, (vref_hi - vcc * rf / (rf + roff))) / rs
    eff_width = q / i_set if i_set > 0 else 0.0
    return dict(i_set=i_set, t_first=t_first, t_90=t_90, t_off10=t_off10,
                eff_width=eff_width, i_peak=i_peak, trace=trace)

def report(name, **kw):
    print(f'--- {name}')
    for ton in (10e-6, 25e-6, 50e-6, 100e-6, 250e-6):
        r = simulate(t_on=ton, t_total=ton + 150e-6, **kw)
        tf = r['t_first']; t9 = r['t_90']
        print(f"  cmd {ton*1e6:6.0f} us  Iset {r['i_set']*1e3:6.1f} mA  first light "
              f"{'never' if tf is None else f'{tf*1e6:5.1f} us'}  90% "
              f"{'never' if t9 is None else f'{t9*1e6:5.1f} us'}  off10% "
              f"{'-' if r['t_off10'] is None else f'{r['t_off10']*1e6:4.1f} us'}  "
              f"effective width {r['eff_width']*1e6:6.1f} us  peak {r['i_peak']*1e3:6.1f} mA "
              f"({100*r['i_peak']/r['i_set']:5.1f}% of set)")

if __name__ == '__main__':
    # Revision 1: IRFZ44N (Vth ~3 V), 2.5 ohm sense, reference 0-143 mV.
    report('REV 1  IRFZ44N, Rs 2.5, pot at max (52 mA)', vref_hi=0.143, rs=2.5, vth=3.0, kfet=3.6, ciss=1.47e-9)
    report('REV 1  IRFZ44N, Rs 2.5, pot at half (25 mA)', vref_hi=0.075, rs=2.5, vth=3.0, kfet=3.6, ciss=1.47e-9)
    report('REV 1  worst-case Vth 4 V, pot at max', vref_hi=0.143, rs=2.5, vth=4.0, kfet=3.6, ciss=1.47e-9)
    # Revision 2: IRLB8721 (Vth ~1.9 V), 50 ohm sense, reference 0-3.3 V.
    report('REV 2  IRLB8721, Rs 50, pot at max (66 mA)', vref_hi=3.3, rs=50.0)
    report('REV 2  IRLB8721, Rs 50, 50 mA preset', vref_hi=2.5, rs=50.0)
    report('REV 2  IRLB8721, Rs 50, 20 mA', vref_hi=1.0, rs=50.0)
    report('REV 2  worst-case Vth 2.6 V, 50 mA', vref_hi=2.5, rs=50.0, vth=2.6)
    report('REV 2  slow op-amp (0.25 V/us), 50 mA', vref_hi=2.5, rs=50.0, sr=0.25e6)
