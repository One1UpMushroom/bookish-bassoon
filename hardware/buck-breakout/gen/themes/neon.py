"""Neon Noir Chartreuse: one acid-green light in a rain-dark city.

From the theme file (design library, themes/neon-noir-chartreuse.md v1.0.0):
  - hard geometry: sharp corners and 45-degree cut corners, the theme's
    signature, on the board outline and on every frame (section 6)
  - thin lines and grids, like signage: the output table is a departure
    board with fine scanlines between rows; a strip of ticks runs along the
    bottom edge like a scanline overlay (sections 6 and 7)
  - signage type: tall, narrow capitals; titles in Oswald, small text in a
    condensed stroke font (section 5)
  - light is the accent, never the field: the board stays mostly dark, with
    no bare-metal decoration; chartreuse itself belongs to an LED or the
    enclosure, as the theme treats it as light (principle 1)
  - black board, white lettering, gold pads (section 11)
The neon buck hangs on the back like a sign, left of the departure board,
with HACK THE PLANET underneath.
"""
import deer

from . import content as C
from . import kit

ID = "neon"
NAME = "Neon Noir Chartreuse"
CORNERS = kit.outline(*[("chamfer", 0.9)] * 4)
COLORS = dict(mask="Black", silk="White", finish="ENIG")
ORDER = dict(mask="Black (matte black if offered)", silk="White", finish="ENIG",
             note="black mask needs a slightly wider mask dam at some board "
                  "houses (JLCPCB: 0.13 mm); this board's pads are well apart")

T = dict(h=0.85, w=0.6, t=0.15)      # condensed labels: tall and narrow
TC = dict(h=0.85, w=0.6, t=0.15)     # (0.85 mm: 0.95 crowded the pads beside them)
TS = dict(h=0.85, w=0.6, t=0.15)     # stacked lists: 0.15 mm between lines
PITCH = 1.3
FONT = "oswald-600"
SOLID = {"/": 0.19}    # Oswald's slash is 0.135 mm at this size: redraw it bolder
W_LINE = 0.15                        # thin lines


def frame(k, x1, y1, x2, y2, cut=0.6):
    k.cut_frame(x1, y1, x2, y2, cut, W_LINE)


def ticks(k, x1, x2, y, length=0.7, pitch=0.6):
    """A strip of short upright ticks, like a scanline overlay."""
    n = int((x2 - x1) / pitch) + 1
    with k.element("ticks"):                 # one strip, one element
        for i in range(n):
            x = x1 + i * pitch
            k.sharp([(x, y - length / 2), (x, y + length / 2)], W_LINE, square_ends=False)


def decorate(board, W, H, ox=0.0, oy=0.0):
    top(kit.Ink(board, "top", W, H, ox, oy))
    bottom(kit.Ink(board, "bottom", W, H, ox, oy))


# ------------------------------------------------------------------ top ---
def top(k):
    for s, x, y, a in kit.TOP_REFS:
        k.text(s, x, y, just="c", ang=a, **T)
    for s, x in kit.TOP_PINS_A:
        k.text(s, x, 3.25, just="c", **T)
    for s, x in kit.TOP_PINS_B:      # 0.8 mm: it sits between R4's pads and the header's
        k.text(s, x, 20.07, just="c", h=0.8, w=0.6, t=0.15)
    k.text("+", *kit.C10_PLUS_TOP, h=1.0, w=1.0, t=0.15, just="c")
    kit.c10_arc(k, W_LINE)

    # title as a sign: tall capitals in a cut-corner plate
    # (between the panel's tab holes in the top edge and L1's pads)
    # (KiCad's "/" dips below the line, so the subtitle has none: L1 is close)
    frame(k, 25.0, 0.75, 37.1, 2.55, cut=0.6)
    k.title("BUCK//33630", 31.05, 2.30, 1.3, FONT, just="c", track=0.14, solid=SOLID)
    k.text("3.8-36V IN  3A SYNC", 31.05, 3.32, just="c", **TS)

    # top left: three signage slashes and HANDMADE
    with k.element("slashes"):
        for i in range(3):
            x = 5.7 + 0.75 * i
            k.sharp([(x, 2.03), (x + 0.54, 0.68)], 0.2, square_ends=False)
    # 1.35 mm: big enough that the holes in the A's stay open, small enough
    # to fit between the tab holes above and the C3 label below
    k.title("HANDMADE", 8.4, 2.03, 1.35, FONT, just="l", track=0.16)

    # limits; cut-corner box to write the built voltage in
    k.text("VIN > VOUT", 37.85, 4.45, just="l", **T)
    k.text("VIN MAX 36V", 37.85, 4.45 + PITCH, just="l", **T)
    k.text("VOUT =", 37.9, 16.0, just="l", **T)
    c = 0.5
    k.poly([(37.9 + c, 16.85), (42.9 - c, 16.85), (42.9, 16.85 + c), (42.9, 19.15 - c),
            (42.9 - c, 19.15), (37.9 + c, 19.15), (37.9, 19.15 - c), (37.9, 16.85 + c)])

    # bottom edge: tick strips either side of the theme's name
    w = k.text_width(f"NEON NOIR  {C.REV}", **T)
    k.text(f"NEON NOIR  {C.REV}", 24.15, 21.65, just="c", **T)
    ticks(k, 8.3, 24.15 - w / 2 - 0.7, 21.65)
    ticks(k, 24.15 + w / 2 + 0.7, 40.1, 21.65)


# --------------------------------------------------------------- bottom ---
def bottom(k):
    for s, x in kit.BOT_PINS_A:
        k.text(s, x, 3.0, just="c", **T)
    for s, x in kit.BOT_PINS_B:      # 0.8 mm: it sits between R4's pads and the header's
        k.text(s, x, 20.07, just="c", h=0.8, w=0.6, t=0.15)
    for s, x, y, a in kit.BOT_REFS:
        if s == "C10":
            y = 9.5
        k.text(s, x, y, just="c", ang=a, **T)
    k.text("+", *kit.C10_PLUS_BOT, h=1.0, w=1.0, t=0.15, just="c")

    # title band
    w = k.title("BUCK//33630", 8.0, 2.1, 1.3, FONT, just="l", track=0.12, solid=SOLID)
    k.text("3.8-36V IN   3A SYNC   KEEP VIN > VOUT", 8.0 + w + 1.0, 1.45, just="l", **T)

    # the neon buck sign, with a fine rule and HACK THE PLANET beneath
    k.place(deer.make("neon-noir-chartreuse"), 0.7, 4.85)
    k.sharp([(1.0, 16.3), (10.8, 16.3)], W_LINE, square_ends=False)
    k.title("HACK THE PLANET", 12.4, 18.9, 1.45, FONT, just="c", track=0.16)

    # departure board: header, then rows split by fine scanlines, each line
    # exactly between two rows (0.15 mm clear of the letters either side)
    x1, y1, x2, y2 = 11.3, 3.3, 24.35, 14.7
    with k.element("departure board"):    # the frame and its two full rules
        frame(k, x1, y1, x2, y2, cut=0.5)
        k.sharp([(x1, 5.0), (x2, 5.0)], W_LINE, square_ends=False)
        k.sharp([(x1, 6.55), (x2, 6.55)], W_LINE, square_ends=False)
    k.text("VOUT SELECT", (x1 + x2) / 2, 4.15, just="c", **T)
    cols = list(zip(C.KIT_HEAD, *C.KIT))
    xs = k.columns(cols, x1 + 0.6, x2 - 0.45, lambda s: k.text_width(s, **TS))
    for x, s in zip(xs, C.KIT_HEAD):
        k.text(s, x, 5.8, just="l", **TS)
    for i, row in enumerate(C.KIT):
        y = 7.35 + 1.65 * i
        for x, s in zip(xs, row):
            k.text(s, x, y, just="l", **TS)
        if i < len(C.KIT) - 1:     # digits stand a little taller: line sits low
            k.sharp([(x1 + 0.45, y + 0.8), (x2 - 0.45, y + 0.8)], W_LINE,
                    square_ends=False)

    # parts, plain, right-aligned under the departure board
    for i, s in enumerate(("C1 C2 10u 50V  C3 220n", "C4 100n C5 1u R4 100k")):
        k.text(s, 24.3, 15.5 + 1.2 * i, just="r", **TS)
    k.text("C10 47-100u  D1 SMBJ24A OPT", 24.3, 20.05, just="r", **TS)

    # 1 % values and notes, right side
    x1, y1, x2, y2 = 34.95, 2.55, 41.05, 10.3
    frame(k, x1, y1, x2, y2, cut=0.5)
    k.text("1% R2*", (x1 + x2) / 2, 3.45, just="c", **TS)
    for i, (label, r2) in enumerate(C.EXACT):
        y = 4.75 + 1.2 * i
        k.text(label, x1 + 0.45, y, just="l", **TS)
        k.text(r2, x2 - 0.55, y, just="r", **TS)
    x1, y1, x2, y2 = 34.95, 10.75, 47.55, 16.15
    frame(k, x1, y1, x2, y2, cut=0.5)
    for i, s in enumerate(("R2*: R1 100k, R3 0R", C.L_SAT, "C6-C9 4x 22u 25V",
                           "24V: 10u 50V, IN>=28V")):
        k.text(s, x1 + 0.45, 11.65 + 1.2 * i, just="l", **TS)

    # thermal pad call-out: a bracket with cut corners
    px1, py1, px2, py2 = kit.U1_PAD_BOT
    k.sharp([(px1 - 0.4, py1 - 0.1), (px1 - 0.4, py2 - 0.1), (px1 - 0.05, py2 + 0.35),
             (px2 + 0.05, py2 + 0.35), (px2 + 0.4, py2 - 0.1), (px2 + 0.4, py1 - 0.1)],
            W_LINE, square_ends=False)
    k.text("SOLDER U1 PAD", 30.6, 10.25, just="c", **T)

    # bottom edge: a long scanline strip
    ticks(k, 8.3, 40.1, 21.65)
