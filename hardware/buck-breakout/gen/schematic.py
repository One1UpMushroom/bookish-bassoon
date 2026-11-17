#!/usr/bin/env python3
"""Draw the breakout's schematic as img/schematic.svg (+ .png via rsvg-convert).

Pure Python.  The netlist drawn here is the one in build_pcb.py (PARTS).
"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "img", "schematic.svg")

BG, WIRE, PART, REF, VAL, NET, DIM = (
    "#0b0f14", "#00e5ff", "#e6edf3", "#ff4fd8", "#9fb3c8", "#ffd400", "#5d7186")
W, H = 1240, 560
o = []


def wire(*pts):
    d = " ".join(f"{x},{y}" for x, y in pts)
    o.append(f'<polyline points="{d}" fill="none" stroke="{WIRE}" stroke-width="2"/>')


def dot(x, y):
    o.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{WIRE}"/>')


def text(x, y, s, fill=VAL, size=13, anchor="start", weight="normal"):
    o.append(f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
             f'text-anchor="{anchor}" font-weight="{weight}">{s}</text>')


def label(x, y, ref, val, anchor="start"):
    text(x, y, ref, REF, 14, anchor, "bold")
    for i, line in enumerate(val.split("|")):
        text(x, y + 16 + 15 * i, line, VAL, 12, anchor)


def gnd(x, y):
    wire((x, y), (x, y + 10))
    for i, hw in enumerate((12, 8, 4)):
        yy = y + 10 + i * 5
        o.append(f'<line x1="{x - hw}" y1="{yy}" x2="{x + hw}" y2="{yy}" '
                 f'stroke="{DIM}" stroke-width="2"/>')


def res_v(x, y1, y2):
    """Vertical resistor between y1 and y2 (zig-zag body 40 px long)."""
    m = (y1 + y2) / 2
    wire((x, y1), (x, m - 20))
    wire((x, m + 20), (x, y2))
    pts = [(x, m - 20)]
    for i in range(6):
        pts.append((x + (7 if i % 2 == 0 else -7), m - 20 + 40 * (i + 0.5) / 6))
    pts.append((x, m + 20))
    d = " ".join(f"{a},{b:.1f}" for a, b in pts)
    o.append(f'<polyline points="{d}" fill="none" stroke="{PART}" stroke-width="2"/>')


def cap_v(x, y1, y2, polar=False):
    m = (y1 + y2) / 2
    wire((x, y1), (x, m - 4))
    wire((x, m + 4), (x, y2))
    for yy in (m - 4, m + 4):
        o.append(f'<line x1="{x - 12}" y1="{yy}" x2="{x + 12}" y2="{yy}" '
                 f'stroke="{PART}" stroke-width="2.5"/>')
    if polar:
        text(x + 7, m - 9, "+", PART, 13)


def cap_h(x1, x2, y):
    m = (x1 + x2) / 2
    wire((x1, y), (m - 4, y))
    wire((m + 4, y), (x2, y))
    for xx in (m - 4, m + 4):
        o.append(f'<line x1="{xx}" y1="{y - 12}" x2="{xx}" y2="{y + 12}" '
                 f'stroke="{PART}" stroke-width="2.5"/>')


def tvs_v(x, y1, y2):
    """Unidirectional TVS, cathode up (to VIN)."""
    m = (y1 + y2) / 2
    wire((x, y1), (x, m - 8))
    wire((x, m + 8), (x, y2))
    o.append(f'<polygon points="{x - 10},{m + 8} {x + 10},{m + 8} {x},{m - 8}" '
             f'fill="none" stroke="{PART}" stroke-width="2"/>')
    o.append(f'<polyline points="{x - 14},{m - 4} {x - 10},{m - 8} {x + 10},{m - 8} '
             f'{x + 14},{m - 12}" fill="none" stroke="{PART}" stroke-width="2"/>')


def ind_h(x1, x2, y):
    n = 4
    r = (x2 - x1 - 20) / (2 * n)
    wire((x1, y), (x1 + 10, y))
    wire((x2 - 10, y), (x2, y))
    d = f"M {x1 + 10},{y}"
    for i in range(n):
        d += f" a {r},{r} 0 0 1 {2 * r},0"
    o.append(f'<path d="{d}" fill="none" stroke="{PART}" stroke-width="2"/>')


def term(x, y, name, side):
    o.append(f'<rect x="{x - 7}" y="{y - 7}" width="14" height="14" fill="{BG}" '
             f'stroke="{NET}" stroke-width="2"/>')
    if side == "l":
        text(x - 14, y + 5, name, NET, 14, "end", "bold")
    else:
        text(x + 14, y + 5, name, NET, 14, "start", "bold")


def pin(x, y, name, num, side):
    if side == "l":
        text(x + 8, y + 5, name, PART, 13)
        text(x - 6, y - 5, num, DIM, 11, "end")
    elif side == "r":
        text(x - 8, y + 5, name, PART, 13, "end")
        text(x + 6, y - 5, num, DIM, 11)
    else:
        text(x, y - 8, name, PART, 13, "middle")
        text(x + 6, y + 14, num, DIM, 11)


def build():
    o.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    o.append(f'<rect x="6" y="6" width="{W - 12}" height="{H - 12}" fill="none" '
             f'stroke="{DIM}" stroke-width="1"/>')
    text(24, 34, "BUCK//33630", PART, 20, weight="bold")
    text(196, 34, "LMR33630ADDAR  3.8-36 V in  /  1-24 V out  /  3 A  /  400 kHz "
         "synchronous", VAL, 13)

    VY, EY = 110, 300            # VIN rail, EN line
    U = dict(x1=540, x2=730, y1=78, y2=340)

    # ---- input side ----
    term(60, VY, "VIN", "l")
    wire((67, VY), (U["x1"], VY))
    term(60, EY, "EN", "l")
    term(60, 420, "GND", "l")
    wire((67, 420), (100, 420))
    gnd(100, 420)

    # EN pull-up and optional UVLO divider
    res_v(140, VY, EY)
    dot(140, VY)
    label(152, 198, "R4", "100k")
    wire((67, EY), (520, EY), (520, 190), (U["x1"], 190))
    dot(140, EY)
    res_v(140, EY, 400)
    gnd(140, 400)
    label(152, 345, "R5", "UVLO|(optional)")

    for x, kind, ref, val in ((215, "tvs", "D1", "SMBJ24A|(optional)"),
                              (290, "cp", "C10", "47-100u|50V"),
                              (360, "c", "C1", "10u 50V|X7R 1210"),
                              (430, "c", "C2", "10u 50V|X7R 1210"),
                              (495, "c", "C3", "220n|50V")):
        dot(x, VY)
        if kind == "tvs":
            tvs_v(x, VY, 215)
        else:
            cap_v(x, VY, 215, kind == "cp")
        gnd(x, 215)
        label(x - 8, 262, ref, val, "middle")

    # ---- U1 ----
    o.append(f'<rect x="{U["x1"]}" y="{U["y1"]}" width="{U["x2"] - U["x1"]}" '
             f'height="{U["y2"] - U["y1"]}" rx="4" fill="#111a24" stroke="{REF}" '
             f'stroke-width="2"/>')
    text(635, 215, "U1", REF, 16, "middle", "bold")
    text(635, 233, "LMR33630ADDAR", VAL, 12, "middle")
    text(635, 249, "HSOIC-8", DIM, 11, "middle")
    pin(U["x1"], VY, "VIN", "2", "l")
    pin(U["x1"], 190, "EN", "3", "l")
    pin(U["x2"], VY, "BOOT", "7", "r")
    pin(U["x2"], 160, "SW", "8", "r")
    pin(U["x2"], 250, "FB", "5", "r")
    pin(U["x2"], 310, "PG", "4", "r")
    pin(580, U["y2"], "VCC", "6", "b")
    pin(640, U["y2"], "PGND", "1", "b")
    pin(695, U["y2"], "AGND", "pad", "b")

    # VCC capacitor, grounds
    cap_v(580, U["y2"], 430)
    gnd(580, 430)
    label(566, 392, "C5", "1u", "end")
    wire((640, U["y2"]), (640, 372), (695, 372), (695, U["y2"]))
    dot(668, 372)
    gnd(668, 372)

    # ---- switch node, bootstrap, inductor ----
    wire((U["x2"], 160), (830, 160))
    wire((U["x2"], VY), (760, VY))
    cap_h(760, 800, VY)
    wire((800, VY), (810, VY), (810, 160))
    dot(810, 160)
    label(780, 70, "C4", "100n", "middle")
    ind_h(830, 930, 160)
    label(880, 128, "L1", "", "middle")
    text(880, 190, "10 / 15 / 22 uH", VAL, 12, "middle")
    text(880, 205, "(see table)", VAL, 12, "middle")

    # ---- output ----
    OY = 160
    wire((930, OY), (1170, OY))
    term(1177, OY, "VOUT", "r")
    # feedback divider
    dot(975, OY)
    res_v(975, OY, 250)
    dot(975, 250)
    wire((U["x2"], 250), (975, 250))
    res_v(975, 250, 330)
    res_v(975, 330, 410)
    gnd(975, 410)
    label(988, 210, "R1", "RFBT")
    label(988, 290, "R2", "RFBB")
    label(988, 370, "R3", "RFBB")
    text(852, 244, "FB = 1.0 V", NET, 12, "middle")
    # output capacitors
    dot(1090, OY)
    cap_v(1090, OY, 260)
    gnd(1090, 260)
    label(1106, 212, "C6-C9", "4x 22u 25V|X7R 1210")
    # power good and ground terminals
    wire((U["x2"], 310), (770, 310), (770, 480), (1170, 480))
    term(1177, 480, "PG", "r")
    term(1177, 420, "GND", "r")
    wire((1170, 420), (1140, 420))
    gnd(1140, 420)

    # ---- notes ----
    text(24, 478, "VOUT = 1.0 V x (1 + R1 / (R2 + R3))", PART, 13)
    text(24, 498, "EN: leave open = on (R4).  Pull to GND = off.  "
         "R5 sets a turn-on voltage: VON = 1.231 V x (1 + R4 / R5).", VAL, 12)
    text(24, 516, "PG: open-drain, low = fault.  Pull up to 18 V max "
         "(or use an MCU pin's internal pull-up).", VAL, 12)
    text(24, 534, "Keep VIN above VOUT; 24 V out needs 28-36 V in "
         "(C6-C9 then 4x 10u 50V).", VAL, 12)

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}" font-family="DejaVu Sans Mono, Menlo, '
           f'Consolas, monospace">\n' + "\n".join(o) + "\n</svg>\n")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(svg)
    subprocess.run(["rsvg-convert", "-z", "1.6", OUT, "-o",
                    OUT.replace(".svg", ".png")], check=True)


if __name__ == "__main__":
    build()
    print("wrote", os.path.relpath(OUT))
