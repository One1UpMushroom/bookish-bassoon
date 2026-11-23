"""Four buck (male deer) marks for the BUCK//33630 silkscreen, one per theme
in the design library. Each fits inside a 10 x 10 mm square.

    dawnworks             the buck's head as a circuit: 45-degree traces, vias
    mahogany-lounge       mid-century figurine: tapered splayed legs, starburst
    neon-noir-chartreuse  the same head as thin neon tubes in a cut-corner frame
    parkside-98           pixel-art head inside a marquee of pixel light bulbs

How the drawings are stored
---------------------------
Every mark is a list of simple shapes measured in millimetres inside its own
10 x 10 mm box: x to the right, y DOWN (the same as KiCad), (0, 0) at the
top-left corner. There are only five kinds of shape, all things a board
factory prints without trouble:

    line   a stroke with round ends, like a copper track
    poly   a filled polygon (straight edges between the points)
    dot    a filled circle
    ring   a circle outline (r is the radius of the line's centre)
    pixel  pixel art, stored as filled rectangles (one per run of '#')

Ink can only be added, never removed, so the "holes" in a drawing (the
middle of a via ring, the eyes of the pixel deer) are made by leaving gaps.

Silkscreen limits these drawings are built to
---------------------------------------------
From JLCPCB's character design guidance (updated 16 Nov 2026), using their
recommended production values rather than the absolute minimums:

    LINE_MIN  0.20 mm  narrowest printed line  (absolute minimum 0.15 mm)
    GAP_MIN   0.20 mm  narrowest space between lines  (absolute 0.15 mm)
    HOLE_MIN  0.25 mm  narrowest enclosed hole, e.g. inside a ring

(None of the marks has lettering, so the 1.0 mm minimum letter height
doesn't come into it.)

gen/deer_check.py measures each drawing against these numbers.

Using a mark on the board
-------------------------
In art.py, for example on the back of the board:

    import deer
    deer.add_to_board(k.b, deer.make("dawnworks"), x, y, layer=BS, flip=True)

x, y is where the mark's top-left corner lands, in board coordinates.
flip=True mirrors it left-right, which is what the bottom side needs so the
drawing reads the right way round when you turn the board over. Keep the
whole 10 x 10 mm box at least 0.25 mm clear of pads: the factory removes
silkscreen that comes closer than 0.15 mm to exposed copper.

This file needs only Python itself; add_to_board() also needs KiCad's
pcbnew module, which build_pcb.py already uses.
"""
import math

BOX = 10.0          # every mark fits inside a BOX x BOX millimetre square
LINE_MIN = 0.20     # silkscreen limits, explained above
GAP_MIN = 0.20
HOLE_MIN = 0.25


# =================================================================== shapes ===

class Art:
    """One drawing: a name and a list of shapes, all in millimetres."""

    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.shapes = []

    def line(self, pts, w):
        """A stroke of width w through the points, with round ends and round
        corners (exactly how KiCad draws a silkscreen line)."""
        self.shapes.append(("line", [(float(x), float(y)) for x, y in pts], float(w)))

    def poly(self, pts):
        """A filled polygon."""
        self.shapes.append(("poly", [(float(x), float(y)) for x, y in pts]))

    def dot(self, c, r):
        """A filled circle of radius r centred on c."""
        self.shapes.append(("dot", (float(c[0]), float(c[1])), float(r)))

    def ring(self, c, r, w):
        """A circle outline: r is the radius to the middle of the line, w the
        line width. The hole in the middle has radius r - w/2."""
        self.shapes.append(("ring", (float(c[0]), float(c[1])), float(r), float(w)))

    def box(self, x1, y1, x2, y2):
        """A filled rectangle between two opposite corners."""
        self.poly([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])

    def sharp_line(self, pts, w, closed=False, square_ends=True):
        """A stroke with sharp (mitred) corners and square ends, built from
        polygons. KiCad's own lines always have round ends; this is for
        drawings that want crisp geometry."""
        for p in mitre_stroke(pts, w, closed, square_ends):
            self.poly(p)

    def pixels(self, x0, y0, rows, px):
        """Pixel art. rows is a list of strings; '#' is ink, anything else is
        blank. Each pixel is px millimetres square, and (x0, y0) is the top-left
        corner of the grid. Each horizontal run of '#' becomes one rectangle;
        rectangles in neighbouring rows touch exactly, and both KiCad and the
        factory treat touching ink as one shape."""
        for r, row in enumerate(rows):
            c = 0
            while c < len(row):
                if row[c] != "#":
                    c += 1
                    continue
                start = c                       # a run of ink starts here...
                while c < len(row) and row[c] == "#":
                    c += 1                      # ...and ends just before c
                self.box(x0 + start * px, y0 + r * px, x0 + c * px, y0 + (r + 1) * px)

    def bounds(self):
        """The smallest rectangle that holds all the ink: (x1, y1, x2, y2)."""
        xs, ys = [], []
        for s in self.shapes:
            kind = s[0]
            if kind == "line":
                h = s[2] / 2
                for x, y in s[1]:
                    xs += [x - h, x + h]
                    ys += [y - h, y + h]
            elif kind == "poly":
                xs += [x for x, _ in s[1]]
                ys += [y for _, y in s[1]]
            else:
                (x, y), r = s[1], s[2] + (s[3] / 2 if kind == "ring" else 0)
                xs += [x - r, x + r]
                ys += [y - r, y + r]
        return min(xs), min(ys), max(xs), max(ys)

    def moved(self, dx, dy):
        """A copy of the drawing shifted by (dx, dy)."""
        out = Art(self.id, self.name)
        for s in self.shapes:
            kind = s[0]
            if kind in ("line", "poly"):
                pts = [(x + dx, y + dy) for x, y in s[1]]
                out.shapes.append((kind, pts) + tuple(s[2:]))
            else:
                out.shapes.append((kind, (s[1][0] + dx, s[1][1] + dy)) + tuple(s[2:]))
        return out

    def scaled(self, k, about=(BOX / 2, BOX / 2)):
        """A copy enlarged k times around a point. Positions, dot sizes and
        ring sizes grow; line widths and ring line widths stay as they are, so
        enlarging only ever widens the gaps."""
        ox, oy = about
        f = lambda x, y: (ox + (x - ox) * k, oy + (y - oy) * k)
        out = Art(self.id, self.name)
        for s in self.shapes:
            kind = s[0]
            if kind in ("line", "poly"):
                out.shapes.append((kind, [f(x, y) for x, y in s[1]]) + tuple(s[2:]))
            elif kind == "dot":
                out.shapes.append(("dot", f(*s[1]), s[2] * k))
            else:
                out.shapes.append(("ring", f(*s[1]), s[2] * k, s[3]))
        return out

    def centred(self):
        """A copy moved so the ink sits in the middle of the BOX square."""
        x1, y1, x2, y2 = self.bounds()
        return self.moved((BOX - x1 - x2) / 2, (BOX - y1 - y2) / 2)


# ------------------------------------------------------- geometry helpers ---

def mitre_stroke(pts, w, closed=False, square_ends=True, limit=3.0):
    """Polygons that together draw a stroke of width w with sharp corners.

    Each straight piece becomes a rectangle; at each corner a small wedge
    fills the outside of the bend up to the sharp point (or is cut flat if the
    bend is so tight the point would stick out more than `limit` half-widths).
    With square_ends, open strokes stick out w/2 past their end points."""
    h = w / 2
    segs = list(zip(pts, pts[1:]))
    if closed:
        segs.append((pts[-1], pts[0]))

    def unit(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy)
        return dx / n, dy / n

    polys = []
    for i, (a, b) in enumerate(segs):
        ux, uy = unit(a, b)
        nx, ny = -uy, ux                       # sideways, at right angles
        ea = h if (square_ends and not closed and i == 0) else 0
        eb = h if (square_ends and not closed and i == len(segs) - 1) else 0
        ax, ay = a[0] - ux * ea, a[1] - uy * ea
        bx, by = b[0] + ux * eb, b[1] + uy * eb
        polys.append([(ax + nx * h, ay + ny * h), (bx + nx * h, by + ny * h),
                      (bx - nx * h, by - ny * h), (ax - nx * h, ay - ny * h)])
    corners = range(len(segs)) if closed else range(1, len(segs))
    for i in corners:
        (a0, b0), (a1, b1) = segs[i - 1], segs[i]
        u0, u1 = unit(a0, b0), unit(a1, b1)
        turn = u0[0] * u1[1] - u0[1] * u1[0]
        if abs(turn) < 1e-9:
            continue                           # straight on: nothing to fill
        s = -1 if turn > 0 else 1              # which side is the outside
        n0 = (-u0[1] * s, u0[0] * s)
        n1 = (-u1[1] * s, u1[0] * s)
        p = b0
        o0 = (p[0] + n0[0] * h, p[1] + n0[1] * h)
        o1 = (p[0] + n1[0] * h, p[1] + n1[1] * h)
        bis = (n0[0] + n1[0], n0[1] + n1[1])
        blen = math.hypot(*bis)
        reach = h / (blen / 2)                 # distance to the sharp point
        if reach <= limit * h:
            m = (p[0] + bis[0] / blen * reach, p[1] + bis[1] / blen * reach)
            polys.append([p, o0, m, o1])
        else:
            polys.append([p, o0, o1])
    return polys


def bezier(*ctrl, n=16):
    """Points along a Bezier curve (3 control points = quadratic, 4 = cubic)."""
    out = []
    for i in range(n + 1):
        t = i / n
        pts = list(ctrl)
        while len(pts) > 1:                    # de Casteljau: repeated blending
            pts = [((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1])
                   for a, b in zip(pts, pts[1:])]
        out.append(pts[0])
    return out


def smooth_loop(anchors, n=8):
    """A closed smooth outline through the anchor points (a Catmull-Rom
    spline): handy for organic silhouettes drawn from a few points."""
    out = []
    k = len(anchors)
    for i in range(k):
        p0, p1, p2, p3 = (anchors[(i + j) % k] for j in (-1, 0, 1, 2))
        for s in range(n):
            t = s / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[d]) + (-p0[d] + p2[d]) * t
                                    + (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d]) * t2
                                    + (-p0[d] + 3 * p1[d] - 3 * p2[d] + p3[d]) * t3)
                             for d in (0, 1)))
    return out


def circle_pts(c, r, n=48, a0=0.0, a1=360.0):
    """Points around a circle (or an arc from angle a0 to a1, in degrees)."""
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def leaf(base, tip, width, r_end=0.11, n=14):
    """A leaf-shaped filled outline from base to tip, `width` across at its
    widest, with both ends rounded to radius r_end so no point is thinner
    than the printable minimum (2 x 0.11 = 0.22 mm)."""
    L = math.dist(base, tip)
    ux, uy = (tip[0] - base[0]) / L, (tip[1] - base[1]) / L
    vx, vy = -uy, ux
    half = lambda t: width / 2 * math.sin(math.pi * t)
    # where the leaf is exactly 2 * r_end wide, near each end
    t0 = math.asin(min(1.0, r_end / (width / 2))) / math.pi
    t1 = 1 - t0
    at = lambda t, side: (base[0] + ux * t * L + vx * side * half(t),
                          base[1] + uy * t * L + vy * side * half(t))
    left = [at(t0 + (t1 - t0) * i / n, 1) for i in range(n + 1)]
    right = [at(t1 - (t1 - t0) * i / n, -1) for i in range(n + 1)]
    ang = math.degrees(math.atan2(vy, vx))
    c1 = (base[0] + ux * t1 * L, base[1] + uy * t1 * L)
    c0 = (base[0] + ux * t0 * L, base[1] + uy * t0 * L)
    cap1 = circle_pts(c1, r_end, 8, ang, ang - 180)[1:-1]      # round the tip
    cap0 = circle_pts(c0, r_end, 8, ang + 180, ang)[1:-1]      # round the base
    return left + cap1 + right + cap0


def taper(top1, top2, foot, foot_w):
    """A tapering leg: a straight-sided shape from a top edge (top1 to top2)
    down to a narrow foot centred on `foot`. Add a dot of radius foot_w / 2 at
    the foot to round it."""
    mx, my = (top1[0] + top2[0]) / 2, (top1[1] + top2[1]) / 2
    L = math.dist((mx, my), foot)
    ux, uy = (foot[0] - mx) / L, (foot[1] - my) / L
    vx, vy = -uy, ux
    h = foot_w / 2
    return [top1, top2, (foot[0] - vx * h, foot[1] - vy * h),
            (foot[0] + vx * h, foot[1] + vy * h)]


def mirror_x(pts, axis=BOX / 2):
    """The same points reflected left-right about the vertical line x = axis."""
    return [(2 * axis - x, y) for x, y in pts]


# ================================================================ the deer ===

# ---- the buck's head, shared by Dawnworks and Neon Noir -------------------
# A front view made only of straight lines that turn at 45 or 90 degrees.
# The antlers and ears are written out for the left side only; the right
# side is their mirror image. Millimetres, before the drawing is enlarged and
# centred in its box.
HEAD_FACE = [(5.0, 4.6), (6.25, 4.6), (6.25, 5.85), (5.5, 6.6), (5.5, 7.85),
             (5.0, 8.35), (4.5, 7.85), (4.5, 6.6), (3.75, 5.85), (3.75, 4.6)]
HEAD_EAR = [(3.85, 4.75), (3.85, 5.45), (2.85, 4.45), (2.85, 3.85),
            (3.45, 3.85), (3.85, 4.25)]           # left ear, as a filled shape
HEAD_EAR_LINE = [(3.75, 5.35), (2.85, 4.45), (2.85, 3.85), (3.45, 3.85),
                 (3.75, 4.15), (3.75, 4.6)]       # the same ear as an outline
HEAD_EYES = [(4.42, 5.35), (5.58, 5.35)]
HEAD_NOSE = [(4.5, 7.4), (5.5, 7.4), (5.5, 7.85), (5.0, 8.35), (4.5, 7.85)]
HEAD_BEAM = [(4.25, 4.6), (4.25, 3.95), (1.75, 1.45)]   # up, then out at 45
HEAD_TINES = [[(3.75, 3.45), (3.75, 2.2)],              # brow tine
              [(2.9, 2.6), (2.9, 1.0)]]                 # second tine


def antlers():
    """Every antler line as a list of points: beam and tines, left then right.
    Each line starts where it grows out and ends at its tip."""
    left = [HEAD_BEAM] + HEAD_TINES
    return left + [mirror_x(line) for line in left]


def dawnworks():
    """Dawnworks: the buck drawn as a circuit. Every line is a 0.25 mm trace
    that turns only at 45 or 90 degrees (theme section 6), and every antler
    tine ends in a via. The ears are solid pads, the eyes test points and the
    nose a solder pad: filled pads against line traces, as on a real board.
    Symmetric like a component footprint."""
    a = Art("dawnworks", "Dawnworks")
    T = 0.25                                # trace width
    VR, VW = 0.33, 0.22                     # via: ring centre radius, ring width
    a.line(HEAD_FACE + HEAD_FACE[:1], T)    # face: one closed loop of trace
    a.poly(HEAD_EAR)
    a.poly(mirror_x(HEAD_EAR))
    for eye in HEAD_EYES:
        a.dot(eye, 0.21)
    a.poly(HEAD_NOSE)
    for trace in antlers():
        *start, (vx, vy) = trace            # the tip is where the via goes
        px_, py_ = start[-1]
        L = math.dist((px_, py_), (vx, vy))
        k = (VR + VW / 2) / L               # stop at the ring's outer edge,
        a.line(start + [(vx - (vx - px_) * k, vy - (vy - py_) * k)], T)
        a.ring((vx, vy), VR, VW)            # so the via's hole stays open
    return a.scaled(1.17).centred()


def mahogany_lounge():
    """Mahogany Lounge: a mid-century figurine in profile. A long soft body,
    an elegant neck, legs that taper and splay like the legs of a 1950s
    sideboard ("float and taper", principle 2), fine-line antlers, and an
    atomic starburst as the original ornament the theme asks for (section 6)."""
    a = Art("mahogany-lounge", "Mahogany Lounge")
    W = 0.2                       # fine line weight: antlers and starburst
    # head, neck and body as one smooth outline, facing left
    a.poly(smooth_loop([
        (1.3, 3.95), (1.5, 3.68), (2.15, 3.3), (2.65, 3.02), (3.15, 3.0),
        (3.5, 3.3), (3.8, 3.95), (4.25, 4.75), (4.9, 5.28), (6.2, 5.3),
        (7.5, 5.35), (8.05, 5.55), (8.25, 6.0), (8.0, 6.6), (7.0, 6.9),
        (5.6, 7.0), (4.4, 6.9), (3.7, 6.6), (3.35, 6.1), (3.1, 5.3),
        (2.75, 4.55), (2.45, 4.22), (1.8, 4.17), (1.42, 4.08)]))
    a.poly(leaf((3.45, 3.4), (4.4, 3.27), 0.48))             # ear
    a.poly(leaf((7.9, 5.75), (8.62, 5.24), 0.34))            # little tail
    # legs: tapered, splayed, rounded feet
    for top1, top2, foot in (((3.85, 6.5), (4.35, 6.65), (3.55, 9.55)),
                             ((4.65, 6.75), (5.1, 6.8), (4.85, 9.55)),
                             ((6.75, 6.8), (7.3, 6.75), (7.1, 9.55)),
                             ((7.55, 6.65), (8.0, 6.5), (8.35, 9.55))):
        a.poly(taper(top1, top2, foot, 0.24))
        a.dot(foot, 0.12)
    # antlers: two fine curved beams with tines, round ends
    # both grow from one point on the crown and fan out about 36 degrees
    # apart, so the notch between them stays short (see deer_check.py)
    near = bezier((3.05, 3.1), (3.2, 2.4), (3.5, 1.4), (3.0, 0.5))
    far = bezier((3.05, 3.1), (3.75, 2.5), (4.35, 1.5), (4.05, 0.6))
    a.line(near, W)
    a.line(far, W)
    a.line([near[5], (2.35, 2.05)], W)
    a.line([near[10], (2.45, 1.0)], W)
    a.line([far[7], (4.95, 1.65)], W)
    a.line([far[11], (4.9, 0.75)], W)
    # atomic starburst: four long rays, four short ones, a dot in the middle
    cx, cy = 7.45, 2.1
    a.dot((cx, cy), 0.28)
    for i in range(8):
        ang = math.radians(i * 45)
        r2 = 1.3 if i % 2 == 0 else 0.92
        a.line([(cx + 0.62 * math.cos(ang), cy + 0.62 * math.sin(ang)),
                (cx + r2 * math.cos(ang), cy + r2 * math.sin(ang))], W)
    return a.scaled(1.04).centred()


def neon_noir():
    """Neon Noir Chartreuse: the same buck's head as Dawnworks, redrawn as a
    neon sign: one thin tube weight, sharp corners and square ends (theme
    sections 6 and 9), with outlines where Dawnworks has solid pads and no
    vias. It sits in a frame with all four corners cut at 45 degrees, the
    theme's signature. On the board it is white ink on black; the chartreuse
    itself would come from an LED or the enclosure, since the theme treats
    chartreuse as light."""
    W = 0.2                                 # tube width
    head = Art("neon-noir-chartreuse", "Neon Noir Chartreuse")
    head.sharp_line(HEAD_FACE, W, closed=True)
    head.sharp_line(HEAD_EAR_LINE, W, square_ends=False)
    head.sharp_line(mirror_x(HEAD_EAR_LINE), W, square_ends=False)
    for x, y in HEAD_EYES:                  # small square eyes
        head.box(x - 0.2, y - 0.2, x + 0.2, y + 0.2)
    head.sharp_line(HEAD_NOSE[:2], W, square_ends=False)   # top of the nose
    for tube in antlers():
        head.sharp_line(tube, W)
    a = head.scaled(1.08).centred()
    c = 1.3                                 # size of each corner cut
    lo, hi = 0.3, 9.7                       # frame line centre, all round
    a.sharp_line([(lo + c, lo), (hi - c, lo), (hi, lo + c), (hi, hi - c),
                  (hi - c, hi), (lo + c, hi), (lo, hi - c), (lo, lo + c)], W,
                 closed=True)
    return a


# Parkside 98: the buck's head as pixel art, one string per row ('#' is ink).
# It is symmetric about its middle column, so each string holds the left 16
# columns plus the middle column; the right 16 are the mirror image.
BUCK_ICON_LEFT = [
    "...##............",   # antler tips
    "...##..#..#......",
    "...##..#..#......",
    "...##..#..#......",
    "...###.#..#......",
    "....####..#..#...",   # tines rise from the curving beam
    ".....####.#..#...",
    ".......####..#...",
    ".........#####...",
    "...........######",   # top of the head
    "....######.######",   # ears
    "...##############",
    "..###############",
    "...##############",
    "...........#..###",   # eyes
    "...........#..###",
    "...........######",
    "............#####",
    "............#####",
    "............#####",
    "............#####",
    ".............####",
    ".............####",
    ".............####",
    ".............#...",   # nose
    ".............#...",
    ".............####",
    "..............###",
]


def parkside_98():
    """Parkside 98: a 33 x 28 pixel buck's head (theme section 6: square
    pixels, square corners, no smoothing) inside a marquee of pixel light
    bulbs, the sign-board side of the theme's sunny theme park. Each pixel is
    0.25 mm, so every line, gap and hole is at least 0.25 mm."""
    a = Art("parkside-98", "Parkside 98")
    px = 0.25
    n = 39                                  # 39 x 0.25 mm = 9.75 mm square
    grid = [["."] * n for _ in range(n)]
    for r, half in enumerate(BUCK_ICON_LEFT):
        row = half + half[:16][::-1]        # left, middle, then the mirror
        for c, ch in enumerate(row):
            if ch == "#":
                grid[5 + r][3 + c] = "#"    # 2 clear pixels inside the bulbs
    # marquee: ten bulbs along each side, 4 pixels apart; each bulb is a
    # 3 x 3 plus sign, which is how pixel art draws something round
    bulb = [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)]
    for i in range(10):
        p = 4 * i
        for top, left in ((0, p), (n - 3, p), (p, 0), (p, n - 3)):
            for dr, dc in bulb:
                grid[top + dr][left + dc] = "#"
    a.pixels(0, 0, ["".join(row) for row in grid], px)
    return a.centred()


DESIGNS = {
    "dawnworks": dawnworks,
    "mahogany-lounge": mahogany_lounge,
    "neon-noir-chartreuse": neon_noir,
    "parkside-98": parkside_98,
}


def make(id):
    """The drawing for one theme id (see DESIGNS)."""
    return DESIGNS[id]()


# ============================================================ output: KiCad ===

def add_to_board(board, art, x, y, layer=None, flip=False):
    """Add a drawing to a KiCad board as silkscreen.

    x, y: board position (mm) for the top-left corner of the 10 x 10 mm box.
    layer: pcbnew.F_SilkS (default) or pcbnew.B_SilkS.
    flip: mirror left-right inside the box; use it on the bottom side.
    Returns the list of KiCad shapes it added (so a caller can group them)."""
    import pcbnew
    from pcbnew import FromMM, VECTOR2I
    if layer is None:
        layer = pcbnew.F_SilkS

    def P(px_, py_):
        if flip:
            px_ = BOX - px_
        return VECTOR2I(FromMM(x + px_), FromMM(y + py_))

    added = []

    def put(shape):
        shape.SetLayer(layer)
        board.Add(shape)
        added.append(shape)

    for s in art.shapes:
        kind = s[0]
        if kind == "line":
            for p, q in zip(s[1], s[1][1:]):
                seg = pcbnew.PCB_SHAPE(board)
                seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
                seg.SetStart(P(*p))
                seg.SetEnd(P(*q))
                seg.SetWidth(FromMM(s[2]))
                put(seg)
        elif kind == "poly":
            pol = pcbnew.PCB_SHAPE(board)
            pol.SetShape(pcbnew.SHAPE_T_POLY)
            pol.SetPolyPoints([P(*p) for p in s[1]])
            pol.SetFilled(True)
            pol.SetWidth(0)
            put(pol)
        else:                                       # dot or ring
            (cx, cy), r = s[1], s[2]
            cir = pcbnew.PCB_SHAPE(board)
            cir.SetShape(pcbnew.SHAPE_T_CIRCLE)
            cir.SetCenter(P(cx, cy))
            cir.SetEnd(P(cx + (-r if flip else r), cy))
            if kind == "dot":
                cir.SetFilled(True)
                cir.SetWidth(0)
            else:
                cir.SetFilled(False)
                cir.SetWidth(FromMM(s[3]))
            put(cir)
    return added


# ============================================================== output: SVG ===

def to_svg(art, ink="#FFFFFF", paper=None, size=None):
    """The drawing as an SVG picture, 10 x 10 units = 10 x 10 mm.

    ink: colour of the silkscreen ("currentColor" lets a web page choose it).
    paper: background colour (None = clear). size: optional width/height
    attribute, e.g. "10mm" or "240".

    All the filled polygons go into one path, each turned the same way round,
    so a browser paints them as one shape: separate shapes that touch (the
    pixel art) would otherwise show hairline seams."""
    fills, out = [], []
    for s in art.shapes:
        kind = s[0]
        if kind == "line":
            d = "M" + " L".join(f"{x:.4f} {y:.4f}" for x, y in s[1])
            out.append(f'<path d="{d}" fill="none" stroke-width="{s[2]:.4f}" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>')
        elif kind == "poly":
            pts = s[1]
            area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2)
                       in zip(pts, pts[1:] + pts[:1]))
            if area < 0:                       # make every outline clockwise
                pts = pts[::-1]
            fills.append("M" + " L".join(f"{x:.4f} {y:.4f}" for x, y in pts) + "Z")
        elif kind == "dot":
            out.append(f'<circle cx="{s[1][0]:.4f}" cy="{s[1][1]:.4f}" r="{s[2]:.4f}" '
                       f'stroke="none"/>')
        else:
            out.append(f'<circle cx="{s[1][0]:.4f}" cy="{s[1][1]:.4f}" r="{s[2]:.4f}" '
                       f'fill="none" stroke-width="{s[3]:.4f}"/>')
    if fills:
        out.insert(0, f'<path d="{" ".join(fills)}" stroke="none" fill-rule="nonzero"/>')
    dims = f' width="{size}" height="{size}"' if size else ""
    bg = f'<rect width="{BOX}" height="{BOX}" fill="{paper}"/>' if paper else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BOX} {BOX}"{dims}>'
            f'{bg}<g fill="{ink}" stroke="{ink}">' + "".join(out) + "</g></svg>\n")
