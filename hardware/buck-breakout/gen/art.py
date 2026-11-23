"""Silkscreen for the buck breakout: assembly labels, the output-voltage
value table, and the cyberpunk trim.  Called from build_pcb.py.

Top side: reference designators, pin names, a write-on box for the voltage
the board was built for.  Bottom side: the value table (the bottom is free of
parts, so there is room), pin names again, limits, and most of the artwork.

Bottom-side helpers take "view" coordinates: x measured from the left edge as
you look at the bottom of the board (view x = W - board x).
"""
import pcbnew
from pcbnew import FromMM, VECTOR2I

import values

FS, BS = pcbnew.F_SilkS, pcbnew.B_SilkS
JUST = {"l": pcbnew.GR_TEXT_H_ALIGN_LEFT, "c": pcbnew.GR_TEXT_H_ALIGN_CENTER,
        "r": pcbnew.GR_TEXT_H_ALIGN_RIGHT}


class Silk:
    def __init__(self, board, W, H, ox=0.0, oy=0.0):
        self.b, self.W, self.H, self.ox, self.oy = board, W, H, ox, oy

    # ---- primitives (board coordinates) ----
    def text(self, s, x, y, h=0.8, w=None, t=None, layer=FS, just="c", ang=0):
        w = w or h * 0.92
        tx = pcbnew.PCB_TEXT(self.b)
        tx.SetText(s)
        tx.SetLayer(layer)
        tx.SetTextSize(VECTOR2I(FromMM(w), FromMM(h)))
        tx.SetTextThickness(FromMM(t or max(0.11, h * 0.15)))
        tx.SetHorizJustify(JUST[just])
        tx.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        tx.SetMirrored(layer == BS)
        tx.SetTextAngleDegrees(ang)
        tx.SetPosition(VECTOR2I(FromMM(x + self.ox), FromMM(y + self.oy)))
        self.b.Add(tx)

    def line(self, pts, w=0.15, layer=FS):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            s = pcbnew.PCB_SHAPE(self.b)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(VECTOR2I(FromMM(x1 + self.ox), FromMM(y1 + self.oy)))
            s.SetEnd(VECTOR2I(FromMM(x2 + self.ox), FromMM(y2 + self.oy)))
            s.SetWidth(FromMM(w))
            s.SetLayer(layer)
            self.b.Add(s)

    def poly(self, pts, layer=FS):
        s = pcbnew.PCB_SHAPE(self.b)
        s.SetShape(pcbnew.SHAPE_T_POLY)
        s.SetPolyPoints([VECTOR2I(FromMM(x + self.ox), FromMM(y + self.oy))
                         for x, y in pts])
        s.SetFilled(True)
        s.SetWidth(0)
        s.SetLayer(layer)
        self.b.Add(s)

    def box(self, x1, y1, x2, y2, layer=FS):
        self.poly([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], layer)

    # ---- bottom side, view coordinates ----
    def bt(self, s, xv, y, h=0.8, w=None, t=None, just="l"):
        self.text(s, self.W - xv, y, h, w, t, BS, just)

    def bl(self, pts, w=0.15):
        self.line([(self.W - x, y) for x, y in pts], w, BS)

    def bp(self, pts):
        self.poly([(self.W - x, y) for x, y in pts], BS)

    def hazard(self, x1, y1, x2, y2, pitch=0.9, bottom=False):
        """Diagonal warning stripes filling the box x1..x2, y1..y2."""
        h = y2 - y1
        x = x1 - h
        while x < x2:
            pts = [(x, y2), (x + pitch / 2, y2), (x + pitch / 2 + h, y1),
                   (x + h, y1)]
            # clip to the box (simple horizontal clamp of the parallelogram)
            cl = []
            for px, py in pts:
                cl.append((min(max(px, x1), x2), py))
            if abs(cl[0][0] - cl[1][0]) > 0.05 or abs(cl[2][0] - cl[3][0]) > 0.05:
                (self.bp if bottom else self.poly)(cl)
            x += pitch


    def sunrise(self, cx, cy, r, half_len, bottom=False, rays=5, lw=0.15):
        """A half sun on a horizon line: the maker's mark.  (cx, cy) is the
        middle of the horizon; on the bottom side cx is a view coordinate."""
        import math
        ln = self.bl if bottom else self.line
        pl = self.bp if bottom else self.poly
        pl([(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
            for a in range(180, 361, 12)])
        for i in range(rays):
            a = math.radians(200 + i * 140 / (rays - 1))
            ln([(cx + 1.4 * r * math.cos(a), cy + 1.4 * r * math.sin(a)),
                (cx + 2.05 * r * math.cos(a), cy + 2.05 * r * math.sin(a))], lw)
        ln([(cx - half_len, cy), (cx + half_len, cy)], lw)

    def pixels(self, x0, y0, rows, px=0.2, layer=FS):
        """Pixel art: one filled rectangle per horizontal run of 'X'.  Runs
        overlap their neighbours by a hair so no seams show in the plot."""
        e = 0.01
        for r, row in enumerate(rows):
            c = 0
            while c < len(row):
                if row[c] != "X":
                    c += 1
                    continue
                c0 = c
                while c < len(row) and row[c] == "X":
                    c += 1
                self.box(x0 + c0 * px - e, y0 + r * px - e,
                         x0 + c * px + e, y0 + (r + 1) * px + e, layer)

    def sprig(self, x, y, size=1.0, bottom=False, lw=0.15):
        """Two leaves on a short stem growing up from (x, y)."""
        import math
        ln = self.bl if bottom else self.line
        pl = self.bp if bottom else self.poly
        top = y - 0.45 * size
        ln([(x, y), (x, top)], lw)
        for ang in (-48, -132):
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            pts = []
            n = 8
            for sgn in (1, -1):
                rng = range(n + 1) if sgn == 1 else range(n - 1, 0, -1)
                for i in rng:
                    t = i / n
                    u, v = t * 1.15 * size, sgn * 0.27 * size * math.sin(math.pi * t)
                    pts.append((x + u * ca - v * sa, top + u * sa + v * ca))
            pl(pts)


def decorate(board, W, H, ox=0.0, oy=0.0):
    k = Silk(board, W, H, ox, oy)
    top(k)
    bottom(k)


# 11 x 13 pixel thumbs-up: thumb, three curled fingers, shirt cuff
THUMBS_UP = [
    ".....XX....",
    "....XXX....",
    "....XXX....",
    "....XXX....",
    "...XXXX....",
    "...XXXXXXX.",
    "XX.XXXXXXXX",
    "XX.XXXX....",
    "XX.XXXXXXXX",
    "XX.XXXXXXXX",
    "XX.XXXX....",
    "XX.XXXXXXX.",
    "XX..XXXXXX.",
]


# ------------------------------------------------------------------ top ---
def top(k):
    import math
    W, H = k.W, k.H
    R = dict(h=0.75, w=0.68, t=0.12)      # reference designators
    N = dict(h=0.72, w=0.6, t=0.12)       # pin names
    # reference designators (sit where the part will cover them, or beside it)
    refs = [("U1", 17.3, 3.95, 0), ("L1", 31.0, 11.43, 0),
            ("C1", 9.75, 5.2, 0), ("C2", 9.75, 10.0, 0), ("C3", 12.6, 2.75, 0),
            ("C4", 22.7, 1.45, 0), ("C5", 22.7, 17.3, 0),
            ("C6", 39.9, 9.88, 90), ("C7", 39.9, 12.98, 90),
            ("C8", 45.0, 9.88, 90), ("C9", 45.0, 12.98, 90),
            ("C10", 4.1, 10.4, 0), ("D1", 4.4, 14.6, 0),
            ("R1", 19.6, 16.11, 90), ("R2", 17.06, 16.11, 90),
            ("R3", 14.52, 16.11, 90), ("R4", 1.65, 17.75, 0),
            ("R5", 11.25, 16.55, 0)]
    for s, x, y, a in refs:
        k.text(s, x, y, ang=a, **R)
    k.text("+", 2.35, 6.3, 1.0, 1.0, 0.15)
    # electrolytic outline, open toward the board edge
    arc = [(4.1 + 4.0 * math.cos(math.radians(a)),
            8.0 + 4.0 * math.sin(math.radians(a))) for a in range(-150, 151, 10)]
    k.line(arc, 0.12)

    # pin names, inboard of each header pin
    for s, x in (("GND", 1.37), ("VIN", 3.81)):
        k.text(s, x, 3.25, **N)
    for s, x in (("GND", 1.37), ("VIN", 3.81), ("EN", 6.35)):
        k.text(s, x, 20.07, **N)
    for s, x in (("OUT", 44.45), ("GND", 46.89)):
        k.text(s, x, 3.25, **N)
    for s, x in (("PG", 41.91), ("OUT", 44.45), ("GND", 46.89)):
        k.text(s, x, 20.07, **N)

    # title block above the inductor
    k.text("BUCK//33630", 31.0, 1.5, 1.25, 1.05, 0.2)
    k.text("3.8-36V IN  //  3A SYNC", 31.0, 3.05, 0.7, 0.6, 0.11)
    k.poly([(24.6, 0.9), (25.2, 0.9), (24.7, 2.1), (24.1, 2.1)])
    k.poly([(37.5, 0.9), (38.1, 0.9), (37.6, 2.1), (37.0, 2.1)])
    # warning stripes over the input side
    k.hazard(5.7, 0.75, 8.5, 1.35, 0.9)
    # maker's mark: sunrise + HANDMADE
    k.sunrise(10.15, 1.9, 0.45, 1.05)
    k.text("HANDMADE", 11.7, 1.5, 0.75, 0.62, 0.13, just="l")
    k.pixels(17.1, 0.45, THUMBS_UP)

    # limits, upper right
    k.text("VIN > VOUT", 37.85, 3.85, 0.72, 0.52, 0.115, just="l")
    k.text("VIN MAX 36V", 37.85, 5.0, 0.72, 0.52, 0.115, just="l")
    # write-on box: note the voltage this board was built for
    k.text("VOUT =", 37.9, 16.05, 0.72, 0.6, 0.12, just="l")
    k.box(37.9, 16.85, 42.9, 19.35)


# --------------------------------------------------------------- bottom ---
def bottom(k):
    W, H = k.W, k.H
    T = dict(h=0.85, w=0.66, t=0.13)
    S = dict(h=0.72, w=0.58, t=0.115)
    C = dict(S, just="c")

    # ---- value table (under the inductor and output capacitors) ----
    k.bt("VOUT SELECT", 6.9, 3.3, 1.0, 0.86, 0.16)
    k.bl([(16.6, 3.3), (22.3, 3.3), (22.95, 3.95)], 0.15)
    k.bp([(22.75, 2.75), (23.6, 2.75), (23.6, 3.6)])
    cols = [1.2, 4.6, 8.0, 11.2, 14.4, 17.8, 21.2]
    head = ["VOUT", "R1", "R2", "R3", "GETS", "R2*", "L1"]
    y = 5.45
    for x, s in zip(cols, head):
        k.bt(s, x, y, **S)
    k.bl([(1.1, y + 0.72), (23.6, y + 0.72)], 0.12)
    y += 1.55
    for row in values.TABLE:
        cells = [row["label"], row["r1"], row["r2"], row["r3"],
                 row["gets"], row["r2_exact"], row["l"]]
        for x, s in zip(cols, cells):
            k.bt(s, x, y, **T)
        y += 1.38
    k.bl([(1.1, y - 0.62), (23.6, y - 0.62)], 0.12)
    y += 0.2
    notes = ["R2* = 1% PART, WITH R1 100k, R3 = 0R LINK",
             "L1 uH, >=5.1A SAT.  C6-C9 4x 22u 25V",
             "24V OUT: C6-C9 4x 10u 50V, VIN 28-36V",
             "C1 C2 10u 50V  C3 220n  D1 SMBJ24A OPT",
             "C4 100n   C5 1u   R4 100k   C10 47-100u"]
    for n in notes:
        k.bt(n, 1.2, y, **S)
        y += 1.14
    # frame with cut corners around the table
    k.bl([(0.8, 4.6), (0.8, 18.9), (1.25, 19.35), (5.2, 19.35)], 0.15)
    k.bl([(23.95, 4.6), (23.95, 18.85), (23.45, 19.35), (8.2, 19.35)], 0.15)

    # ---- pin names ----
    for s, bx in (("GND", 46.99), ("VOUT", 44.45)):
        k.bt(s, W - bx, 3.0, **C)
    for s, bx in (("GND", 46.99), ("VOUT", 44.45), ("PG", 41.91)):
        k.bt(s, W - bx, 20.05, **C)
    for s, bx in (("GND", 1.27), ("VIN", 3.81)):
        k.bt(s, W - bx, 3.0, **C)
    for s, bx in (("GND", 1.27), ("VIN", 3.81), ("EN", 6.35)):
        k.bt(s, W - bx, 20.05, **C)

    # ---- title, input-side half ----
    k.hazard(W - 20.6, 2.5, W - 6.2, 2.9, 0.8, bottom=True)
    k.bt("BUCK//33630", W - 13.4, 4.25, 1.55, 1.3, 0.24, just="c")
    k.bt("HACK THE PLANET", 33.2, 6.3, 0.95, 0.74, 0.15)
    # thermal pad call-out
    k.bl([(28.95, 6.6), (28.95, 9.5), (32.95, 9.5), (32.95, 7.4)], 0.12)
    k.bt("SOLDER U1 PAD", 31.0, 10.3, **C)
    # references for the through-hole parts, to check from the solder side
    for s, bx, y, a in (("R1", 19.6, 16.1, 90), ("R2", 17.06, 16.1, 90),
                        ("R3", 14.52, 16.1, 90), ("C4", 22.7, 5.6, 0),
                        ("C5", 22.7, 13.15, 0), ("C10", 4.1, 9.75, 0),
                        ("R4", 5.08, 17.2, 0), ("R5", 11.2, 18.6, 0)):
        k.text(s, bx, y, 0.72, 0.6, 0.115, BS, "c", a)
    k.text("+", 2.35, 6.3, 1.0, 1.0, 0.15, BS)
    # limits
    k.sunrise(W - 7.05, 12.4, 0.8, 5.75, bottom=True, rays=7)
    k.sprig(W - 10.9, 12.4, 1.0, bottom=True)
    k.sprig(W - 3.2, 12.4, 1.0, bottom=True)
    k.bt("IN 3.8-36V  3A MAX", W - 7.3, 13.3, 0.72, 0.56, 0.115, just="c")
    k.bt("KEEP VIN > VOUT", W - 7.3, 14.45, 0.72, 0.56, 0.115, just="c")
    k.bt(values.REV, W - 7.3, 15.6, 0.72, 0.56, 0.115, just="c")
