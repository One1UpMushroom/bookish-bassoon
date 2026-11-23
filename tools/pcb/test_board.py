#!/usr/bin/env python3
"""Tests the driver board's factory files on their own terms.

    <python with pcbnew, gerbonara and shapely> tools/pcb/test_board.py

The Gerber and drill files are read back as shapes, independently of KiCad: the copper is
traced into nets (pads joined by copper, the two layers joined by plated holes) and compared
with the circuit in design.py. The shapes are then measured against the board maker's limits,
the circuit's currents and voltages, the parts' leads, and the firmware's pin map. Writes
hardware/tasklamp-driver/board-tests.json and exits non-zero if anything fails.
"""
import json
import math
import os
import re
import sys
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, 'hardware', 'tasklamp-driver')
FAB = os.path.join(OUT, 'gerbers')
PROJECT = 'tasklamp-driver'
sys.path.insert(0, HERE)

import pcbnew  # noqa: E402
from gerbonara import ExcellonFile, GerberFile  # noqa: E402
from gerbonara.utils import MM  # noqa: E402
from shapely import affinity  # noqa: E402
from shapely.geometry import LineString, Point, Polygon, box  # noqa: E402
from shapely.ops import polygonize, unary_union  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

import design  # noqa: E402

warnings.filterwarnings('ignore', category=SyntaxWarning)   # gerbonara notes KiCad's header order

# The board maker's limits. PCBWay's standard service allows 0.1 mm (4 mil) traces and gaps
# and a 0.15 mm annular ring; these limits sit above that on purpose, so nothing here relies on
# the edge of what the factory can do. The mask dam is the black-mask figure (black needs a
# wider web between openings than green).
LIMITS = {
    'trace_mm': 0.15, 'gap_mm': 0.15, 'ring_mm': 0.15, 'drill_mm': 0.30, 'hole_gap_mm': 0.50,
    'copper_edge_mm': 0.30, 'hole_edge_mm': 0.50, 'mask_dam_mm': 0.13, 'silk_line_mm': 0.15,
    'silk_text_mm': 0.80, 'hole_tol_mm': 0.08,
}
COPPER_OZ_MIL = 1.378        # 1 oz copper is 35 um = 1.378 mil thick
RHO_CU = 1.72e-8 * 1.1       # copper resistivity, ohm m, at about 45 C
IPC_B2_24V_MM = 0.10         # IPC-2221B table 6-1, B2 (outer layer, uncoated), 16-30 V

results = {}
fails = []


def record(name, ok, detail, data=None, warn=False):
    status = 'PASS' if ok else ('WARN' if warn else 'FAIL')
    results[name] = {'status': status, 'detail': detail, 'data': data or {}}
    print('  %s %-34s %s' % (status, name, detail))
    if status == 'FAIL':
        fails.append(name)


# =============================================================================================
# Gerber shapes
def arc_points(p, step_deg=5.0):
    a1 = math.atan2(p.y1 - p.cy, p.x1 - p.cx)
    a2 = math.atan2(p.y2 - p.cy, p.x2 - p.cx)
    r = math.hypot(p.x1 - p.cx, p.y1 - p.cy)
    if p.is_circle:
        sweep = -2 * math.pi if p.clockwise else 2 * math.pi
    else:
        sweep = a2 - a1
        if p.clockwise and sweep > 0:
            sweep -= 2 * math.pi
        if not p.clockwise and sweep < 0:
            sweep += 2 * math.pi
    n = max(2, int(abs(math.degrees(sweep)) / step_deg) + 1)
    return [(p.cx + r * math.cos(a1 + sweep * i / (n - 1)), p.cy + r * math.sin(a1 + sweep * i / (n - 1)))
            for i in range(n)]


def to_shape(p):
    kind = type(p).__name__
    if kind == 'Circle':
        return Point(p.x, p.y).buffer(p.r, quad_segs=32)
    if kind == 'Line':
        if math.isclose(p.x1, p.x2, abs_tol=1e-9) and math.isclose(p.y1, p.y2, abs_tol=1e-9):
            return Point(p.x1, p.y1).buffer(p.width / 2, quad_segs=32)
        return LineString([(p.x1, p.y1), (p.x2, p.y2)]).buffer(p.width / 2, quad_segs=16)
    if kind == 'Arc':
        return LineString(arc_points(p)).buffer(max(p.width, 1e-4) / 2, quad_segs=16)
    if kind == 'Rectangle':
        return affinity.rotate(box(p.x - p.w / 2, p.y - p.h / 2, p.x + p.w / 2, p.y + p.h / 2), p.rotation,
                               origin=(p.x, p.y), use_radians=True)
    if kind == 'ArcPoly':
        pts = p.approximate_arcs(max_error=0.002) if any(c is not None for c in (p.arc_centers or [])) else p.outline
        poly = Polygon(list(pts) if not hasattr(pts, 'outline') else pts.outline)
        return poly if poly.is_valid else poly.buffer(0)
    raise ValueError('unknown primitive ' + kind)


class Layer:
    """One Gerber file as shapes: the whole layer (dark minus clear, in order), its flashes
    (pads and mask openings) and its stroked lines (tracks, silk strokes)."""

    def __init__(self, name):
        self.path = os.path.join(FAB, '%s-%s' % (PROJECT, name))
        g = GerberFile.open(self.path)
        self.flashes, self.lines, self.regions = [], [], []
        geom, batch = None, []
        for obj in g.objects:
            kind = type(obj).__name__
            for prim in obj.to_primitives(MM):
                shp = to_shape(prim)
                if prim.polarity_dark:
                    batch.append(shp)
                    if kind == 'Flash':
                        self.flashes.append(shp)
                    elif kind in ('Line', 'Arc'):
                        self.lines.append((prim, shp))
                    elif kind == 'Region':
                        self.regions.append(shp)
                else:
                    if batch:
                        geom = unary_union(batch if geom is None else [geom] + batch)
                        batch = []
                    if geom is not None:
                        geom = geom.difference(shp)
        if batch:
            geom = unary_union(batch if geom is None else [geom] + batch)
        self.geom = geom

    def islands(self):
        g = self.geom
        return list(g.geoms) if g.geom_type == 'MultiPolygon' else [g]


def drills(name):
    path = os.path.join(FAB, '%s-%s.drl' % (PROJECT, name))
    return [(o.x, o.y, o.aperture.diameter) for o in ExcellonFile.open(path).objects]


def outline():
    edge = Layer('Edge_Cuts.gm1')
    segs = [LineString([(p.x1, p.y1), (p.x2, p.y2)]) for p, _ in edge.lines]
    polys = list(polygonize(unary_union(segs)))
    return max(polys, key=lambda q: q.area), segs


# =============================================================================================
def board_pads():
    """Every pad's centre in Gerber coordinates (y up) with its reference and number."""
    board = pcbnew.LoadBoard(os.path.join(OUT, PROJECT + '.kicad_pcb'))
    pads = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            pos = pad.GetPosition()
            pads.append({'ref': fp.GetReference(), 'pin': pad.GetNumber(), 'x': pcbnew.ToMM(pos.x),
                         'y': -pcbnew.ToMM(pos.y), 'drill': pcbnew.ToMM(pad.GetDrillSize().x),
                         'fp': fp.GetFPIDAsString(), 'npth': pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH})
    return board, pads


class Find:
    def __init__(self):
        self.parent = {}

    def __call__(self, a):
        self.parent.setdefault(a, a)
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def join(self, a, b):
        self.parent[self(a)] = self(b)


def locate(tree, shapes, x, y):
    pt = Point(x, y)
    for i in tree.query(pt):
        if shapes[i].covers(pt):
            return int(i)
    return None


def test_connectivity(layers, pth, pads):
    """Trace the copper of the factory files into nets and compare them with design.py."""
    print('copper traced from the Gerbers, against the circuit')
    isl = {side: layers[side].islands() for side in ('F', 'B')}
    trees = {side: STRtree(isl[side]) for side in isl}
    groups = Find()
    for x, y, d in pth:                        # plating joins the two layers at every plated hole
        f, b = locate(trees['F'], isl['F'], x, y), locate(trees['B'], isl['B'], x, y)
        if f is not None and b is not None:
            groups.join(('F', f), ('B', b))
    pin_group = {}
    for p in pads:
        if p['npth']:
            continue
        hits = [(s, locate(trees[s], isl[s], p['x'], p['y'])) for s in ('F', 'B')]
        hits = [h for h in hits if h[1] is not None]
        pin_group['%s.%s' % (p['ref'], p['pin'])] = groups(hits[0]) if hits else None
    nets = design.netlist()
    want = {pin: net for net, pins in nets.items() for pin in pins}
    opens, shorts, missing = [], [], []
    for net, pins in nets.items():
        g = {pin_group.get(pin) for pin in pins}
        if None in g:
            missing += [pin for pin in pins if pin_group.get(pin) is None]
        if len(g - {None}) > 1:
            opens.append(net)
    by_group = {}
    for pin, g in pin_group.items():
        if g is not None and pin in want:
            by_group.setdefault(g, set()).add(want[pin])
    shorts = sorted('+'.join(sorted(s)) for s in by_group.values() if len(s) > 1)
    unused = [pin for pin in pin_group if pin not in want]
    ok = not opens and not shorts and not missing
    record('B1 nets in the Gerbers', ok,
           '%d nets, %d pins traced through %d + %d copper islands and %d plated holes: %s' % (
               len(nets), len(want), len(isl['F']), len(isl['B']), len(pth),
               'every net joined, none touching another' if ok else 'opens %s, shorts %s, unconnected %s' % (
                   opens, shorts, missing)),
           {'opens': opens, 'shorts': shorts, 'missing': missing, 'pins_not_in_design': unused})
    # copper with no pad on it (would be a stray island)
    used = {g for g in pin_group.values() if g is not None}
    stray = [(s, i) for s in ('F', 'B') for i in range(len(isl[s])) if groups((s, i)) not in used]
    record('B2 no stray copper', not stray, '%d islands carry no pad' % len(stray), {'stray': stray})
    # island -> net, for the clearance tests
    island_net = {}
    for s in ('F', 'B'):
        for i in range(len(isl[s])):
            names = by_group.get(groups((s, i)))
            island_net[(s, i)] = sorted(names)[0] if names else None
    return isl, island_net


def min_gap(shapes, labels=None, only=None):
    """Smallest distance between any two shapes (with different labels, if given)."""
    tree = STRtree(shapes)
    best = (float('inf'), None, None)
    for i, a in enumerate(shapes):
        for j in tree.query(a.buffer(2.0)):
            j = int(j)
            if j <= i:
                continue
            if labels is not None and labels[i] == labels[j]:
                continue
            if only is not None and not (only(labels[i]) or only(labels[j])):
                continue
            d = a.distance(shapes[j])
            if d < best[0]:
                best = (d, i, j)
    return best


def test_dfm(layers, pth, npth, edge_poly):
    print('manufacturing limits (from the Gerbers and drill files)')
    L = LIMITS
    widths = [p.width for side in ('F', 'B') for p, _ in layers[side].lines]
    record('B3 trace width', min(widths) >= L['trace_mm'], 'narrowest %.2f mm (limit %.2f)' % (
        min(widths), L['trace_mm']), {'min_mm': min(widths)})
    gaps = {}
    for s in ('F', 'B'):
        d, i, j = min_gap(layers[s].islands())
        gaps[s] = d
    g = min(gaps.values())
    record('B4 copper gaps', g >= L['gap_mm'], 'closest copper of different islands: %.3f mm top, %.3f mm bottom '
           '(limit %.2f)' % (gaps['F'], gaps['B'], L['gap_mm']), gaps)
    holes = [(x, y, d, True) for x, y, d in pth] + [(x, y, d, False) for x, y, d in npth]
    sizes = sorted({round(d, 3) for _, _, d, _ in holes})
    record('B5 drill sizes', min(sizes) >= L['drill_mm'], '%d holes in %d sizes, %s mm' % (
        len(holes), len(sizes), ', '.join('%g' % s for s in sizes)), {'sizes_mm': sizes})
    # annular ring: copper around each plated hole, on each side, less the hole tolerance
    rings = []
    for s in ('F', 'B'):
        isl = layers[s].islands()
        tree = STRtree(isl)
        for x, y, d in pth:
            i = locate(tree, isl, x, y)
            if i is not None:
                rings.append((isl[i].boundary.distance(Point(x, y)) - d / 2, s, x, y, d))
    worst = min(rings)
    record('B6 annular ring', worst[0] - L['hole_tol_mm'] / 2 >= L['ring_mm'],
           'smallest %.3f mm (%.3f mm with the hole at its +0.08 mm tolerance; limit %.2f), %g mm hole' % (
               worst[0], worst[0] - L['hole_tol_mm'] / 2, L['ring_mm'], worst[4]), {'min_mm': worst[0]})
    hg = min(math.hypot(a[0] - b[0], a[1] - b[1]) - (a[2] + b[2]) / 2
             for k, a in enumerate(holes) for b in holes[k + 1:])
    record('B7 hole to hole', hg >= L['hole_gap_mm'], 'closest edges %.2f mm (limit %.2f)' % (hg, L['hole_gap_mm']),
           {'min_mm': hg})
    rim = edge_poly.exterior
    ce = min(rim.distance(layers[s].geom) for s in ('F', 'B'))
    he = min(rim.distance(Point(x, y)) - d / 2 for x, y, d, _ in holes)
    record('B8 clearance to the board edge', ce >= L['copper_edge_mm'] and he >= L['hole_edge_mm'],
           'copper %.2f mm (limit %.2f), holes %.2f mm (limit %.2f)' % (ce, L['copper_edge_mm'], he,
                                                                       L['hole_edge_mm']),
           {'copper_mm': ce, 'hole_mm': he})
    inside = all(edge_poly.buffer(1e-3).contains(layers[k].geom) for k in ('F', 'B', 'FS', 'BS', 'FM', 'BM'))
    record('B9 everything inside the outline', inside, 'copper, mask and silk all lie within the board')


def test_mask_and_silk(layers, vias=()):
    print('solder mask and silkscreen')
    L = LIMITS
    worst_exp, bare = float('inf'), 0
    dams = {}
    for cu, mk in (('F', 'FM'), ('B', 'BM')):
        openings = layers[mk].islands()
        tree = STRtree(openings)
        for pad in layers[cu].flashes:
            c0 = pad.centroid
            if any(abs(c0.x - vx) < 0.01 and abs(c0.y - vy) < 0.01 for vx, vy in vias):
                continue                         # stitching vias are tented on purpose
            c = pad.representative_point()
            i = locate(tree, openings, c.x, c.y)
            if i is None or not openings[i].buffer(1e-4).contains(pad):
                bare += 1
                continue
            worst_exp = min(worst_exp, openings[i].exterior.distance(pad.exterior))
        dams[mk] = min_gap(openings)[0]
    record('B10 mask openings', bare == 0 and worst_exp >= 0.04,
           '%d pads not fully open; every opening at least %.3f mm larger than its pad (want 0.05)' % (
               bare, worst_exp), {'uncovered': bare, 'expansion_mm': worst_exp})
    dam = min(dams.values())
    record('B11 mask dams', dam >= L['mask_dam_mm'], 'narrowest web between openings %.3f mm top, %.3f mm bottom '
           '(limit %.2f, for black mask)' % (dams['FM'], dams['BM'], L['mask_dam_mm']), dams)
    over = sum(layers[sk].geom.intersection(layers[mk].geom).area for sk, mk in (('FS', 'FM'), ('BS', 'BM')))
    record('B12 no silk on pads', over < 1e-4, 'silk inside mask openings: %.4f mm2' % over, {'area_mm2': over})
    strokes = [p.width for k in ('FS', 'BS') for p, _ in layers[k].lines if p.width > 0]
    # filled lettering (the TrueType signage): any part narrower than the limit vanishes when
    # the letter is opened (shrunk, then grown back) by half the limit
    thin, total = 0.0, 0.0
    for k in ('FS', 'BS'):
        for g in layers[k].regions:
            opened = g.buffer(-L['silk_line_mm'] / 2, quad_segs=8).buffer(L['silk_line_mm'] / 2, quad_segs=8)
            thin += g.difference(opened).area
            total += g.area
    record('B13 silk line width', min(strokes) >= L['silk_line_mm'] - 1e-6 and thin / total < 0.02,
           'thinnest stroke %.2f mm (limit %.2f); in the filled lettering %.2f %% of the ink is thinner than that '
           '(rounding at sharp corners)' % (min(strokes), L['silk_line_mm'], 100 * thin / total),
           {'min_stroke_mm': min(strokes), 'thin_fraction': thin / total})


def test_text(board):
    small = []
    for item in board.GetDrawings():
        if item.GetClass() in ('PCB_TEXT', 'PTEXT'):
            small.append((pcbnew.ToMM(item.GetTextHeight()), item.GetText()))
    for fp in board.GetFootprints():
        for item in [fp.Reference(), fp.Value()] + [g for g in fp.GraphicalItems() if g.GetClass() == 'PCB_TEXT']:
            if item.IsVisible() and item.GetLayerName() in ('F.Silkscreen', 'B.Silkscreen'):
                small.append((pcbnew.ToMM(item.GetTextHeight()), item.GetText()))
    lo = min(small)
    record('B14 text height', lo[0] >= LIMITS['silk_text_mm'], 'smallest lettering %.2f mm ("%s"; limit %.2f)' % (
        lo[0], lo[1], LIMITS['silk_text_mm']), {'min_mm': lo[0]})


# =============================================================================================
def net_currents():
    """Each net's current with everything on, from the circuit simulation where it gives one."""
    sim = os.path.join(OUT, 'sim', 'results.json')
    t1 = json.load(open(sim))['tests']['T1 all channels on, 3.29 V gates']['data']['fit']
    i_all = t1['i_total']
    cur = {'VIN': i_all, 'VFUSE': i_all, '+24V': i_all, 'GND': i_all, '+5V': 0.10, 'QT_5V': 0.10, '+3V3': 0.09,
           'SW': 0.10}
    for ch, i in t1['i_ch'].items():
        cur['OUT_' + ch] = i
    return cur


def test_current(board):
    print('currents and voltages')
    cur = net_currents()
    tracks = {}
    for t in board.GetTracks():
        net = t.GetNetname()
        w = pcbnew.ToMM(t.GetWidth())
        length = pcbnew.ToMM(t.GetLength())
        r = RHO_CU * length * 1e-3 / (w * 1e-3 * 35e-6)
        e = tracks.setdefault(net, {'min_w': w, 'r': 0.0, 'len': 0.0})
        e['min_w'] = min(e['min_w'], w)
        e['r'] += r
        e['len'] += length
    rows = []
    for net, e in tracks.items():
        i = cur.get(net, 0.01)
        area = e['min_w'] / 0.0254 * COPPER_OZ_MIL                    # cross-section in square mils
        rise = (i / (0.048 * area ** 0.725)) ** (1 / 0.44)              # IPC-2221, outer layer
        rows.append({'net': net, 'amps': i, 'min_width_mm': e['min_w'], 'rise_K': rise,
                     'track_mohm': e['r'] * 1e3, 'drop_mV': e['r'] * i * 1e3})
    hot = max(rows, key=lambda r: r['rise_K'])
    drop = max(rows, key=lambda r: r['drop_mV'])
    record('B15 track heating', hot['rise_K'] < 10,
           'worst %s: %.2f A in %.1f mm, %.1f K above the board (IPC-2221; limit 10 K)' % (
               hot['net'], hot['amps'], hot['min_width_mm'], hot['rise_K']), {'rows': rows})
    record('B16 voltage drop in the tracks', drop['drop_mV'] < 100,
           'worst %s: %.0f mohm of track at %.2f A, %.0f mV at most (all of its track in series)' % (
               drop['net'], drop['track_mohm'], drop['amps'], drop['drop_mV']), {})


def test_clearance_by_voltage(isl, island_net):
    hv = {'VIN', 'VFUSE', '+24V', 'SW', 'BOOT'} | {'OUT_' + c for c in design.CHANNELS}   # SW swings to 24 V
    worst = float('inf')
    for s in ('F', 'B'):
        shapes = isl[s]
        labels = [island_net[(s, i)] for i in range(len(shapes))]
        d, i, j = min_gap(shapes, labels, only=lambda n: n in hv)
        worst = min(worst, d)
    record('B17 24 V clearance', worst >= IPC_B2_24V_MM,
           'closest copper between a 24 V net and any other net: %.2f mm (IPC-2221B asks %.2f mm at 16-30 V)' % (
               worst, IPC_B2_24V_MM), {'min_mm': worst})


# =============================================================================================
# Parts against their footprints. Lead sizes from the parts' drawings. A round lead fits when
# it passes the hole at the bottom of its tolerance with 0.1 mm to spare for solder; a flat or
# square lead (solder fills along its sides) when its diagonal passes.
LEADS = {
    'Package_TO_SOT_THT:TO-220-3_Vertical':
        ('IRLB8721 (TO-220AB)', 'flat', math.hypot(0.81, 0.46), math.hypot(1.02, 0.61),
         'lead 0.81 x 0.46 mm typical, 1.02 x 0.61 mm maximum (TO-220AB drawing)'),
    'Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal': ('1N5819 (DO-41)', 'round', 0.80, 0.864, 'lead dia. 0.71-0.864 mm'),
    'Diode_THT:D_DO-15_P12.70mm_Horizontal': ('P6KE30A (DO-15)', 'round', 0.80, 0.864, 'lead dia. 0.71-0.864 mm'),
    'Diode_THT:D_DO-201AD_P15.24mm_Horizontal': ('SB560 (DO-201AD)', 'round', 1.27, 1.32, 'lead dia. 1.22-1.32 mm'),
    'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal': ('1/4 W resistor', 'round', 0.55, 0.60,
                                                                       'lead dia. 0.5-0.6 mm'),
    'Capacitor_THT:CP_Radial_D8.0mm_P3.50mm': ('100 uF 50 V, 8 mm', 'round', 0.6, 0.6, 'lead dia. 0.6 mm'),
    'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm': ('10 uF 50 V, 5 mm', 'round', 0.5, 0.5, 'lead dia. 0.5 mm'),
    'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm': ('100 nF ceramic', 'round', 0.5, 0.6, 'lead dia. 0.5-0.6 mm'),
    'Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical': ('0.1 in header', 'square', math.hypot(0.64, 0.64),
                                                                    math.hypot(0.64, 0.64), '0.64 mm square'),
    'TaskLamp:QTPy_RP2040_Socket': ('Sullins PPTC071LFBN-RC', 'square', math.hypot(0.64, 0.64),
                                    math.hypot(0.64, 0.64), '0.64 mm square tails'),
    'TaskLamp:C_Dual_THT-P5.08_or_0805-1206': ('radial ceramic, 5.08 mm', 'round', 0.5, 0.6, 'lead dia. 0.5-0.6 mm'),
}
# drawn from the maker's own recommended hole, not checked against a lead size here
MAKER_HOLE = {
    'TerminalBlock_Phoenix': 'Phoenix MKDS 1,5 recommends a 1.3 mm hole; the On Shore OSTTC blocks are made '
                             'to the same footprint',
    'Fuse:Fuseholder_Blade_Mini_Keystone_3568': "Keystone's drawing for the 3568",
    'Converter_DCDC:Converter_DCDC_Murata_OKI-78SR_Vertical': "Murata's footprint for the OKI-78SR",
    'TestPoint': 'test pad, no lead', 'MountingHole': 'M3 screw',
    'TaskLamp:HSOIC-8-1EP_HandSolder_BackHole': 'plated hole in the thermal pad, for soldering it from the back',
}


def test_footprints(pads):
    print('parts against their footprints')
    seen = {}
    for p in pads:
        if p['drill'] > 0:                       # surface-mount pads have no hole to fit
            seen.setdefault(p['fp'], set()).add(p['drill'])
    tight, bad, rows = [], [], []
    for fp, drill_set in sorted(seen.items()):
        drill = min(drill_set)
        if fp in LEADS:
            part, kind, typ, mx, note = LEADS[fp]
            low = drill - LIMITS['hole_tol_mm']
            room = 0.1 if kind == 'round' else 0.0
            status = 'fit' if low >= mx + room else ('tight' if low >= typ + room else 'no')
            rows.append({'footprint': fp, 'part': part, 'drill_mm': drill, 'lead_typ_mm': typ, 'lead_max_mm': mx,
                         'status': status, 'note': note})
            if status == 'tight':
                tight.append('%s (%.2f mm hole; %s)' % (part, drill, note))
            elif status == 'no':
                bad.append(part)
        else:
            why = next((v for k, v in MAKER_HOLE.items() if fp.startswith(k) or k in fp), None)
            rows.append({'footprint': fp, 'drill_mm': drill, 'status': 'maker' if why else 'unchecked',
                         'note': why or ''})
            if not why:
                bad.append(fp)
    record('B18 leads fit their holes', not bad and not tight,
           ('every lead fits with the hole at its smallest' if not tight else
            'fits only for typical leads: ' + '; '.join(tight)) + (('; does not fit: ' + ', '.join(bad)) if bad else ''),
           {'rows': rows}, warn=not bad)


def test_terminals(board, edge_poly):
    """Screw terminals: the wire must enter from the board edge. In KiCad's Phoenix MKDS
    horizontal footprints the entry is on the +y side at 0 degrees (the front bevel lines)."""
    worst = []
    minx, miny, maxx, maxy = edge_poly.bounds
    for fp in board.GetFootprints():
        if not fp.GetFPIDAsString().startswith('TerminalBlock'):
            continue
        rot = fp.GetOrientationDegrees() % 360
        pos = fp.GetPosition()
        x, y = pcbnew.ToMM(pos.x), -pcbnew.ToMM(pos.y)
        # direction the wire comes from, in Gerber coordinates (y up): 0 deg -> board +y -> Gerber -y
        dx, dy = {0: (0, -1), 90: (-1, 0), 180: (0, 1), 270: (1, 0)}[round(rot) % 360]
        to_edge = {(0, -1): y - miny, (0, 1): maxy - y, (-1, 0): x - minx, (1, 0): maxx - x}[(dx, dy)]
        others = min(y - miny, maxy - y, x - minx, maxx - x)
        worst.append((fp.GetReference(), round(to_edge, 2), round(others, 2)))
    ok = all(abs(t - o) < 1e-6 for _, t, o in worst)
    record('B19 wires enter from the edge', ok, ', '.join('%s %.1f mm from its edge' % (r, t) for r, t, _ in worst),
           {'terminals': worst})


# =============================================================================================
QTPY_GPIO = {'A0': 29, 'A1': 28, 'A2': 27, 'A3': 26, 'SDA': 24, 'SCL': 25, 'TX': 20, 'RX': 5,
             'SCK': 6, 'MI': 4, 'MO': 3}           # Adafruit QT Py RP2040 pinout


def test_firmware_pins():
    print('firmware against the board')
    src = open(os.path.join(ROOT, 'firmware', 'TaskLamp', 'config.h')).read()
    # the five LED pins, one per line, each followed by a comment
    block = re.search(r'kLedPins\[5\]\s*=\s*\{([^}]*)\}', src).group(1)
    led = [int(m) for m in re.findall(r'^\s*(\d+),', block, re.M)]

    def const(name):
        return int(re.search(r'k%s\s*=\s*(-?\d+)' % name, src).group(1))
    want = {const('TftCs'): 'TFT_CS', const('TftDc'): 'TFT_DC', const('SpiSck'): 'TFT_SCK',
            const('SpiMosi'): 'TFT_MOSI', const('TftBacklight'): 'TFT_LITE', const('EncIntPin'): 'ENC_INT'}
    for gpio, ch in zip(led, design.CHANNELS):
        want[gpio] = 'PWM_' + ch
    board = {QTPY_GPIO[pad]: net for _, (pad, net) in design.QTPY_PINS.items() if pad in QTPY_GPIO}
    wrong = ['GP%d: firmware %s, board %s' % (g, n, board.get(g)) for g, n in want.items() if board.get(g) != n]
    record('B20 pin map', not wrong, 'all %d firmware pins land on the right nets%s' % (
        len(want), '' if not wrong else ': ' + '; '.join(wrong)), {'wrong': wrong})
    # RP2040: GPIO n drives PWM slice (n >> 1) & 7, output A or B by n & 1; GPIOs 16 apart share one
    outs = {}
    for g in led + [const('TftBacklight')]:
        outs.setdefault(((g >> 1) & 7, 'AB'[g & 1]), []).append(g)
    clash = {'%d%s' % k: v for k, v in outs.items() if len(v) > 1}
    record('B21 one PWM output per light', not clash, 'outputs %s' % ', '.join(
        'GP%d=%d%s' % (g, (g >> 1) & 7, 'AB'[g & 1]) for g in led + [const('TftBacklight')]), {'clash': clash})


# =============================================================================================
# Pinouts from the parts' datasheets: pin number -> what must be connected there.
PINOUTS = {
    'IRLB8721 (gate, drain, source)': (['Q1', 'Q2', 'Q3', 'Q4', 'Q5'],
                                       lambda ch: {'1': 'GATE_' + ch, '2': 'OUT_' + ch, '3': 'GND'}),
    '1N5819 clamps (1 = cathode band to +24 V)': (['D1', 'D2', 'D3', 'D4', 'D5'],
                                                  lambda ch: {'1': '+24V', '2': 'OUT_' + ch}),
    'SB560 (cathode to the rail)': (['D7'], lambda ch: {'1': '+24V', '2': 'VFUSE'}),
    'P6KE30A (cathode to the rail)': (['D8'], lambda ch: {'1': '+24V', '2': 'GND'}),
    '1N5819 to the QT Py (cathode to its 5V pad)': (['D6'], lambda ch: {'1': 'QT_5V', '2': '+5V'}),
    'LMR33630 (1 GND, 2 VIN, 3 EN, 4 PG, 5 FB, 6 VCC, 7 BOOT, 8 SW, pad GND)':
        (['U2'], lambda ch: {'1': 'GND', '2': '+24V', '3': '+24V', '5': 'FB', '6': 'VCC', '7': 'BOOT', '8': 'SW',
                             '9': 'GND'}),
    'electrolytics (1 = +)': (['C1', 'C2'], lambda ch: None),
    'J1 (2 = +, beside the "+" mark)': (['J1'], lambda ch: {'1': 'GND', '2': 'VIN'}),
    'strip terminals (1 = +24 V common)': (['J3', 'J2'], lambda ch: None),
}


def test_pinouts():
    parts = {p['ref']: p for p in design.parts()}
    wrong = []
    for what, (refs, want) in PINOUTS.items():
        for i, ref in enumerate(refs):
            pins = parts[ref]['pins']
            ch = design.CHANNELS[i] if len(refs) == 5 else None
            w = want(ch)
            if w is None:          # polarity only: pin 1 on the positive side, pin 2 or more elsewhere
                ok = pins['1'] in ('+24V', '+5V') and all(v not in ('+24V', '+5V') for k, v in pins.items() if k != '1')
            else:
                ok = pins == w
            if not ok:
                wrong.append('%s %s: %s' % (what, ref, pins))
    record('B22 pinouts and polarity', not wrong, 'transistors, diodes, converter, capacitors and terminals all wired '
           'to their datasheet pinouts' if not wrong else '; '.join(wrong), {'wrong': wrong})


# =============================================================================================
def main():
    layers = {'F': Layer('F_Cu.gtl'), 'B': Layer('B_Cu.gbl'), 'FM': Layer('F_Mask.gts'), 'BM': Layer('B_Mask.gbs'),
              'FS': Layer('F_Silkscreen.gto'), 'BS': Layer('B_Silkscreen.gbo')}
    pth, npth = drills('PTH'), drills('NPTH')
    edge_poly, _ = outline()
    board, pads = board_pads()
    isl, island_net = test_connectivity(layers, pth, pads)
    test_dfm(layers, pth, npth, edge_poly)
    vias = [(pcbnew.ToMM(v.GetPosition().x), -pcbnew.ToMM(v.GetPosition().y))
            for v in board.GetTracks() if v.GetClass() == 'PCB_VIA']
    test_mask_and_silk(layers, vias)
    test_text(board)
    test_current(board)
    test_clearance_by_voltage(isl, island_net)
    test_footprints(pads)
    test_terminals(board, edge_poly)
    test_firmware_pins()
    test_pinouts()
    with open(os.path.join(OUT, 'board-tests.json'), 'w') as fh:
        json.dump({'limits': LIMITS, 'results': results}, fh, indent=1, default=str)
    n_warn = sum(1 for r in results.values() if r['status'] == 'WARN')
    print('\n%d tests, %d failed, %d warnings%s' % (len(results), len(fails), n_warn,
                                                    (': ' + ', '.join(fails)) if fails else ''))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
