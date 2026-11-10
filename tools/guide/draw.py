"""SVG drawing of breadboards and parts for the build booklet.

Plan view, one unit = one breadboard pitch (0.1 in). Colours inside the
drawings are the colours of the physical objects, on a board that is drawn
light in both page themes; anything drawn off the board uses page tokens.
"""
import math

from layout import LEFT, RAILS, ROWS, parse

P = 16.0  # px per pitch
COLX = {"L+": 0, "L-": 1, "a": 4, "b": 5, "c": 6, "d": 7, "e": 8,
        "f": 11, "g": 12, "h": 13, "i": 14, "j": 15, "R+": 18, "R-": 19}
PAD = 1.2            # board edge to first rail column, in units
BOARD_W = 19 + 2 * PAD
BOARD_TOP = -0.45    # top edge of the board body, in rows (row 1 sits at y = 1)

WIRE = {"red": "#E0312B", "black": "#23272D", "orange": "#F08A1C", "yellow": "#F2C811",
        "white": "#F5F5F1", "pink": "#EC4F8B", "lime": "#6FBF3A", "sky": "#2F9DF2",
        "amber": "#F7B23B", "ice": "#B9E1F8", "bare": "#B9C0C7", "violet": "#8E5BD6"}
DIGIT = {"0": "#1D1D1B", "1": "#7A4A21", "2": "#D12A1F", "3": "#F08A1C", "4": "#F4D31E",
         "5": "#2E9E48", "6": "#2764D9", "7": "#8E44AD", "8": "#8C9196", "9": "#FFFFFF"}
BANDS = {  # five-band, 1 % metal film
    "100": "10001", "220": "22001", "1k": "10011", "10k": "10021", "100k": "10031", "1M": "10041",
}
NICE = {"100": "100 Ω", "220": "220 Ω", "1k": "1 kΩ", "10k": "10 kΩ", "100k": "100 kΩ", "1M": "1 MΩ",
        "1n": "1 nF", "100n": "100 nF", "330n": "330 nF", "10u": "10 µF", "100u": "100 µF"}


def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def hx(col):
    return (COLX[col] + PAD) * P


def hy(row):
    return row * P


def pt(hole):
    c, r = parse(hole)
    return hx(c), hy(r)


def board_symbol(sid, plus_label, title):
    """Empty breadboard, drawn once and reused with <use>."""
    w = BOARD_W * P
    top, bot = BOARD_TOP * P, (ROWS + 1 - BOARD_TOP) * P
    o = [f'<g id="{sid}">']
    o.append(f'<rect x="0" y="{f(top)}" width="{f(w)}" height="{f(bot - top)}" rx="9" fill="#F4F0E6" stroke="#CFC8B6" stroke-width="1.5"/>')
    # trench
    tx = (hx("e") + hx("f")) / 2
    o.append(f'<rect x="{f(tx - 0.62 * P)}" y="{f(0.5 * P)}" width="{f(1.24 * P)}" height="{f(ROWS * P)}" rx="4" fill="#E2DCCB"/>')
    # rail stripes
    for side in ("L", "R"):
        xp, xm = hx(side + "+"), hx(side + "-")
        o.append(f'<line x1="{f(xp - 0.5 * P)}" y1="{f(0.55 * P)}" x2="{f(xp - 0.5 * P)}" y2="{f((ROWS + 0.45) * P)}" stroke="#D9342B" stroke-width="1.6"/>')
        o.append(f'<line x1="{f(xm + 0.5 * P)}" y1="{f(0.55 * P)}" x2="{f(xm + 0.5 * P)}" y2="{f((ROWS + 0.45) * P)}" stroke="#2B62D9" stroke-width="1.6"/>')
    holes = []
    for col in COLX:
        for r in range(1, ROWS + 1):
            holes.append(f'M{f(hx(col) - 2.6)},{f(hy(r) - 2.6)}h5.2v5.2h-5.2z')
    o.append(f'<path d="{"".join(holes)}" fill="#3A3A36"/>')
    # row numbers: both gutters and the trench
    for r in range(1, ROWS + 1):
        for x in ((hx("L-") + hx("a")) / 2, tx, (hx("j") + hx("R+")) / 2):
            o.append(f'<text x="{f(x)}" y="{f(hy(r) + 2.8)}" text-anchor="middle" class="bn">{r}</text>')
    o.append("</g>")
    return "".join(o)


def ruler(r0, r1):
    """Column letters at the top and bottom of a view; a strip hides what a crop cuts through."""
    o = []
    for edge, row in (("top", r0), ("bot", r1)):
        whole = (row == 1) if edge == "top" else (row == ROWS)
        if edge == "top":
            y0, base = (row - 1.55) * P, ((0.12 if whole else row - 0.88) * P) + 3
        else:
            y0, base = (row + 0.55) * P, ((ROWS + 0.9 if whole else row + 1.22) * P) + 3
        if not whole:
            o.append(f'<rect x="0" y="{f(y0)}" width="{f(BOARD_W * P)}" height="{f(P)}" fill="#F4F0E6"/>')
            edge_y = y0 + P if edge == "top" else y0
            o.append(f'<line x1="0" y1="{f(edge_y)}" x2="{f(BOARD_W * P)}" y2="{f(edge_y)}" stroke="#CFC8B6" stroke-width="1" stroke-dasharray="4 3"/>')
        o.append(letters(base))
    return "".join(o)


def view_rows(r0, r1):
    """Top and bottom of a cropped view in px."""
    y0 = (BOARD_TOP - 0.2) * P if r0 == 1 else (r0 - 1.55) * P
    y1 = (ROWS + 1 - BOARD_TOP + 0.2) * P if r1 == ROWS else (r1 + 1.55) * P
    return y0, y1


def letters(y):
    o = []
    for col in "abcdefghij":
        o.append(f'<text x="{f(hx(col))}" y="{f(y)}" text-anchor="middle" class="bl">{col}</text>')
    for rail in RAILS:
        sign = "+" if rail[1] == "+" else "−"
        cls = "bp" if rail[1] == "+" else "bm"
        o.append(f'<text x="{f(hx(rail))}" y="{f(y)}" text-anchor="middle" class="{cls}">{sign}</text>')
    return "".join(o)


# --------------------------------------------------------------------------
# Parts
# --------------------------------------------------------------------------
def _along(p1, p2):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    d = math.hypot(dx, dy) or 1
    return d, math.degrees(math.atan2(dy, dx))


def lead(p1, p2, color="#A9B0B7", w=2.2):
    return f'<line x1="{f(p1[0])}" y1="{f(p1[1])}" x2="{f(p2[0])}" y2="{f(p2[1])}" stroke="{color}" stroke-width="{w}" stroke-linecap="round"/>'


def resistor(p1, p2, value):
    d, ang = _along(p1, p2)
    L = min(2.45 * P, d - 0.55 * P)
    T = 0.74 * P
    cx, cy = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    o = [lead(p1, p2)]
    o.append(f'<g transform="translate({f(cx)},{f(cy)}) rotate({f(ang)})">')
    o.append(f'<rect x="{f(-L / 2)}" y="{f(-T / 2)}" width="{f(L)}" height="{f(T)}" rx="{f(T * 0.42)}" fill="#8CCBEA" stroke="#3C7FA8" stroke-width="1"/>')
    code = BANDS[value]
    pos = [0.16, 0.30, 0.44, 0.58, 0.84]
    for k, ch in enumerate(code):
        col = DIGIT[ch] if k < 3 else ({"0": DIGIT["0"], "1": DIGIT["1"], "2": DIGIT["2"], "3": DIGIT["3"], "4": DIGIT["4"]}[ch] if k == 3 else DIGIT["1"])
        o.append(f'<rect x="{f(-L / 2 + pos[k] * L - 1.5)}" y="{f(-T / 2 + 0.6)}" width="3" height="{f(T - 1.2)}" fill="{col}"/>')
    o.append("</g>")
    return "".join(o)


def ceramic(p1, p2, value):
    d, ang = _along(p1, p2)
    cx, cy = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    rx = max(0.62 * P, min(0.8 * P, d * 0.42))
    return (lead(p1, p2)
            + f'<g transform="translate({f(cx)},{f(cy)}) rotate({f(ang)})">'
            + f'<ellipse rx="{f(rx)}" ry="{f(0.5 * P)}" fill="#EDB63C" stroke="#A47A16" stroke-width="1"/></g>')


def diode(pa, pk):
    d, ang = _along(pa, pk)
    L, T = min(2.0 * P, d - 0.6 * P), 0.8 * P
    cx, cy = (pa[0] + pk[0]) / 2, (pa[1] + pk[1]) / 2
    return (lead(pa, pk, "#B7BDC3", 2.8)
            + f'<g transform="translate({f(cx)},{f(cy)}) rotate({f(ang)})">'
            + f'<rect x="{f(-L / 2)}" y="{f(-T / 2)}" width="{f(L)}" height="{f(T)}" rx="2.5" fill="#26282B"/>'
            + f'<rect x="{f(L / 2 - 0.42 * P)}" y="{f(-T / 2)}" width="{f(0.26 * P)}" height="{f(T)}" fill="#D7DBDF"/></g>')


def ecap(pp, pm, value):
    cx, cy = (pp[0] + pm[0]) / 2, (pp[1] + pm[1]) / 2
    r = (1.55 if value == "100u" else 1.1) * P
    ang = math.atan2(pm[1] - pp[1], pm[0] - pp[0])
    a0, a1 = ang - 0.95, ang + 0.95
    x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    mx, my = cx + (r - 0.42 * P) * math.cos(ang), cy + (r - 0.42 * P) * math.sin(ang)
    return (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="#22315C" stroke="#141D38" stroke-width="1"/>'
            + f'<path d="M{f(cx)},{f(cy)}L{f(x0)},{f(y0)}A{f(r)},{f(r)} 0 0 1 {f(x1)},{f(y1)}z" fill="#DDE3EA"/>'
            + f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r * 0.56)}" fill="#C5CBD2" stroke="#8C949D" stroke-width="0.8"/>'
            + f'<text x="{f(mx)}" y="{f(my + 4)}" text-anchor="middle" class="pm">−</text>')


def to220(pins, names):
    """Label faces left; metal tab on the right. pins top to bottom."""
    (x, y0), (_, y2) = pins[0], pins[2]
    cy = (y0 + y2) / 2
    top, bot = cy - 2.0 * P, cy + 2.0 * P
    o = [f'<rect x="{f(x + 0.5 * P)}" y="{f(top)}" width="{f(0.52 * P)}" height="{f(bot - top)}" rx="1.5" fill="#C3C9CF" stroke="#7F8891" stroke-width="1"/>']
    o.append(f'<rect x="{f(x - 0.86 * P)}" y="{f(top + 0.05 * P)}" width="{f(1.4 * P)}" height="{f(bot - top - 0.1 * P)}" rx="2.5" fill="#2A2D31" stroke="#0F1113" stroke-width="1"/>')
    for (px, py), name in zip(pins, names):
        o.append(f'<text x="{f(px - 0.16 * P)}" y="{f(py + 3)}" text-anchor="middle" class="pl">{name}</text>')
    return "".join(o)


def dip14(pins):
    xe, xf = hx("e"), hx("f")
    ys = sorted({p[1] for p in pins})
    top, bot = ys[0] - 0.62 * P, ys[-1] + 0.62 * P
    o = []
    for y in ys:
        o.append(f'<rect x="{f(xe - 2.2)}" y="{f(y - 2.6)}" width="{f(0.5 * P)}" height="5.2" fill="#C3C9CF"/>')
        o.append(f'<rect x="{f(xf - 0.5 * P + 2.2)}" y="{f(y - 2.6)}" width="{f(0.5 * P)}" height="5.2" fill="#C3C9CF"/>')
    bx0, bx1 = xe + 0.3 * P, xf - 0.3 * P
    o.append(f'<rect x="{f(bx0)}" y="{f(top)}" width="{f(bx1 - bx0)}" height="{f(bot - top)}" rx="2.5" fill="#2A2D31" stroke="#0F1113" stroke-width="1"/>')
    mx = (bx0 + bx1) / 2
    o.append(f'<path d="M{f(mx - 6)},{f(top)}a6,6 0 0 0 12,0z" fill="#73797F"/>')
    o.append(f'<circle cx="{f(bx0 + 6)}" cy="{f(top + 9)}" r="2.6" fill="#E9ECEF"/>')
    o.append(f'<text transform="translate({f(mx + 3.5)},{f((top + bot) / 2)}) rotate(90)" text-anchor="middle" class="ic">LM324</text>')
    return "".join(o)


def pot(pins, left):
    (x, y0), (_, y2) = pins[0], pins[2]
    cy = (y0 + y2) / 2
    top, bot = cy - 3.2 * P, cy + 3.2 * P
    if left:
        bx0, bx1 = x - 3.75 * P, x + 0.55 * P
        sx0, sx1 = bx0 - 1.55 * P, bx0
    else:
        bx0, bx1 = x - 0.55 * P, x + 3.75 * P
        sx0, sx1 = bx1, bx1 + 1.55 * P
    o = [f'<rect x="{f(sx0)}" y="{f(cy - 0.62 * P)}" width="{f(sx1 - sx0)}" height="{f(1.24 * P)}" rx="2" fill="#D9DDE2" stroke="#8A929B" stroke-width="1"/>']
    o.append(f'<rect x="{f(bx0)}" y="{f(top)}" width="{f(bx1 - bx0)}" height="{f(bot - top)}" rx="7" fill="#AEB6BF" stroke="#6E7781" stroke-width="1"/>')
    back = x - 0.2 * P if left else x - 0.5 * P
    o.append(f'<rect x="{f(back)}" y="{f(top + 0.25 * P)}" width="{f(0.7 * P)}" height="{f(bot - top - 0.5 * P)}" rx="2" fill="#3F6E3A"/>')
    for (px, py), name in zip(pins, ("1", "W", "3")):
        o.append(f'<circle cx="{f(px)}" cy="{f(py)}" r="3.2" fill="#E9ECEF" stroke="#59626B" stroke-width="0.8"/>')
    lx = (bx0 + back) / 2 if left else (back + 0.7 * P + bx1) / 2
    o.append(f'<text x="{f(lx)}" y="{f(cy + 4)}" text-anchor="middle" class="pk">10k</text>')
    return "".join(o)


def staple(p1, p2):
    return (lead(p1, p2, "#8E979F", 3) + f'<circle cx="{f(p1[0])}" cy="{f(p1[1])}" r="2.6" fill="#8E979F"/>'
            + f'<circle cx="{f(p2[0])}" cy="{f(p2[1])}" r="2.6" fill="#8E979F"/>')


def wire_path(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    if abs(x1 - x2) < 1 or abs(y1 - y2) < 1:
        return f"M{f(x1)},{f(y1)}L{f(x2)},{f(y2)}"
    return f"M{f(x1)},{f(y1)}C{f((x1 + x2) / 2)},{f(y1)} {f((x1 + x2) / 2)},{f(y2)} {f(x2)},{f(y2)}"


def wire(d, color, thick=False):
    w = 5.4 if thick else 3.3
    c = WIRE[color]
    return (f'<path d="{d}" fill="none" stroke="#14181D" stroke-opacity=".55" stroke-width="{w + 1.7}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')


def part_svg(p):
    k = p.kind
    if k == "res":
        return resistor(pt(p.pins["1"]), pt(p.pins["2"]), p.value)
    if k == "cap":
        return ceramic(pt(p.pins["1"]), pt(p.pins["2"]), p.value)
    if k == "diode":
        return diode(pt(p.pins["A"]), pt(p.pins["K"]))
    if k == "ecap":
        return ecap(pt(p.pins["+"]), pt(p.pins["-"]), p.value)
    if k == "to220":
        names = list(p.pins)
        short = {"IN": "I", "GND": "G", "OUT": "O"}
        return to220([pt(h) for h in p.pins.values()], [short.get(n, n) for n in names])
    if k == "dip14":
        return dip14([pt(h) for h in p.pins.values()])
    if k == "pot":
        return pot([pt(p.pins[n]) for n in ("1", "W", "3")], parse(p.pins["1"])[0] in LEFT)
    if k == "staple":
        return staple(pt(p.pins["1"]), pt(p.pins["2"]))
    raise ValueError(k)


def halo(p):
    """Outline drawn under a newly added part."""
    k = p.kind
    hs = [pt(h) for h in p.pins.values()]
    if k in ("res", "cap", "diode", "staple"):
        (x1, y1), (x2, y2) = hs[0], hs[1]
        return f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" class="hl" stroke-width="{f(1.25 * P)}"/>'
    if k == "ecap":
        cx, cy = (hs[0][0] + hs[1][0]) / 2, (hs[0][1] + hs[1][1]) / 2
        r = (1.55 if p.value == "100u" else 1.1) * P + 4
        return f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" class="hf"/>'
    if k == "to220":
        x, cy = hs[0][0], (hs[0][1] + hs[2][1]) / 2
        return f'<rect x="{f(x - 0.86 * P - 4)}" y="{f(cy - 2 * P - 4)}" width="{f(1.9 * P + 8)}" height="{f(4 * P + 8)}" rx="6" class="hf"/>'
    if k == "dip14":
        ys = sorted({h[1] for h in hs})
        return f'<rect x="{f(hx("e") - 6)}" y="{f(ys[0] - 0.62 * P - 4)}" width="{f(hx("f") - hx("e") + 12)}" height="{f(ys[-1] - ys[0] + 1.24 * P + 8)}" rx="6" class="hf"/>'
    if k == "pot":
        x, cy = hs[0][0], (hs[0][1] + hs[2][1]) / 2
        left = parse(p.pins["1"])[0] in LEFT
        bx0 = x - 3.75 * P if left else x - 0.55 * P
        return f'<rect x="{f(bx0 - 4)}" y="{f(cy - 3.2 * P - 4)}" width="{f(4.3 * P + 8)}" height="{f(6.4 * P + 8)}" rx="10" class="hf"/>'
    return ""


def wire_halo(d, thick=False):
    return f'<path d="{d}" fill="none" class="hl" stroke-width="{f((0.95 if thick else 0.8) * P)}"/>'


def tag(x, y, text, anchor="middle"):
    w = 7.0 * len(text) + 10
    x0 = x - w / 2 if anchor == "middle" else (x if anchor == "start" else x - w)
    return (f'<rect x="{f(x0)}" y="{f(y - 9)}" width="{f(w)}" height="17" rx="8.5" class="tg"/>'
            f'<text x="{f(x0 + w / 2)}" y="{f(y + 3.6)}" text-anchor="middle" class="tt">{text}</text>')


def badge(x, y, letter):
    return (f'<circle cx="{f(x)}" cy="{f(y)}" r="7.4" class="bd"/>'
            f'<text x="{f(x)}" y="{f(y + 3.4)}" text-anchor="middle" class="bt">{letter}</text>')
