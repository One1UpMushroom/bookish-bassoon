"""Drawing kit shared by the four themed BUCK//33630 boards.

Every theme draws its silkscreen through an Ink, which works in "view"
coordinates: millimetres measured from the top-left corner of the side you
are looking at, x to the right, y down. On the bottom side that means the
picture is mirrored for you, so text and art read correctly when the board
is turned over (the same convention as art.py's bottom helpers).

What an Ink can draw:
  line, sharp     strokes (round-ended like KiCad tracks, or mitred polygons)
  poly, rect      filled shapes
  ring, disc      circles
  text            KiCad's own stroke font (kept for small, functional text)
  title           letters from a real font, stored as outlines in glyphs.json
  pixel_text      the pixel font below (Parkside 98)
  pixels          pixel art from rows of '#'
  place           one of the 10 mm deer marks from deer.py
  open_*          openings in the solder mask, which show bare metal (the
                  board's finish: gold for ENIG, silver for HASL) wherever
                  copper lies underneath

Elements: everything one of those calls draws (one label, one title, one
frame, the deer) is kept together in a KiCad group, called an element here.
In KiCad, clicking an element selects all of it. The silkscreen check
(gen/silk_check.py) lets the parts of one element touch, but keeps every
element at least 0.15 mm from every other one. Where separate calls are
meant to touch (a trace running into its via), wrap them in
`with ink.element("name"):` so they count as one.
"""
import contextlib
import functools
import json
import math
import os
import sys

import pcbnew
from pcbnew import FromMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import deer  # noqa: E402

JUST = {"l": pcbnew.GR_TEXT_H_ALIGN_LEFT, "c": pcbnew.GR_TEXT_H_ALIGN_CENTER,
        "r": pcbnew.GR_TEXT_H_ALIGN_RIGHT}
_GLYPHS = None


def glyph_fonts():
    """The letter outlines made by make_glyphs.py, loaded once."""
    global _GLYPHS
    if _GLYPHS is None:
        with open(os.path.join(HERE, "glyphs.json")) as f:
            _GLYPHS = json.load(f)
    return _GLYPHS


# ------------------------------------------------------------ pixel font ---
# Five pixels high. No two pixels of a letter touch only at a corner (that
# would be a zero-width join that may or may not print), which is why some
# letters are a little square: A, B, D, N, R.
PIXEL_FONT = {
    "A": ["####", "#..#", "####", "#..#", "#..#"],
    "B": ["###.", "#.##", "###.", "#.##", "###."],
    "C": ["###", "#..", "#..", "#..", "###"],
    "D": ["###.", "#.##", "#..#", "#.##", "###."],
    "E": ["###", "#..", "###", "#..", "###"],
    "F": ["###", "#..", "###", "#..", "#.."],
    "G": ["####", "#...", "#.##", "#..#", "####"],
    "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"],
    "J": ["..#", "..#", "..#", "#.#", "###"],
    "K": ["#..#", "#.##", "###.", "#.##", "#..#"],
    "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["##.##", "#####", "#.#.#", "#...#", "#...#"],
    "N": ["#..#", "##.#", "####", "#.##", "#..#"],
    "O": ["####", "#..#", "#..#", "#..#", "####"],
    "P": ["####", "#..#", "####", "#...", "#..."],
    "Q": ["####", "#..#", "#..#", "#.##", "####"],
    "R": ["####", "#..#", "####", "#.##", "#..#"],
    "S": ["####", "#...", "####", "...#", "####"],
    "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"],
    "V": ["#.#", "#.#", "#.#", "###", ".#."],
    "W": ["#...#", "#...#", "#.#.#", "#####", "##.##"],
    "X": ["##.##", ".###.", "..#..", ".###.", "##.##"],
    "Y": ["#.#", "#.#", "###", ".#.", ".#."],
    "Z": ["####", "..##", ".##.", "##..", "####"],
    "0": ["###", "#.#", "#.#", "#.#", "###"],
    "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"],
    "3": ["###", "..#", "###", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"],
    "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"],
    "7": ["###", "..#", "..#", "..#", "..#"],
    "8": ["###", "#.#", "###", "#.#", "###"],
    "9": ["###", "#.#", "###", "..#", "###"],
    "/": ["..#", ".##", ".#.", "##.", "#.."],
    "-": ["...", "...", "###", "...", "..."],
    ".": [".", ".", ".", ".", "#"],
    ":": [".", "#", ".", "#", "."],
    "=": ["...", "###", "...", "###", "..."],
    ">": ["#..", "##.", ".##", "##.", "#.."],
    "+": ["...", ".#.", "###", ".#.", "..."],
    " ": ["..", "..", "..", "..", ".."],
}


# Narrow forms of two four-pixel letters, for labels that must fit a 2.54 mm
# pin pitch (narrow=True below). D and N have no three-pixel form without
# pixels that touch only at a corner, so they keep their width.
PIXEL_NARROW = {
    "G": ["###", "#..", "#.#", "#.#", "###"],
    "O": ["###", "#.#", "#.#", "#.#", "###"],
}


def pixel_rows(s, gap=1, narrow=False):
    """A string laid out in the pixel font: five rows of '#' and '.'.
    narrow=True uses the narrow G and O."""
    rows = [""] * 5
    for i, ch in enumerate(s.upper()):
        g = (narrow and PIXEL_NARROW.get(ch)) or PIXEL_FONT[ch]
        for r in range(5):
            rows[r] += ("." * gap if i else "") + g[r]
    return rows


# --------------------------------------------------------- board outline ---

def outline(tl=("chamfer", 0.8), tr=("chamfer", 0.8), br=("chamfer", 0.8),
            bl=("chamfer", 0.8), steps=12):
    """A corners function for build_pcb.outline_pts. Each corner is
    ("square",), ("chamfer", size) or ("round", radius), in mm. The header
    pins sit near the corners, so chamfers stop at 0.9 mm and radii at
    1.5 mm to keep copper 0.3 mm from the edge."""
    def corner(kind, cx, cy, sx, sy, a0):
        # (cx, cy) is the corner; sx, sy point into the board; a0 is the
        # start angle of the round's arc (degrees, y down).
        if kind[0] == "square":
            return [(cx, cy)]
        size = kind[1]
        if kind[0] == "chamfer":
            # first the point on the edge we arrive along, then the next edge
            pts = [(cx, cy + sy * size), (cx + sx * size, cy)]
            if a0 in (270, 90):                   # TR and BL arrive along x
                pts = [(cx + sx * size, cy), (cx, cy + sy * size)]
            return pts
        ccx, ccy = cx + sx * size, cy + sy * size
        return [(ccx + size * math.cos(math.radians(a0 + 90 * i / steps)),
                 ccy + size * math.sin(math.radians(a0 + 90 * i / steps)))
                for i in range(steps + 1)]

    def corners(W, H):
        return (corner(tl, 0, 0, 1, 1, 180) + corner(tr, W, 0, -1, 1, 270)
                + corner(br, W, H, -1, -1, 0) + corner(bl, 0, H, 1, -1, 90))
    return corners


# ------------------------------------------------------------- stackup ---

def set_stackup(path, mask, silk="White", finish="ENIG"):
    """Write the board's colours and pad finish into the saved .kicad_pcb.
    KiCad's 3D viewer shows them; the board house still takes the colours
    from the order form. mask is a KiCad colour name or "#RRGGBBAA"."""
    s = open(path).read()
    block = f'''  (setup
    (stackup
      (layer "F.SilkS" (type "Top Silk Screen") (color "{silk}"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (color "{mask}") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.035))
      (layer "B.Mask" (type "Bottom Solder Mask") (color "{mask}") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen") (color "{silk}"))
      (copper_finish "{finish}")
      (dielectric_constraints no)
    )
'''
    if "(stackup" in s:
        return
    assert s.count("  (setup\n") == 1, "unexpected board file layout"
    open(path, "w").write(s.replace("  (setup\n", block, 1))


def _title_layout(s, cap, font, track, kern):
    """For a title: the font, the size of one em in mm, where each letter
    starts (mm from the left end), and the total width."""
    f = glyph_fonts()[font]
    em = cap / f["cap"]
    kern = kern or {}
    starts, x = [], 0.0
    for i, ch in enumerate(s):
        starts.append(x)
        x += f["glyphs"][ch]["adv"] * em
        if i < len(s) - 1:
            x += track + kern.get(s[i:i + 2], 0.0)
    return f, em, starts, x


def _solid_stroke(loop, width_em):
    """A letter that is one straight stroke (like "/") as a plain
    four-cornered stroke `width_em` wide (measured square to the stroke),
    keeping the letter's slant, height and flat top and bottom ends. Font
    units (em), y up."""
    ys = [y for _, y in loop]
    lo, hi = min(ys), max(ys)
    bottom = [x for x, y in loop if abs(y - lo) < 1e-6]
    top = [x for x, y in loop if abs(y - hi) < 1e-6]
    xb, xt = (min(bottom) + max(bottom)) / 2, (min(top) + max(top)) / 2
    slant = math.atan2(hi - lo, xt - xb)
    half = width_em / (2 * math.sin(slant))    # half the width along a flat end
    return [(xb - half, lo), (xt - half, hi), (xt + half, hi), (xb + half, lo)]


# ------------------------------------------------------------------ Ink ---

def drawing(method):
    """Marks one of Ink's drawing methods: all it draws in one call becomes
    one element (see Ink.element). Its name is the method's name, plus the
    text for the methods that draw text."""
    @functools.wraps(method)
    def draw_as_one_element(self, *args, **kwargs):
        name = method.__name__
        if args and isinstance(args[0], str):
            name += " " + args[0]
        with self.element(name):
            return method(self, *args, **kwargs)
    return draw_as_one_element


class Ink:
    """Draws on one side of one board copy. side is "top" or "bottom"; W, H
    is the board size and (ox, oy) where this copy sits (panels hold eight)."""

    def __init__(self, board, side, W, H, ox=0.0, oy=0.0):
        self.b, self.W, self.H, self.ox, self.oy = board, W, H, ox, oy
        self.bottom = side == "bottom"
        self.silk = pcbnew.B_SilkS if self.bottom else pcbnew.F_SilkS
        self.mask = pcbnew.B_Mask if self.bottom else pcbnew.F_Mask
        self._group = None        # the element being drawn, if any
        self._in_group = 0        # how many items it holds so far

    @contextlib.contextmanager
    def element(self, name):
        """Everything drawn inside `with ink.element(name):` becomes one
        element: one KiCad group. An element started while another is open
        just joins the outer one, so a frame drawn inside a window element
        is part of the window."""
        if self._group is not None:
            yield self._group
            return
        group = pcbnew.PCB_GROUP(self.b)
        group.SetName(name)
        self.b.Add(group)
        self._group, self._in_group = group, 0
        try:
            yield group
        finally:
            if self._in_group == 0:       # nothing drawn: drop the empty group
                self.b.Remove(group)
            self._group = None

    # -- coordinates
    def P(self, x, y):
        """View mm -> a KiCad point on the board."""
        bx = self.W - x if self.bottom else x
        return VECTOR2I(FromMM(bx + self.ox), FromMM(y + self.oy))

    def _add(self, shape, layer):
        shape.SetLayer(self.silk if layer is None else layer)
        self.b.Add(shape)
        self._join(shape)

    def _join(self, item):
        """Put an item that is already on the board into the open element."""
        if self._group is not None:
            self._group.AddItem(item)
            self._in_group += 1

    # -- strokes and shapes
    @drawing
    def line(self, pts, w=0.15, layer=None):
        """Round-ended stroke through the points."""
        for a, b in zip(pts, pts[1:]):
            s = pcbnew.PCB_SHAPE(self.b)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(self.P(*a))
            s.SetEnd(self.P(*b))
            s.SetWidth(FromMM(w))
            self._add(s, layer)

    @drawing
    def poly(self, pts, layer=None):
        """Filled polygon (no holes)."""
        s = pcbnew.PCB_SHAPE(self.b)
        s.SetShape(pcbnew.SHAPE_T_POLY)
        s.SetPolyPoints([self.P(x, y) for x, y in pts])
        s.SetFilled(True)
        s.SetWidth(0)
        self._add(s, layer)

    @drawing
    def shape_with_holes(self, loops, layer=None):
        """Filled shape from closed loops, holes found by nesting (a loop
        inside an odd number of others is a hole). KiCad's drawn polygons
        can't hold holes, so the shape is cut open into hole-free pieces
        (the same trick KiCad uses for copper zones)."""
        def inside(p, loop):
            x, y = p
            hit = False
            for (x1, y1), (x2, y2) in zip(loop, loop[1:] + loop[:1]):
                if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                    hit = not hit
            return hit
        sps = pcbnew.SHAPE_POLY_SET()
        depth = [sum(inside(loop[0], other) for j, other in enumerate(loops) if j != i)
                 for i, loop in enumerate(loops)]
        for i, loop in enumerate(loops):
            if depth[i] % 2 == 0:                      # an outer loop
                o = sps.NewOutline()
                for x, y in loop:
                    p = self.P(x, y)
                    sps.Append(p.x, p.y, o)
                for j, hole in enumerate(loops):
                    if depth[j] == depth[i] + 1 and inside(hole[0], loop):
                        h = sps.NewHole(o)
                        for x, y in hole:
                            p = self.P(x, y)
                            sps.Append(p.x, p.y, o, h)
        sps.Simplify(pcbnew.SHAPE_POLY_SET.PM_FAST)
        sps.Fracture(pcbnew.SHAPE_POLY_SET.PM_FAST)
        for i in range(sps.OutlineCount()):
            one = pcbnew.SHAPE_POLY_SET()
            one.AddOutline(sps.Outline(i))
            s = pcbnew.PCB_SHAPE(self.b)
            s.SetShape(pcbnew.SHAPE_T_POLY)
            s.SetPolyShape(one)
            s.SetFilled(True)
            s.SetWidth(0)
            self._add(s, layer)

    @drawing
    def rect(self, x1, y1, x2, y2, layer=None):
        self.poly([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], layer)

    @drawing
    def sharp(self, pts, w=0.15, closed=False, square_ends=True, layer=None):
        """Stroke with mitred corners and square ends (crisp geometry)."""
        for p in deer.mitre_stroke(pts, w, closed, square_ends):
            self.poly(p, layer)

    @drawing
    def ring(self, c, r, w=0.15, layer=None):
        """Circle outline; r is the radius to the middle of the line."""
        s = pcbnew.PCB_SHAPE(self.b)
        s.SetShape(pcbnew.SHAPE_T_CIRCLE)
        s.SetCenter(self.P(*c))
        s.SetEnd(self.P(c[0] + r, c[1]))
        s.SetWidth(FromMM(w))
        s.SetFilled(False)
        self._add(s, layer)

    @drawing
    def disc(self, c, r, layer=None):
        s = pcbnew.PCB_SHAPE(self.b)
        s.SetShape(pcbnew.SHAPE_T_CIRCLE)
        s.SetCenter(self.P(*c))
        s.SetEnd(self.P(c[0] + r, c[1]))
        s.SetWidth(0)
        s.SetFilled(True)
        self._add(s, layer)

    # -- frames
    @drawing
    def round_frame(self, x1, y1, x2, y2, r, w=0.15, layer=None, steps=8):
        """Rectangle outline with rounded corners (radius r to the line's middle)."""
        pts = []
        for cx, cy, a0 in ((x2 - r, y1 + r, 270), (x2 - r, y2 - r, 0),
                           (x1 + r, y2 - r, 90), (x1 + r, y1 + r, 180)):
            pts += [(cx + r * math.cos(math.radians(a0 + 90 * i / steps)),
                     cy + r * math.sin(math.radians(a0 + 90 * i / steps)))
                    for i in range(steps + 1)]
        self.line(pts + pts[:1], w, layer)

    @drawing
    def cut_frame(self, x1, y1, x2, y2, cut, w=0.15, corners="tl tr br bl",
                  layer=None):
        """Rectangle outline with 45-degree cuts on the named corners, drawn
        with sharp corners."""
        c = {k: (cut if k in corners.split() else 0) for k in ("tl", "tr", "br", "bl")}
        pts = [(x1 + c["tl"], y1), (x2 - c["tr"], y1), (x2, y1 + c["tr"]),
               (x2, y2 - c["br"]), (x2 - c["br"], y2), (x1 + c["bl"], y2),
               (x1, y2 - c["bl"]), (x1, y1 + c["tl"])]
        clean = [p for i, p in enumerate(pts) if p != pts[i - 1]]
        self.sharp(clean, w, closed=True, layer=layer)

    @drawing
    def round_fill(self, x1, y1, x2, y2, r, layer=None, steps=8):
        """Filled rectangle with rounded corners."""
        pts = []
        for cx, cy, a0 in ((x2 - r, y1 + r, 270), (x2 - r, y2 - r, 0),
                           (x1 + r, y2 - r, 90), (x1 + r, y1 + r, 180)):
            pts += [(cx + r * math.cos(math.radians(a0 + 90 * i / steps)),
                     cy + r * math.sin(math.radians(a0 + 90 * i / steps)))
                    for i in range(steps + 1)]
        self.poly(pts, layer)

    @drawing
    def starburst(self, c, r_long, r_short=None, n=8, w=0.15, dot=None, layer=None):
        """Mid-century starburst: n rays, alternating long and short, round
        ends. The rays start far enough out that neighbours stay 0.2 mm apart;
        dot puts a filled centre of that radius inside them."""
        r_short = r_short or r_long * 0.65
        r_in = (0.2 + w) / (2 * math.sin(math.pi / n)) + w / 2
        if dot:
            r_in = max(r_in, dot + 0.2 + w / 2)
            self.disc(c, dot, layer)
        for i in range(n):
            a = 2 * math.pi * i / n - math.pi / 2
            r = r_long if i % 2 == 0 else r_short
            self.line([(c[0] + r_in * math.cos(a), c[1] + r_in * math.sin(a)),
                       (c[0] + r * math.cos(a), c[1] + r * math.sin(a))], w, layer)

    # -- text
    @drawing
    def text(self, s, x, y, h=0.9, w=None, t=0.15, just="l", ang=0, layer=None):
        """KiCad stroke-font text, vertically centred on y."""
        w = w or h * 0.8
        tx = pcbnew.PCB_TEXT(self.b)
        tx.SetText(s)
        tx.SetTextSize(VECTOR2I(FromMM(w), FromMM(h)))
        tx.SetTextThickness(FromMM(t))
        tx.SetHorizJustify(JUST[just])
        tx.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        tx.SetMirrored(self.bottom)
        tx.SetTextAngleDegrees(ang)
        tx.SetPosition(self.P(x, y))
        self._add(tx, layer)
        return tx

    def text_width(self, s, h=0.9, w=None, t=0.15):
        """How wide KiCad will draw s, in mm (ink, without the margins)."""
        w = w or h * 0.8
        tx = pcbnew.PCB_TEXT(self.b)
        tx.SetText(s)
        tx.SetTextSize(VECTOR2I(FromMM(w), FromMM(h)))
        tx.SetTextThickness(FromMM(t))
        return pcbnew.ToMM(tx.GetTextBox().GetWidth()) - t

    @drawing
    def spaced(self, s, x, y, h=0.9, w=None, t=0.15, track=0.25, just="l"):
        """Stroke text with extra space between letters (tracking, in mm)."""
        widths = [self.text_width(ch, h, w, t) if ch != " " else h * 0.45 for ch in s]
        total = sum(widths) + track * (len(s) - 1)
        x0 = {"l": x, "c": x - total / 2, "r": x - total}[just]
        for ch, cw in zip(s, widths):
            if ch != " ":
                self.text(ch, x0, y, h, w, t, "l")
            x0 += cw + track
        return total

    @drawing
    def title(self, s, x, y, cap, font, just="l", track=0.0, layer=None, kern=None,
              solid=None):
        """Text in a real font: cap is the height of a capital letter in mm,
        (x, y) the left/centre/right end of the baseline. Returns the width.

        track: extra space between all letters, mm.
        kern:  extra space after particular pairs, mm, e.g. {"K/": 0.12}
               (where a font sets two letters too close to print apart).
        solid: letters that are one straight stroke, like "/", redrawn as a
               plain stroke of the given width in mm, with the font's own
               slant and height, e.g. {"/": 0.19} (for a font whose slash is
               too thin to print this small)."""
        f, em, starts, total = _title_layout(s, cap, font, track, kern)
        x0 = {"l": x, "c": x - total / 2, "r": x - total}[just]
        for ch, sx in zip(s, starts):
            glyph = f["glyphs"][ch]["loops"]
            if solid and ch in solid and glyph:
                glyph = [_solid_stroke(glyph[0], solid[ch] / em)]
            loops = [[(x0 + sx + px * em, y - py * em) for px, py in loop]
                     for loop in glyph]
            if loops:
                self.shape_with_holes(loops, layer)
        return total

    def title_width(self, s, cap, font, track=0.0, kern=None):
        return _title_layout(s, cap, font, track, kern)[3]

    def columns(self, cols, x0, x1, measure, min_gap=0.35):
        """Left edges for columns of text spread across x0..x1. cols is a list
        of columns (each a list of strings); measure(s) gives a string's
        width. Each column is as wide as its widest entry and the spare room
        is shared out as equal gaps. Stops if the table can't fit."""
        widths = [max(measure(s) for s in col) for col in cols]
        gap = (x1 - x0 - sum(widths)) / (len(cols) - 1)
        assert gap >= min_gap, (f"table too wide: {sum(widths):.2f} mm of text "
                                f"in {x1 - x0:.2f} mm")
        xs, x = [], x0
        for w in widths:
            xs.append(x)
            x += w + gap
        return xs

    # -- pixels
    @drawing
    def pixels(self, x0, y0, rows, px, layer=None):
        """Pixel art: one rectangle per run of '#', (x0, y0) top-left."""
        for r, row in enumerate(rows):
            c = 0
            while c < len(row):
                if row[c] != "#":
                    c += 1
                    continue
                start = c
                while c < len(row) and row[c] == "#":
                    c += 1
                self.rect(x0 + start * px, y0 + r * px, x0 + c * px,
                          y0 + (r + 1) * px, layer)

    @drawing
    def pixel_text(self, s, x, y, px=0.2, just="l", gap=1, layer=None):
        """Pixel-font text; y is the top of the letters. Returns the width."""
        rows = pixel_rows(s, gap)
        width = len(rows[0]) * px
        x0 = {"l": x, "c": x - width / 2, "r": x - width}[just]
        self.pixels(x0, y, rows, px, layer)
        return width

    @drawing
    def pixel_label(self, s, x, y, px=0.18, ang=0, layer=None, narrow=False):
        """Pixel-font text centred on (x, y), level (ang 0) or turned to read
        upward (ang 90, like KiCad's 90-degree text)."""
        rows = pixel_rows(s, narrow=narrow)
        w, h = len(rows[0]) * px, 5 * px
        for r, row in enumerate(rows):
            c = 0
            while c < len(row):
                if row[c] != "#":
                    c += 1
                    continue
                start = c
                while c < len(row) and row[c] == "#":
                    c += 1
                # the run as a rectangle relative to the text's centre
                ax, bx = start * px - w / 2, c * px - w / 2
                ay, by = r * px - h / 2, (r + 1) * px - h / 2
                if ang == 90:        # turn a quarter left: (dx, dy) -> (dy, -dx)
                    ax, bx, ay, by = ay, by, -bx, -ax
                self.rect(x + ax, y + ay, x + bx, y + by, layer)
        return w

    def pixel_width(self, s, px=0.18, gap=1, narrow=False):
        return len(pixel_rows(s, gap, narrow)[0]) * px

    # -- the deer
    @drawing
    def place(self, art, x, y):
        """Put a 10 x 10 mm deer mark with its box's top-left at view (x, y)."""
        if self.bottom:
            shapes = deer.add_to_board(self.b, art, self.ox + self.W - x - deer.BOX,
                                       self.oy + y, self.silk, flip=True)
        else:
            shapes = deer.add_to_board(self.b, art, self.ox + x, self.oy + y, self.silk)
        for shape in shapes:
            self._join(shape)

    # -- solder-mask openings (bare metal shows where there is copper)
    @drawing
    def open_disc(self, c, r):
        self.disc(c, r, self.mask)

    @drawing
    def open_poly(self, pts):
        self.poly(pts, self.mask)

    @drawing
    def open_line(self, pts, w):
        self.line(pts, w, self.mask)

    @drawing
    def open_rect(self, x1, y1, x2, y2):
        self.rect(x1, y1, x2, y2, self.mask)


# ------------------------------------------------- shared board content ---
# Panel tabs. In the panel of eight, break-away tabs drill a row of 0.5 mm
# holes 0.25 mm inside each board's edge, each with an opening in the solder
# mask on both sides (build_pcb.py: TABS_LONG, TABS_SHORT, BITE_*). Keep all
# silkscreen at least 0.15 mm from them, that is at least 0.65 mm from the
# edge, over these stretches (view coordinates):
#   top and bottom edges   top side x 10.1-14.9 and 33.1-37.9
#                          bottom side x 10.4-15.2 and 33.4-38.2
#   left and right edges   y 9.0-13.9
# silk_check.py checks every single board against these holes.
# Positions of the functional labels, from art.py. Top side in board
# coordinates (the same as view coordinates there).
TOP_REFS = [("U1", 17.3, 3.95, 0), ("L1", 31.0, 11.43, 0),
            ("C1", 9.75, 5.2, 0), ("C2", 9.75, 10.0, 0), ("C3", 12.6, 2.75, 0),
            ("C4", 22.7, 1.45, 0), ("C5", 22.7, 17.3, 0),
            ("C6", 39.9, 9.88, 90), ("C7", 39.9, 12.98, 90),
            ("C8", 45.0, 9.88, 90), ("C9", 45.0, 12.98, 90),
            ("C10", 4.1, 10.4, 0), ("D1", 4.4, 14.6, 0),
            ("R1", 19.6, 16.11, 90), ("R2", 17.06, 16.11, 90),
            ("R3", 14.52, 16.11, 90), ("R4", 1.65, 17.75, 0),
            ("R5", 11.25, 16.55, 0)]
# pin names: (text, x) per header row; rows at y 1.27 (A) and 21.59 (B)
TOP_PINS_A = [("GND", 1.37), ("VIN", 3.81), ("OUT", 44.45), ("GND", 46.89)]
TOP_PINS_B = [("GND", 1.37), ("VIN", 3.81), ("EN", 6.35),
              ("PG", 41.91), ("OUT", 44.45), ("GND", 46.89)]
# bottom side, view x (seen from below)
BOT_PINS_A = [("GND", 1.27), ("VOUT", 3.81), ("VIN", 44.45), ("GND", 46.99)]
BOT_PINS_B = [("GND", 1.27), ("VOUT", 3.81), ("PG", 6.35),
              ("EN", 41.91), ("VIN", 44.45), ("GND", 46.99)]
# through-hole parts' references on the bottom: (text, view x, y, angle)
BOT_REFS = [("R1", 28.66, 16.1, 90), ("R2", 31.2, 16.1, 90), ("R3", 33.74, 16.1, 90),
            ("C4", 25.56, 5.6, 0), ("C5", 25.56, 13.15, 0), ("C10", 44.16, 9.75, 0),
            ("R4", 43.18, 17.2, 0), ("R5", 37.06, 18.6, 0)]
C10_PLUS_BOT = (45.91, 6.3)     # the "+" beside C10's square pad, bottom view
C10_PLUS_TOP = (2.35, 6.3)
U1_PAD_BOT = (29.66, 5.85, 32.26, 8.95)   # thermal pad's hole, bottom view


def spread_out(items, lo, hi, gap):
    """Slide labels along a row so none run into each other or off the
    board. items: (centre, width) for each label, in order along the row.
    Returns the new centres: each stays where it belongs unless it must move
    to keep inside lo..hi and at least `gap` from its neighbours. Stops if
    the row is too crowded to fit."""
    c = [x for x, _ in items]
    w = [width for _, width in items]
    for i in range(len(c)):                       # push right, from the left
        left = lo if i == 0 else c[i - 1] + w[i - 1] / 2 + gap
        c[i] = max(c[i], left + w[i] / 2)
    for i in reversed(range(len(c))):             # push left, from the right
        right = hi if i == len(c) - 1 else c[i + 1] - w[i + 1] / 2 - gap
        c[i] = min(c[i], right - w[i] / 2)
    for i in range(len(c)):
        assert c[i] - w[i] / 2 >= lo - 1e-9, "row of labels too crowded"
        if i:
            assert (c[i] - w[i] / 2) - (c[i - 1] + w[i - 1] / 2) >= gap - 1e-9, \
                "row of labels too crowded"
    return c


def c10_arc(ink, w=0.12):
    """The electrolytic capacitor's outline on top, open toward the edge
    (its ends stop 0.5 mm clear of the panel's tab holes in that edge)."""
    arc = [(4.1 + 4.0 * math.cos(math.radians(a)), 8.0 + 4.0 * math.sin(math.radians(a)))
           for a in range(-140, 141, 10)]
    ink.line(arc, w)
