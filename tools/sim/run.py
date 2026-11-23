#!/usr/bin/env python3
"""Circuit simulations for the task-lamp driver board, in ngspice.

    python3 tools/sim/run.py [out_dir]       (needs ngspice; matplotlib for the plots)

Each test builds a netlist from the board's values (tools/pcb/design.py), runs ngspice in
batch mode and checks the result against a limit: PASS or FAIL. INFO lines are findings with
no limit to meet. Results go to <out_dir>/results.json and plots to <out_dir>/*.png, each in a
light and a dark version (default out_dir: hardware/tasklamp-driver/sim). The models are in
models/: parts.lib says where each comes from, and mos_variant() explains the three MOSFET
models and why there are three.
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'hardware', 'tasklamp-driver', 'sim')
MODELS = os.path.join(HERE, 'models')
SETTINGS_CPP = os.path.join(ROOT, 'firmware', 'TaskLamp', 'settings.cpp')

# ---- the board (schematic values) -----------------------------------------------------------
R_GATE = 220.0           # R1-R5
R_PULLDOWN = 100e3       # R6-R10
C_BULK = 100e-6          # C1, C2: 100 uF 50 V electrolytic
R_FUSE = 0.0556          # F1: Littelfuse 0297002 (2 A mini blade), cold resistance
FUSE_I2T = 5.8           # A^2 s: the lower of the two published melting figures (5.8 and 9)
# ---- the world around the board (assumptions; each is used where it is named) ----------------
V_SUPPLY = 24.0
R_CABLE, L_CABLE = 0.10, 1.5e-6      # 1.5 m supply lead: both conductors, loop inductance
ESR_BULK = 0.3           # general-purpose electrolytic (a low-ESR type is nearer 0.05)
C_BUCK_IN = 10e-6        # buck input ceramics C3, C4 (2 x 10 uF 50 V X7R, about 5 uF each at 24 V) + C5
R_GPIO = 100.0           # RP2040 pad at its default 4 mA drive strength
V_GPIO = 3.3             # IOVDD, from the QT Py's 3.3 V regulator
L_STRIP = 1.0e-6         # strip lead plus strip copper, each channel
QTPY_LOAD = 0.085        # QT Py, TFT with backlight and the encoder, from the 5 V pin
RAIL = 23.4              # the 24 V rail after F1 and D7 with every channel on (test T1)
CHANNELS = [('R', 'STRIP_R'), ('G', 'STRIP_GB'), ('B', 'STRIP_GB'), ('WW', 'STRIP_W'), ('CW', 'STRIP_W')]
STRIPS = [('white', 'STRIP_W'), ('green/blue', 'STRIP_GB'), ('red', 'STRIP_R')]
STRIP_LABEL = {s: l for l, s in STRIPS}
# ---- IRLB8721 datasheet (typical unless named) ------------------------------------------------
VTH_MIN, VTH_TYP, VTH_MAX = 1.35, 1.80, 2.35     # VGS(th) at VDS = VGS, ID = 25 uA
VTH_TC = -0.0070                                 # VGS(th) temperature coefficient, V/K
RDS10_TYP, RDS10_MAX = 6.5e-3, 8.7e-3            # VGS 10 V, ID 31 A
RDS45_TYP, RDS45_MAX = 13.1e-3, 16e-3            # VGS 4.5 V, ID 25 A
QGS1, QGS2, QG_TYP, QG_MAX = 1.9e-9, 1.2e-9, 7.6e-9, 13e-9   # VDS 15 V, ID 25 A, up to 4.5 V
CISS, COSS, CRSS = 1077e-12, 360e-12, 110e-12    # VDS 15 V, VGS 0, 1 MHz
PLATEAU_25A = (QGS1 + QGS2) / CISS               # gate voltage at 25 A, about 2.88 V

VENDOR_VTO, VENDOR_KP = 2.65155, 66.1931         # as published (models/irlb8721pbf.spi)
VENDOR_RS, VENDOR_RD = 0.00422807, 0.0001        # its source and drain resistances
I_STRIP_W = 0.271        # white channel current on the 23.4 V rail (test T1)

# ---- the threshold region -----------------------------------------------------------------------
# Below its threshold a MOSFET still conducts: the current falls tenfold for every 77-150 mV
# less gate voltage (the subthreshold swing, 2.3 n kT/q). The EKV equation joins that region to
# the square law above it. Drawn through the datasheet's two typical points, 25 uA at VGS(th)
# and 25 A at the gate-charge plateau, it gives the gate voltage at the strip current for any
# swing. n = 2.0 (118 mV/decade) is taken as the central value and n = 1.3-2.5 as the range.
K_B_Q = 8.617333e-5      # Boltzmann's constant over the electron charge, V/K
N_CENTRAL, N_RANGE = 2.0, (1.3, 1.6, 2.0, 2.5)
SCREEN_V, SCREEN_R = 9.0, 1000.0
# ---- the 5 V buck (LMR33630ADDA, datasheet SNVSAN3F, typical) ----------------------------------
BUCK_VOUT = 1.0 * (1 + 100e3 / 24.9e3)       # VREF 1.0 V, R11 100k, R12 24.9k: 5.016 V
BUCK_RHS, BUCK_RLS = 0.095, 0.066            # switch on-resistance, ohms
BUCK_ILIM_MIN = 3.85                         # high-side current limit, minimum, A
BUCK_L, BUCK_DCR = 10e-6, 0.085              # Bourns SRP7028A-100M: 10 uH, 85 mohm max
BUCK_COUT_EACH = 16e-6                       # one 22 uF 25 V 1210 X7R at 5 V (estimate)
BUCK_CIN_EACH = 5e-6                         # one 10 uF 50 V 1210 X7R at 24 V (estimate)   # the MOSFET screening test: 9 V battery, 1 kohm, gate tied to drain


def ekv(vg, vd, vt0, k, n, t_c=25.0):
    """Drain current (A) of the EKV equation, source at 0 V; k is twice the square-law coefficient."""
    a = 2 * n * K_B_Q * (t_c + 273.15)

    def f(x):
        return math.log1p(math.exp(x)) ** 2 if x < 40 else x * x
    return k / 2 * a * a * (f((vg - vt0) / a) - f((vg - vt0 - n * vd) / a))


def solve_rising(target, fn, lo, hi):
    """x in [lo, hi] where the rising function fn(x) reaches target (bisection)."""
    for _ in range(200):
        mid = (lo + hi) / 2
        if fn(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def ekv_fit(n):
    """vt0 and k of the EKV curve with swing n through 25 uA at VGS(th) and 25 A at the plateau."""
    v2 = PLATEAU_25A - 25 * VENDOR_RS             # the plateau less the drop across the source resistance
    a = 2 * n * K_B_Q * 298.15

    def k_for(vt0):
        return 25 / (0.5 * a * a * math.log1p(math.exp((v2 - vt0) / a)) ** 2)
    # a higher vt0 (with the 25 A point held) means less current at VGS(th): find 25 uA
    vt0 = solve_rising(0, lambda x: -(ekv(VTH_TYP, VTH_TYP, x, k_for(x), n) - 25e-6), 0.5, v2)
    return vt0, k_for(vt0)


def level3_fit():
    """VTO, KP and THETA for the 'fit' model (a square law with mobility roll-off). It carries
    the white strip's current at the gate voltage the central EKV curve gives, 25 A at the
    gate-charge plateau, and has the datasheet's typical 13.1 mohm at 4.5 V."""
    vt0, k = ekv_fit(N_CENTRAL)
    v1 = solve_rising(I_STRIP_W, lambda vg: ekv(vg, 15, vt0, k, N_CENTRAL), 0, 6)
    v2 = PLATEAU_25A - 25 * VENDOR_RS
    v3 = 4.5 - 25 * VENDOR_RS
    vds3 = 25 * (RDS45_TYP - VENDOR_RS - VENDOR_RD)

    def theta_kp(vto):
        # theta and KP that put the strip current at v1 and 25 A at v2, for this VTO
        x1, x2 = v1 - vto, v2 - vto
        r = 25 * x1 * x1 / (I_STRIP_W * x2 * x2)
        theta = (1 - r) / (r * x2 - x1)
        return theta, 2 * I_STRIP_W * (1 + theta * x1) / (x1 * x1)

    def rds45_current(vto):
        theta, kp = theta_kp(vto)
        x3 = v3 - vto
        return kp / (1 + theta * x3) * (x3 - vds3 / 2) * vds3
    return vto_search(theta_kp, rds45_current, v1)


def vto_search(theta_kp, rds45_current, v1):
    """Scan VTO below v1 for the value that gives 25 A at 4.5 V (13.1 mohm), keeping THETA >= 0."""
    best = None
    steps = 6000
    for i in range(1, steps):
        vto = v1 - 0.9 * i / steps
        theta, kp = theta_kp(vto)
        if theta < 0 or kp <= 0:
            continue
        err = abs(rds45_current(vto) - 25)
        if best is None or err < best[0]:
            best = (err, vto, kp, theta)
    _, vto, kp, theta = best
    return vto, kp, theta, v1


FIT_VTO, FIT_KP, FIT_THETA, FIT_V_STRIP = level3_fit()

results = {'tests': {}, 'curves': {}}
fails = []


def record(name, ok, detail, data=None, info=False):
    results['tests'][name] = {'status': 'INFO' if info else ('PASS' if ok else 'FAIL'), 'detail': detail,
                              'data': data or {}}
    print('  %s %-34s %s' % ('INFO' if info else ('PASS' if ok else 'FAIL'), name, detail))
    if not ok and not info:
        fails.append(name)


def spice(netlist, keep=None):
    """Run a netlist with its own .control block; return ({name: value}, log)."""
    with tempfile.TemporaryDirectory(prefix='tlsim') as tmp:
        with open(os.path.join(tmp, 'run.cir'), 'w') as fh:
            fh.write(netlist)
        r = subprocess.run(['ngspice', '-b', 'run.cir'], capture_output=True, text=True, cwd=tmp, timeout=900)
        log = r.stdout + r.stderr
        vals = {}
        for m in re.finditer(r'^\s*([A-Za-z_]\w*)\s*=\s*([-+]?\d[\d.]*(?:e[-+]?\d+)?)', log, re.M | re.I):
            vals[m.group(1).lower()] = float(m.group(2))
        for name in keep or []:
            p = os.path.join(tmp, name)
            if os.path.exists(p):
                with open(p) as fh, open(os.path.join(OUT, name), 'w') as out:
                    out.write(fh.read())
        if r.returncode != 0 or not vals and not keep:
            raise RuntimeError(log[-3000:])
        return vals, log


def prints(**exprs):
    """ngspice joins 'print a b' into one expression at an operating point, so give each
    quantity its own name with let and print it on its own line."""
    return ''.join('let %s = %s\nprint %s\n' % (k, e, k) for k, e in exprs.items())


def vendor_text():
    src = open(os.path.join(MODELS, 'irlb8721pbf.spi')).read()
    return src[src.index('.SUBCKT irlb8721pbf'):src.index('.ENDS irlb8721pbf') + len('.ENDS irlb8721pbf')]


def mos_variant(kind, name, shift=0.0, kp_scale=1.0):
    """One IRLB8721 as a .subckt called `name`, its threshold moved by `shift` volts (to stand
    for another part from the datasheet's VGS(th) spread, or another temperature) and its gain
    scaled by `kp_scale`.

    'vendor'  Infineon's published model, as is. It matches the datasheet's on-resistance and
              capacitances, but its threshold is 2.65 V and its 25 A plateau about 3.6 V, where
              the datasheet's VGS(th) and gate-charge figures say 1.8 V and 2.9 V: pessimistic
              wherever the gate drive is low, which is the 3.3 V question.
    'fit'     the vendor's capacitances, body diode and resistances with the channel refitted
              (level 3: VTO, KP, THETA, from level3_fit) to the datasheet's typical figures: the
              strip current at the gate voltage the central EKV curve gives, 25 A at the
              plateau, 13.1 mohm at 4.5 V. Like any square law it carries nothing below VTO,
              so the weak-inversion tail is missing; the EKV bound in test T2 covers that.
    'dsmax'   an independent square-law model at the datasheet's MAXIMUM on-resistance
              (VTO 1.85, KP 37.23, THETA 0.143, as published in a public behavioural library).
    """
    if kind == 'dsmax':
        return """.SUBCKT {n} d g s
Rg g gi 2.0
M1 d gi s s NM_{n} L=1u W=1u
.model NM_{n} NMOS(LEVEL=3 VTO={vto:.4f} KP={kp:.4f} THETA=0.14341 RD=0.00075 RS=0.00075)
Cgs gi s 967p
Cgd gi d 110p
Dbody s d DB_{n}
.model DB_{n} D(IS=1.055e-12 N=1.2 RS=0.004 CJO=1420p VJ=0.8 M=0.5 BV=30)
.ENDS {n}
""".format(n=name, vto=1.85 + shift, kp=37.23 * kp_scale)
    body = vendor_text()
    if kind == 'vendor':
        body = body.replace('VTO=2.65155', 'VTO=%.5f' % (VENDOR_VTO + shift))
        body = body.replace('KP=66.1931', 'KP=%.4f' % (VENDOR_KP * kp_scale))
    else:
        body = body.replace('LEVEL=1', 'LEVEL=3').replace('+VTO=2.65155 LAMBDA=0 KP=66.1931',
                                                          '+VTO=%.5f THETA=%.5f KP=%.4f' % (
                                                              FIT_VTO + shift, FIT_THETA, FIT_KP * kp_scale))
    body = body.replace('.SUBCKT irlb8721pbf', '.SUBCKT %s' % name).replace('.ENDS irlb8721pbf', '.ENDS %s' % name)
    body = re.sub(r'\.MODEL (\w+)', lambda m: '.MODEL %s_%s' % (m.group(1), name), body)
    for mod in ('MM', 'MD', 'MD1', 'MD2', 'MD3'):
        body = re.sub(r'(?<=\s)%s(?=\s|$)' % mod, '%s_%s' % (mod, name), body, flags=re.M)
    return body + '\n'


def header():
    return """* task-lamp driver board
.include {m}/irlb8721pbf.spi
.include {m}/parts.lib
.options reltol=1e-4 abstol=1e-9 vntol=1e-6
{fit}""".format(m=MODELS, fit=mos_variant('fit', 'irlb_fit'))


SUB = {'vendor': 'irlb8721pbf', 'fit': 'irlb_fit'}


def load_wr(path, n):
    """wrdata writes a (time, value) pair for each vector; return the times and n value columns."""
    t, cols = [], [[] for _ in range(n)]
    for line in open(path):
        parts = line.split()
        if len(parts) >= 2 * n:
            t.append(float(parts[0]))
            for k in range(n):
                cols[k].append(float(parts[2 * k + 1]))
    return t, cols


def integrate(t, y, a, b):
    return sum(0.5 * (y[i] + y[i - 1]) * (t[i] - t[i - 1]) for i in range(1, len(t)) if t[i - 1] >= a and t[i] <= b)


def crossing(t, y, level, after, falling=False):
    for i in range(1, len(t)):
        if t[i] > after and ((y[i - 1] > level >= y[i]) if falling else (y[i - 1] < level <= y[i])):
            return t[i - 1] + (level - y[i - 1]) / (y[i] - y[i - 1]) * (t[i] - t[i - 1])
    return None


# =============================================================================================
def t0_models():
    print('T0  MOSFET models against the IRLB8721 datasheet')
    kinds = [('vendor', 'irlb8721pbf'), ('fit', 'irlb_fit'), ('dsmax', 'DSMAX')]
    net = header() + mos_variant('dsmax', 'DSMAX')
    q = {}
    for k, (_, sub) in enumerate(kinds):
        net += 'Vga{k} ga{k} 0 10\nIa{k} 0 da{k} 31\nXa{k} da{k} ga{k} 0 {s}\n'.format(k=k, s=sub)
        net += 'Vgb{k} gb{k} 0 4.5\nIb{k} 0 db{k} 25\nXb{k} db{k} gb{k} 0 {s}\n'.format(k=k, s=sub)
        q['ra%d' % k], q['rb%d' % k] = 'v(da%d)/31' % k, 'v(db%d)/25' % k
    # body diode: 25 A pulled backwards through a MOSFET that is off
    net += 'Vgd gd 0 0\nIdd dd 0 25\nXd dd gd 0 irlb8721pbf\n'
    q['vsd'] = '-v(dd)'
    v, _ = spice(net + '.control\nop\n' + prints(**q) + '.endc\n.end\n')
    r = {kind: (v['ra%d' % k], v['rb%d' % k]) for k, (kind, _) in enumerate(kinds)}
    ok = r['vendor'][0] <= RDS10_MAX and r['vendor'][1] <= RDS45_MAX and r['fit'][1] <= RDS45_MAX and v['vsd'] <= 1.0
    record('T0a on-resistance, body diode', ok,
           'at 10 V/31 A and 4.5 V/25 A: vendor %.1f/%.1f mohm; fitted %.1f mohm at 4.5 V (datasheet typ 6.5/13.1, '
           'max 8.7/16; the fitted model is for gates up to 4.5 V and reads %.0f mohm at 10 V); body diode %.2f V '
           'at 25 A (max 1.0)' % (r['vendor'][0] * 1e3, r['vendor'][1] * 1e3, r['fit'][1] * 1e3, r['fit'][0] * 1e3,
                                  v['vsd']),
           {k: {'rds10_mohm': a * 1e3, 'rds45_mohm': b * 1e3} for k, (a, b) in r.items()})
    a, b = r['dsmax']
    record('T0b worst-case model', abs(a - RDS10_MAX) < 0.1 * RDS10_MAX and abs(b - RDS45_MAX) < 0.1 * RDS45_MAX,
           'maximum-resistance model: %.2f mohm at 10 V (max 8.7), %.2f mohm at 4.5 V (max 16)' % (a * 1e3, b * 1e3),
           {'rds10_mohm': a * 1e3, 'rds45_mohm': b * 1e3})

    # capacitances at VDS 15 V, VGS 0, 1 MHz (the fitted model shares the vendor's)
    net = header() + """
Vgs1 g1 0 DC 0 AC 1
Vds1 d1 0 DC 15
X1 d1 g1 0 irlb8721pbf
Vgs2 g2 0 DC 0
Vds2 d2 0 DC 15 AC 1
X2 d2 g2 0 irlb8721pbf
.control
ac lin 1 1meg 1meg
""" + prints(ciss='abs(imag(i(vgs1)))/(2*pi*1e6)', crss='abs(imag(i(vds1)))/(2*pi*1e6)',
             coss='abs(imag(i(vds2)))/(2*pi*1e6)') + '.endc\n.end\n'
    v, _ = spice(net)
    ok = all(abs(x - y) / y < 0.35 for x, y in ((v['ciss'], CISS), (v['coss'], COSS), (v['crss'], CRSS)))
    record('T0c capacitances', ok, 'Ciss %.0f pF (datasheet 1077), Coss %.0f pF (360), Crss %.0f pF (110)' % (
        v['ciss'] * 1e12, v['coss'] * 1e12, v['crss'] * 1e12),
        {'ciss_pF': v['ciss'] * 1e12, 'coss_pF': v['coss'] * 1e12, 'crss_pF': v['crss'] * 1e12})

    # gate charge, in the datasheet's test circuit: 25 A held by a clamped load, VDS 15 V.
    # The MOSFET's share of the 25 A is read from the clamp diode, which carries the rest.
    def gate_charge(sub):
        v, _ = spice(header() + """
Vdd dd 0 15
Iload dd d 25
Dcl d dc DCL
Vdc dc dd 0
.model DCL D(IS=1e-12 N=0.02 RS=1u)
X1 d g 0 {s}
* 100 Mohm gives the gate a DC path, so the run starts with it at 0 V
Rgg g 0 100Meg
Ig 0 g PULSE(0 1m 0 1n 1n 1 2)
.control
tran 2n 24u
meas tran t_on when i(vdc)=24.75 fall=1
meas tran v_on find v(g) when i(vdc)=24.75 fall=1
meas tran t_pl when i(vdc)=0.25 fall=1
meas tran v_pl find v(g) when i(vdc)=0.25 fall=1
meas tran t_45 when v(g)=4.5 rise=1
.endc
.end
""".format(s=sub))
        return {'q_on_nC': v['t_on'] * 1e6, 'v_on': v['v_on'], 'q_pl_nC': v['t_pl'] * 1e6, 'v_pl': v['v_pl'],
                'qg_nC': v['t_45'] * 1e6}

    gv, gf = gate_charge('irlb8721pbf'), gate_charge('irlb_fit')
    ok = abs(gf['q_pl_nC'] - 3.1) < 0.4 and abs(gf['v_pl'] - PLATEAU_25A) < 0.1 and gf['qg_nC'] <= 13
    record('T0d gate charge, fitted model', ok,
           'to the 25 A plateau: %.1f nC at %.2f V (datasheet: Qgs1 + Qgs2 = 3.1 nC, so ~%.2f V); to 4.5 V: %.1f nC '
           '(typ 7.6, max 13). It starts conducting (0.25 A) at %.2f V' % (
               gf['q_pl_nC'], gf['v_pl'], PLATEAU_25A, gf['qg_nC'], gf['v_on']), gf)
    record('T0e gate charge, vendor model', True,
           'to the 25 A plateau: %.1f nC at %.2f V; to 4.5 V: %.1f nC. Its plateau sits %.2f V above the '
           "datasheet's, so it under-rates a 3.3 V gate drive" % (
               gv['q_pl_nC'], gv['v_pl'], gv['qg_nC'], gv['v_pl'] - PLATEAU_25A), gv, info=True)
    record('T0f fitted model parameters', True,
           'VTO %.3f V, KP %.1f, THETA %.2f: carries %.3f A at %.3f V (the central EKV curve, 118 mV/decade, '
           'through 25 uA at 1.80 V and 25 A at the plateau)' % (FIT_VTO, FIT_KP, FIT_THETA, I_STRIP_W, FIT_V_STRIP),
           {'vto': FIT_VTO, 'kp': FIT_KP, 'theta': FIT_THETA, 'v_strip': FIT_V_STRIP}, info=True)


# =============================================================================================
def board_power(gate_v, mos, vsup=V_SUPPLY):
    """The 24 V side of the board with every channel's gate held at gate_v."""
    s = """
Vsup sup 0 DC {vs}
Rcab sup vin {rc}
Rfuse vin vfuse {rf}
XD7 vfuse rail SB560
XD8 0 rail P6KE30A
C1 rail c1e {cb}
Rc1 c1e 0 {esr}
C2 rail c2e {cb}
Rc2 c2e 0 {esr}
* the LMR33630 buck: 5 V x the QT Py's load at about 85 %, plus 0.05 W of its own, above 6 V
Bbuck rail 0 I = V(rail) > 6 ? (5*{il}/0.85 + 0.05)/V(rail) : 0
""".format(vs=vsup, rc=R_CABLE, rf=R_FUSE, cb=C_BULK, esr=ESR_BULK, il=QTPY_LOAD + 0.01)
    for name, strip in CHANNELS:
        # Vm_ is a 0 V source in the strip lead: it measures the channel current
        s += ('Vg_{n} g_{n} 0 DC {vg}\nX{n} d_{n} g_{n} 0 {m}\nVm_{n} rail m_{n} 0\nXs_{n} m_{n} d_{n} {st}\n'
              'Dc_{n} d_{n} rail D1N5819\n').format(n=name, vg=gate_v, m=mos, st=strip)
    return s


def t1_all_on():
    print('T1  every channel at 100 %')
    vg = V_GPIO * R_PULLDOWN / (R_PULLDOWN + R_GATE)
    out = {}
    subs = dict(SUB, dsmax='DSMAX')
    for kind in ('fit', 'vendor', 'dsmax'):
        q = dict(isup='-i(vsup)', rail='v(rail)', vd7='v(vfuse)-v(rail)')
        for n, _ in CHANNELS:
            q['vds_' + n], q['ich_' + n] = 'v(d_%s)' % n, 'i(vm_%s)' % n
        v, _ = spice(header() + mos_variant('dsmax', 'DSMAX') + board_power(vg, subs[kind]) + '.control\nop\n' +
                     prints(**q) + '.endc\n.end\n')
        out[kind] = {'i_total': v['isup'], 'rail': v['rail'], 'sb560_v': v['vd7'],
                     'vds_mV': {n: v['vds_' + n.lower()] * 1e3 for n, _ in CHANNELS},
                     'i_ch': {n: v['ich_' + n.lower()] for n, _ in CHANNELS}}
    f = out['fit']
    p7 = f['sb560_v'] * f['i_total']
    ok = all(x < 100 for x in f['vds_mV'].values()) and 0.85 < f['i_total'] < 1.15 and f['rail'] > 23
    record('T1 all channels on, 3.29 V gates', ok,
           'supply %.3f A; rail %.2f V; strip currents %s A; MOSFET VDS %s mV (vendor model: up to %.1f mV; '
           'maximum-resistance model: up to %.1f mV)' % (
               f['i_total'], f['rail'], ', '.join('%s %.3f' % (n, f['i_ch'][n]) for n, _ in CHANNELS),
               ', '.join('%.1f' % f['vds_mV'][n] for n, _ in CHANNELS), max(out['vendor']['vds_mV'].values()),
               max(out['dsmax']['vds_mV'].values())),
           out)
    # thermal: SB560 in DO-201AD on 1 oz pads; RthJA ~40 K/W is a conservative figure for short leads
    pmos = max(f['vds_mV'][n] * 1e-3 * f['i_ch'][n] for n, _ in CHANNELS)
    record('T9 temperatures', p7 * 40 < 40,
           'SB560 %.2f V x %.2f A = %.2f W, about %.0f K above ambient at ~40 K/W; F1 %.0f mW; worst MOSFET %.1f mW '
           '(<0.2 K, no heatsink needed)' % (f['sb560_v'], f['i_total'], p7, p7 * 40, f['i_total'] ** 2 * R_FUSE * 1e3,
                                            pmos * 1e3),
           {'sb560_w': p7, 'sb560_rise_K': p7 * 40, 'fuse_mW': f['i_total'] ** 2 * R_FUSE * 1e3, 'mos_mW': pmos * 1e3})
    return f


# =============================================================================================
def t2_gate_margin():
    print('T2  3.3 V gate drive against the datasheet threshold spread')
    shifts = {'min': VTH_MIN - VTH_TYP, 'typ': 0.0, 'high': 0.30, 'max': VTH_MAX - VTH_TYP}
    temps = [0, 25, 85]
    gates = [3.20, 3.29]
    rows, subckts, lines, k = [], '', '', 0
    for kind in ('fit', 'vendor'):
        for corner, sh in shifts.items():
            for t in temps:
                for vg in gates:
                    k += 1
                    name = 'M%02d' % k
                    kps = ((t + 273.15) / 298.15) ** -1.5          # mobility falls as it warms
                    subckts += mos_variant(kind, name, sh + VTH_TC * (t - 25), kps)
                    lines += 'Vg{k} g{k} 0 DC {vg}\nX{k} d{k} g{k} 0 {n}\nVm{k} r m{k} 0\nXs{k} m{k} d{k} STRIP_W\n'.format(
                        k=k, vg=vg, n=name)
                    rows.append({'model': kind, 'corner': corner, 'vth_25C': VTH_TYP + sh, 'temp_C': t, 'vgs': vg,
                                 'k': k})
    q = {}
    for r in rows:
        q['vds%d' % r['k']] = 'v(d%d)' % r['k']
        q['id%d' % r['k']] = 'i(vm%d)' % r['k']
    v, _ = spice(header() + subckts + 'Vr r 0 DC %g\n' % RAIL + lines + '.control\nop\n' + prints(**q) +
                 '.endc\n.end\n')
    for r in rows:
        r['vds_mV'] = v['vds%d' % r['k']] * 1e3
        r['id'] = v['id%d' % r['k']]

    def pick(kind, corner, vg, t=None):
        sel = [r for r in rows if r['model'] == kind and r['corner'] == corner and r['vgs'] == vg and
               (t is None or r['temp_C'] == t)]
        return max(sel, key=lambda r: r['vds_mV'])

    typ = [pick(kd, 'typ', 3.29, 25) for kd in ('fit', 'vendor')]
    record('T2a typical part', all(r['vds_mV'] < 100 for r in typ),
           'VDS at %.2f A, 3.29 V gate, 25 C: fitted model %.1f mV, vendor model %.1f mV' % (
               typ[0]['id'], typ[0]['vds_mV'], typ[1]['vds_mV']), {'rows': typ})
    wf = pick('fit', 'max', 3.20)
    record('T2b part at the maximum VGS(th), fitted model', wf['vds_mV'] < 100,
           'VGS(th) 2.35 V, 3.20 V gate, worst of 0/25/85 C (%d C): VDS %.1f mV, %.3f A' % (
               wf['temp_C'], wf['vds_mV'], wf['id']), {'rows': rows})
    v25, v0 = pick('vendor', 'max', 3.29, 25), pick('vendor', 'max', 3.29, 0)
    record('T2c the same part, vendor model', True,
           'at 3.29 V it carries %.0f %% of the strip current at 25 C and %.0f %% at 0 C. The vendor model puts the '
           'threshold 0.85 V above the datasheet, so this is the pessimistic bound' % (
               100 * v25['id'] / I_STRIP_W, 100 * v0['id'] / I_STRIP_W), {}, info=True)

    # The EKV bound: every curve through the datasheet's two typical points, for subthreshold
    # swings from 77 to 148 mV/decade. Gate voltage needed to be fully on (VDS 0.1 V at the
    # white strip's current) for a part at the maximum VGS(th); and what a part would read in the
    # screening test (gate tied to drain, fed from a 9 V battery through 1 kohm, at room temperature).
    bound = []
    for n in N_RANGE:
        vt0, k = ekv_fit(n)

        def full_on(shift, t_c, vt0=vt0, k=k, n=n):
            kt = k * ((t_c + 273.15) / 298.15) ** -1.5
            vt = vt0 + shift + VTH_TC * (t_c - 25)
            return solve_rising(I_STRIP_W, lambda vg: ekv(vg, 0.1, vt, kt, n, t_c), 0, 6)
        reading = solve_rising(0, lambda vg: ekv(vg, vg, vt0, k, n) - (SCREEN_V - vg) / SCREEN_R, 0, 5)
        bound.append({'n': n, 'swing_mV': 2.302585 * n * K_B_Q * 298.15 * 1e3, 'typ_25C': full_on(0, 25),
                      'max_25C': full_on(VTH_MAX - VTH_TYP, 25), 'max_0C': full_on(VTH_MAX - VTH_TYP, 0),
                      'reading_typ': reading, 'offset_0C': full_on(0, 0) - reading})
    results['curves']['ekv_bound'] = bound
    central = [b for b in bound if b['n'] <= N_CENTRAL]
    record('T2d maximum-VGS(th) part, every datasheet-consistent curve', all(3.20 - b['max_0C'] >= 0 for b in central),
           'gate needed to be fully on, at 25 C / 0 C: %s; available 3.20 V' % '; '.join(
               '%.0f mV/dec %.2f / %.2f V' % (b['swing_mV'], b['max_25C'], b['max_0C']) for b in bound),
           {'rows': bound})
    limit = 3.20 - 0.10 - max(b['offset_0C'] for b in bound)
    limit = math.floor(limit * 20) / 20                      # round down to 0.05 V
    results['curves']['screening_limit_V'] = limit
    record('T2e screening limit', True,
           'gate tied to drain, 9 V through 1 kohm: a typical part reads %.2f-%.2f V. A part reading %.2f V or less '
           'keeps 0.1 V of margin at 0 C on every curve' % (
               min(b['reading_typ'] for b in bound), max(b['reading_typ'] for b in bound), limit),
           {'limit_V': limit}, info=True)

    # VDS against VGS(th), 3.29 V gate, 25 C (plotted)
    steps = [x / 20 for x in range(-9, 31)]          # -0.45 ... +1.50 V around the typical 1.80 V
    sweep = {}
    for kind in ('fit', 'vendor'):
        subckts, lines, q = '', '', {}
        for i, sh in enumerate(steps):
            subckts += mos_variant(kind, 'S%02d' % i, sh)
            lines += 'Vh{i} h{i} 0 DC 3.29\nXh{i} e{i} h{i} 0 S{i:02d}\nXw{i} r e{i} STRIP_W\n'.format(i=i)
            q['e%d' % i] = 'v(e%d)' % i
        v, _ = spice(header() + subckts + 'Vr r 0 DC %g\n' % RAIL + lines + '.control\nop\n' + prints(**q) +
                     '.endc\n.end\n')
        sweep[kind] = [(VTH_TYP + sh, v['e%d' % i]) for i, sh in enumerate(steps)]
    results['curves']['threshold_sweep'] = sweep


# =============================================================================================
def channel_tran(ctrl, period, width, tstop, mos='irlb_fit', strip='STRIP_W', l_strip=L_STRIP, clamp=True,
                 r_gpio=R_GPIO, r_gate=R_GATE, step='1n'):
    """One channel: GPIO pad, gate resistor and pull-down, MOSFET, strip lead, strip, clamp."""
    return header() + """
Vr rail 0 DC {rail}
Vp pad 0 PULSE(0 {vgp} 1u 2n 2n {w} {per})
Rpad pad pin {rp}
Rgate pin g {rg}
Rpd g 0 {rpd}
X1 d g 0 {mos}
Ls rail sl {ls}
Xs sl d {strip}
{clamp}
.control
tran {step} {tstop}
{ctrl}
.endc
.end
""".format(rail=RAIL, vgp=V_GPIO, w=width, per=period, rp=r_gpio, rg=r_gate, rpd=R_PULLDOWN, ls=l_strip,
           clamp='Dc d rail D1N5819' if clamp else '', step=step, tstop=tstop, ctrl=ctrl, strip=strip, mos=mos)


def firmware_min_duty():
    """The Min duty defaults in settings.cpp, in percent, by channel."""
    src = open(SETTINGS_CPP).read()
    m = re.search(r'kMinDuty\[kCh\]\s*=\s*\{([^}]*)\}', src)
    if m:
        vals = [int(x) for x in re.findall(r'\d+', m.group(1))]
    else:
        vals = [int(re.search(r'hw\.chMin\[i\]\s*=\s*(\d+)\s*;', src).group(1))] * len(CHANNELS)
    return {c: x / 1000.0 for (c, _), x in zip(CHANNELS, vals)}      # stored in 0.001 % units


def t3_pwm():
    print('T3  switching edges and the bottom of the dimming range')
    on_at, width, stop = 1e-6, 20e-6, 32e-6
    off_at = on_at + width
    edges = {}
    for kind in ('fit', 'vendor'):
        for label, strip in STRIPS:
            fn = 'edge_%s_%s.txt' % (kind, strip.lower())
            spice(channel_tran('wrdata %s v(g) v(d) i(ls)\n' % fn, 1.0, width, stop, mos=SUB[kind], strip=strip,
                               step='5n'), keep=[fn])
            t, (vg, vd, i) = load_wr(os.path.join(OUT, fn), 3)
            sel = [k for k, x in enumerate(t) if off_at - 5e-6 <= x <= off_at - 0.1e-6]
            ion = sum(i[k] for k in sel) / len(sel)
            pcond = sum(vd[k] * i[k] for k in sel) / len(sel)
            p = [a * b for a, b in zip(vd, i)]
            t10, t90 = crossing(t, i, 0.1 * ion, on_at), crossing(t, i, 0.9 * ion, on_at)
            f90, f10 = crossing(t, i, 0.9 * ion, off_at, True), crossing(t, i, 0.1 * ion, off_at, True)
            # the light pulse is shorter than the gate pulse by this much (from the charge it carries)
            dead = width - integrate(t, i, 0, stop) / ion
            edges[(kind, label)] = {
                'i_on': ion, 'delay_on_us': (t10 - on_at) * 1e6, 'rise_us': (t90 - t10) * 1e6,
                'delay_off_us': (f90 - off_at) * 1e6, 'fall_us': (f10 - f90) * 1e6,
                'e_sw_nJ': (integrate(t, p, on_at, on_at + 8e-6) - pcond * 8e-6 + integrate(t, p, off_at, stop)) * 1e9,
                'dead_us': dead * 1e6}
    results['curves']['edges'] = {'%s/%s' % k: e for k, e in edges.items()}
    w = edges[('fit', 'white')]
    loss20 = max(e['e_sw_nJ'] * 1e-9 * 20000 for (kind, _), e in edges.items() if kind == 'fit')
    record('T3a switching', loss20 < 0.05,
           'white channel, %.2f A: on after %.2f us, rising over %.2f us; off after %.2f us, falling over %.2f us. '
           'Switching loss at 20 kHz, the firmware maximum: %.1f mW per MOSFET' % (
               w['i_on'], w['delay_on_us'], w['rise_us'], w['delay_off_us'], w['fall_us'], loss20 * 1e3),
           {'loss_20k_mW': loss20 * 1e3})

    # The dimming floor. Each light pulse is shorter than its gate pulse by the dead time (the
    # gate takes time to rise to the plateau, and to fall back through it). The firmware starts
    # every channel at its Min duty, so Min duty should be that dead time over the PWM period.
    fw = firmware_min_duty()
    sim = {c: edges[('fit', STRIP_LABEL[s])]['dead_us'] * 1e-6 * 2000 * 100 for c, s in CHANNELS}
    ok = all(abs(fw[c] - sim[c]) <= 0.35 * sim[c] for c, _ in CHANNELS)
    record('T3b Min duty defaults (2 kHz)', ok,
           'dead time (fitted model) %s us, so Min duty %s %%; firmware defaults %s %%' % (
               ', '.join('%s %.2f' % (l, edges[('fit', l)]['dead_us']) for l, _ in STRIPS),
               ', '.join('%s %.3f' % (c, sim[c]) for c, _ in CHANNELS),
               ', '.join('%s %.3f' % (c, fw[c]) for c, _ in CHANNELS)),
           {'sim_pct': sim, 'firmware_pct': fw})
    record('T3c dead time, vendor model', True,
           '%s us: Min duty would be %s %% at 2 kHz. At 20 kHz every floor is ten times larger' % (
               ', '.join('%s %.2f' % (l, edges[('vendor', l)]['dead_us']) for l, _ in STRIPS),
               ', '.join('%.3f' % (edges[('vendor', l)]['dead_us'] * 0.2) for l, _ in STRIPS)), {}, info=True)

    # single short pulses: light delivered against an ideal switch (plotted)
    widths = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 20.0]
    curves = {}
    for kind in ('fit', 'vendor'):
        ion = edges[(kind, 'white')]['i_on']
        pts = []
        for wd in widths:
            v, _ = spice(channel_tran('meas tran q integ i(ls) from=0 to=%g\n' % ((wd + 15) * 1e-6), 1.0, wd * 1e-6,
                                      (wd + 15) * 1e-6, mos=SUB[kind], step='2n'))
            pts.append((wd, 100 * v['q'] / (ion * wd * 1e-6)))
        curves[kind] = pts
    results['curves']['single_pulse'] = curves
    results['curves']['fw_min_duty_white_us'] = fw['WW'] / 100 / 2000 * 1e6


# =============================================================================================
def t4_turn_off():
    print('T4  turn-off spike from the strip wiring')
    out = {}
    for l_strip in (1e-6, 3e-6):
        for clamp in (True, False):
            # worst case: the gate pulled down hard, so the current stops as fast as it can
            v, _ = spice(channel_tran('meas tran vmax max v(d) from=10u to=40u\n', 1.0, 10e-6, 40e-6, l_strip=l_strip,
                                      clamp=clamp, r_gpio=1, r_gate=10, step='0.5n'))
            out['%s_%duH' % ('clamped' if clamp else 'bare', round(l_strip * 1e6))] = v['vmax']
    ok = out['clamped_3uH'] < 26.0
    record('T4 drain spike at turn-off', ok,
           'peak drain voltage with D1-D5: %.1f V (1 uH lead), %.1f V (3 uH); without them: %.1f V, %.1f V '
           '(MOSFET rated 30 V; the model clamps at 30 V)' % (
               out['clamped_1uH'], out['clamped_3uH'], out['bare_1uH'], out['bare_3uH']), out)


# =============================================================================================
def t5_hot_plug():
    print('T5  plugging in a live 24 V lead')
    cases = [('general-purpose capacitors, 1.5 m lead', ESR_BULK, 1.5e-6, 0.10),
             ('low-ESR capacitors, short heavy lead', 0.05, 1.0e-6, 0.03),
             ('general-purpose capacitors, 5 m lead', ESR_BULK, 5e-6, 0.30)]
    data = {}
    for k, (label, esr, lc, rc) in enumerate(cases):
        v, _ = spice(header() + """
Vsup sup 0 PWL(0 0 10u 0 11u {vs})
Lcab sup s2 {lc}
Rcab s2 vin {rc}
Rfuse vin vfuse {rf}
XD7 vfuse rail SB560
XD8 0 rail P6KE30A
C1 rail c1e {cb}
Rc1 c1e 0 {esr}
C2 rail c2e {cb}
Rc2 c2e 0 {esr}
Coki rail ce {co}
Rcoki ce 0 0.01
Bbuck rail 0 I = V(rail) > 6 ? 0.65/V(rail) : 0
.control
tran 20n 3m uic
meas tran ipk max i(lcab)
meas tran vpk max v(rail)
let i2 = i(lcab)*i(lcab)
meas tran i2t integ i2 from=0 to=3m
wrdata hotplug_{k}.txt i(lcab) v(rail)
.endc
.end
""".format(vs=V_SUPPLY, lc=lc, rc=rc, rf=R_FUSE, cb=C_BULK, esr=esr, co=C_BUCK_IN, k=k), keep=['hotplug_%d.txt' % k])
        data[label] = {'ipk': v['ipk'], 'vpk': v['vpk'], 'i2t': v['i2t']}
    worst_v = max(d['vpk'] for d in data.values())
    worst_i2t = max(d['i2t'] for d in data.values())
    # Littelfuse's pulse guideline: a pulse under 22 % of the melting I2t survives 100,000 times
    ok = worst_v < 28.5 and worst_i2t < 0.22 * FUSE_I2T
    record('T5 hot-plug', ok, '; '.join('%s: %.0f A peak, rail peaks at %.1f V, %.2f A2s' % (
        k, d['ipk'], d['vpk'], d['i2t']) for k, d in data.items()) +
        '. Fuse melts at ~%.1f A2s; the TVS starts at 28.5 V, the buck chip is rated 36 V' % FUSE_I2T, data)


# =============================================================================================
def t6_reverse():
    print('T6  supply wired backwards')
    v, _ = spice(header() + board_power(0.0, 'irlb_fit', vsup=-V_SUPPLY) + '.control\nop\n' +
                 prints(isup='i(vsup)', rail='v(rail)', hold='v(rail)-v(vfuse)') + '.endc\n.end\n')
    i = abs(v['isup'])
    record('T6 reverse polarity', i < 1e-3 and v['rail'] > -0.5,
           'current drawn %.1f uA; rail %.3f V; D7 holds off %.1f V' % (i * 1e6, v['rail'], v['hold']),
           {'i_uA': i * 1e6, 'rail': v['rail']})


# =============================================================================================
def t7_five_volt():
    print('T7  the QT Py supply: 24 V is the only input; USB on the QT Py stays separate')
    out = {}
    for label, oki, usb in (('24 V only', BUCK_VOUT, 0.0), ('USB only, board off', 0.0, 5.0),
                            ('both', BUCK_VOUT, 5.0), ('both, USB at 5.25 V', BUCK_VOUT, 5.25)):
        v, _ = spice(header() + """
* the buck's output, regulated, behind its 4 x 22 uF
Voki o5x 0 DC {oki}
Roki o5x o5 0.01
C4 o5 0 64u
D6 o5 qt5 D1N5819
Vusb vb 0 DC {usb}
Rusb vb vbi 0.2
Dusb vbi qt5 DNSR0320
* the QT Py's 3.3 V regulator: its load, while it has headroom
Bldo qt5 0 I = V(qt5) > 3.4 ? {il} + 55u : 1u
.control
op
""".format(oki=oki, usb=usb, il=QTPY_LOAD) + prints(v5='v(qt5)', ioki='-i(voki)', iusb='-i(vusb)') + '.endc\n.end\n')
        out[label] = {'v5': v['v5'], 'i_oki': v['ioki'], 'i_usb': v['iusb']}
    back = min(min(d['i_oki'], d['i_usb']) for d in out.values())
    ok = all(d['v5'] > 4.5 for d in out.values()) and back > -100e-6
    record('T7 5 V path', ok, '; '.join('%s: 5V pin %.2f V (buck %.0f mA, USB %.0f mA)' % (
        k, d['v5'], d['i_oki'] * 1e3, d['i_usb'] * 1e3) for k, d in out.items()) +
        '; at most %.1f uA flows back into either source' % max(0.0, -back * 1e6), out)


# =============================================================================================
def t8_reset():
    print('T8  pins undriven (reset, bootloader, QT Py unplugged)')
    v, _ = spice(header() + """
Vr rail 0 DC {rail}
Ileak 0 pin DC 1u
Rgate pin g 220
Rpd g 0 100k
X1 d g 0 irlb_fit
Vm rail m 0
Xs m d STRIP_W
.control
op
""".format(rail=RAIL) + prints(vg='v(g)', istrip='abs(i(vm))') + '.endc\n.end\n')
    ok = v['vg'] < VTH_MIN / 2
    record('T8 gate held off by 100k', ok,
           'with 1 uA of pin leakage the gate sits at %.3f V (VGS(th) min %.2f V); strip current %.2g A' % (
               v['vg'], VTH_MIN, v['istrip']), {'vg': v['vg'], 'i_strip': v['istrip']})


# =============================================================================================
def t10_ripple():
    print('T10 every channel switching together at 2 kHz, 50 %')
    net = header() + """
Vsup sup 0 DC {vs}
Lcab sup s2 {lc}
Rcab s2 vin {rc}
Rfuse vin vfuse {rf}
XD7 vfuse rail SB560
XD8 0 rail P6KE30A
C1 rail c1a {cb}
Vc1 c1a c1e 0
Rc1 c1e 0 {esr}
C2 rail c2a {cb}
Vc2 c2a c2e 0
Rc2 c2e 0 {esr}
Coki rail ce {co}
Rcoki ce 0 0.01
Bbuck rail 0 I = V(rail) > 6 ? (5*{il}/0.85 + 0.05)/V(rail) : 0
Vp pad 0 PULSE(0 {vgp} 0 2n 2n 250u 500u)
""".format(vs=V_SUPPLY, lc=L_CABLE, rc=R_CABLE, rf=R_FUSE, cb=C_BULK, esr=ESR_BULK, co=C_BUCK_IN,
           il=QTPY_LOAD + 0.01, vgp=V_GPIO)
    for n, strip in CHANNELS:
        net += ('Rp_{n} pad pin_{n} {rp}\nRg_{n} pin_{n} g_{n} {rg}\nRpd_{n} g_{n} 0 {rpd}\nX{n} d_{n} g_{n} 0 irlb_fit\n'
                'Ls_{n} rail sl_{n} {ls}\nXs_{n} sl_{n} d_{n} {st}\nDc_{n} d_{n} rail D1N5819\n').format(
            n=n, rp=R_GPIO, rg=R_GATE, rpd=R_PULLDOWN, ls=L_STRIP, st=strip)
    v, _ = spice(net + """.control
tran 20n 4m
meas tran vpp pp v(rail) from=2m to=4m
meas tran vmin min v(rail) from=2m to=4m
meas tran ic1 rms i(vc1) from=2m to=4m
meas tran isup rms i(lcab) from=2m to=4m
meas tran ipk max i(lcab) from=2m to=4m
.endc
.end
""")
    # a general-purpose 100 uF 50 V electrolytic is rated about 0.2 A rms at 120 Hz, more at 2 kHz
    ok = v['vpp'] < 0.5 and v['ic1'] < 0.2
    record('T10 rail ripple', ok,
           'rail ripple %.2f V p-p (low point %.2f V); each bulk capacitor carries %.0f mA rms; supply lead %.2f A rms, '
           '%.2f A peak' % (v['vpp'], v['vmin'], v['ic1'] * 1e3, v['isup'], v['ipk']),
           {'vpp': v['vpp'], 'vmin': v['vmin'], 'ic_rms_mA': v['ic1'] * 1e3, 'isup_rms': v['isup'], 'ipk': v['ipk']})


# =============================================================================================
def t11_buck():
    """The buck's power stage: the chip's switches as switches with the datasheet's on-resistance,
    taking turns at 400 kHz; inductor, ceramic capacitors and load as on the board. The chip's
    control loop isn't modelled (TI publishes no model of it), so the duty cycle is set to land
    on 5.0 V; what this checks is everything the parts around the chip decide."""
    print('T11 the 5 V buck converter, power stage')
    rows = []
    cases = [('QT Py, display and encoder', RAIL, 0.10, 400e3, 1.0),
             ('half an amp', RAIL, 0.5, 400e3, 1.0),
             ('the chip\'s full 3 A', RAIL, 3.0, 400e3, 1.0),
             ('3 A, worst case: 26.4 V in, slow clock, L -20 %', 26.4, 3.0, 340e3, 0.8)]
    for label, vin, iout, fsw, lscale in cases:
        per = 1 / fsw
        d = (BUCK_VOUT + iout * (BUCK_DCR + BUCK_RLS)) / (vin - iout * (BUCK_RHS - BUCK_RLS))
        ton, dead = d * per, 10e-9
        deck = header() + """
VIN vsrc 0 DC {vin}
LSRC vsrc vlead 1u
RSRC vlead vin 0.05
C1 vin c1 100u
R1 c1 0 {esr}
VS1 vin s1 0
CIN1 s1 cin1 {cin}
RIN1 cin1 0 0.004
VS2 vin s2 0
CIN2 s2 cin2 {cin}
RIN2 cin2 0 0.004
CHF vin 0 0.2u
VGH gh 0 PULSE(0 1 {dead} 1n 1n {ton1} {per})
VGL gl 0 PULSE(0 1 {tl0} 1n 1n {tl1} {per})
SHS vin sw gh 0 HSW
SLS sw 0 gl 0 LSW
DBODY 0 sw DB
DBODYH sw vin DB
.model HSW SW(Ron={rhs} Roff=1e6 Vt=0.5 Vh=0.1)
.model LSW SW(Ron={rls} Roff=1e6 Vt=0.5 Vh=0.1)
.model DB D(Is=1e-12 N=1.2 Rs=0.02)
L1 sw lx {l} IC={iout}
RL lx vout {dcr}
""".format(vin=vin, esr=ESR_BULK, cin=BUCK_CIN_EACH, dead=dead, ton1=ton - 2e-9, per=per, tl0=ton + 2 * dead,
                tl1=per - ton - 3 * dead - 2e-9, rhs=BUCK_RHS, rls=BUCK_RLS, l=BUCK_L * lscale, iout=iout,
                dcr=BUCK_DCR) + ''.join('C{i} vout c{i} {c} IC={v}\nRC{i} c{i} 0 0.003\n'.format(
                    i=i + 10, c=BUCK_COUT_EACH, v=BUCK_VOUT) for i in range(4)) + """RLOAD vout 0 {rl}
.options method=gear reltol=1e-4
.control
tran 2n {t1} {t0} 2n uic
meas tran vavg AVG v(vout)
meas tran vpp PP v(vout)
meas tran ilmax MAX i(L1)
meas tran ilmin MIN i(L1)
let pinst = v(vsrc)*(-i(VIN))
meas tran pin AVG pinst
let icin = i(VS1)+i(VS2)
meas tran icinrms RMS icin
.endc
.end
""".format(rl=BUCK_VOUT / iout, t1=500 * per, t0=460 * per)
        v, _ = spice(deck)
        pout = v['vavg'] ** 2 / (BUCK_VOUT / iout)
        rows.append({'case': label, 'vin': vin, 'iout': iout, 'vout': v['vavg'], 'ripple_A': v['ilmax'] - v['ilmin'],
                     'peak_A': v['ilmax'], 'vout_pp_mV': v['vpp'] * 1e3, 'cin_rms_A': v['icinrms'],
                     'loss_W': v['pin'] - pout, 'eff': pout / v['pin']})
    results['curves']['buck'] = rows
    full = rows[2]
    worst = rows[3]
    ok = worst['peak_A'] < BUCK_ILIM_MIN and all(r['vout_pp_mV'] < 50 for r in rows)
    record('T11a buck current and ripple', ok,
           'inductor ripple %.2f A peak to peak; peak %.2f A at 3 A (%.2f A worst case) against the chip\'s 3.85 A '
           'minimum limit; output ripple %s mV' % (full['ripple_A'], full['peak_A'], worst['peak_A'],
                                                   ', '.join('%.0f' % r['vout_pp_mV'] for r in rows)), {'rows': rows})
    light = rows[0]
    ok = all(r['cin_rms_A'] < 2 * 3.0 for r in rows) and light['loss_W'] < 0.25
    record('T11b buck losses', ok,
           'at the lamp\'s real load (0.1 A) the switches and inductor lose %.0f mW (conduction only; the chip '
           'skips pulses at light load, which this forced-PWM model does not); at 3 A %.2f W, %.0f %% efficient; '
           'input capacitors carry %.2f A rms at 3 A (each 10 uF 1210 is good for about 3 A)' % (
               light['loss_W'] * 1e3, full['loss_W'], full['eff'] * 100, full['cin_rms_A']), {})
    # the feedback divider's tolerance: VREF 0.985-1.015 V, both resistors 1 %
    lo = 0.985 * (1 + 100e3 * 0.99 / (24.9e3 * 1.01))
    hi = 1.015 * (1 + 100e3 * 1.01 / (24.9e3 * 0.99))
    record('T11c 5 V setting', 4.75 <= lo and hi <= 5.25,
           'nominal %.3f V; %.2f-%.2f V with VREF and both resistors at their limits (USB-style 4.75-5.25 V)' % (
               BUCK_VOUT, lo, hi), {'lo': lo, 'hi': hi})


# =============================================================================================
THEMES = {
    # the dataviz reference palette: chart surface, text tokens, hairlines, series slots 1-3
    'light': dict(surface='#fcfcfb', ink='#0b0b0b', ink2='#52514e', muted='#898781', grid='#e1e0d9',
                  base='#c3c2b7', series=['#2a78d6', '#eb6834', '#1baf7a']),
    'dark': dict(surface='#1a1a19', ink='#f0efec', ink2='#c3c2b7', muted='#898781', grid='#2c2c2a',
                 base='#383835', series=['#3987e5', '#d95926', '#199e70']),
}
PX = 72 / 100.0          # one CSS pixel in points, for a figure laid out at 100 dpi


def plots():
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FuncFormatter
    except ImportError:
        print('  (matplotlib not installed: no plots)')
        return
    model_label = {'fit': 'datasheet-fitted model', 'vendor': 'vendor model'}

    def style(ax, th, title, xl, yl):
        ax.set_facecolor(th['surface'])
        ax.set_title(title, loc='left', fontsize=10, color=th['ink'], pad=8)
        ax.set_xlabel(xl, color=th['ink2'], fontsize=9)
        ax.set_ylabel(yl, color=th['ink2'], fontsize=9)
        ax.grid(True, color=th['grid'], linewidth=1 * PX, linestyle='-')
        ax.set_axisbelow(True)
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
        for side in ('left', 'bottom'):
            ax.spines[side].set_color(th['base'])
            ax.spines[side].set_linewidth(1 * PX)
        ax.tick_params(colors=th['muted'], labelsize=8, length=0)
        for lab in ax.get_xticklabels() + ax.get_yticklabels():
            lab.set_color(th['ink2'])

    def line(ax, th, x, y, slot, label=None, marker=False):
        kw = dict(color=th['series'][slot], linewidth=2 * PX, solid_capstyle='round', solid_joinstyle='round',
                  label=label)
        if marker:
            kw.update(marker='o', markersize=8 * PX, markeredgecolor=th['surface'], markeredgewidth=2 * PX)
        ax.plot(x, y, **kw)

    def ref(ax, th, horizontal, value, text, where, ha='left'):
        (ax.axhline if horizontal else ax.axvline)(value, color=th['ink2'], linewidth=1 * PX)
        if text:
            ax.annotate(text, where, xycoords=('axes fraction', 'data') if horizontal else ('data', 'axes fraction'),
                        fontsize=7.5, color=th['ink2'], ha=ha, va='bottom')

    def legend(fig_or_ax, th, **kw):
        lg = fig_or_ax.legend(frameon=False, fontsize=8, labelcolor=th['ink'], **kw)
        return lg

    def save(fig, th_name, stem):
        fig.savefig(os.path.join(OUT, '%s%s.png' % (stem, '' if th_name == 'light' else '-dark')), dpi=200,
                    facecolor=fig.get_facecolor())
        plt.close(fig)

    curves = results['curves']
    for th_name, th in THEMES.items():
        # 1. switching edges, white channel: gate voltage and strip current, both models
        fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.6), sharey='row', facecolor=th['surface'])
        for col, (a, b, title) in enumerate(((0.6, 5.0, 'Turn-on'), (20.6, 23.5, 'Turn-off'))):
            for slot, kind in enumerate(('fit', 'vendor')):
                rows = [list(map(float, l.split())) for l in open(os.path.join(OUT, 'edge_%s_strip_w.txt' % kind))]
                sel = [r for r in rows if a <= r[0] * 1e6 <= b]
                line(axes[0][col], th, [r[0] * 1e6 for r in sel], [r[1] for r in sel], slot,
                     model_label[kind] if col == 0 else None)
                line(axes[1][col], th, [r[0] * 1e6 for r in sel], [r[5] for r in sel], slot)
            style(axes[0][col], th, title + ', white channel: gate', '', 'volts' if col == 0 else '')
            style(axes[1][col], th, 'Strip current', 'microseconds', 'amps' if col == 0 else '')
        legend(fig, th, loc='upper right', ncol=2, bbox_to_anchor=(0.99, 1.0))
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        save(fig, th_name, 'pwm_edges')

        # 2. light from one short pulse, against an ideal switch
        fig, ax = plt.subplots(figsize=(7.2, 3.4), facecolor=th['surface'])
        for slot, kind in enumerate(('fit', 'vendor')):
            pts = curves['single_pulse'][kind]
            line(ax, th, [p[0] for p in pts], [p[1] for p in pts], slot, model_label[kind], marker=True)
            ax.annotate(model_label[kind], (pts[-1][0], pts[-1][1]), xytext=(6, -3), textcoords='offset points',
                        fontsize=7.5, color=th['ink2'])
        ax.set_xscale('log')
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: ('%g' % x)))
        ax.set_xlim(0.09, 60)
        ax.set_ylim(0, 105)
        style(ax, th, 'Light from one pulse, as a share of a perfect switch (white channel)',
              'gate pulse, microseconds', 'percent')
        fwus = curves['fw_min_duty_white_us']
        ref(ax, th, False, fwus, 'Min duty default\n(white, 2 kHz) ', (fwus, 0.80), ha='right')
        legend(ax, th, loc='center right')
        fig.tight_layout()
        save(fig, th_name, 'dimming_floor')

        # 3. how far the threshold can rise before the switch is not fully on
        fig, ax = plt.subplots(figsize=(7.2, 3.4), facecolor=th['surface'])
        for slot, kind in enumerate(('fit', 'vendor')):
            pts = curves['threshold_sweep'][kind]
            line(ax, th, [p[0] for p in pts], [max(p[1], 1e-3) for p in pts], slot, model_label[kind], marker=True)
        ax.set_yscale('log')
        ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: ('%g' % y)))
        style(ax, th, 'Drain voltage with the white strip on, 3.29 V gate, by threshold voltage',
              'VGS(th) of the part, volts (datasheet: 1.35 to 2.35)', 'VDS, volts')
        ref(ax, th, True, 0.1, ' 0.1 V: fully on below this line', (0.01, 0.105))
        ref(ax, th, False, VTH_MAX, 'datasheet maximum ', (VTH_MAX, 0.70), ha='right')
        legend(ax, th, loc='upper left')
        fig.tight_layout()
        save(fig, th_name, 'threshold_sweep')

        # 4. hot-plug: inrush current and rail voltage, three cases
        fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), facecolor=th['surface'])
        labels = list(results['tests']['T5 hot-plug']['data'].keys())
        for k, lab in enumerate(labels):
            rows = [list(map(float, l.split())) for l in open(os.path.join(OUT, 'hotplug_%d.txt' % k))]
            sel = [r for r in rows if r[0] < 0.25e-3]
            line(axes[0], th, [r[0] * 1e3 for r in sel], [r[1] for r in sel], k, lab)
            line(axes[1], th, [r[0] * 1e3 for r in sel], [r[3] for r in sel], k)
        style(axes[0], th, 'Inrush current', 'milliseconds', 'amps')
        style(axes[1], th, 'Rail voltage', 'milliseconds', 'volts')
        axes[1].set_ylim(0, 30)
        ref(axes[1], th, True, 28.5, ' TVS starts conducting', (0.02, 28.6))
        legend(fig, th, loc='upper center', ncol=1, bbox_to_anchor=(0.5, 1.0))
        fig.tight_layout(rect=(0, 0, 1, 0.80))
        save(fig, th_name, 'hot_plug')


def main():
    os.makedirs(OUT, exist_ok=True)
    t0_models()
    t1_all_on()
    t2_gate_margin()
    t3_pwm()
    t4_turn_off()
    t5_hot_plug()
    t6_reverse()
    t7_five_volt()
    t8_reset()
    t10_ripple()
    t11_buck()
    plots()
    for name in os.listdir(OUT):              # waveforms were only needed for the plots
        if name.endswith('.txt'):
            os.remove(os.path.join(OUT, name))
    with open(os.path.join(OUT, 'results.json'), 'w') as fh:
        json.dump(results, fh, indent=1, default=float)
    n = sum(1 for t in results['tests'].values() if t['status'] != 'INFO')
    print('\n%d tests, %d failed%s' % (n, len(fails), (': ' + ', '.join(fails)) if fails else ''))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
