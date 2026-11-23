#!/usr/bin/env python3
"""
Render the buck breakout in any set of board colours, to preview a look
before ordering boards.

    python3 gen/theme_render.py looks.json out_dir [--zoom 12] [--board file.kicad_pcb]

What it makes: for every look in looks.json, two pictures of the single board,
<id>-top.png (seen from above) and <id>-bottom.png (seen from below). The
background and the drilled holes are transparent, so a web page can show the
board on any backdrop.

looks.json is a list. Each entry describes one look:

    [
      {
        "id": "dawnworks",     # short name, used for the file names
        "mask": "#4F6D3A",     # solder-mask colour (the board's main colour)
        "silk": "#F4EBD0",     # silkscreen colour (the printed lettering and art)
        "finish": "enig",      # exposed metal: "enig" gold, "hasl" silver,
                               #   "osp" bare copper, or any "#hex" colour
        "sheen": "gloss"       # "gloss", "satin" or "matte": how much the
                               #   mask catches the light
      }
    ]

How it works, in three steps:
  1. KiCad draws each layer of the real board file (copper, solder-mask
     openings, silkscreen, outline) as a black picture on a clear background.
  2. Each picture becomes a stencil: a grid of numbers from 0 (no ink here)
     to 1 (ink here), one number per pixel.
  3. The stencils are painted in the look's colours, in the order a factory
     builds a board: mask over the copper, then the bare metal pads, then
     the silkscreen ink on top.

The colours are screen stand-ins. A real board's mask and ink colours come
from the factory, so compare them with the factory's photos or a sample
board before deciding. Needs KiCad 7 (kicad-cli), librsvg (rsvg-convert),
numpy and Pillow.
"""
import argparse
import json
import os
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, "..", "kicad", "buck33630.kicad_pcb")

# Screen stand-ins for the metal finishes. These are approximate values chosen
# for previews, not measurements of real boards.
FINISHES = {
    "enig": "#D3AF63",   # ENIG: a thin layer of gold over nickel; pale gold
    "hasl": "#C8CCD0",   # HASL: solder melted onto the pads; silvery
    "osp":  "#C67A48",   # OSP: bare copper under a clear protective film
}
FR4 = "#BCAD7E"          # bare board material (glass fibre and resin)

# How strongly the mask brightens toward the top-left, as if lit from there.
# 0.035 means 3.5 % brighter at the top-left corner and 3.5 % darker at the
# bottom-right one. Matte mask scatters light evenly, so it gets none.
SHEEN = {"gloss": 0.035, "satin": 0.018, "matte": 0.0}


# ---------------------------------------------------------------- colours ---
# Colours are handled as three numbers from 0 to 1: red, green, blue.
# To make a colour "a bit darker" in a way that looks even to the eye, we
# convert it to OKLab, a colour space where the first number is perceived
# lightness, change that number, and convert back.

def hex_to_rgb(hex_color):
    """'#4F6D3A' -> numpy array [0.31, 0.43, 0.23]."""
    h = hex_color.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255


def to_linear(c):
    # Screen values are stored "gamma encoded"; this undoes that, giving
    # numbers proportional to the actual amount of light.
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_screen(c):
    # The reverse of to_linear, clipped to the 0..1 range a screen can show.
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


# The two fixed matrices that define OKLab (from Björn Ottosson, its author).
M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
               [0.2119034982, 0.6806995451, 0.1073969566],
               [0.0883024619, 0.2817188376, 0.6299787005]])
M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
               [1.9779984951, -2.4285922050, 0.4505937099],
               [0.0259040371, 0.7827717662, -0.8086757660]])


def to_oklab(rgb):
    """Red/green/blue -> [lightness, green-red axis, blue-yellow axis]."""
    return M2 @ np.cbrt(M1 @ to_linear(rgb))


def from_oklab(lab):
    return to_screen(np.linalg.inv(M1) @ (np.linalg.inv(M2) @ lab) ** 3)


def mask_shades(hex_color):
    """Return the mask colour twice: over copper, and over bare board.

    Most of this board's surface has copper under the mask, so the theme
    colour is used there unchanged. Where the mask lies on bare board
    material (the thin gaps around traces and pads) it looks darker and a
    little duller. That difference is what lets you faintly see the hidden
    copper traces on a real board. Very dark masks (black) hide them more,
    so the step shrinks for dark colours."""
    over_copper = hex_to_rgb(hex_color)
    lab = to_oklab(over_copper)
    step = 0.07 * min(1.0, max(0.4, lab[0] / 0.45))
    bare = lab.copy()
    bare[0] -= step          # darker
    bare[1:] *= 0.85         # slightly less saturated
    return over_copper, from_oklab(bare)


# --------------------------------------------------------------- stencils ---

def draw_layer(layer, mirror, zoom, tmp, board=BOARD):
    """Have KiCad draw one board layer, then turn the drawing into stencils.

    Returns two arrays the size of the picture: where KiCad drew in black
    (the layer's shapes) and where it drew in white. KiCad draws drilled
    holes in white on top of copper layers, which is how we find the holes."""
    svg = os.path.join(tmp, layer + ("-mirrored" if mirror else "") + ".svg")
    png = svg[:-4] + ".png"
    cmd = ["kicad-cli", "pcb", "export", "svg", board, "-o", svg, "-l", layer,
           "--black-and-white",        # plain black shapes, no colour theme
           "--page-size-mode", "2",    # crop the picture to the board
           "--exclude-drawing-sheet"]  # no title block or frame
    if mirror:
        cmd.append("--mirror")         # flip left-right: the board seen from below
    subprocess.run(cmd, check=True, capture_output=True)
    # rsvg-convert turns the drawing into pixels; -z is the zoom factor.
    # With no background colour the empty parts stay transparent.
    subprocess.run(["rsvg-convert", "-z", str(zoom), svg, "-o", png], check=True)
    px = np.asarray(Image.open(png).convert("RGBA"), np.float32) / 255
    alpha = px[..., 3]                 # how solid each pixel is (0 = clear)
    light = px[..., :3].mean(axis=2)   # 0 for black ink, 1 for white ink
    return alpha * (1 - light), alpha * light


def grow(stencil, pixels):
    """Make every shape in a stencil `pixels` wider on all sides."""
    img = Image.fromarray(np.uint8(np.clip(stencil, 0, 1) * 255))
    return np.asarray(img.filter(ImageFilter.MaxFilter(2 * pixels + 1)), np.float32) / 255


def shrink(stencil, pixels):
    """Make every shape in a stencil `pixels` narrower on all sides."""
    img = Image.fromarray(np.uint8(np.clip(stencil, 0, 1) * 255))
    return np.asarray(img.filter(ImageFilter.MinFilter(2 * pixels + 1)), np.float32) / 255


def fill_outline(outline):
    """Turn the board outline (a thin closed line) into a solid board shape.

    Imagine pouring paint into the empty space outside the line: everything
    the paint can't reach is the board."""
    h, w = outline.shape
    line = Image.fromarray(np.uint8(outline > 0.25) * 255)
    canvas = Image.new("L", (w + 4, h + 4), 0)   # a 2-pixel clear border all
    canvas.paste(line, (2, 2))                    # round joins up the outside
    ImageDraw.floodfill(canvas, (0, 0), 128)      # pour from the top-left corner
    inside = np.asarray(canvas)[2:-2, 2:-2] != 128
    # The outline line has some width; trim back to its centre, which is the
    # real edge, then soften the edge by about a pixel so it isn't jagged.
    shape = shrink(np.float32(inside), 2)
    shape = Image.fromarray(np.uint8(shape * 255)).filter(ImageFilter.GaussianBlur(0.7))
    return np.asarray(shape, np.float32) / 255


def side_stencils(side, zoom, tmp, board=BOARD):
    """All the stencils for one side of the board: side is "F" (front/top)
    or "B" (back/bottom)."""
    mirror = side == "B"
    copper, holes = draw_layer(side + ".Cu", mirror, zoom, tmp, board)
    # On a mask layer KiCad draws the places where the mask is LEFT OFF
    # (the openings over pads), not the mask itself.
    opening, _ = draw_layer(side + ".Mask", mirror, zoom, tmp, board)
    silk, _ = draw_layer(side + ".SilkS", mirror, zoom, tmp, board)
    outline, _ = draw_layer("Edge.Cuts", mirror, zoom, tmp, board)
    st = dict(copper=copper, holes=holes, opening=opening, silk=silk,
              board=fill_outline(outline))
    sizes = {k: v.shape for k, v in st.items()}
    assert len(set(sizes.values())) == 1, f"layer pictures differ in size: {sizes}"
    return st


# --------------------------------------------------------------- painting ---

def blend(base, colour, amount):
    """Paint `colour` over `base`. `amount` is a stencil: 0 keeps the base,
    1 gives the colour, values between mix the two (smooth edges)."""
    return base + (colour - base) * amount[..., None]


def paint(st, look):
    """Paint one side's stencils in one look's colours. Returns a picture."""
    h, w = st["board"].shape
    copper, holes, opening, silk, board = (
        st[k] for k in ("copper", "holes", "opening", "silk", "board"))
    yy, xx = np.mgrid[0:h, 0:w]
    diagonal = (xx / w + yy / h) / 2         # 0 at top-left, 1 at bottom-right
    toward_light = 1 - 2 * diagonal          # +1 at top-left, -1 at bottom-right

    # 1. Solder mask everywhere, a little lighter wherever copper is under it.
    over_copper, over_bare = mask_shades(look["mask"])
    rgb = np.empty((h, w, 3), np.float32)
    rgb[:] = over_bare
    rgb = blend(rgb, over_copper, copper)
    rgb *= (1 + SHEEN[look.get("sheen", "gloss")] * toward_light)[..., None]

    # 2. Bare metal where the mask is left off over copper: the pads.
    finish = look["finish"]
    metal = np.empty_like(rgb)
    metal[:] = hex_to_rgb(FINISHES.get(finish, finish))
    metal *= (1 + 0.04 * toward_light)[..., None]   # metal catches the light too
    if finish == "hasl":
        # Melted solder sets with a slightly uneven, rippled surface: add a
        # soft random texture of about +/-2 % brightness. The blur turns
        # pixel-sized speckle into broad, gentle ripples. The fixed seed (1)
        # makes the texture the same on every run.
        noise = np.random.default_rng(1).random((h, w), dtype=np.float32)
        noise = Image.fromarray(np.uint8(noise * 255)).filter(ImageFilter.GaussianBlur(8))
        noise = np.asarray(noise, np.float32)
        noise = (noise - noise.mean()) / noise.std()
        metal *= (1 + 0.02 * noise)[..., None]
    rgb = blend(rgb, metal, opening * copper)
    rgb = blend(rgb, hex_to_rgb(FR4), opening * (1 - copper))  # opening without copper

    # 3. A dark ring just inside each drilled hole: the hole's plated wall,
    # seen at a slight angle, is in shadow.
    ring = np.clip(grow(holes, 2) - holes, 0, 1)
    rgb = blend(rgb, rgb * 0.55, ring)

    # 4. Silkscreen ink on top, except on pads: the factory trims ink off
    # anything that has to be soldered.
    rgb = blend(rgb, hex_to_rgb(look["silk"]), silk * (1 - opening))

    # 5. Darken a 2-pixel band along the board's edge, so the board reads as
    # a solid object against any backdrop.
    edge = np.clip(board - shrink(board, 2), 0, 1)
    rgb = blend(rgb, rgb * 0.7, edge)

    # Transparency: solid on the board, clear outside it and in the holes.
    alpha = board * (1 - holes)
    out = np.dstack([np.clip(rgb, 0, 1), alpha]) * 255
    return Image.fromarray(np.uint8(np.round(out)), "RGBA")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("looks", help="JSON file listing the looks (see the top of this file)")
    ap.add_argument("out_dir", help="folder for the pictures")
    ap.add_argument("--zoom", type=float, default=12,
                    help="picture scale; 12 gives about 45 pixels per mm")
    ap.add_argument("--board", default=BOARD,
                    help="board file to draw (default: the standard board)")
    args = ap.parse_args()

    with open(args.looks) as f:
        looks = json.load(f)
    os.makedirs(args.out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        # Draw the layers once per side, then paint them once per look.
        for side, name in (("F", "top"), ("B", "bottom")):
            st = side_stencils(side, args.zoom, tmp, args.board)
            for look in looks:
                path = os.path.join(args.out_dir, f"{look['id']}-{name}.png")
                paint(st, look).save(path, optimize=True)
                print("wrote", path)


if __name__ == "__main__":
    main()
