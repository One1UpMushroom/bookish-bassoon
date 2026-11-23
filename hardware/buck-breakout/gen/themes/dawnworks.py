"""Dawnworks: cybernetic gadgetry for a hopeful dawn.

From the theme file (design library, themes/dawnworks.md v2.0.0):
  - "The circuit is the face", "structure like a PCB": information sits in
    modules with two diagonal corners cut at 45 degrees (top-left and
    bottom-right), joined by traces that turn only at 45/90 degrees and end
    in vias; labels read like silkscreen reference designators (section 6)
  - pin rows: small gold dots spaced like a pin header (section 6), made in
    real gold here: openings in the solder mask over the ground plane, so the
    ENIG finish shows
  - dawn light: a gold sun rising under the circuit buck
  - moss board, parchment lettering, gold pads (sections 4 and 11); the
    outline cuts the same two corners as the modules
  - headings in Chakra Petch (section 5); small labels in KiCad's stroke font
    so they stay printable
The deer sits on the back, left of the output table: it is a module too.
"""
import math

import deer

from . import content as C
from . import kit

ID = "dawnworks"
NAME = "Dawnworks"
CORNERS = kit.outline(tl=("chamfer", 0.9), tr=("square",), br=("chamfer", 0.9),
                      bl=("square",))
COLORS = dict(mask="#4F6D3AFF", silk="White", finish="ENIG")
ORDER = dict(mask="Green", silk="White", finish="ENIG",
             note="ask for a dark or olive green if the board house offers one")

T = dict(h=0.85, w=0.66, t=0.15)     # labels
TC = dict(h=0.85, w=0.62, t=0.15)    # table cells
TN = dict(h=0.85, w=0.6, t=0.15)     # long lines (KiCad needs w >= 4 x t)
PITCH = 1.2                          # line spacing: 0.15 mm between strokes
TRACE = 0.2                          # silkscreen "trace" width
VR, VW = 0.3, 0.15                   # silkscreen via ring: radius, width
FONT = "chakra-600"
KERN = {"K/": 0.12}                  # Chakra sets the slash 0.06 mm from the K


def via(ink, x, y):
    ink.ring((x, y), VR, VW)


def module(ink, x1, y1, x2, y2, cut=0.9):
    """A Dawnworks module outline: top-left and bottom-right corners cut."""
    ink.cut_frame(x1, y1, x2, y2, cut, 0.15, corners="tl br")


def trace(ink, pts, end_vias=True):
    """A silkscreen trace with a via at each end: one element, since the
    trace runs into its vias."""
    with ink.element("trace"):
        ink.line(pts, TRACE)
        if end_vias:
            via(ink, *pts[0])
            via(ink, *pts[-1])


def sun(ink, cx, cy, r):
    """Gold half-sun (bare ENIG through a mask opening) on a silkscreen
    horizon, with silkscreen rays. (cx, cy) is the middle of its flat edge."""
    with ink.element("sun"):
        ink.open_poly([(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
                       for a in range(180, 361, 10)])
        ink.line([(cx - r - 1.6, cy + 0.3), (cx + r + 1.6, cy + 0.3)], 0.15)
        for a in (200, 235, 270, 305, 340):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            ink.line([(cx + (r + 0.35) * ca, cy + (r + 0.35) * sa),
                      (cx + (r + 0.9) * ca, cy + (r + 0.9) * sa)], 0.15)


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
    kit.c10_arc(k, 0.15)

    # title block above the inductor, with a trace and two vias under it
    # (it sits between the panel's tab holes in the top edge and L1's pads)
    k.title("BUCK//33630", 31.05, 2.0, 1.3, FONT, just="c", track=0.04, kern=KERN)
    k.text("3.8-36V IN // 3A SYNC", 31.05, 2.74, just="c", **TN)
    trace(k, [(25.1, 3.72), (37.0, 3.72)])

    # maker's mark: a gold sun rising, HANDMADE, a trace running off to a via
    sun(k, 7.15, 1.95, 0.65)
    k.text("HANDMADE", 9.75, 1.5, just="l", **T)
    with k.element("trace to via"):
        trace(k, [(15.85, 1.5), (16.9, 1.5)], end_vias=False)
        via(k, 17.25, 1.5)

    # limits and the box to write the built voltage in
    k.text("VIN > VOUT", 37.85, 4.4, just="l", **TN)
    k.text("VIN MAX 36V", 37.85, 4.4 + PITCH, just="l", **TN)
    k.text("VOUT =", 37.9, 16.05, just="l", **T)
    c = 0.6
    k.poly([(37.9 + c, 16.85), (42.9, 16.85), (42.9, 19.35 - c), (42.9 - c, 19.35),
            (37.9, 19.35), (37.9, 16.85 + c)])

    # bottom edge: a bus with the theme's name riding on it
    trace(k, [(8.05, 21.65), (13.6, 21.65)])
    k.text(f"DAWNWORKS  {C.REV}", 24.15, 21.65, just="c", **TN)
    trace(k, [(34.7, 21.65), (40.25, 21.65)])


# --------------------------------------------------------------- bottom ---
def bottom(k):
    for s, x in kit.BOT_PINS_A:
        k.text(s, x, 3.0, just="c", h=0.85, w=0.6, t=0.15)
    for s, x in kit.BOT_PINS_B:      # 0.8 mm: it sits between R4's pads and the header's
        k.text(s, x, 20.07, just="c", h=0.8, w=0.6, t=0.15)
    for s, x, y, a in kit.BOT_REFS:
        if s == "C10":
            y = 9.5                      # clear of the notes module below
        k.text(s, x, y, just="c", ang=a, **T)
    k.text("+", *kit.C10_PLUS_BOT, h=1.0, w=1.0, t=0.15, just="c")

    # title band along the top edge
    w = k.title("BUCK//33630", 7.8, 2.05, 1.3, FONT, just="l", track=0.04, kern=KERN)
    k.text("3.8-36V IN   3A SYNC   KEEP VIN > VOUT", 7.8 + w + 1.0, 1.45,
           just="l", **TN)

    # the circuit buck, and the gold sun rising beneath it
    k.place(deer.make("dawnworks"), 0.7, 5.0)
    sun(k, 5.7, 18.95, 1.25)

    # output table: one module
    x1, y1, x2, y2 = 11.3, 3.4, 24.35, 14.5
    module(k, x1, y1, x2, y2)
    cols = list(zip(C.KIT_HEAD, *C.KIT))
    xs = k.columns(cols, x1 + 0.45, x2 - 0.4, lambda s: k.text_width(s, **TC))
    for x, s in zip(xs, C.KIT_HEAD):
        k.text(s, x, 4.75, just="l", **TC)
    k.line([(x1 + 0.45, 5.5), (x2 - 0.4, 5.5)], TRACE)
    for i, row in enumerate(C.KIT):
        for x, s in zip(xs, row):
            k.text(s, x, 6.35 + 1.35 * i, just="l", **TC)
    k.line([(x1 + 0.45, 12.75), (x2 - 1.3, 12.75)], TRACE)
    k.text("VOUT SELECT", x1 + 0.45, 13.65, just="l", **TN)

    # parts module under the table, wired to the bus along the bottom edge
    # (one element: the traces run into the module and the bus)
    x1, y1, x2, y2 = 11.3, 15.05, 24.35, 20.75
    with k.element("parts module on the bus"):
        module(k, x1, y1, x2, y2, cut=0.7)
        k.line([(7.7, 22.05), (40.65, 22.05)], 0.15)
        for x in (12.7, 22.86):
            k.line([(x, 20.8), (x, 22.0)], TRACE)
    for i, s in enumerate(("C1 C2 10u 50V", "C3 220n  C4 100n", "C5 1u  R4 100k",
                           "C10 47-100u  D1 OPT")):
        k.text(s, x1 + 0.45, 16.0 + PITCH * i, just="l", **TN)

    # exact-value module, top right, and the notes module below it, joined
    # by a short trace (one element)
    with k.element("1% and notes modules"):
        module(k, 34.95, 2.55, 41.05, 10.3, cut=0.5)
        module(k, 34.95, 10.75, 47.55, 16.15, cut=0.7)
        k.line([(38.0, 10.35), (38.0, 10.7)], TRACE)
    x1, y1, x2, y2 = 34.95, 2.55, 41.05, 10.3
    k.text("1% R2*", (x1 + x2) / 2, 3.45, just="c", **TC)
    for i, (label, r2) in enumerate(C.EXACT):
        y = 4.75 + PITCH * i
        k.text(label, x1 + 0.45, y, just="l", **TC)
        k.text(r2, x2 - 0.65, y, just="r", **TC)

    # notes, lower right
    x1, y1, x2, y2 = 34.95, 10.75, 47.55, 16.15
    for i, s in enumerate(("R2*: R1 100k, R3 0R", C.L_SAT, "C6-C9 4x 22u 25V",
                           "24V: 10u 50V, IN>=28V")):
        k.text(s, x1 + 0.45, 11.65 + PITCH * i, just="l", **TN)

    # thermal pad call-out: a bracket with one cut corner, and a label
    px1, py1, px2, py2 = kit.U1_PAD_BOT
    k.sharp([(px1 - 0.4, py1 - 0.1), (px1 - 0.4, py2 + 0.35), (px2 + 0.1, py2 + 0.35),
             (px2 + 0.4, py2 + 0.05), (px2 + 0.4, py1 - 0.1)], 0.15)
    k.text("SOLDER U1 PAD", (px1 + px2) / 2, 10.2, just="c", **TN)

    # gold pin row along the bottom edge, just above the silkscreen bus
    # (drawn with the parts module); the module's traces thread between the
    # dots
    for i in range(13):
        k.open_disc((8.89 + 2.54 * i, 21.4), 0.3)
