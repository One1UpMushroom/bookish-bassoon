"""Reads the exported factory files back and compares them with the board.

KiCad wrote these files, so this is not a second opinion on the design; it
is a check that what goes to the factory is what was checked: every hole
the board has, at the size and place the board has it, and an outline of the
right size with nothing drilled outside it.

Needs `pcbnew` for the board side; the Excellon and Gerber parsing is plain Python.
"""
import os
import re

import pcbnew

import gen_pcb


def read_excellon(path):
    """[(x, y, diameter)] in board millimetres (origin top-left, y down)."""
    tools, holes, tool = {}, [], None
    metric = False
    for line in open(path):
        line = line.strip()
        if line == 'METRIC' or line.startswith('METRIC,'):
            metric = True
        m = re.match(r'^T(\d+)C([\d.]+)', line)
        if m:
            tools[int(m.group(1))] = float(m.group(2))
            continue
        m = re.match(r'^T(\d+)$', line)
        if m:
            tool = int(m.group(1))
            continue
        m = re.match(r'^X(-?[\d.]+)Y(-?[\d.]+)', line)
        if m and tool:
            assert '.' in m.group(1), 'expected decimal coordinates in %s' % path
            holes.append((float(m.group(1)) - gen_pcb.OX, -float(m.group(2)) - gen_pcb.OY, tools[tool]))
    assert metric, '%s is not in millimetres' % path
    return holes


def read_gerber_extent(path):
    """Bounding box (x0, y0, x1, y1) of all coordinates, in board millimetres."""
    text = open(path).read()
    m = re.search(r'%FSLAX(\d)(\d)Y(\d)(\d)\*%', text)
    assert m and '%MOMM*%' in text, 'unexpected Gerber format in %s' % path
    scale = 10.0 ** int(m.group(2))
    xs, ys = [], []
    for mm in re.finditer(r'X(-?\d+)Y(-?\d+)(?:I-?\d+J-?\d+)?D0[123]\*', text):   # draw/move/flash only
        xs.append(int(mm.group(1)) / scale - gen_pcb.OX)
        ys.append(-int(mm.group(2)) / scale - gen_pcb.OY)
    return min(xs), min(ys), max(xs), max(ys)


def board_holes(pcb_path):
    board = pcbnew.LoadBoard(pcb_path)
    mm = pcbnew.ToMM
    plated, unplated = [], []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            d = mm(pad.GetDrillSize().x)
            if d <= 0:
                continue
            pos = pad.GetPosition()
            hole = (mm(pos.x) - gen_pcb.OX, mm(pos.y) - gen_pcb.OY, d)
            (unplated if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else plated).append(hole)
    return plated, unplated


def same_holes(a, b, tol=0.005):
    key = lambda h: (round(h[0], 2), round(h[1], 2), round(h[2], 3))  # noqa: E731
    a, b = sorted(a, key=key), sorted(b, key=key)
    if len(a) != len(b):
        return False
    return all(abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol and abs(p[2] - q[2]) <= tol
               for p, q in zip(a, b))


def verify(pcb_path, fab_dir, project):
    """Returns (problems, summary lines)."""
    problems, notes = [], []
    need = ['F_Cu.gtl', 'B_Cu.gbl', 'F_Mask.gts', 'B_Mask.gbs', 'F_Silkscreen.gto', 'B_Silkscreen.gbo',
            'Edge_Cuts.gm1', 'PTH.drl', 'NPTH.drl']
    for suffix in need:
        path = os.path.join(fab_dir, '%s-%s' % (project, suffix))
        if not os.path.exists(path) or os.path.getsize(path) < 200:
            problems.append('missing or empty: %s' % os.path.basename(path))
    if problems:
        return problems, notes

    plated, unplated = board_holes(pcb_path)
    pth = read_excellon(os.path.join(fab_dir, project + '-PTH.drl'))
    npth = read_excellon(os.path.join(fab_dir, project + '-NPTH.drl'))
    if not same_holes(plated, pth):
        problems.append('plated holes differ: board %d, drill file %d' % (len(plated), len(pth)))
    if not same_holes(unplated, npth):
        problems.append('unplated holes differ: board %d, drill file %d' % (len(unplated), len(npth)))
    sizes = {}
    for _, _, d in pth:
        sizes[d] = sizes.get(d, 0) + 1
    notes.append('%d plated holes (%s), %d unplated: same as the board' % (
        len(pth), ', '.join('%d x %.2f mm' % (n, d) for d, n in sorted(sizes.items())), len(npth)))

    x0, y0, x1, y1 = read_gerber_extent(os.path.join(fab_dir, project + '-Edge_Cuts.gm1'))
    if max(abs(x0), abs(y0), abs(x1 - gen_pcb.W), abs(y1 - gen_pcb.H)) > 0.06:
        problems.append('outline spans (%.2f, %.2f)-(%.2f, %.2f), expected 0,0-%.2f,%.2f' % (
            x0, y0, x1, y1, gen_pcb.W, gen_pcb.H))
    notes.append('outline %.2f x %.2f mm' % (x1 - x0, y1 - y0))
    for x, y, d in pth + npth:
        if min(x - d / 2, y - d / 2, gen_pcb.W - x - d / 2, gen_pcb.H - y - d / 2) < 0.8:
            problems.append('hole at (%.2f, %.2f) is within 0.8 mm of the edge' % (x, y))
    for suffix in ('F_Cu.gtl', 'B_Cu.gbl', 'F_Mask.gts', 'B_Mask.gbs', 'F_Silkscreen.gto', 'B_Silkscreen.gbo'):
        a0, b0, a1, b1 = read_gerber_extent(os.path.join(fab_dir, '%s-%s' % (project, suffix)))
        if a0 < -0.1 or b0 < -0.1 or a1 > gen_pcb.W + 0.1 or b1 > gen_pcb.H + 0.1:
            problems.append('%s reaches outside the outline: (%.2f, %.2f)-(%.2f, %.2f)' % (suffix, a0, b0, a1, b1))
    return problems, notes
