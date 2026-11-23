#!/usr/bin/python3
"""
Silkscreen check for the things KiCad's own design-rule check leaves out.

    /usr/bin/python3 gen/silk_check.py board.kicad_pcb [more boards] [--no-pixels]
    ... --no-pixels   skip the pixel test (check 3), about 30 s a board
    ... --with-text   run the pixel test on KiCad's text too (see below)

Run it with the Python that has KiCad 7's pcbnew (it also needs numpy,
Pillow, kicad-cli and rsvg-convert, like deer_check.py).

Why this exists
---------------
KiCad checks silkscreen text against everything, and all silkscreen against
pads, solder-mask openings and the board edge. But it treats all the shapes
drawn on a board (lines, filled outlines, circles) as one big drawing, and
never checks one of them against another. A test board showed it: two
overlapping rectangles passed KiCad's check, while a rectangle overlapping a
piece of text failed it. On the themed boards most lettering is drawn shapes
(pixel letters, letters from real fonts), so two labels could run into each
other and KiCad would say nothing. This script covers that gap.

The checks
----------
1. Spacing (exact, from the board's own geometry). The build keeps
   everything one drawing call makes (one label, one title, one frame, the
   deer) in one KiCad group, an "element" (see gen/themes/kit.py). Any two
   elements on the same side must be at least 0.15 mm apart; parts of one
   element may touch. Shapes that are in no group (as on the standard board)
   count as one element with whatever they touch.
2. Line widths (exact). Every drawn line and ring at least 0.15 mm wide,
   every dot at least 0.15 mm across.
3. The factory's view (pixels). KiCad plots each silkscreen layer the same
   way it does for the Gerber files. The picture, 100 pixels per mm, gets the
   round-brush tests from deer_check.py: every line must be wide enough for
   the brush, every gap too, and every enclosed hole must stay open. This
   finds what the first two can't see: a thin neck inside a letter, two
   strokes of one drawing almost touching, a hole that would fill in.
   One pixel is 0.01 mm and a pixel brush has to be an odd number of pixels
   across, so the brush is 13 pixels (0.13 mm) across: the 0.15 mm limit
   less one pixel of drawing error at each edge. Checks 1 and 2 are the exact
   0.15 mm ones. A pointed corner always narrows to nothing at its tip
   (the printer just rounds it off), so thin ink within 0.30 mm of where the
   brush did reach is allowed, the same allowance as for notches.
   The pixel test leaves out text in KiCad's own font: KiCad's check already
   holds every piece of it to 0.8 mm tall and 0.15 mm strokes, and at that
   size the font's own letter gaps and the holes in A, D or 8 come out
   narrower than the brush on any board (--with-text shows them).
4. Letters of the real-font titles, measured exactly. Stroke width: from the
   middle of every edge of every letter a ray goes straight across the ink,
   and its length is the stroke's width there (only rays that come out
   through the opposite side of the stroke count; at a pointed corner every
   ray is short). No stroke under 0.15 mm, and no two letters (or parts of
   one, like the dots of a colon) closer than 0.15 mm.
5. Bare metal. Every opening drawn in the solder mask (the gold or silver
   accents) must lie wholly over copper, so the factory's finish shows
   through it and not the bare board. Compared, in pixels, with KiCad's plot
   of that side's copper (skipped with --no-pixels).
6. Silkscreen to openings. All silkscreen, KiCad's text included, at least
   0.15 mm from every opening in the solder mask on its side: pads, the drawn
   openings, and the holes the panel's break-away tabs drill into each board
   (so a single board that passes is ready for the panel). KiCad only reports
   silkscreen that actually overlaps an opening; a test board with silkscreen
   0.05 mm from an opening passed its check. In pixels, so skipped with
   --no-pixels; --no-tabs leaves the tab holes out. Notches where two strokes meet at an angle (inside a V or a
   K) always narrow to nothing; like deer_check.py, notches up to 0.30 mm deep
   are allowed.
"""
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

import pcbnew
from pcbnew import ToMM

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deer_check as dc  # noqa: E402  (the pixel tools: spread, shrink, label)

CLEAR = 0.15          # mm: separate elements at least this far apart
WIDTH = 0.15          # mm: narrowest line, ring or dot
TOUCH = 0.001         # mm: closer than this counts as touching
BRUSH = 0.14          # mm: brush for the pixel tests (0.15 less one pixel)
NOTCH = 0.30          # mm: deepest allowed notch where strokes meet at an angle
TIP = 0.30            # mm: how far a pointed corner may narrow below the brush
RING_STEPS = 64       # a ring is measured as this many short lines
LAYERS = (("F.SilkS", pcbnew.F_SilkS), ("B.SilkS", pcbnew.B_SilkS))


# ------------------------------------------------------------- geometry ---
def mm(p):
    return ToMM(p.x), ToMM(p.y)


def chain(c):
    """The corner points of a KiCad outline (SHAPE_LINE_CHAIN), in mm."""
    return [mm(c.CPoint(i)) for i in range(c.PointCount())]


class Element:
    """One drawing on one silkscreen layer, broken into simple pieces:
    lines with round ends (a dot is a line of length 0) and filled outlines.
    Every piece also gives up its edges as lines of width 0, so measuring the
    gap between two elements comes down to measuring between lines."""

    def __init__(self, name, grouped):
        self.name, self.grouped = name, grouped
        self.segs = []       # rows of (x1, y1, x2, y2, r): r is half the width
        self.fills = []      # filled outlines: (list of loops, bounding box)
        self.points = []     # one point on every piece, for "inside?" tests

    def line(self, a, b, r):
        self.segs.append((a[0], a[1], b[0], b[1], r))
        self.points.append(a)

    def fill(self, loops):
        arr = [np.array(lp, float) for lp in loops if len(lp) >= 3]
        if not arr:
            return
        allp = np.vstack(arr)
        self.fills.append((arr, (allp[:, 0].min(), allp[:, 1].min(),
                                 allp[:, 0].max(), allp[:, 1].max())))
        for lp in loops:
            for p, q in zip(lp, lp[1:] + lp[:1]):
                self.segs.append((p[0], p[1], q[0], q[1], 0.0))
        self.points.append(loops[0][0])

    def finish(self):
        self.S = np.array(self.segs, float).reshape(-1, 5)
        S, r = self.S, self.S[:, 4]
        self.seg_box = np.stack([np.minimum(S[:, 0], S[:, 2]) - r,
                                 np.minimum(S[:, 1], S[:, 3]) - r,
                                 np.maximum(S[:, 0], S[:, 2]) + r,
                                 np.maximum(S[:, 1], S[:, 3]) + r], axis=1)
        b = self.seg_box
        self.box = (b[:, 0].min(), b[:, 1].min(), b[:, 2].max(), b[:, 3].max())
        self.P = np.array(self.points, float).reshape(-1, 2)


def add_shape(el, s, widths):
    """Turn one KiCad drawing into pieces of `el`; note any line too thin."""
    kind, w = s.GetShape(), ToMM(s.GetWidth())
    where = None
    if kind == pcbnew.SHAPE_T_SEGMENT:
        a, b = mm(s.GetStart()), mm(s.GetEnd())
        el.line(a, b, w / 2)
        where = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        thin = w < WIDTH - 1e-6
    elif kind == pcbnew.SHAPE_T_CIRCLE:
        c, R = mm(s.GetCenter()), ToMM(s.GetRadius())
        where = c
        if s.IsFilled():                         # a dot
            el.line(c, c, R + w / 2)
            thin = 2 * R + w < WIDTH - 1e-6
        else:                                    # a ring: a chain of short lines
            sag = R * (1 - math.cos(math.pi / RING_STEPS))   # chain cuts inside
            pts = [(c[0] + R * math.cos(2 * math.pi * i / RING_STEPS),
                    c[1] + R * math.sin(2 * math.pi * i / RING_STEPS))
                   for i in range(RING_STEPS)]
            for p, q in zip(pts, pts[1:] + pts[:1]):
                el.line(p, q, w / 2 + sag)
            thin = w < WIDTH - 1e-6
    elif kind in (pcbnew.SHAPE_T_POLY, pcbnew.SHAPE_T_RECT):
        if kind == pcbnew.SHAPE_T_RECT:
            (x1, y1), (x2, y2) = mm(s.GetStart()), mm(s.GetEnd())
            all_loops = [[[(x1, y1), (x2, y1), (x2, y2), (x1, y2)]]]
        else:
            ps = s.GetPolyShape()
            all_loops = [[chain(ps.Outline(i))] + [chain(ps.Hole(i, h))
                                                   for h in range(ps.HoleCount(i))]
                         for i in range(ps.OutlineCount())]
        for loops in all_loops:
            if s.IsFilled():
                el.fill(loops)
            if w > 0:                            # an outline drawn as a line
                for lp in loops:
                    for p, q in zip(lp, lp[1:] + lp[:1]):
                        el.line(p, q, w / 2)
        where = all_loops[0][0][0] if all_loops and all_loops[0][0] else None
        thin = 0 < w < WIDTH - 1e-6
    elif kind == pcbnew.SHAPE_T_ARC:
        c, R = mm(s.GetCenter()), ToMM(s.GetRadius())
        a0 = math.atan2(mm(s.GetStart())[1] - c[1], mm(s.GetStart())[0] - c[0])
        sweep = math.radians(s.GetArcAngle().AsDegrees())
        n = max(2, int(abs(sweep) / (2 * math.pi) * RING_STEPS) + 1)
        sag = R * (1 - math.cos(abs(sweep) / n / 2))
        pts = [(c[0] + R * math.cos(a0 + sweep * i / n), c[1] + R * math.sin(a0 + sweep * i / n))
               for i in range(n + 1)]
        for p, q in zip(pts, pts[1:]):
            el.line(p, q, w / 2 + sag)
        where, thin = pts[n // 2], w < WIDTH - 1e-6
    else:
        raise ValueError(f"silk_check: can't measure shape type {kind} in {el.name}")
    if thin:
        widths.append((el.name, w, where))


def collect(board, layer):
    """Every board drawing (not text, not footprint) on one layer, gathered
    into elements by their KiCad group. Returns (elements, thin lines)."""
    found, widths = {}, []
    for d in board.GetDrawings():
        if not isinstance(d, pcbnew.PCB_SHAPE) or d.GetLayer() != layer:
            continue
        g = d.GetParentGroup()
        key = g.m_Uuid.AsString() if g else d.m_Uuid.AsString()
        if key not in found:
            found[key] = Element(g.GetName() if g else "drawing", bool(g))
        add_shape(found[key], d, widths)
    els = [e for e in found.values() if e.segs]
    for e in els:
        e.finish()
    return els, widths


def point_to_lines(px, py, x1, y1, x2, y2):
    """Distance from points to lines (numpy arrays that broadcast together)."""
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    t = ((px - x1) * dx + (py - y1) * dy) / np.where(L2 > 0, L2, 1.0)
    t = np.clip(np.where(L2 > 0, t, 0.0), 0.0, 1.0)
    return np.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def line_gaps(A, B):
    """Gap between the inked edges of every line in A and every line in B
    (a len(A) x len(B) table, negative where they overlap)."""
    ax1, ay1, ax2, ay2, ar = (A[:, i:i + 1] for i in range(5))
    bx1, by1, bx2, by2, br = (B[None, :, i] for i in range(5))
    d = np.minimum.reduce([point_to_lines(ax1, ay1, bx1, by1, bx2, by2),
                           point_to_lines(ax2, ay2, bx1, by1, bx2, by2),
                           point_to_lines(bx1, by1, ax1, ay1, ax2, ay2),
                           point_to_lines(bx2, by2, ax1, ay1, ax2, ay2)])

    def side(px, py, qx, qy, rx, ry):           # which side of p->q is r on
        return (qx - px) * (ry - py) - (qy - py) * (rx - px)
    crossing = ((side(ax1, ay1, ax2, ay2, bx1, by1) * side(ax1, ay1, ax2, ay2, bx2, by2) < 0)
                & (side(bx1, by1, bx2, by2, ax1, ay1) * side(bx1, by1, bx2, by2, ax2, ay2) < 0))
    return np.where(crossing, 0.0, d) - ar - br


def inside(P, loops):
    """Which of the points P (n x 2) lie inside a filled outline (with holes:
    a point inside an even number of loops is outside)."""
    hit = np.zeros(len(P), bool)
    px, py = P[:, 0:1], P[:, 1:2]
    for lp in loops:
        x1, y1 = lp[None, :, 0], lp[None, :, 1]
        x2, y2 = np.roll(x1, -1, axis=1), np.roll(y1, -1, axis=1)
        straddles = (y1 > py) != (y2 > py)
        xs = x1 + (py - y1) * (x2 - x1) / np.where(y2 != y1, y2 - y1, 1.0)
        hit ^= (np.count_nonzero(straddles & (px < xs), axis=1) % 2) == 1
    return hit


def near(seg_box, box, reach):
    return ((seg_box[:, 0] <= box[2] + reach) & (seg_box[:, 2] >= box[0] - reach)
            & (seg_box[:, 1] <= box[3] + reach) & (seg_box[:, 3] >= box[1] - reach))


def gap(a, b, reach=CLEAR):
    """How far apart the ink of elements a and b is (0 if they touch or
    overlap), and roughly where they come closest. Only gaps under `reach`
    are measured exactly; a bigger one comes back as infinity."""
    best, where = math.inf, None
    Sa = a.S[near(a.seg_box, b.box, reach)]
    Sb = b.S[near(b.seg_box, a.box, reach)]
    step = max(1, 300000 // max(1, len(Sb)))
    for i in range(0, len(Sa) if len(Sb) else 0, step):
        g = line_gaps(Sa[i:i + step], Sb)
        k = np.unravel_index(np.argmin(g), g.shape)
        if g[k] < best:
            best = g[k]
            p, q = Sa[i + k[0]], Sb[k[1]]
            where = ((p[0] + p[2] + q[0] + q[2]) / 4, (p[1] + p[3] + q[1] + q[3]) / 4)
    if best > 0:                                 # one wholly inside the other?
        for x, y in ((a, b), (b, a)):
            for loops, fb in y.fills:
                cand = x.P[(x.P[:, 0] >= fb[0]) & (x.P[:, 0] <= fb[2])
                           & (x.P[:, 1] >= fb[1]) & (x.P[:, 1] <= fb[3])]
                if len(cand):
                    hit = inside(cand, loops)
                    if hit.any():
                        return 0.0, tuple(cand[np.argmax(hit)])
    return max(best, 0.0), where


def spacing(els):
    """All pairs of elements closer than CLEAR, as (gap, a, b, where)."""
    if len(els) < 2:
        return []
    boxes = np.array([e.box for e in els])
    close = ((boxes[:, None, 0] <= boxes[None, :, 2] + CLEAR)
             & (boxes[None, :, 0] <= boxes[:, None, 2] + CLEAR)
             & (boxes[:, None, 1] <= boxes[None, :, 3] + CLEAR)
             & (boxes[None, :, 1] <= boxes[:, None, 3] + CLEAR))
    pairs = [(i, j) for i, j in zip(*np.nonzero(np.triu(close, 1)))]
    gaps = {(i, j): gap(els[i], els[j]) for i, j in pairs}
    # shapes in no group: those that touch are one drawing (union-find)
    parent = list(range(len(els)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for (i, j), (g, _) in gaps.items():
        if g <= TOUCH and not els[i].grouped and not els[j].grouped:
            parent[find(i)] = find(j)
    out = []
    for (i, j), (g, where) in gaps.items():
        if g < CLEAR - 1e-6 and not (not els[i].grouped and not els[j].grouped
                                     and find(i) == find(j)):
            out.append((g, els[i].name, els[j].name, where))
    return sorted(out)


# --------------------------------------------------------------- pixels ---
def plot(board_path, layers, tmp, name, threshold=0.5):
    """KiCad's own plot of some layers, as a grid of ink pixels (True = ink).
    The picture covers the board's outline, so its top-left pixel is the
    top-left corner of the board's bounding box."""
    svg = os.path.join(tmp, name + ".svg")
    png = svg[:-4] + ".png"
    subprocess.run(["kicad-cli", "pcb", "export", "svg", board_path, "-o", svg,
                    "-l", layers, "--black-and-white", "--page-size-mode", "2",
                    "--exclude-drawing-sheet"], check=True, capture_output=True)
    zoom = dc.PPM / (96 / 25.4)               # rsvg draws 1 mm as 96/25.4 px
    subprocess.run(["rsvg-convert", "-z", str(zoom), svg, "-o", png], check=True)
    alpha = np.asarray(Image.open(png).convert("RGBA"), np.float32)[..., 3] / 255
    return alpha > threshold


def centres(labels, ids, origin):
    """Board position (mm) of the middle of each numbered patch."""
    out = []
    for i in ids:
        ys, xs = np.nonzero(labels == i)
        out.append((round(origin[0] + xs.mean() / dc.PPM, 2),
                    round(origin[1] + ys.mean() / dc.PPM, 2)))
    return out


def patches(mask, origin):
    """Middles of the separate patches in mask, leaving out specks."""
    labels, _ = dc.label(mask, True)
    return centres(labels, sorted(dc.real_ids(labels)), origin)


def without_text(board_path, tmp):
    """A copy of the board with the KiCad-font text taken off the
    silkscreen (KiCad's own check covers text); returns its path."""
    board = pcbnew.LoadBoard(board_path)
    for d in board.GetDrawings():
        if isinstance(d, pcbnew.PCB_TEXT) and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            d.SetLayer(pcbnew.Cmts_User)      # a layer the plot leaves out
    path = os.path.join(tmp, "shapes-only.kicad_pcb")
    pcbnew.SaveBoard(path, board)
    return path


def pixel_checks(board_path, origin, tmp, text=True):
    """The factory-view tests on each silkscreen layer. Returns a list of
    (layer, what went wrong, places). text=False tests the drawn shapes
    only, on a copy of the board without its KiCad-font text."""
    problems = []
    if not text:
        board_path = without_text(board_path, tmp)
    r = dc.brush_radius(BRUSH)          # 6.5 pixels: a brush 13 pixels across
    # plotting the outline with each layer keeps every picture the same size;
    # the outline alone, plotted once, is then taken out again
    edge = plot(board_path, "Edge.Cuts", tmp, "edge", threshold=0.05)
    for layer_name, _ in LAYERS:
        drawn = plot(board_path, layer_name + ",Edge.Cuts", tmp, layer_name)
        ink = drawn & ~dc.spread(edge, 1.5)
        if not ink.any():
            continue
        ink_labels, _ = dc.label(ink, True)
        ink_ids = dc.real_ids(ink_labels)

        # 1. lines: ink the brush can't reach is thinner than the brush. A
        #    pointed corner always narrows to nothing at its tip (the printer
        #    just rounds it), so only ink further than TIP from where the
        #    brush did reach counts, plus any piece it can't enter at all
        opened = dc.spread(dc.shrink(ink, r), r)
        thin = ink & ~opened & ~dc.spread(opened, TIP * dc.PPM)
        if thin.any():
            problems.append((layer_name, "lines too thin for the brush", patches(thin, origin)))
        entered = set(np.unique(ink_labels[opened]).tolist())
        missed = sorted(ink_ids - entered)
        if missed:
            problems.append((layer_name, "pieces too thin for the brush to enter",
                             centres(ink_labels, missed, origin)))
        # a shape that the brush can only cover in separate parts has a neck
        # too thin for it
        op_labels, _ = dc.label(opened, True)
        pairs = np.unique(np.stack([ink_labels[opened], op_labels[opened]], 1), axis=0)
        ids, counts = np.unique(pairs[:, 0], return_counts=True)
        split = [i for i, c in zip(ids, counts) if c > 1 and i in ink_ids]
        if split:
            problems.append((layer_name, "shapes with a neck too thin for the brush",
                             centres(ink_labels, split, origin)))

        # 2. gaps: the same brush run over the blank space. Blank the brush
        #    can't get into gets filled ("closed").
        closed = dc.shrink(dc.spread(ink, r), r)
        filled = closed & ~ink
        fill_labels, _ = dc.label(filled, True)
        # a filled patch touching two separate shapes bridges a gap too narrow
        touching = []
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nb = np.roll(np.roll(ink_labels, dy, 0), dx, 1)
            m = filled & (nb > 0)
            touching.append(np.stack([fill_labels[m], nb[m]], 1))
        pairs = np.unique(np.vstack(touching), axis=0)
        pairs = pairs[np.isin(pairs[:, 1], list(ink_ids))]
        ids, counts = np.unique(pairs[:, 0], return_counts=True)
        bridges = [i for i, c in zip(ids, counts) if c > 1]
        if bridges:
            problems.append((layer_name, "gaps between separate shapes too narrow for the brush",
                             centres(fill_labels, bridges, origin)))
        # a filled patch reaching far from open blank space is a long, narrow
        # slot inside one shape (shallow notches where strokes meet are fine)
        deep = filled & ~dc.spread(~closed, NOTCH * dc.PPM)
        if deep.any():
            problems.append((layer_name, f"slots too narrow for the brush (deeper than {NOTCH} mm)",
                             patches(deep, origin)))

        # 3. holes: every enclosed blank area must stay open
        blank, edge_ids = dc.label(~ink, False)
        holes = dc.real_ids(blank) - edge_ids
        if holes:
            shut = sorted(holes - set(np.unique(blank[~closed]).tolist()))
            if shut:
                problems.append((layer_name, "holes too small for the brush",
                                 centres(blank, shut, origin)))
    return problems


def bare_metal(board_path, origin, tmp):
    """Check 5: every opening drawn in the solder mask (the gold or silver
    accents) must lie wholly over copper, so it shows the finish and not bare
    board. The openings are drawn from the board's own geometry; the copper
    is KiCad's plot of that side (pads, tracks and the filled ground plane).
    Returns a list of (side, area mm2 of openings, places not over copper)."""
    board = pcbnew.LoadBoard(board_path)
    out = []
    for mask, copper in ((pcbnew.F_Mask, "F.Cu"), (pcbnew.B_Mask, "B.Cu")):
        els, _ = collect(board, mask)
        if not els:
            continue
        cu = plot(board_path, copper + ",Edge.Cuts", tmp, copper)
        edge = plot(board_path, "Edge.Cuts", tmp, "edge", threshold=0.05)
        cu &= ~dc.spread(edge, 1.5)
        H, W = cu.shape
        img = Image.new("L", (W, H), 0)
        draw = ImageDraw.Draw(img)
        P = lambda x, y: ((x - origin[0]) * dc.PPM, (y - origin[1]) * dc.PPM)  # noqa: E731
        for e in els:
            for loops, _ in e.fills:
                draw.polygon([P(x, y) for x, y in loops[0]], fill=255)
            for x1, y1, x2, y2, r in e.S:
                if r > 0:                         # lines and dots
                    draw.line([P(x1, y1), P(x2, y2)], fill=255, width=max(1, round(2 * r * dc.PPM)))
                    for x, y in ((x1, y1), (x2, y2)):
                        cx, cy = P(x, y)
                        rr = r * dc.PPM
                        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=255)
        opening = np.asarray(img) > 127
        # allow two pixels (0.02 mm) for the two pictures' edge smoothing
        bare = dc.shrink(opening, 2) & ~cu
        out.append((copper[0], opening.sum() / dc.PPM ** 2, patches(bare, origin)))
    return out


def tab_holes(W, H):
    """Where the panel's break-away tabs drill their 0.5 mm holes into one
    board (positions from build_pcb.py), in board mm. Every board in the
    panel gets the same holes, each with an opening in the solder mask on
    both sides."""
    import build_pcb as bp
    n = int((bp.TAB_W - 0.5) // bp.BITE_PITCH) + 1
    offs = [-(n - 1) * bp.BITE_PITCH / 2 + i * bp.BITE_PITCH for i in range(n)]
    holes = []
    for tx in bp.TABS_LONG:
        for d in offs:
            holes += [(tx + d, bp.BITE_INSET), (tx + d, H - bp.BITE_INSET)]
    for ty in bp.TABS_SHORT:
        for d in offs:
            holes += [(bp.BITE_INSET, ty + d), (W - bp.BITE_INSET, ty + d)]
    return holes


def silk_to_openings(board_path, origin, tmp, size, tabs=True):
    """Check 6: all silkscreen, text included, at least CLEAR from every
    opening in the solder mask on its side: the pads, the drawn openings and
    (with tabs) the panel's tab holes. KiCad only reports silkscreen that
    actually overlaps an opening. Returns (side, places too close)."""
    edge = plot(board_path, "Edge.Cuts", tmp, "edge", threshold=0.05)
    away = ~dc.spread(edge, 1.5)
    out = []
    for silk_name, mask_name in (("F.SilkS", "F.Mask"), ("B.SilkS", "B.Mask")):
        silk = plot(board_path, silk_name + ",Edge.Cuts", tmp, silk_name) & away
        mask = plot(board_path, mask_name + ",Edge.Cuts", tmp, mask_name) & away
        if tabs:
            img = Image.fromarray(mask.astype(np.uint8) * 255)
            draw = ImageDraw.Draw(img)
            for x, y in tab_holes(*size):
                cx, cy = (x - origin[0]) * dc.PPM, (y - origin[1]) * dc.PPM
                r = 0.25 * dc.PPM
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
            mask = np.asarray(img) > 127
        # one pixel (0.01 mm) allowed for the two pictures' edge smoothing
        near = silk & dc.spread(mask, CLEAR * dc.PPM - 1)
        out.append((silk_name, patches(near, origin)))
    return out


def narrowest_stroke(el, opposite_within=20):
    """Narrowest stroke (mm) in an element drawn as filled outlines (the
    letters of a title). From the middle of every edge of every outline, a
    ray goes straight into the ink until it comes out the other side; its
    length is the stroke's width there.

    The two sides of a stroke run opposite ways, so a ray only counts if it
    comes out through an edge running within `opposite_within` degrees of
    the opposite way. A ray that leaves through an edge at a steep angle has
    cut across a corner instead (a pointed tip, where any ray is short).
    Returns (width, where)."""
    best = (math.inf, None)
    cos_lim = math.cos(math.radians(opposite_within))
    for loops, _ in el.fills:
        edges = [(p, q) for lp in loops for p, q in zip(lp, np.roll(lp, -1, axis=0))]
        # KiCad stores a letter with a hole as one outline cut open to the
        # hole along a pair of edges running both ways: drop those pairs
        keyed = {(tuple(np.round(p, 6)), tuple(np.round(q, 6))) for p, q in edges}
        edges = [(p, q) for p, q in edges
                 if (tuple(np.round(q, 6)), tuple(np.round(p, 6))) not in keyed]
        if not edges:
            continue
        E = np.array([[p[0], p[1], q[0], q[1]] for p, q in edges])
        d = E[:, 2:] - E[:, :2]
        L = np.hypot(d[:, 0], d[:, 1])
        E, d, L = E[L > 1e-6], d[L > 1e-6], L[L > 1e-6]
        mid, unit = (E[:, :2] + E[:, 2:]) / 2, d / L[:, None]
        nrm = np.stack([-unit[:, 1], unit[:, 0]], 1)
        # point the normals into the ink (even-odd test over all the edges)
        probe = mid + 1e-4 * nrm
        px, py = probe[:, 0:1], probe[:, 1:2]
        x1, y1, x2, y2 = (E[None, :, i] for i in range(4))
        straddles = (y1 > py) != (y2 > py)
        xs = x1 + (py - y1) * (x2 - x1) / np.where(y2 != y1, y2 - y1, 1.0)
        into = (np.count_nonzero(straddles & (px < xs), axis=1) % 2) == 1
        nrm[~into] *= -1
        # ray from each middle along its normal: the first edge it crosses
        ox, oy, rx, ry = mid[:, 0:1], mid[:, 1:2], nrm[:, 0:1], nrm[:, 1:2]
        ex, ey = x2 - x1, y2 - y1
        den = rx * ey - ry * ex
        safe = np.where(np.abs(den) > 1e-12, den, 1.0)
        t = ((x1 - ox) * ey - (y1 - oy) * ex) / safe        # along the ray
        u = ((x1 - ox) * ry - (y1 - oy) * rx) / safe        # along the edge
        hit = (np.abs(den) > 1e-12) & (t > 1e-6) & (u >= 0) & (u <= 1)
        np.fill_diagonal(hit, False)
        t = np.where(hit, t, np.inf)
        first = np.argmin(t, axis=1)
        length = t[np.arange(len(t)), first]
        # keep the rays that came out through an opposite-running side
        facing = (unit * unit[first]).sum(axis=1) < -cos_lim
        length = np.where(facing, length, np.inf)
        i = int(np.argmin(length))
        if length[i] < best[0]:
            best = (float(length[i]), (round(float(mid[i, 0]), 2), round(float(mid[i, 1]), 2)))
    return best


def letter_gaps(el, reach=0.6):
    """Gaps between the separate pieces of a title (its letters, and the
    parts of letters such as the two dots of a colon), measured exactly.
    Returns (narrowest gap, where), looking only at pieces within `reach` mm
    of each other (letters further apart can't be the narrowest)."""
    pieces = []
    for loops, box in el.fills:
        p = Element(el.name, True)
        p.fill([[tuple(pt) for pt in lp] for lp in loops])
        p.finish()
        pieces.append(p)
    best = (math.inf, None)
    for i, a in enumerate(pieces):
        for b in pieces[i + 1:]:
            if (a.box[0] > b.box[2] + reach or b.box[0] > a.box[2] + reach
                    or a.box[1] > b.box[3] + reach or b.box[1] > a.box[3] + reach):
                continue
            g = gap(a, b, reach)
            if g[0] < best[0]:
                best = g
    return best


# ----------------------------------------------------------------- main ---
def check(board_path, pixels=True, quiet=False, with_text=False, tabs=True):
    """Run the checks on one board, print a report, and return the number of
    problems found."""
    board = pcbnew.LoadBoard(board_path)
    bb = board.GetBoardEdgesBoundingBox()
    x0, y0 = ToMM(bb.GetX()), ToMM(bb.GetY())
    right = x0 + ToMM(bb.GetWidth())
    say = (lambda *a: None) if quiet else print
    say(os.path.basename(board_path))
    n = 0
    for layer_name, layer in LAYERS:
        els, widths = collect(board, layer)
        close = spacing(els)
        n += len(close) + len(widths)
        say(f"  {layer_name}: {len(els)} drawn elements; "
            + ("all at least 0.15 mm apart" if not close else f"{len(close)} pairs too close")
            + ("; every line and dot at least 0.15 mm wide" if not widths
               else f"; {len(widths)} lines or dots too thin"))
        for g, a, b, (x, y) in close[:40]:
            view = f"; {right - x + x0:.2f} seen from below" if layer == pcbnew.B_SilkS else ""
            say(f"      {g:.3f} mm  {a!r} and {b!r} near ({x:.2f}, {y:.2f}{view})")
        for name, w, where in widths[:20]:
            say(f"      {w:.3f} mm wide: {name!r} near {where}")
        titles = [e for e in els if e.name.startswith("title ") and e.fills]
        if titles:
            strokes = sorted((*narrowest_stroke(e), e.name[6:]) for e in titles)
            gaps = sorted((*letter_gaps(e), e.name[6:]) for e in titles)
            thin = [t for t in strokes if t[0] < WIDTH - 1e-6]
            tight = [t for t in gaps if t[0] < CLEAR - 1e-6]
            n += len(thin) + len(tight)
            (w, where, name), (g, gw, gname) = strokes[0], gaps[0]
            apart = (f"letters at least {g:.3f} mm apart ({gname!r} near "
                     f"({gw[0]:.2f}, {gw[1]:.2f}))" if gw else "letters over 0.6 mm apart")
            say(f"      real-font titles: narrowest stroke {w:.3f} mm ({name!r} near {where}); "
                + apart)
            for w, where, name in thin:
                say(f"      stroke UNDER {WIDTH} mm: {w:.3f} mm in {name!r} near {where}")
            for g, gw, name in tight:
                say(f"      letters closer than {CLEAR} mm: {g:.3f} mm in {name!r} near "
                    f"({gw[0]:.2f}, {gw[1]:.2f})")
    if pixels:
        with tempfile.TemporaryDirectory() as tmp:
            found = pixel_checks(board_path, (x0, y0), tmp, text=with_text)
        n += sum(len(p) for _, _, p in found)
        span = 2 * int(dc.brush_radius(BRUSH)) + 1
        what = "everything" if with_text else "the drawn shapes"
        if not found:
            say(f"  KiCad's plot of {what}, both sides ({1 / dc.PPM:.2f} mm pixels, a brush "
                f"{span} pixels across): lines, necks, gaps, slots and holes all pass")
        for layer_name, problem, places in found:
            say(f"  KiCad's plot, {layer_name}: {len(places)} {problem}: "
                + ", ".join(f"({x:.2f}, {y:.2f})" for x, y in places[:12]))
    if pixels:
        with tempfile.TemporaryDirectory() as tmp:
            near = silk_to_openings(board_path, (x0, y0), tmp,
                                    (ToMM(bb.GetWidth()) + 2 * x0, ToMM(bb.GetHeight()) + 2 * y0),
                                    tabs=tabs)
        for side, places in near:
            n += len(places)
            say(f"  {side} to pads, openings{' and tab holes' if tabs else ''}: "
                + ("all at least 0.15 mm clear" if not places else
                   f"{len(places)} places closer than 0.15 mm: "
                   + ", ".join(f"({x:.2f}, {y:.2f})" for x, y in places[:12])))
        with tempfile.TemporaryDirectory() as tmp:
            metal = bare_metal(board_path, (x0, y0), tmp)
        for side, area, places in metal:
            n += len(places)
            say(f"  solder-mask openings, {'top' if side == 'F' else 'bottom'}: {area:.2f} mm2, "
                + ("all over copper (they show the finish)" if not places else
                   f"{len(places)} places over bare board: "
                   + ", ".join(f"({x:.2f}, {y:.2f})" for x, y in places[:12])))
    say(f"  {'no problems' if n == 0 else str(n) + ' problems'}")
    return n


def main():
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    total = sum(check(p, pixels="--no-pixels" not in sys.argv,
                      with_text="--with-text" in sys.argv,
                      tabs="--no-tabs" not in sys.argv) for p in paths)
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
