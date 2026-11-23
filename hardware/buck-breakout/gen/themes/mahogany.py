"""Mahogany Lounge: a mid-century den of bottle green, cream and brass.

From the theme file (design library, themes/mahogany-lounge.md v1.0.0):
  - softened rectangles: the board's corners are rounded, and so are the
    frames around the table and notes (section 6)
  - thin, precise line weight: fine rules under titles and between parts
    of the table, nothing heavy (section 6)
  - original mid-century ornament: atomic starbursts and a boomerang
    (sections 6 and 9)
  - "brass is jewelry, in small doses" (principle 3): the boomerang is real
    gold, a mask opening over the ground plane showing the ENIG finish
  - bottle-green board, cream lettering, gold pads that echo brass (sections
    4 and 12); titles in Jost, uppercase and widely spaced (section 5)
The figurine buck stands on the back, right of the table, over its brass
boomerang like a piece on a sideboard.
"""
import deer

from . import content as C
from . import kit

ID = "mahogany"
NAME = "Mahogany Lounge"
CORNERS = kit.outline(*[("round", 1.5)] * 4)
COLORS = dict(mask="#1F3D2BFF", silk="White", finish="ENIG")
ORDER = dict(mask="Green", silk="White", finish="ENIG",
             note="choose the darkest green the board house offers")

T = dict(h=0.85, w=0.66, t=0.15)     # labels
TC = dict(h=0.85, w=0.62, t=0.15)    # table cells
TN = dict(h=0.85, w=0.6, t=0.15)     # long lines
PITCH = 1.2
FONT = "jost-600"
FRAME = 0.15                         # fine line weight


def boomerang(k, cx, cy, arms=(3.1, 2.4), width=0.95, droop=1.0):
    """A brass boomerang: two tapering arms of unequal length bent at
    (cx, cy), drawn as an opening in the solder mask so the gold finish
    shows. Each arm starts 0.7 mm past the elbow, so the two overlap there
    and the factory makes them one shape."""
    for side, arm in zip((-1, 1), arms):
        k.open_poly(deer.leaf((cx - side * 0.7, cy - 0.2),
                              (cx + side * arm, cy + droop), width, r_end=0.2))


def decorate(board, W, H, ox=0.0, oy=0.0):
    top(kit.Ink(board, "top", W, H, ox, oy))
    bottom(kit.Ink(board, "bottom", W, H, ox, oy))


# ------------------------------------------------------------------ top ---
def top(k):
    for s, x, y, a in kit.TOP_REFS:
        k.text(s, x, y, just="c", ang=a, **T)
    for s, x in kit.TOP_PINS_A:
        k.text(s, x, 3.25, just="c", h=0.85, w=0.6, t=0.15)
    for s, x in kit.TOP_PINS_B:      # 0.8 mm: it sits between R4's pads and the header's
        k.text(s, x, 20.07, just="c", h=0.8, w=0.6, t=0.15)
    k.text("+", *kit.C10_PLUS_TOP, h=1.0, w=1.0, t=0.15, just="c")
    kit.c10_arc(k, FRAME)

    # title above the inductor: spaced capitals over a fine rule
    # (between the panel's tab holes in the top edge and L1's pads)
    k.title("BUCK 33630", 31.05, 2.05, 1.25, FONT, just="c", track=0.16)
    k.line([(25.4, 2.33), (36.7, 2.33)], FRAME)
    k.text("STEP-DOWN  3.8-36V  3A", 31.05, 3.2, just="c", **TN)

    # maker's mark: a starburst and HANDMADE
    k.starburst((7.0, 1.4), 1.05, dot=0.25)
    k.title("HANDMADE", 8.7, 1.95, 1.1, FONT, just="l", track=0.2)

    # limits, and a rounded box to write the built voltage in
    k.spaced("VIN > VOUT", 37.85, 4.65, track=0.06, **TN)
    k.spaced("VIN MAX 36V", 37.85, 4.65 + PITCH, track=0.06, **TN)
    k.spaced("VOUT =", 37.9, 16.05, track=0.06, **TN)
    k.round_fill(37.9, 16.85, 42.9, 19.35, 0.6)

    # along the bottom edge: fine rules and the theme's name
    w = k.spaced(f"MAHOGANY LOUNGE  {C.REV}", 24.15, 21.6, track=0.02, just="c", **TN)
    k.line([(8.3, 21.6), (24.15 - w / 2 - 0.6, 21.6)], FRAME)
    k.line([(24.15 + w / 2 + 0.6, 21.6), (40.0, 21.6)], FRAME)


# --------------------------------------------------------------- bottom ---
def bottom(k):
    for s, x in kit.BOT_PINS_A:
        k.text(s, x, 3.0, just="c", h=0.85, w=0.6, t=0.15)
    for s, x in kit.BOT_PINS_B:      # 0.8 mm: it sits between R4's pads and the header's
        k.text(s, x, 20.07, just="c", h=0.8, w=0.6, t=0.15)
    for s, x, y, a in kit.BOT_REFS:
        if s == "C10":
            y = 9.5
        k.text(s, x, y, just="c", ang=a, **T)
    k.text("+", *kit.C10_PLUS_BOT, h=1.0, w=1.0, t=0.15, just="c")

    # title band: name, a small starburst, the limits
    w = k.title("BUCK 33630", 6.0, 2.05, 1.25, FONT, just="l", track=0.14)
    k.starburst((6.0 + w + 1.15, 1.45), 0.75, n=4)
    k.spaced("3.8-36V IN   3A   KEEP VIN > VOUT", 6.0 + w + 2.3, 1.45, track=0.03, **TN)

    # the figurine, standing over its brass boomerang, HANDMADE beneath
    k.place(deer.make("mahogany-lounge"), 14.35, 4.3)
    boomerang(k, 19.35, 15.3)
    k.title("HANDMADE", 19.35, 19.0, 1.1, FONT, just="c", track=0.24)

    # output table in a rounded frame
    x1, y1, x2, y2 = 0.8, 3.9, 13.75, 14.5      # x1: clear of the side tab holes
    k.round_frame(x1, y1, x2, y2, 0.9, FRAME)
    k.spaced("VOUT SELECT", (x1 + x2) / 2, 4.9, track=0.12, just="c", **TN)
    k.line([(x1 + 0.9, 5.65), (x2 - 0.9, 5.65)], FRAME)
    cols = list(zip(C.KIT_HEAD, *C.KIT))
    xs = k.columns(cols, x1 + 0.45, x2 - 0.45, lambda s: k.text_width(s, **TC))
    for x, s in zip(xs, C.KIT_HEAD):
        k.text(s, x, 6.5, just="l", **TC)
    for i, row in enumerate(C.KIT):
        for x, s in zip(xs, row):
            k.text(s, x, 7.75 + 1.3 * i, just="l", **TC)

    # parts list under the table, no frame
    for i, s in enumerate(("C1 C2 10u 50V  C3 220n", "C4 100n C5 1u R4 100k",
                           "C10 47-100u D1 SMBJ24A")):
        k.text(s, 0.8, 15.55 + PITCH * i, just="l", **TN)

    # 1 % values, top right, in a rounded frame
    x1, y1, x2, y2 = 34.95, 2.55, 41.05, 10.3
    k.round_frame(x1, y1, x2, y2, 0.7, FRAME)
    k.spaced("1% R2*", (x1 + x2) / 2, 3.5, track=0.08, just="c", **TC)
    for i, (label, r2) in enumerate(C.EXACT):
        y = 4.75 + PITCH * i
        k.text(label, x1 + 0.5, y, just="l", **TC)
        k.text(r2, x2 - 0.5, y, just="r", **TC)

    # notes, lower right
    x1, y1, x2, y2 = 34.95, 10.75, 47.55, 16.15
    k.round_frame(x1, y1, x2, y2, 0.7, FRAME)
    for i, s in enumerate(("R2*: R1 100k, R3 0R", C.L_SAT, "C6-C9 4x 22u 25V",
                           "24V: 10u 50V, IN>=28V")):
        k.text(s, x1 + 0.5, 11.65 + PITCH * i, just="l", **TN)

    # thermal pad call-out: a soft bracket and a spaced label
    px1, py1, px2, py2 = kit.U1_PAD_BOT
    with k.element("thermal bracket"):
        k.line([(px1 - 0.4, py1 - 0.1), (px1 - 0.4, py2 - 0.2)], FRAME)
        k.line([(px1 - 0.4, py2 - 0.2), (px1 - 0.35, py2 + 0.05), (px1 - 0.2, py2 + 0.25),
                (px1 + 0.05, py2 + 0.35), (px2 - 0.05, py2 + 0.35), (px2 + 0.2, py2 + 0.25),
                (px2 + 0.35, py2 + 0.05), (px2 + 0.4, py2 - 0.2)], FRAME)
        k.line([(px2 + 0.4, py2 - 0.2), (px2 + 0.4, py1 - 0.1)], FRAME)
    k.text("SOLDER U1 PAD", 30.6, 10.2, just="c", **TN)

    # bottom edge: a fine rule with a starburst at its centre
    k.line([(8.2, 21.95), (23.0, 21.95)], FRAME)
    k.starburst((24.15, 21.95), 0.62, n=4)
    k.line([(25.3, 21.95), (40.3, 21.95)], FRAME)
