#!/usr/bin/env python3
"""
Draw the four buck marks from deer.py and check them against the
silkscreen limits.

    python3 gen/deer_check.py out_dir            (checks deer.py's own drawing)
    /usr/bin/python3 gen/deer_check.py out_dir --kicad

With --kicad (needs KiCad 7's pcbnew and kicad-cli, and rsvg-convert), the
marks are also put on a scratch KiCad board, top and bottom, plotted by KiCad
the same way the factory files are, and the checks are repeated on KiCad's
plot. That proves the shapes survive the trip into KiCad, and that a mark
mirrored for the bottom side reads the right way round from below.

Writes to out_dir:
  sheet.png    all four marks, large, on their themes' board colours
  <id>.svg     each mark as a vector picture (white ink, clear background)
  report.txt   the measurements (also printed)

How the checks work
-------------------
Each mark is painted into a fine grid of pixels (100 per millimetre, so
one pixel is 0.01 mm), then tested with a round "brush" the size of the limit:

  Lines   Paint everything the 0.20 mm brush can reach while staying inside
          the ink. Anything it can't reach is thinner than 0.20 mm. Sharp
          outside corners always leave a sliver (about 0.04 mm on a square
          corner), so only leftovers deeper than 0.05 mm count, and so does
          any piece the brush can't enter at all.
  Gaps    The same test on the blank space between the ink, with the same
          brush. A gap is too narrow if filling it would join two separate
          shapes, close up a hole, or leave a filled channel deeper than
          0.30 mm. Where two lines branch at an angle (antler tines) the
          notch between them always narrows to nothing; notches like that are
          normal (every V or K in printed text has one) and are allowed.
  Holes   Every enclosed hole must still be open after filling with a
          0.25 mm brush.
  Size    The ink must lie inside the 10 x 10 mm box.

"Narrowest line" and "narrowest gap" are found by trying bigger and bigger
brushes until a test fails. Results are good to about 0.01 mm. On shapes with
square corners (the pixel art) the line figure can't read much above 0.25 mm,
because bigger brushes leave corner slivers deeper than the allowance. Specks of
under 0.03 mm (a few pixels, from smoothing at the bottom of a sharp notch)
are ignored: they are far below anything a factory can print.

Needs numpy and Pillow (the same as theme_render.py).
"""
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deer  # noqa: E402

PPM = 100              # pixels per millimetre for the checks
MARGIN = 0.5           # blank border around the 10 mm box, mm
CORNER_TOL = 0.05      # sharp-corner sliver allowed by the line test, mm
NOTCH_TOL = 0.30       # branching notch allowed by the gap test, mm
SPECK = 9              # pieces or holes of this many pixels or fewer (a speck
                       # under 0.03 mm) are smoothing noise in the picture,
                       # far below anything a factory can print: ignored

# Board colours for each theme: solder mask and silkscreen ink, the same
# values used for the theme previews of the whole board.
THEMES = {
    "dawnworks":            {"mask": "#4F6D3A", "silk": "#F4EBD0"},
    "mahogany-lounge":      {"mask": "#1F3D2B", "silk": "#EFE6D2"},
    "neon-noir-chartreuse": {"mask": "#16191A", "silk": "#FFFFFF"},
    "parkside-98":          {"mask": "#336ECC", "silk": "#FFFFFF"},
}


# ---------------------------------------------------------------- drawing ---

def rasterize(art, ppm, margin=MARGIN, aa=4):
    """Paint a drawing into a grid of numbers: 1 where there is ink, 0 where
    there isn't, values between on smoothed edges.

    ppm: pixels per millimetre. margin: blank border around the 10 mm box (mm).
    aa: draw this many times larger, then shrink, to smooth the edges."""
    x1, y1, _, _ = art.bounds()             # shift by under half a pixel so
    snap = lambda v: (round((v + margin) * ppm) - (v + margin) * ppm) / ppm
    art = art.moved(snap(x1), snap(y1))     # the ink's corner is on the grid
    s = ppm * aa
    n = int(round((deer.BOX + 2 * margin) * s))
    img = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(img)

    def P(x, y):
        return ((x + margin) * s, (y + margin) * s)

    def disc(draw, c, r, fill=255):
        (x, y) = P(*c)
        draw.ellipse([x - r * s, y - r * s, x + r * s, y + r * s], fill=fill)

    for sh in art.shapes:
        kind = sh[0]
        if kind == "poly":
            d.polygon([P(*p) for p in sh[1]], fill=255)
        elif kind == "line":
            pts, h = sh[1], sh[2] / 2
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                L = math.hypot(x2 - x1, y2 - y1) or 1e-9
                nx, ny = -(y2 - y1) / L * h, (x2 - x1) / L * h
                d.polygon([P(x1 + nx, y1 + ny), P(x2 + nx, y2 + ny),
                           P(x2 - nx, y2 - ny), P(x1 - nx, y1 - ny)], fill=255)
            for p in pts:                       # round ends and corners
                disc(d, p, h)
        elif kind == "dot":
            disc(d, sh[1], sh[2])
        elif kind == "ring":
            # a ring removes ink in its middle, so draw it on its own sheet
            # and then add that sheet to the picture
            layer = Image.new("L", (n, n), 0)
            ld = ImageDraw.Draw(layer)
            (cx, cy), r, w = sh[1], sh[2], sh[3]
            disc(ld, (cx, cy), r + w / 2, 255)
            disc(ld, (cx, cy), r - w / 2, 0)
            img = Image.fromarray(np.maximum(np.asarray(img), np.asarray(layer)))
            d = ImageDraw.Draw(img)
    if aa > 1:
        img = img.resize((n // aa, n // aa), Image.BOX)
    return np.asarray(img, np.float32) / 255


def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def paint(cover, mask_hex, silk_hex):
    """Colour an ink-coverage grid: board colour where there's no ink."""
    m, s = hex_rgb(mask_hex), hex_rgb(silk_hex)
    rgb = m + (s - m) * cover[..., None]
    return Image.fromarray(np.uint8(np.round(rgb)), "RGB")


def sheet(arts, path, ppm=60):
    """All marks side by side, large, each on its theme's board colour, with
    a thin grey line showing the 10 x 10 mm box."""
    tiles = []
    for art in arts:
        t = THEMES[art.id]
        cover = rasterize(art, ppm, margin=0.6)
        im = paint(cover, t["mask"], t["silk"])
        d = ImageDraw.Draw(im)
        o, e = 0.6 * ppm, (0.6 + deer.BOX) * ppm
        d.rectangle([o - 1, o - 1, e, e], outline=(150, 150, 150))
        tiles.append(im)
    w, h = tiles[0].size
    out = Image.new("RGB", (len(tiles) * (w + 12) + 12, h + 24), (110, 110, 108))
    for i, im in enumerate(tiles):
        out.paste(im, (12 + i * (w + 12), 12))
    out.save(path)


# ------------------------------------------------------------- morphology ---
# "Spreading" ink by a radius r paints every pixel within r of existing ink;
# "shrinking" keeps only pixels whose whole r-neighbourhood is ink. Both are
# done by counting the ink under a round brush at every pixel, which a
# Fourier transform does for the whole picture at once.

def brush(r):
    """A round brush: 1s inside a circle of radius r pixels."""
    R = int(math.floor(r))
    y, x = np.mgrid[-R:R + 1, -R:R + 1]
    return (x * x + y * y <= r * r).astype(np.float64)


def count_under(img, k):
    """For every pixel, how much of `img` lies under the brush k centred there."""
    H, W = img.shape
    kh, kw = k.shape
    sh, sw = H + kh - 1, W + kw - 1
    f = np.fft.rfft2(img.astype(np.float64), (sh, sw)) * np.fft.rfft2(k, (sh, sw))
    full = np.fft.irfft2(f, (sh, sw))
    return full[kh // 2:kh // 2 + H, kw // 2:kw // 2 + W]


def spread(mask, r):
    return count_under(mask, brush(r)) > 0.5


def shrink(mask, r):
    k = brush(r)
    return count_under(mask, k) > k.sum() - 0.5


def brush_radius(d_mm, ppm=PPM):
    """Radius in pixels of a brush that just fits a d_mm-wide line drawn at
    ppm: a line d_mm wide covers about d_mm * ppm pixels."""
    return max(0.0, (d_mm * ppm - 1) / 2)


def label(m, eight):
    """Number the separate pieces of True pixels in m.

    Returns (labels, edge_ids): labels has 0 where m is False and a piece
    number elsewhere; edge_ids are the pieces that touch the picture's border.
    Works row by row: each run of pixels in a row is joined to the runs it
    touches in the row above (union-find). eight=True also joins pixels that
    touch only at a corner."""
    parent, edge, runs = [], [], []

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    k = 1 if eight else 0
    H, W = m.shape
    prev = []
    for y in range(H):
        d = np.diff(np.concatenate(([0], m[y].astype(np.int8), [0])))
        starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
        cur, j = [], 0
        for s, e in zip(starts.tolist(), ends.tolist()):
            i = len(parent)
            parent.append(i)
            edge.append(y == 0 or y == H - 1 or s == 0 or e == W)
            while j < len(prev) and prev[j][1] + k <= s:
                j += 1
            jj = j
            while jj < len(prev) and prev[jj][0] < e + k:
                a, b = find(i), find(prev[jj][2])
                if a != b:
                    parent[a] = b
                    edge[b] = edge[b] or edge[a]
                jj += 1
            cur.append((s, e, i))
            runs.append((y, s, e, i))
        prev = cur
    labels = np.zeros((H, W), np.int32)
    for y, s, e, i in runs:
        labels[y, s:e] = find(i) + 1
    edge_ids = {find(i) + 1 for i in range(len(parent)) if edge[find(i)]}
    return labels, edge_ids


def pieces_and_holes(mask):
    """Count separate pieces of ink, and holes (blank areas enclosed by ink).
    Ink touching only at a corner counts as joined; blank areas must share an
    edge to join."""
    ink_labels, _ = label(mask, True)
    blank_labels, edge_ids = label(~mask, False)
    return (len(real_ids(ink_labels)),
            len(real_ids(blank_labels) - edge_ids))


def real_ids(labels):
    """Piece numbers in a label grid, leaving out specks of SPECK pixels or
    fewer."""
    sizes = np.bincount(labels.ravel())
    return {i for i in range(1, len(sizes)) if sizes[i] > SPECK}


def deepest(leftover, kept, steps=(0.02, 0.05, 0.1, 0.2, 0.3, 0.5)):
    """How far the leftover pixels reach beyond the kept area, in mm: the
    first step of the list that covers all of them (or > the last)."""
    if not leftover.any():
        return 0.0
    for t in steps:
        if not (leftover & ~spread(kept, t * PPM)).any():
            return t
    return float("inf")


# ------------------------------------------------------------------ tests ---

def line_test(ink, base, d):
    """Does every bit of ink fit a d mm brush? Returns (ok, deepest sliver)."""
    r = brush_radius(d)
    opened = spread(shrink(ink, r), r)
    depth = deepest(ink & ~opened, opened)
    same_pieces = pieces_and_holes(opened)[0] == base[0]
    return same_pieces and depth <= CORNER_TOL, depth


def gap_test(ink, base, d, notch_tol=NOTCH_TOL):
    """Does every blank space fit a d mm brush? Returns (ok, deepest fill)."""
    r = brush_radius(d)
    closed = shrink(spread(ink, r), r)
    inner = np.zeros_like(ink)                  # ignore the picture's border
    b = int(2 * r) + 2
    inner[b:-b, b:-b] = True
    filled = closed & ~ink & inner
    depth = deepest(filled, ~closed)
    same = pieces_and_holes(closed) == base
    return same and depth <= notch_tol, depth


def hole_test(ink, d):
    """Does every enclosed hole have room for a d mm brush somewhere in it?"""
    blank, edge_ids = label(~ink, False)
    ids = real_ids(blank) - edge_ids
    holes = np.isin(blank, list(ids))
    room = shrink(holes, brush_radius(d))   # centres where the brush fits
    return ids <= set(np.unique(blank[room]))


def largest_passing(test, lo=0.05, hi=0.8):
    """Biggest brush size (mm, to 0.01) for which test(d) passes."""
    if not test(lo):
        return 0.0
    while hi - lo > 0.0101:
        mid = round((lo + hi) / 2, 3)
        if test(mid):
            lo = mid
        else:
            hi = mid
    return math.floor(lo * 100 + 1e-6) / 100


def measure(ink, art=None):
    """All the checks for one mark, from its ink grid."""
    base = pieces_and_holes(ink)
    line_ok, line_sliver = line_test(ink, base, deer.LINE_MIN)
    gap_ok, gap_notch = gap_test(ink, base, deer.GAP_MIN)
    hole_ok = hole_test(ink, deer.HOLE_MIN)
    res = {
        "pieces": base[0], "holes": base[1],
        "line_ok": line_ok, "corner_sliver": line_sliver,
        "gap_ok": gap_ok, "notch": gap_notch, "hole_ok": hole_ok,
        "narrowest_line": largest_passing(lambda d: line_test(ink, base, d)[0]),
        # separate shapes and holes only: notches don't limit this number
        "narrowest_gap": largest_passing(
            lambda d: gap_test(ink, base, d, notch_tol=float("inf"))[0]),
        "smallest_hole": largest_passing(lambda d: hole_test(ink, d))
        if base[1] else None,
        "ink_share": float(ink[int(MARGIN * PPM):-int(MARGIN * PPM),
                               int(MARGIN * PPM):-int(MARGIN * PPM)].mean()),
    }
    if art is not None:
        x1, y1, x2, y2 = art.bounds()
        res["bounds"] = (x1, y1, x2, y2)
        res["size_ok"] = x1 >= 0 and y1 >= 0 and x2 <= deer.BOX and y2 <= deer.BOX
    return res


# ------------------------------------------------------- KiCad cross-check ---

def kicad_plots(arts, tmp):
    """Put every mark on a scratch board, on the top silkscreen and, mirrored,
    on the bottom silkscreen; plot both layers with KiCad. Returns, for each
    mark, its ink grid as plotted on the top and as seen from below."""
    import pcbnew
    from pcbnew import FromMM, VECTOR2I
    pitch, n = 12.0, len(arts)
    x0, y0, x1, y1 = -1.0, -1.0, n * pitch - 1.0, 11.0     # board outline
    ew = 0.1                                               # outline width
    board = pcbnew.BOARD()
    edge = pcbnew.PCB_SHAPE(board)
    edge.SetShape(pcbnew.SHAPE_T_RECT)
    edge.SetStart(VECTOR2I(FromMM(x0), FromMM(y0)))
    edge.SetEnd(VECTOR2I(FromMM(x1), FromMM(y1)))
    edge.SetWidth(FromMM(ew))
    edge.SetLayer(pcbnew.Edge_Cuts)
    board.Add(edge)
    off = -x0 + ew / 2                          # board mm -> picture mm
    for i, art in enumerate(arts):
        ax, ay, _, _ = art.bounds()             # line up with the pixel grid
        gx = i * pitch + ax + off
        gy = ay - y0 + ew / 2
        dx = (round(gx * PPM) - gx * PPM) / PPM
        dy = (round(gy * PPM) - gy * PPM) / PPM
        deer.add_to_board(board, art, i * pitch + dx, dy, pcbnew.F_SilkS)
        # bottom: seen from below, the board's left and right swap, so the
        # mark that should appear in slot i sits at the mirrored position
        deer.add_to_board(board, art, (x0 + x1) - (i * pitch + deer.BOX), 0.0,
                          pcbnew.B_SilkS, flip=True)
    path = os.path.join(tmp, "deer-check.kicad_pcb")
    pcbnew.SaveBoard(path, board)
    zoom = PPM / (96 / 25.4)                    # rsvg draws 1 mm as 96/25.4 px
    grids = {}
    for layer, mirror in (("F.SilkS", False), ("B.SilkS", True)):
        svg = os.path.join(tmp, layer + ".svg")
        png = svg[:-4] + ".png"
        cmd = ["kicad-cli", "pcb", "export", "svg", path, "-o", svg, "-l", layer,
               "--black-and-white", "--page-size-mode", "2",
               "--exclude-drawing-sheet"] + (["--mirror"] if mirror else [])
        subprocess.run(cmd, check=True, capture_output=True)
        subprocess.run(["rsvg-convert", "-z", str(zoom), svg, "-o", png], check=True)
        alpha = np.asarray(Image.open(png).convert("RGBA"), np.float32)[..., 3] / 255
        grids[layer] = alpha
    out = []
    for i in range(n):
        cells = []
        for layer in ("F.SilkS", "B.SilkS"):
            g = grids[layer]
            px0 = int(round((i * pitch - MARGIN + off) * PPM))
            py0 = int(round((-MARGIN - y0 + ew / 2) * PPM))
            size = int(round((deer.BOX + 2 * MARGIN) * PPM))
            cell = np.zeros((size, size), np.float32)
            crop = g[py0:py0 + size, px0:px0 + size]
            cell[:crop.shape[0], :crop.shape[1]] = crop
            cells.append(cell)
        out.append(cells)
    return out


def best_overlap(a, b, reach=3):
    """Share of pixels that differ between two ink grids, after sliding b by
    up to `reach` pixels to line them up (picture edges round to a pixel)."""
    best = 1.0
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            s = np.roll(np.roll(b, dy, 0), dx, 1)
            diff = (a != s).sum() / max(1, (a | s).sum())
            best = min(best, diff)
    return best


# -------------------------------------------------------------------- main ---

def report_lines(art, m, label="deer.py"):
    x1, y1, x2, y2 = m["bounds"]
    ok = lambda b: "pass" if b else "FAIL"
    return [
        f"{art.name} ({art.id}), checked on {label}",
        f"  size      {x2 - x1:.2f} x {y2 - y1:.2f} mm, inside the 10 mm box: {ok(m['size_ok'])}",
        f"  lines     all at least {deer.LINE_MIN:.2f} mm: {ok(m['line_ok'])}"
        f"   (narrowest {m['narrowest_line']:.2f} mm; corner slivers up to {m['corner_sliver']:.2f} mm)",
        f"  gaps      all at least {deer.GAP_MIN:.2f} mm: {ok(m['gap_ok'])}"
        f"   (narrowest between shapes {m['narrowest_gap']:.2f} mm; branch notches up to {m['notch']:.2f} mm)",
        f"  holes     all at least {deer.HOLE_MIN:.2f} mm: {ok(m['hole_ok'])}"
        + (f"   (smallest {m['smallest_hole']:.2f} mm across; " if m['holes'] else "   (")
        + f"{m['holes']} holes, {m['pieces']} separate pieces of ink)",
        f"  ink       {100 * m['ink_share']:.1f} % of the 10 x 10 mm square",
    ]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_dir = args[0] if args else "."
    os.makedirs(out_dir, exist_ok=True)
    arts = [deer.make(i) for i in deer.DESIGNS]
    sheet(arts, os.path.join(out_dir, "sheet.png"))
    lines, results = [], {}
    for art in arts:
        with open(os.path.join(out_dir, art.id + ".svg"), "w") as f:
            f.write(deer.to_svg(art))
        ink = rasterize(art, PPM) >= 0.5
        m = measure(ink, art)
        results[art.id] = (ink, m)
        lines += report_lines(art, m) + [""]
    if "--kicad" in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            plots = kicad_plots(arts, tmp)
        for art, (top, bottom) in zip(arts, plots):
            ink, m0 = results[art.id]
            top_ink, bot_ink = top >= 0.5, bottom >= 0.5
            m = measure(top_ink)
            m["bounds"], m["size_ok"] = m0["bounds"], m0["size_ok"]
            lines += report_lines(art, m, "KiCad's plot of the top side")
            lines.append(f"  KiCad's top plot differs from deer.py's drawing on "
                         f"{100 * best_overlap(ink, top_ink):.2f} % of inked pixels")
            lines.append(f"  bottom side, seen from below, differs on "
                         f"{100 * best_overlap(ink, bot_ink):.2f} % (reads the right way round)")
            lines.append("")
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(out_dir, "report.txt"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
