"""Parkside 98: late-'90s desktop chrome meets a sunny pixel theme park.

From the theme file (design library, themes/parkside-98.md v1.0.0):
  - windows: a title bar with a close box, a body, a status bar (section 6);
    the output table is a window, the parts list a text field, and each side
    has a status bar along its bottom edge
  - light comes from the top-left (principle 1): the table window's top and
    left inner edges carry a highlight in bare silver, openings in the
    solder mask over the ground plane that show the HASL finish (chrome grey
    is close to solder)
  - hard pixels, square corners, no smoothing (principle 3): a square board,
    and pixel lettering throughout, from kit.PIXEL_FONT
  - readability beats nostalgia (principle 4): the long notes use the plain
    stroke font, the theme's "monospace fallback ... fine for long documents"
  - pool-blue board, pure white lettering (off-white fails contrast on this
    blue), silver pads (sections 4 and 12)
The pixel buck in its marquee of bulbs sits on the back, right of the table
window, like a desktop icon beside an open window. The pixel thumbs-up from
the standard board waves beside HANDMADE on top. On top, the title window is
rolled up to just its title bar: it has to fit between the panel's tab holes
in the board's edge and the inductor's pads.
"""
import deer

from . import content as C
from . import kit

ID = "parkside"
NAME = "Parkside 98"
CORNERS = kit.outline(("square",), ("square",), ("square",), ("square",))
COLORS = dict(mask="#336ECCFF", silk="White", finish="HAL lead-free")
ORDER = dict(mask="Blue", silk="White", finish="HASL lead-free",
             note="pure white lettering: off-white falls below the contrast "
                  "standard on this blue")

PX = 0.17          # small pixel lettering: 0.85 mm letters, 0.17 mm strokes
PXP = 0.16         # pin names: 0.8 mm letters (the board houses' minimum
                   # height) with the narrow G and O, so names 2.54 mm apart
                   # still read as separate words
PXT = 0.2          # title-bar lettering: 1.0 mm letters
PXB = 0.25         # banner lettering: 1.25 mm letters
LINE = 0.18        # window lines, one "pixel" wide
TN = dict(h=0.85, w=0.6, t=0.15)     # the stroke-font fallback for long notes
EDGE = 0.2         # pin names stay this far inside the board's edge
PIN_GAP = 0.3      # ...and at least this far from each other

THUMBS_UP = [r.replace("X", "#") for r in (
    ".....XX....", "....XXX....", "....XXX....", "....XXX....", "...XXXX....",
    "...XXXXXXX.", "XX.XXXXXXXX", "XX.XXXX....", "XX.XXXXXXXX", "XX.XXXXXXXX",
    "XX.XXXX....", "XX.XXXXXXX.", "XX..XXXXXX.")]
# the close box: the font's X inside a one-pixel frame (the font's X has no
# pixels that touch only at a corner, so it prints cleanly)
CLOSE_BOX = ["#######"] + ["#" + r + "#" for r in kit.PIXEL_FONT["X"]] + ["#######"]


def box_outline(k, x1, y1, x2, y2, w=LINE):
    """A one-pixel rectangle: four straight strokes with square corners."""
    k.sharp([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], w, closed=True)


def window(k, x1, y1, x2, y2, title, px=PXT, highlight=True):
    """A window: outline, title bar with a close box, and (optionally) the
    raised-bevel highlight in bare silver along the top and left inside
    edges. y2=None draws the title bar alone (a rolled-up window). Returns
    the y where the body starts (or the title bar's bottom edge)."""
    cb = 7 * px                                   # close box size
    top = y1 + 0.3
    bar = top + cb + 0.3                          # bottom of the title bar
    with k.element("window " + title):            # outline and bar line touch
        box_outline(k, x1, y1, x2, bar if y2 is None else y2)
        if y2 is not None:
            k.sharp([(x1, bar), (x2, bar)], LINE, square_ends=False)
    k.pixels(x2 - 0.3 - cb, top, CLOSE_BOX, px)
    k.pixel_text(title, x1 + 0.4, top + (cb - 5 * px) / 2, px)
    if y2 is None:
        return bar
    body = bar + 0.3
    if highlight:
        k.open_rect(x1 + 0.4, body, x2 - 0.4, body + 0.25)            # top edge
        k.open_rect(x1 + 0.4, body, x1 + 0.65, y2 - 0.4)              # left edge
        body += 0.25 + 0.2
    return body


def status_bar(k, x1, x2, left, right=""):
    """A status bar between x1 and x2 along the bottom edge, with text at
    each end. It stops short of the panel's tab holes in that edge and of
    the resistors' pads above it."""
    y1, y2 = 20.6, 22.0
    box_outline(k, x1, y1, x2, y2)
    k.pixel_text(left, x1 + 0.4, y1 + 0.275, PX)
    if right:
        k.pixel_text(right, x2 - 0.4, y1 + 0.275, PX, just="r")


def pin_row(k, pins, y):
    """A row of pin names under (or over) a header, each centred on its pin
    unless it has to slide to stay on the board or clear of its neighbour."""
    widths = [k.pixel_width(s, PXP, narrow=True) for s, _ in pins]
    xs = kit.spread_out([(x, w) for (_, x), w in zip(pins, widths)],
                        EDGE, k.W - EDGE, PIN_GAP)
    for (s, _), x in zip(pins, xs):
        k.pixel_label(s, x, y, PXP, narrow=True)


def decorate(board, W, H, ox=0.0, oy=0.0):
    top(kit.Ink(board, "top", W, H, ox, oy))
    bottom(kit.Ink(board, "bottom", W, H, ox, oy))


# ------------------------------------------------------------------ top ---
def top(k):
    for s, x, y, a in kit.TOP_REFS:
        k.pixel_label(s, x, y, PX, ang=a)
    pin_row(k, kit.TOP_PINS_A, 3.25)
    pin_row(k, kit.TOP_PINS_B, 20.07)
    k.pixel_label("+", *kit.C10_PLUS_TOP, 0.25)
    kit.c10_arc(k, 0.15)

    # the title window, rolled up to its title bar (no silver here: it's
    # beside the switching node's copper, so the top side stays plain)
    window(k, 24.7, 0.78, 37.4, None, "BUCK 33630")
    # what goes in, under the inductor: between its lower pad and the
    # status bar
    k.pixel_text("IN 3.8-36V  3A", 31.05, 19.25, PX, just="c")

    # maker's mark: the thumbs-up and HANDMADE
    k.pixels(5.5, 0.3, THUMBS_UP, PX)
    k.pixel_text("HANDMADE", 8.2, 0.75, PXT)

    # limits, and a box to write the built voltage in
    k.pixel_text("VIN > VOUT", 37.85, 3.95, PX)
    k.pixel_text("VIN MAX 36V", 37.85, 5.25, PX)
    k.pixel_text("VOUT=", 37.9, 15.65, PX)
    k.rect(37.9, 16.85, 42.9, 19.15)

    # status bar, right of the resistors' pads
    rev = " ".join(C.REV.split()[:2])                 # "REV A"
    status_bar(k, 21.2, 40.6, "READY", f"PARKSIDE 98 {rev}")


# --------------------------------------------------------------- bottom ---
def bottom(k):
    out = lambda pins: [("OUT" if s == "VOUT" else s, x) for s, x in pins]  # noqa: E731
    pin_row(k, out(kit.BOT_PINS_A), 3.0)
    pin_row(k, out(kit.BOT_PINS_B), 20.07)
    for s, x, y, a in kit.BOT_REFS:
        if s == "C10":
            y = 9.5
        k.pixel_label(s, x, y, PX, ang=a)
    k.pixel_label("+", *kit.C10_PLUS_BOT, 0.25)

    # banner along the top edge
    k.pixel_text("BUCK//33630   HACK THE PLANET", 7.6, 0.75, PXB)

    # the pixel buck in its marquee, like an icon beside the window
    k.place(deer.make("parkside-98"), 14.4, 4.4)

    # output table: a window, its bevel lit from the top-left (x1 keeps it
    # clear of the tab holes in the board's side)
    x1, y1, x2, y2 = 0.8, 3.85, 12.7, 15.0
    body = window(k, x1, y1, x2, y2, "VOUT.TXT")
    k.pixel_text("R1 100K", x1 + 1.0, body, PX)
    head = ("VOUT", "R2", "R3", "L1")
    rows = [(v, r2.upper(), r3.upper(), ll.upper()) for v, _r1, r2, r3, ll in C.KIT]
    cols = list(zip(head, *rows))
    xs = k.columns(cols, x1 + 1.0, x2 - 0.4, lambda s: k.pixel_width(s, PX))
    y = body + 1.25
    for x, s in zip(xs, head):
        k.pixel_text(s, x, y, PX)
    for i, row in enumerate(rows):
        for x, s in zip(xs, row):
            k.pixel_text(s, x, y + 1.25 + 1.2 * i, PX)

    # parts: a text field across the bottom of the left half
    x1, y1, x2, y2 = 0.8, 15.4, 24.4, 19.3
    box_outline(k, x1, y1, x2, y2)
    for i, s in enumerate(("C1 C2 10U 50V  C3 220N  C4 100N",
                           "C5 1U  R4 100K  C10 47-100U 50V",
                           "D1 SMBJ24A OPT   12V: R1 220K")):
        k.pixel_text(s, x1 + 0.4, 15.7 + 1.2 * i, PX)

    # exact values: a small window, top right (five rows: it starts just
    # under the banner)
    x1, y1, x2, y2 = 34.9, 2.25, 41.1, 10.35
    body = window(k, x1, y1, x2, y2, "R2", px=PX, highlight=False)
    for i, (label, r2) in enumerate(C.EXACT):
        yy = body + 0.1 + 1.2 * i
        k.pixel_text(label, x1 + 0.4, yy, PX)
        k.pixel_text(r2.upper(), x2 - 0.4, yy, PX, just="r")

    # notes in the fallback stroke font, in a plain field (x2 clear of the
    # tab holes in the board's side)
    x1, y1, x2, y2 = 34.9, 10.85, 47.45, 16.15
    box_outline(k, x1, y1, x2, y2)
    for i, s in enumerate(("1% R2: R1 100k, R3 0R", C.L_SAT, "C6-C9 4x 22u 25V",
                           "24V: 10u 50V, IN>=28V")):
        k.text(s, x1 + 0.4, 11.7 + 1.2 * i, just="l", **TN)

    # thermal pad: SOLDER above it, a pixel bracket, U1 PAD below
    px1, py1, px2, py2 = kit.U1_PAD_BOT
    k.sharp([(px1 - 0.35, py1 + 0.3), (px1 - 0.35, py2 + 0.35), (px2 + 0.35, py2 + 0.35),
             (px2 + 0.35, py1 + 0.3)], LINE)
    k.pixel_text("SOLDER", (px1 + px2) / 2, 4.45, PX, just="c")
    k.pixel_text("U1 PAD", (px1 + px2) / 2, 9.65, PX, just="c")

    # status bar, left of the resistors' pads
    status_bar(k, 7.6, 27.1, "3.8-36V IN  3A  VIN > VOUT")
