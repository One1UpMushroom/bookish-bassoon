"""Breadboard layout for the task lamp driver stage, as data.

Everything the build booklet draws comes from this file, and `verify()` proves
that the placement implements the schematic: every lead sits in its own hole,
every net is one electrical node, and no two nets touch.

Two half-size (30-row, 400-point) breadboards:
  Board A  24 V rails, strip switches (WW, CW), current-set pots (R, G, B)
  Board B  12 V rails, L7812, LM324, three RGB current sinks

Hole names: column a-e (left half) or f-j (right half) + row, e.g. "c7".
Rail holes: "L+7", "L-7", "R+7", "R-7" (the row only says where to plug in).
"""
from dataclasses import dataclass, field

ROWS = 30
LEFT, RIGHT = "abcde", "fghij"
RAILS = ("L+", "L-", "R+", "R-")


def parse(hole):
    """'c7' -> ('c', 7); 'L-12' -> ('L-', 12)."""
    for r in RAILS:
        if hole.startswith(r):
            return r, int(hole[len(r):])
    return hole[0], int(hole[1:])


def node(board, hole):
    """Electrical node of a hole: a 5-hole strip, or a whole rail."""
    col, row = parse(hole)
    if col in RAILS:
        return (board, col)
    return (board, "L" if col in LEFT else "R", row)


@dataclass
class Part:
    id: str
    kind: str            # res, cap, ecap, diode, to220, dip14, pot, staple
    board: str
    pins: dict           # pin name -> hole
    nets: dict           # pin name -> net
    value: str = ""
    step: str = ""
    inv: str = ""        # inventory ID
    note: str = ""


@dataclass
class Wire:
    id: str
    a: tuple             # (board, hole) or ("ext", label)
    b: tuple
    net: str
    color: str
    step: str = ""
    thick: bool = False


parts, wires = [], []


def P(id, kind, board, pins, nets, value="", step="", inv="", note=""):
    parts.append(Part(id, kind, board, pins, nets, value, step, inv, note))


def two(id, kind, board, h1, h2, n1, n2, value, step, inv, note=""):
    P(id, kind, board, {"1": h1, "2": h2}, {"1": n1, "2": n2}, value, step, inv, note)


def W(id, a, b, net, color, step, thick=False):
    def end(x):
        if x.startswith("ext:"):
            return ("ext", x[4:])
        board, hole = x.split(":")
        return (board, hole)
    wires.append(Wire(id, end(a), end(b), net, color, step, thick))


# --------------------------------------------------------------------------
# Board A: 24 V rails, strip switches, current-set pots
# --------------------------------------------------------------------------
W("A_br24", "A:L+1", "A:R+1", "P24", "red", "A1")
W("A_brG", "A:L-2", "A:R-2", "GND", "black", "A1")

# Warm-white switch (left half). All TO-220 labels face LEFT: G on top.
P("QW", "to220", "A", {"G": "e6", "D": "e7", "S": "e8"},
  {"G": "GATE_WW", "D": "DRAIN_WW", "S": "GND"}, "IRLB8721", "A2", "Q-004")
# Cool-white switch (right half), five rows lower so the two tabs never face.
P("QC", "to220", "A", {"G": "f12", "D": "f13", "S": "f14"},
  {"G": "GATE_CW", "D": "DRAIN_CW", "S": "GND"}, "IRLB8721", "A2", "Q-004")

two("RgW", "res", "A", "c2", "c6", "PWM_WW", "GATE_WW", "220", "A3", "R-006")
two("RgC", "res", "A", "h8", "h12", "PWM_CW", "GATE_CW", "220", "A3", "R-006")
two("RpW", "res", "A", "a6", "L-6", "GATE_WW", "GND", "100k", "A3", "R-014")
two("RpC", "res", "A", "j12", "R-12", "GATE_CW", "GND", "100k", "A3", "R-014")

# Clamp diodes: anode on the drain row, cathode (stripe) on the +24 V rail.
P("DW", "diode", "A", {"A": "a7", "K": "L+7"}, {"A": "DRAIN_WW", "K": "P24"}, "1N5819", "A4", "D-002")
P("DC", "diode", "A", {"A": "j13", "K": "R+13"}, {"A": "DRAIN_CW", "K": "P24"}, "1N5819", "A4", "D-002")

P("Cb1", "ecap", "A", {"+": "L+12", "-": "L-12"}, {"+": "P24", "-": "GND"}, "100u", "A5", "C-044")
P("Cb2", "ecap", "A", {"+": "R+6", "-": "R-6"}, {"+": "P24", "-": "GND"}, "100u", "A5", "C-044")

W("A_srcW", "A:c8", "A:L-9", "GND", "black", "A6")
W("A_srcC", "A:i14", "A:R-15", "GND", "black", "A6")

# Current-set pots: outer legs = track ends, middle leg = wiper.
P("PR", "pot", "A", {"1": "a16", "W": "a18", "3": "a20"},
  {"1": "PWM_R", "W": "REF_R", "3": "GND"}, "10k", "A7", "E-041")
P("PG", "pot", "A", {"1": "j18", "W": "j20", "3": "j22"},
  {"1": "PWM_G", "W": "REF_G", "3": "GND"}, "10k", "A7", "E-041")
P("PB", "pot", "A", {"1": "a24", "W": "a26", "3": "a28"},
  {"1": "PWM_B", "W": "REF_B", "3": "GND"}, "10k", "A7", "E-041")
W("A_pgR", "A:c20", "A:L-22", "GND", "black", "A8")
W("A_pgG", "A:h22", "A:R-24", "GND", "black", "A8")
W("A_pgB", "A:c28", "A:L-30", "GND", "black", "A8")

# --------------------------------------------------------------------------
# Board B: 12 V rails, regulator, op-amp, three current sinks
# --------------------------------------------------------------------------
W("B_br12", "B:L+29", "B:R+29", "P12", "orange", "B1")
W("B_brG", "B:L-30", "B:R-30", "GND", "black", "B1")

# L7812, label facing left: IN on top, GND, OUT.
P("VR", "to220", "B", {"IN": "f2", "GND": "f3", "OUT": "f4"},
  {"IN": "P24", "GND": "GND", "OUT": "P12"}, "L7812", "B2", "VR-006")
two("Cin", "cap", "B", "h2", "h3", "P24", "GND", "330n", "B2", "C-024")
two("Cout", "cap", "B", "i3", "i4", "GND", "P12", "100n", "B2", "C-021")
P("C12", "ecap", "B", {"+": "R+7", "-": "R-7"}, {"+": "P12", "-": "GND"}, "10u", "B2", "C-038")
W("B_regG", "B:j3", "B:R-3", "GND", "black", "B2")
W("B_reg12", "B:j4", "B:R+4", "P12", "orange", "B2")

# LM324: pins 1-7 down column e (rows 12-18), pins 14-8 down column f.
P("U", "dip14", "B",
  {"1": "e12", "2": "e13", "3": "e14", "4": "e15", "5": "e16", "6": "e17", "7": "e18",
   "14": "f12", "13": "f13", "12": "f14", "11": "f15", "10": "f16", "9": "f17", "8": "f18"},
  {"1": "OUT_R", "2": "FB_R", "3": "REF_R", "4": "P12", "5": "REF_G", "6": "FB_G", "7": "OUT_G",
   "14": "A4", "13": "A4", "12": "GND", "11": "GND", "10": "REF_B", "9": "FB_B", "8": "OUT_B"},
  "LM324", "B3", "IC-001")
W("B_vcc", "B:a15", "B:L+15", "P12", "orange", "B3")
two("SA4", "staple", "B", "h12", "h13", "A4", "A4", "", "B3", "")
two("SGN", "staple", "B", "g14", "g15", "GND", "GND", "", "B3", "")
W("B_icG", "B:j15", "B:R-15", "GND", "black", "B3")
two("Cdec", "cap", "B", "L+19", "L-19", "P12", "GND", "100n", "B3", "C-021")


def sink(ch, step, fet, gate_r, pd, s1, s2, staple, fb, cfb, off, ref, inv_note=""):
    """One current sink. Every argument is a hole or a (hole, hole) pair."""
    n = lambda s: f"{s}_{ch}"
    two(f"S{ch}", "staple", "B", *staple, n("SRC"), n("SRC"), "", step + "a", "")
    P(f"Q{ch}", "to220", "B", {"G": fet[0], "D": fet[1], "S": fet[2]},
      {"G": n("GATE"), "D": n("DRAIN"), "S": n("SRC")}, "IRLB8721", step + "a", "Q-004")
    two(f"Rg{ch}", "res", "B", *gate_r, n("OUT"), n("GATE"), "100", step + "b", "R-005")
    two(f"Rp{ch}", "res", "B", *pd, n("GATE"), "GND", "100k", step + "b", "R-014")
    two(f"Rs1{ch}", "res", "B", *s1, n("SRC"), "GND", "100", step + "c", "R-005")
    two(f"Rs2{ch}", "res", "B", *s2, n("SRC"), "GND", "100", step + "c", "R-005")
    two(f"Rf{ch}", "res", "B", *fb, n("SRC"), n("FB"), "1k", step + "d", "R-008")
    two(f"Cf{ch}", "cap", "B", *cfb, n("OUT"), n("FB"), "1n", step + "d", "C-011")
    two(f"Ro{ch}", "res", "B", *off, n("FB"), "P12", "1M", step + "e", "R-017")
    two(f"Rr{ch}", "res", "B", *ref, n("REF"), "GND", "100k", step + "e", "R-014")


sink("R", "B4", ("e7", "e8", "e9"), ("c12", "c7"), ("a7", "L-7"), ("a9", "L-9"), ("a10", "L-10"),
     ("d9", "d10"), ("b9", "b13"), ("d12", "d13"), ("a13", "L+13"), ("a14", "L-14"))
sink("G", "B5", ("d21", "d22", "d23"), ("c18", "c21"), ("a21", "L-21"), ("a23", "L-23"), ("a24", "L-24"),
     ("c23", "c24"), ("b23", "b17"), ("d18", "d17"), ("a17", "L+17"), ("a16", "L-16"))
sink("B", "B5", ("f21", "f22", "f23"), ("h18", "h21"), ("j21", "R-21"), ("j23", "R-23"), ("j24", "R-24"),
     ("h23", "h24"), ("i23", "i17"), ("g18", "g17"), ("j17", "R+17"), ("j16", "R-16"))

# --------------------------------------------------------------------------
# Hook-up: board to board, controller, power, loads
# --------------------------------------------------------------------------
W("X_24", "A:R+9", "B:j2", "P24", "red", "C1")
W("X_gnd", "A:R-29", "B:L-1", "GND", "black", "C1")
W("X_refR", "A:c18", "B:c14", "REF_R", "pink", "C1")
W("X_refG", "A:h20", "B:c16", "REF_G", "lime", "C1")
W("X_refB", "A:c26", "B:h16", "REF_B", "sky", "C1")

W("Q_A3", "ext:QT Py A3", "A:a2", "PWM_WW", "yellow", "C2")
W("Q_TX", "ext:QT Py TX", "A:j8", "PWM_CW", "white", "C2")
W("Q_A0", "ext:QT Py A0", "A:c16", "PWM_R", "pink", "C2")
W("Q_A1", "ext:QT Py A1", "A:h18", "PWM_G", "lime", "C2")
W("Q_A2", "ext:QT Py A2", "A:c24", "PWM_B", "sky", "C2")
W("Q_G", "ext:QT Py GND", "A:R-30", "GND", "black", "C2")

W("S_24", "ext:Supply +", "A:R+3", "P24", "red", "C3")
W("S_gW", "ext:Supply -", "A:a8", "GND", "black", "C3", thick=True)
W("S_gC", "ext:Supply -", "A:j14", "GND", "black", "C3", thick=True)
W("T_ww", "ext:Strip WW-", "A:b7", "DRAIN_WW", "amber", "C4", thick=True)
W("T_cw", "ext:Strip CW-", "A:h13", "DRAIN_CW", "ice", "C4", thick=True)

W("L_aR", "ext:Red string +", "A:R+25", "P24", "red", "C5")
W("L_aG", "ext:Green string +", "A:R+26", "P24", "red", "C5")
W("L_aB", "ext:Blue string +", "A:R+27", "P24", "red", "C5")
W("L_kR", "ext:Red string -", "B:a8", "DRAIN_R", "pink", "C5")
W("L_kG", "ext:Green string -", "B:a22", "DRAIN_G", "lime", "C5")
W("L_kB", "ext:Blue string -", "B:j22", "DRAIN_B", "sky", "C5")


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------
def covered_holes(p):
    """Holes a flat part's body lies over (they must stay empty)."""
    out = []
    if p.kind in ("res", "diode"):
        (c1, r1), (c2, r2) = (parse(h) for h in p.pins.values())
        if c1 == c2 and c1 not in RAILS:               # along a column
            out += [f"{c1}{r}" for r in range(min(r1, r2) + 1, max(r1, r2))]
        elif r1 == r2:                                  # out to a rail: crosses the nearer rail
            rail = c1 if c1 in RAILS else c2
            if rail == "L+":
                out.append(f"L-{r1}")
            if rail == "R-":
                out.append(f"R+{r1}")
    if p.kind == "to220":
        # Tab side (right of the pins, since every label faces left) stays clear.
        col = parse(next(iter(p.pins.values())))[0]
        rows = [parse(h)[1] for h in p.pins.values()]
        nxt = {"a": "b", "b": "c", "c": "d", "d": "e", "f": "g", "g": "h", "h": "i", "i": "j"}.get(col)
        if nxt:
            out += [f"{nxt}{r}" for r in range(min(rows) - 1, max(rows) + 2)]
    if p.kind == "pot":
        col = parse(p.pins["1"])[0]
        rows = [parse(h)[1] for h in p.pins.values()]
        side = "L" if col in LEFT else "R"
        for r in range(min(rows) - 1, max(rows) + 2):   # body hangs over the rails
            out += [f"{side}+{r}", f"{side}-{r}"]
        out += [f"{col}{min(rows) + 1}", f"{col}{max(rows) - 1}"]
    if p.kind == "ecap":
        col, row = parse(p.pins["+"])
        side = col[0]
        for r in (row - 1, row + 1):
            out += [f"{side}+{r}", f"{side}-{r}"]
    return out


def verify():
    errors = []
    used = {}

    def claim(board, hole, who):
        col, row = parse(hole)
        if not 1 <= row <= ROWS:
            errors.append(f"{who}: {hole} is off the board")
        key = (board, hole)
        if key in used:
            errors.append(f"hole {board}:{hole} used by both {used[key]} and {who}")
        used[key] = who

    for p in parts:
        for pin, hole in p.pins.items():
            claim(p.board, hole, f"{p.id}.{pin}")
    for w in wires:
        for end in (w.a, w.b):
            if end[0] != "ext":
                claim(end[0], end[1], w.id)
    for p in parts:
        for h in covered_holes(p):
            if (p.board, h) in used:
                errors.append(f"{p.id} body lies over {p.board}:{h}, used by {used[(p.board, h)]}")

    # Geometry of fixed-pitch parts.
    for p in parts:
        cr = {k: parse(h) for k, h in p.pins.items()}
        if p.kind == "to220":
            cols = {c for c, _ in cr.values()}
            rows = [r for _, r in cr.values()]
            if len(cols) != 1 or rows != list(range(rows[0], rows[0] + 3)):
                errors.append(f"{p.id}: TO-220 legs must sit in three consecutive rows of one column")
        if p.kind == "pot":
            rows = [cr["1"][1], cr["W"][1], cr["3"][1]]
            if len({c for c, _ in cr.values()}) != 1 or rows[1] - rows[0] != 2 or rows[2] - rows[1] != 2:
                errors.append(f"{p.id}: pot legs must be two rows apart in one column")
        if p.kind == "res":
            (c1, r1), (c2, r2) = cr["1"], cr["2"]
            if c1 == c2 and abs(r1 - r2) < 3:
                errors.append(f"{p.id}: resistor span under 0.3 in")

    # Union-find over strips, rails and wires.
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    ext_nodes = {}
    def wnode(end):
        if end[0] == "ext":
            return ("ext", end[1])
        return node(end[0], end[1])

    for w in wires:
        union(wnode(w.a), wnode(w.b))
    for p in parts:
        if p.kind == "staple":
            hs = list(p.pins.values())
            union(node(p.board, hs[0]), node(p.board, hs[1]))

    comp_nets, net_comps = {}, {}

    def see(n, net, who):
        c = find(n)
        comp_nets.setdefault(c, {}).setdefault(net, []).append(who)
        net_comps.setdefault(net, {}).setdefault(c, []).append(who)

    for p in parts:
        for pin, hole in p.pins.items():
            see(node(p.board, hole), p.nets[pin], f"{p.id}.{pin}")
    for w in wires:
        for end in (w.a, w.b):
            see(wnode(end), w.net, w.id)

    for c, nets in comp_nets.items():
        if len(nets) > 1:
            errors.append("SHORT: " + " | ".join(f"{n}: {', '.join(v[:4])}" for n, v in nets.items()))
    for net, comps in net_comps.items():
        if len(comps) > 1:
            errors.append(f"OPEN: net {net} is split into {len(comps)} pieces: "
                          + " | ".join(", ".join(v[:5]) for v in comps.values()))
    return errors, net_comps


def bom():
    out = {}
    for p in parts:
        key = (p.kind, p.value, p.inv)
        out[key] = out.get(key, 0) + 1
    return out


if __name__ == "__main__":
    errs, nets = verify()
    for e in errs:
        print("ERROR", e)
    print(f"{len(parts)} parts, {len(wires)} wires, {len(nets)} nets, {len(errs)} errors")
    for (kind, value, inv), n in sorted(bom().items()):
        print(f"  {n:2d} x {kind:7s} {value:9s} {inv}")
    raise SystemExit(1 if errs else 0)
