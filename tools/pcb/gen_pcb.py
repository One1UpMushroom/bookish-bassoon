"""Lays out the driver board (KiCad 7) from design.py.

Run with the Python that has KiCad's `pcbnew` module (/usr/bin/python3 on
Ubuntu), normally through build.py.

All positions are millimetres from the board's top-left corner, looking at the
component side. What connects to what comes from design.py; this file only
decides where things sit and where the copper runs. check.py then asks KiCad
whether the result is complete (nothing unrouted) and legal (no clearance
violations) and whether every pad is on the net design.py says.

Layer plan: the bottom layer is one unbroken ground plane. Everything else is
routed on the top layer without a single via, so return currents always have a
straight path underneath. The top layer carries no ground fill: it would only
add slivers between the tracks, and leaving it out keeps every track visible.
"""
import os

import pcbnew
from pcbnew import FromMM, VECTOR2I

import design
from sexpr import Sym, dump

KICAD_FOOTPRINTS = '/usr/share/kicad/footprints/'

# Where the board sits on the drawing sheet.
OX, OY = 100.0, 60.0

W, H = 96.52, 59.0          # board size
CUT = 3.0                   # 45-degree cut on every corner (the theme's cut corner, as a chamfer)

# Look of the board (Neon Noir Chartreuse): matte black mask, white silkscreen, ENIG.
# Signage text is Oswald Bold in capitals; small part labels keep KiCad's stroke font,
# because Oswald's strokes get thinner than the 0.15 mm a fab prints reliably below 1.2 mm.
SIGNAGE_FONT = 'Oswald'
SIGNAGE_MIN = 1.2
SILK_MIN = 0.15          # thinnest silkscreen line the board maker prints reliably, mm
TO220_DRILL = 1.3        # MOSFET holes, mm (see build())           # mm: smallest signage text
MASK_COLOR, SILK_COLOR, FINISH = 'Black', 'White', 'ENIG'

# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------
PITCH = 15.24               # one strip switch every 0.6 inch
X0 = 15.24                  # gate pin of the first switch
RY1 = 27.94                 # top pads of the gate resistors
BUS_Y = RY1 + 5.08          # +24 V bus, under the resistor bodies
RY2 = RY1 + 10.16           # bottom pads of the gate resistors (the gate nodes)
GY = RY1 + 15.24            # MOSFET pins
LANE1, LANE2, LANE3 = GY + 2.8, GY + 4.8, GY + 6.8   # output tracks below the MOSFETs
TY = GY + 10.16             # strip terminal pins

TRUNK_X = 10.16             # +24 V from the input diode down to the bus and J3
DROP_X = X0 + 2 * PITCH + 12.7   # +24 V down to J2, between switches 3 and 4

QX, QY0 = 68.58, 3.81       # QT Py pad 1 (A0); USB socket at the top edge
J4_X = 88.9

# M3 mounting holes on a 88.9 x 50.8 mm (3.5 x 2.0 inch) rectangle.
HOLE_X, HOLE_Y, HOLE_DX, HOLE_DY = 3.6, 4.1, 88.9, 50.8
HOLES = [(HOLE_X, HOLE_Y), (HOLE_X + HOLE_DX, HOLE_Y), (HOLE_X, HOLE_Y + HOLE_DY),
         (HOLE_X + HOLE_DX, HOLE_Y + HOLE_DY)]


def gx(i):
    return X0 + i * PITCH


def placements():
    """{ref: (x, y, rotation in degrees)}: position of pad 1, KiCad's rotation sense."""
    p = {
        # 24 V input, right to left along the top edge: terminal, fuse, diode
        'J1': (52.58, 5.6, 180),        # wires enter from the top edge
        'F1': (31.0, 3.8, 0),
        'D7': (TRUNK_X, 5.5, 0),        # cathode sits on the trunk
        'D8': (4.5, 9.3, 270),          # TVS, down the left edge
        'C1': (TRUNK_X, 13.5, 0),
        # 5 V supply
        'U2': (19.5, 18.0, 0),
        'C4': (30.6, 18.0, 270),
        'C5': (35.6, 18.0, 90),
        'D6': (49.5, 18.0, 180),        # anode toward the converter
        'TP1': (39.34, 13.5, 0),
        'TP2': (43.5, 13.5, 0),
        # controller and display header
        'U1': (QX, QY0, 0),
        'J4': (J4_X, QY0 + 2 * 2.54, 0),
        # strip terminals and their bulk capacitor
        'J3': (TRUNK_X, TY, 0),
        'J2': (DROP_X, TY, 0),
        'C2': (52.0, TY, 180),
    }
    for i in range(5):
        n = i + 1
        p['R%d' % n] = (gx(i), RY1, 270)
        p['R%d' % (n + 5)] = (gx(i) + 3.81, RY1, 270)
        p['Q%d' % n] = (gx(i), GY, 0)
        p['D%d' % n] = (gx(i) + 10.16, BUS_Y, 270)
    for n, (x, y) in enumerate(HOLES, 1):
        p['H%d' % n] = (x, y, 0)
    return p


# ---------------------------------------------------------------------------
# Routing. Every entry: net, width, layer-less list of points (top copper).
# ---------------------------------------------------------------------------
W_PWR, W_BUS, W_OUT, W_5V, W_SIG = 2.0, 3.0, 1.2, 0.8, 0.4


def routes():
    r = []

    def add(net, width, *pts, chamfer=0.0):
        r.append((net, width, list(pts), chamfer))

    # --- input chain
    add('VIN', W_PWR, (40.92, 3.8), (40.92, 7.2))
    add('VIN', W_PWR, (40.92, 5.6), (47.5, 5.6))
    add('VFUSE', W_PWR, (31.0, 3.8), (31.0, 7.2))
    add('VFUSE', W_PWR, (31.0, 5.5), (25.4, 5.5))
    # --- +24 V: trunk, bus, the drop to J2 and the small branches
    add('+24V', W_BUS, (TRUNK_X, 5.5), (TRUNK_X, TY))
    add('+24V', W_BUS, (TRUNK_X, BUS_Y), (gx(4) + 10.16, BUS_Y))
    add('+24V', 1.5, (DROP_X, BUS_Y), (DROP_X, TY))
    add('+24V', 1.5, (4.5, 9.3), (TRUNK_X, 9.3))                  # TVS
    add('+24V', 1.0, (19.5, 18.0), (TRUNK_X, 18.0))              # converter input
    add('+24V', 1.5, (52.0, TY), (DROP_X, TY))                   # C2
    # --- 5 V
    add('+5V', W_5V, (24.58, 18.0), (39.34, 18.0))
    add('+5V', W_5V, (39.34, 18.0), (39.34, 13.5))
    add('QT_5V', 0.6, (49.5, 18.0), (59.0, 18.0), (59.0, 1.9), (QX + 15.24 - 1.91, 1.9),
        (QX + 15.24, QY0), chamfer=1.0)
    # --- display header: five lines straight across, two from under the QT Py
    for k, net in enumerate(['+3V3', 'TFT_MOSI', 'ENC_INT', 'TFT_SCK', 'TFT_LITE']):
        y = QY0 + (2 + k) * 2.54
        add(net, 0.6 if net == '+3V3' else W_SIG, (QX + 15.24, y), (J4_X, y))
    add('TFT_CS', W_SIG, (QX, QY0 + 4 * 2.54), (QX + 6.9, QY0 + 4 * 2.54), (QX + 6.9, QY0 + 7 * 2.54),
        (J4_X, QY0 + 7 * 2.54), chamfer=1.0)
    add('TFT_DC', W_SIG, (QX, QY0 + 5 * 2.54), (QX + 4.4, QY0 + 5 * 2.54), (QX + 4.4, QY0 + 8 * 2.54),
        (J4_X, QY0 + 8 * 2.54), chamfer=1.0)
    # --- PWM lines: down the left of the QT Py, then along the lanes to each gate resistor
    for i in range(4):
        y_pad = QY0 + i * 2.54
        xv = QX - 5.68 + i * 1.0
        lane = 22.6 + i * 1.0
        add('PWM_' + design.CHANNELS[i], W_SIG, (QX, y_pad), (xv, y_pad), (xv, lane), (gx(i), lane),
            (gx(i), RY1), chamfer=0.8)
    add('PWM_CW', W_SIG, (QX, QY0 + 6 * 2.54), (QX, 25.8), (gx(4), 25.8), (gx(4), RY1), chamfer=0.8)
    # --- strip switches
    term = {'R': TRUNK_X + 5.08, 'G': TRUNK_X + 10.16, 'B': TRUNK_X + 15.24,
            'WW': DROP_X + 5.08, 'CW': DROP_X + 10.16}
    lane_of = {'R': LANE1, 'G': LANE2, 'B': LANE3, 'WW': None, 'CW': LANE2}
    for i, ch in enumerate(design.CHANNELS):
        g = gx(i)
        add('GATE_' + ch, W_SIG, (g, RY2), (g, GY))
        add('GATE_' + ch, W_SIG, (g, RY2), (g + 3.81, RY2))
        drain, anode, tx = g + 2.54, g + 10.16, term[ch]
        out = 'OUT_' + ch
        add(out, W_OUT, (anode, GY), (anode, LANE1), (drain, LANE1), chamfer=0.8)   # diode to drain
        if ch == 'R':
            add(out, W_OUT, (drain, GY), (drain, LANE1))
            add(out, W_OUT, (drain, LANE1), (tx, LANE1), (tx, TY), chamfer=0.8)
        elif ch == 'WW':
            add(out, W_OUT, (drain, GY), (drain, TY))
        else:
            lane = lane_of[ch]
            add(out, W_OUT, (drain, GY), (drain, lane), (tx, lane), (tx, TY), chamfer=0.8)
    return r


# ---------------------------------------------------------------------------
# Silkscreen text: (text, x, y, height, rotation, layer)
# ---------------------------------------------------------------------------
def silk():
    """Silkscreen text: (text, x, y, height, rotation, layer, justify, signage?)."""
    t = []

    def add(text, x, y, h=1.0, rot=0, layer='F.SilkS', just='center', sign=False):
        if sign:
            assert h >= SIGNAGE_MIN, text
        t.append((text, x, y, h, rot, layer, just, sign))

    def sign(text, x, y, h=SIGNAGE_MIN, rot=0, layer='F.SilkS', just='center'):
        add(text, x, y, h, rot, layer, just, True)

    # input
    sign('+', 47.5, 12.1, 1.6)
    sign('-', 52.58, 12.0, 1.6)
    sign('24V IN', 50.04, 14.6, 1.3)
    sign('FUSE 2A', 33.4, 10.4)
    sign('+5V', 39.34, 11.7)
    sign('GND', 43.5, 11.7)
    # strip terminals
    for x, s in ((TRUNK_X, '+24'), (TRUNK_X + 5.08, 'R'), (TRUNK_X + 10.16, 'G'), (TRUNK_X + 15.24, 'B')):
        sign(s, x, TY - 6.2)
    for x, s in ((DROP_X, '+24'), (DROP_X + 5.08, 'WW'), (DROP_X + 10.16, 'CW')):
        sign(s, x - (0.9 if s == '+24' else 0), TY - 6.2)
    sign('< RGB STRIP', 37.3, 55.6, 1.3)
    sign('< WHITE STRIP', 81.0, 55.6, 1.3)
    # display header
    for k, s in enumerate(design.J4_LABELS):
        add(s, J4_X + 1.9, QY0 + (2 + k) * 2.54, 0.9, just='left')
    sign('TFT + INT', J4_X + 1.2, 29.6)
    # channel names beside each MOSFET
    names = {'R': 'RED', 'G': 'GRN', 'B': 'BLU', 'WW': 'WARM', 'CW': 'COOL'}
    for i, ch in enumerate(design.CHANNELS):
        sign(names[ch], gx(i) + 6.95, RY2 - 1.6, rot=90)
        add('IRLB8721', gx(i) + 2.54, GY + 2.3, 0.8)     # which TO-220 goes here
    # back of the board: every line sits in a band that has no pads, so no
    # letter is cut by a solder-mask opening
    sign('TASK LAMP DRIVER', W / 2 + 2, RY1 + 2.4, 2.0, layer='B.SilkS')   # glyphs 2.34 mm tall: centred in the pad-free band
    # separated by wide spaces and a bar: Oswald's slash is a hairline at this size
    sign('REV B   |   RGB + TUNABLE WHITE   |   24 V  1 A', W / 2 + 2, BUS_Y + 2.7, layer='B.SilkS')
    for x, s in ((TRUNK_X, '+24'), (TRUNK_X + 5.08, 'R'), (TRUNK_X + 10.16, 'G'), (TRUNK_X + 15.24, 'B'),
                 (DROP_X, '+24'), (DROP_X + 5.08, 'WW'), (DROP_X + 10.16, 'CW')):
        sign(s, x, TY - 3.2, 1.3, layer='B.SilkS')
    sign('+', 47.5, 9.1, 1.6, layer='B.SilkS')
    sign('-', 52.58, 9.0, 1.6, layer='B.SilkS')
    sign('24V IN', 50.04, 11.4, layer='B.SilkS')
    return t


def frames():
    """Signage panels round the connector labels: thin rectangles cut at 45 degrees
    top-left and bottom-right, like the theme's tiles. (x0, y0, x1, y1, cut, layer)."""
    return [
        (45.6, 13.45, 54.5, 15.75, 0.8, 'F.SilkS'),     # 24V IN
        (31.6, 54.4, 43.0, 56.8, 0.8, 'F.SilkS'),       # RGB STRIP
        (74.2, 54.4, 87.8, 56.8, 0.8, 'F.SilkS'),       # WHITE STRIP
    ]


# Value text printed inside each part's outline, so the bare board says what goes where.
VALUE_SILK = {
    'R': 0.9, 'D': 0.8,
}


# ---------------------------------------------------------------------------
# The QT Py footprint (project library)
# ---------------------------------------------------------------------------
def qtpy_footprint():
    def S(*a):
        return [Sym(a[0])] + list(a[1:])

    def line(x1, y1, x2, y2, layer, w=0.15):
        return S('fp_line', S('start', x1, y1), S('end', x2, y2),
                 S('stroke', S('width', w), S('type', Sym('solid'))), S('layer', layer))

    def rect(x1, y1, x2, y2, layer, w=0.15):
        return S('fp_rect', S('start', x1, y1), S('end', x2, y2),
                 S('stroke', S('width', w), S('type', Sym('solid'))), S('fill', Sym('none')), S('layer', layer))

    def text(kind, s, x, y, layer, h=1.0, just=None, hide=False):
        eff = S('effects', S('font', S('size', h, h), S('thickness', max(0.15, round(h * 0.15, 3)))))   # 0.15 mm: the thinnest line a fab prints reliably
        if just:
            eff.append(S('justify', Sym(just)))
        node = S('fp_text', Sym(kind), s, S('at', x, y), S('layer', layer))
        if hide:
            node.append(Sym('hide'))
        node.append(eff)
        return node

    # Module outline from Adafruit's board file: 17.78 x 20.70 mm, pads 1.27 mm in
    # from the long edges, first pad 2.73 mm from the USB end.
    left, right, top, bottom = -1.27, 16.51, -2.73, 17.97
    fp = S('footprint', 'QTPy_RP2040_Socket', S('version', 20221018), S('generator', Sym('tasklamp_gen')),
           S('layer', 'F.Cu'),
           S('descr', 'Adafruit QT Py RP2040 (or any QT Py / XIAO-size board) on two 1x7 2.54 mm sockets, '
                      'rows 15.24 mm apart. Pad 1 = A0, beside the USB socket; pads 8-14 run back up the '
                      'other side, so pad 14 = 5V.'),
           S('tags', 'QT Py RP2040 XIAO socket module'),
           S('attr', Sym('through_hole')),
           text('reference', 'REF**', 7.62, 19.2, 'F.SilkS', 1.0),
           text('value', 'QTPy_RP2040_Socket', 7.62, 21.0, 'F.Fab', 1.0),
           text('user', 'USB', 7.62, -1.1, 'F.SilkS', 1.0),
           text('user', 'QT PY', 7.62, 2.4, 'F.SilkS', 1.1))
    # module outline (silk, broken where it would cross the pads) and courtyard
    fp.append(rect(left, top, right, bottom, 'F.Fab', 0.1))
    fp.append(rect(left - 0.25, top - 0.25, right + 0.25, bottom + 0.25, 'F.CrtYd', 0.05))
    c = 1.5   # the theme's 45-degree cut, top-left and bottom-right
    fp.append(line(left + c, top, right, top, 'F.SilkS'))
    fp.append(line(left, top + c, left + c, top, 'F.SilkS'))
    fp.append(line(left, bottom, right - c, bottom, 'F.SilkS'))
    fp.append(line(right - c, bottom, right, bottom - c, 'F.SilkS'))
    fp.append(line(left, top + c, left, -1.33, 'F.SilkS'))
    fp.append(line(right, top, right, -1.33, 'F.SilkS'))
    fp.append(line(left, 16.57, left, bottom, 'F.SilkS'))
    fp.append(line(right, 16.57, right, bottom - c, 'F.SilkS'))
    # the two socket strips
    for x in (0.0, 15.24):
        inner = x + (1.33 if x == 0 else -1.33)
        fp.append(line(inner, -1.33, inner, 16.57, 'F.SilkS'))
        fp.append(line(x - 1.33, -1.33, x + 1.33, -1.33, 'F.SilkS'))
        fp.append(line(x - 1.33, 16.57, x + 1.33, 16.57, 'F.SilkS'))
    # USB socket position (fab only), 8.94 mm wide
    fp.append(rect(7.62 - 4.47, top - 0.9, 7.62 + 4.47, top + 6.45, 'F.Fab', 0.1))
    # pin names between the rows
    for n in range(1, 8):
        fp.append(text('user', design.QTPY_PINS[str(n)][0], 1.75, (n - 1) * 2.54, 'F.SilkS', 0.8, just='left'))
    for n in range(8, 15):
        fp.append(text('user', design.QTPY_PINS[str(n)][0], 13.49, (14 - n) * 2.54, 'F.SilkS', 0.8, just='right'))
    for n in range(1, 15):
        x, y = (0.0, (n - 1) * 2.54) if n <= 7 else (15.24, (14 - n) * 2.54)
        fp.append(S('pad', str(n), Sym('thru_hole'), Sym('rect' if n == 1 else 'oval'), S('at', x, y),
                    S('size', 1.7, 1.7), S('drill', 1.0), S('layers', '*.Cu', '*.Mask')))
    return dump(fp) + '\n'


# ---------------------------------------------------------------------------
# Board construction
# ---------------------------------------------------------------------------
def outline():
    """Board outline, clockwise from the top-left cut."""
    c = CUT
    return [(c, 0), (W - c, 0), (W, c), (W, H - c), (W - c, H), (c, H), (0, H - c), (0, c)]


def P(x, y):
    return VECTOR2I(FromMM(OX + x), FromMM(OY + y))


def chamfered(pts, c):
    """Replace each right-angle corner by a 45 degree cut of size c."""
    if c <= 0 or len(pts) < 3:
        return pts
    out = [pts[0]]
    for a, b, d in zip(pts, pts[1:], pts[2:]):
        la = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        lb = ((d[0] - b[0]) ** 2 + (d[1] - b[1]) ** 2) ** 0.5
        cut = min(c, la / 2, lb / 2)
        straight = abs((b[0] - a[0]) * (d[1] - b[1]) - (b[1] - a[1]) * (d[0] - b[0])) < 1e-9
        if cut < 0.2 or straight:
            out.append(b)
            continue
        out.append((b[0] - (b[0] - a[0]) / la * cut, b[1] - (b[1] - a[1]) / la * cut))
        out.append((b[0] + (d[0] - b[0]) / lb * cut, b[1] + (d[1] - b[1]) / lb * cut))
    out.append(pts[-1])
    return out


def build(project_dir, project, sym_uuid=None, extra_tracks=(), drop_route=None, swap_pads=None):
    """Returns the board, zones not yet filled (see write()).

    The last three arguments exist for check.py, which uses them to plant known
    faults (a stray track, a missing route, two pads with their nets exchanged)
    and make sure the checks notice.
    """
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_MinClearance = FromMM(0.2)
    ds.m_TrackMinWidth = FromMM(0.2)
    ds.m_ViasMinSize = FromMM(0.6)
    ds.m_MinThroughDrill = FromMM(0.3)
    ds.m_CopperEdgeClearance = FromMM(0.5)
    ds.m_HoleClearance = FromMM(0.25)
    ds.m_HoleToHoleMin = FromMM(0.5)
    ds.m_SilkClearance = FromMM(0.0)
    ds.m_MinSilkTextHeight = FromMM(0.8)
    # KiCad's own floor for text strokes. Its check of TrueType lettering shrinks each letter by
    # half this and flags any that lose a part, which the tapered ends of Oswald's curves do at
    # 0.15 mm; test_board.py measures the lettering in the Gerbers instead (B13).
    ds.m_MinSilkTextThickness = FromMM(0.12)
    # mask openings 0.05 mm larger than each pad all round, so the mask's registration
    # tolerance can't creep onto a pad (test_board.py B10)
    ds.m_SolderMaskExpansion = FromMM(0.05)
    ds.m_SolderMaskMinWidth = FromMM(0)

    parts = design.parts()
    nets = {}
    for name in sorted(design.netlist()):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    # --- footprints
    place = placements()
    for part in parts:
        lib, name = part['fp'].split(':')
        path = os.path.join(project_dir, lib + '.pretty') if lib == 'TaskLamp' else KICAD_FOOTPRINTS + lib + '.pretty'
        fp = pcbnew.FootprintLoad(path, name)
        assert fp is not None, part['fp']
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(part['ref'])
        fp.SetValue(part['value'])
        x, y, rot = place[part['ref']]
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(rot)
        thicken_silk(fp)
        if part['fp'] == design.FP_TO220:
            # TO-220AB leads are up to 1.02 x 0.61 mm (1.19 mm corner to corner): a 1.3 mm hole
            # takes that even at the bottom of its tolerance; the library's 1.1 mm does not
            for pad in fp.Pads():
                pad.SetDrillSize(VECTOR2I(FromMM(TO220_DRILL), FromMM(TO220_DRILL)))
        if sym_uuid:
            fp.SetPath(pcbnew.KIID_PATH('/' + sym_uuid(part['ref'])))
        for pad in fp.Pads():
            net = part['pins'].get(pad.GetNumber())
            if net:
                pad.SetNet(nets[net])
        board.Add(fp)
        tidy_text(fp, part)

    # --- tracks
    wanted = [r for i, r in enumerate(routes()) if i != drop_route]
    for net, width, pts, chamfer in wanted + list(extra_tracks):
        pts = chamfered(pts, chamfer)
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(P(*a))
            t.SetEnd(P(*b))
            t.SetWidth(FromMM(width))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(nets[net])
            board.Add(t)

    if swap_pads:
        (ra, pa), (rb, pb) = swap_pads
        a = next(pad for pad in board.FindFootprintByReference(ra).Pads() if pad.GetNumber() == pa)
        b = next(pad for pad in board.FindFootprintByReference(rb).Pads() if pad.GetNumber() == pb)
        na, nb = a.GetNet(), b.GetNet()
        a.SetNet(nb)
        b.SetNet(na)

    # --- ground: the whole bottom layer
    zone = pcbnew.ZONE(board)
    zone.SetNet(nets['GND'])
    zone.SetLayer(pcbnew.B_Cu)
    zone.SetZoneName('GND')
    zpoly = zone.Outline()
    zpoly.NewOutline()
    for x, y in outline():
        zpoly.Append(FromMM(OX + x), FromMM(OY + y))
    zone.SetLocalClearance(FromMM(0.5))
    zone.SetMinThickness(FromMM(0.3))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(FromMM(0.5))
    zone.SetThermalReliefSpokeWidth(FromMM(0.8))
    zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(zone)

    # --- outline: a rectangle with every corner cut at 45 degrees
    pts = outline()
    for a, b in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a))
        s.SetEnd(P(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(FromMM(0.1))
        board.Add(s)

    # --- silkscreen
    for text, x, y, h, rot, layer, just, _ in silk():
        add_text(board, text, x, y, h, rot, layer, just)
    for x0, y0, x1, y1, c, layer in frames():
        corners = [(x0 + c, y0), (x1, y0), (x1, y1 - c), (x1 - c, y1), (x0, y1), (x0, y0 + c)]
        for a, b in zip(corners, corners[1:] + corners[:1]):
            s = pcbnew.PCB_SHAPE(board)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(P(*a))
            s.SetEnd(P(*b))
            s.SetLayer(pcbnew.F_SilkS if layer == 'F.SilkS' else pcbnew.B_SilkS)
            s.SetWidth(FromMM(0.15))
            board.Add(s)

    return board


def thicken_silk(fp):
    """KiCad's library draws footprint silkscreen at 0.12 mm; the board maker prints 0.15 mm and
    up reliably, so widen anything thinner (test_board.py B13)."""
    for item in fp.GraphicalItems():
        if item.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            continue
        if item.GetClass() == 'FP_TEXT':
            if item.GetTextThickness() < FromMM(SILK_MIN):
                item.SetTextThickness(FromMM(SILK_MIN))
        elif 0 < item.GetWidth() < FromMM(SILK_MIN):
            item.SetWidth(FromMM(SILK_MIN))


def write(board, path):
    """Save, then reload and fill the ground zone.

    A board built in memory has no project behind it and KiCad 7 crashes when
    asked to fill its zones, so the fill is done on the copy read back from disk.
    """
    pcbnew.SaveBoard(path, board)
    style_file(path)
    loaded = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(loaded).Fill(loaded.Zones())
    pcbnew.SaveBoard(path, loaded)
    return loaded


STACKUP = """    (stackup
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
"""


def style_file(path):
    """What the pcbnew Python API can't set: the signage font on silkscreen text, and the
    board's stack-up with its mask, silkscreen and finish (KiCad's 3D view shows them)."""
    import re
    # a text is signage by its words and its place, so a small label that happens to share
    # its words with a sign ("GND" on the display header) keeps the stroke font
    signage = {(text, round(OX + x, 2), round(OY + y, 2)) for text, x, y, *_rest, sign in silk() if sign}
    src = open(path).read()
    pattern = re.compile(r'(\(gr_text "([^"]*)" \(at ([-\d.]+) ([-\d.]+)[^)]*\).*?\(effects )'
                         r'\(font \(size ([\d.]+) ([\d.]+)\) \(thickness ([\d.]+)\)\)', re.S)

    def restyle(m):
        if (m.group(2), round(float(m.group(3)), 2), round(float(m.group(4)), 2)) not in signage:
            return m.group(0)
        return '%s(font (face "%s") (size %s %s) (thickness %s) bold)' % (
            m.group(1), SIGNAGE_FONT, m.group(5), m.group(6), m.group(7))

    src, n = pattern.subn(restyle, src)
    styled = src.count('(face "%s")' % SIGNAGE_FONT)
    expected = sum(1 for *_r, sign in silk() if sign)
    assert styled == expected, 'signage font set on %d texts, expected %d' % (styled, expected)
    if '(stackup' not in src:
        src = src.replace('(setup\n', '(setup\n' + STACKUP.format(mask=MASK_COLOR, silk=SILK_COLOR, finish=FINISH), 1)
    assert '(stackup' in src, 'stack-up not written'
    with open(path, 'w') as fh:
        fh.write(src)


def add_text(board, text, x, y, h, rot=0, layer='F.SilkS', just='center'):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(P(x, y))
    back = layer.startswith('B.')
    t.SetLayer({'F.SilkS': pcbnew.F_SilkS, 'B.SilkS': pcbnew.B_SilkS, 'F.Fab': pcbnew.F_Fab}[layer])
    t.SetTextSize(VECTOR2I(FromMM(h), FromMM(h)))
    t.SetTextThickness(FromMM(max(0.15, h * 0.15)))
    t.SetTextAngleDegrees(rot)
    t.SetHorizJustify({'left': pcbnew.GR_TEXT_H_ALIGN_LEFT, 'center': pcbnew.GR_TEXT_H_ALIGN_CENTER,
                       'right': pcbnew.GR_TEXT_H_ALIGN_RIGHT}[just])
    if back:
        t.SetMirrored(True)
    board.Add(t)
    return t


# Where each reference designator is printed, relative to pad 1 after rotation
# has been applied (board millimetres). Parts not listed keep the library position.
def tidy_text(fp, part):
    """Put the reference where it can be read and print the value inside the outline."""
    ref = part['ref']
    kind = ref.rstrip('0123456789')
    r, v = fp.Reference(), fp.Value()
    for t in (r, v):
        t.SetTextSize(VECTOR2I(FromMM(0.9), FromMM(0.9)))
        t.SetTextThickness(FromMM(0.15))
    v.SetLayer(pcbnew.F_Fab)
    pos = fp.GetPosition()
    px, py = pcbnew.ToMM(pos.x) - OX, pcbnew.ToMM(pos.y) - OY
    board = fp.GetBoard()

    def at(t, x, y, rot=0):
        t.SetPosition(P(x, y))
        t.SetTextAngleDegrees(rot)

    if kind == 'R':
        # vertical resistor: value inside the body, reference hidden on fab
        r.SetLayer(pcbnew.F_Fab)
        at(r, px, py + 5.08, 90)
        v.SetVisible(False)
        add_text(board, part['value'], px, py + 5.08, 0.9, rot=90)
    elif kind == 'Q':
        at(r, px + 2.54, py + 2.25)
        r.SetVisible(False)
        v.SetVisible(False)
    elif kind == 'D' and ref in ('D1', 'D2', 'D3', 'D4', 'D5'):
        r.SetLayer(pcbnew.F_Fab)
        at(r, px, py + 5.08, 90)
        v.SetVisible(False)
        add_text(board, '5819', px, py + 5.08, 0.8, rot=90)
    elif ref == 'D6':
        r.SetLayer(pcbnew.F_Fab)
        at(r, px - 5.08, py)
        v.SetVisible(False)
        add_text(board, '5819', px - 5.08, py, 0.8)
        add_text(board, 'D6', px - 5.08, py + 2.5, 0.9)
    elif ref == 'D7':
        r.SetLayer(pcbnew.F_Fab)
        at(r, px + 7.62, py)
        v.SetVisible(False)
        add_text(board, 'SB560', px + 7.62, py, 1.0)
    elif ref == 'D8':
        r.SetLayer(pcbnew.F_Fab)
        at(r, px, py + 6.35, 90)
        v.SetVisible(False)
        add_text(board, 'P6KE30A', px, py + 6.95, 0.8, rot=90)
    elif ref == 'F1':
        r.SetVisible(False)
        v.SetVisible(False)
    elif ref == 'U2':
        at(r, px + 2.54, py - 6.5)
        r.SetVisible(False)
        v.SetVisible(False)
        add_text(board, '5V CONV', px + 2.54, py - 3.9, 0.9)
        add_text(board, 'IN', px - 1.0, py + 2.3, 0.8)
        add_text(board, 'OUT', px + 6.3, py + 2.3, 0.8)
    elif ref in ('C1', 'C2'):
        r.SetVisible(False)
        v.SetVisible(False)
        if ref == 'C1':
            add_text(board, '100u', px + 6.6, py - 3.3, 0.9, just='left')
        else:
            add_text(board, '100u 50V', px - 1.75, py - 5.0, 0.9)
    elif ref == 'C4':
        r.SetVisible(False)
        v.SetVisible(False)
        add_text(board, '10u', px + 4.4, py + 2.6, 0.9)
    elif ref == 'C5':
        r.SetLayer(pcbnew.F_Fab)
        at(r, px, py - 2.5, 90)
        v.SetVisible(False)
        add_text(board, '100n', px, py - 2.5, 0.8, rot=90)
    elif kind == 'J':
        r.SetVisible(False)
        v.SetVisible(False)
    elif kind in ('TP', 'H'):
        r.SetVisible(False)
        v.SetVisible(False)
    elif ref == 'U1':
        r.SetVisible(False)


PRO_TEMPLATE = {
    "board": {
        "design_settings": {
            "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "silk_line_width": 0.15,
                         "silk_text_size_h": 1.0, "silk_text_size_v": 1.0, "silk_text_thickness": 0.15},
            "rules": {"min_clearance": 0.2, "min_copper_edge_clearance": 0.5, "min_hole_clearance": 0.25,
                      "min_hole_to_hole": 0.5, "min_through_hole_diameter": 0.3, "min_track_width": 0.2,
                      "min_via_annular_width": 0.1, "min_via_diameter": 0.6, "min_silk_clearance": 0.0,
                      "min_text_height": 0.8, "min_text_thickness": 0.12},
            "rule_severities": {"silk_over_copper": "ignore", "silk_overlap": "ignore",
                                "silk_edge_clearance": "warning", "lib_footprint_issues": "ignore",
                                "lib_footprint_mismatch": "ignore", "courtyards_overlap": "error",
                                "unconnected_items": "error", "clearance": "error", "shorting_items": "error"},
            "track_widths": [0.0, 0.4, 0.6, 0.8, 1.2, 2.0, 3.0],
            "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.8, "drill": 0.4}],
        }
    },
    "meta": {"filename": None, "version": 1},
    "net_settings": {
        "classes": [{"name": "Default", "clearance": 0.3, "track_width": 0.4, "via_diameter": 0.8,
                     "via_drill": 0.4, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                     "diff_pair_width": 0.2, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
                     "bus_width": 12, "wire_width": 6, "line_style": 0,
                     "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}],
        "meta": {"version": 3},
        "net_colors": None,
        "netclass_assignments": None,
        "netclass_patterns": [],
    },
    "pcbnew": {"last_paths": {"gencad": "", "idf": "", "netlist": "", "specctra_dsn": "", "step": "", "vrml": ""},
               "page_layout_descr_file": ""},
    "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
    "sheets": [],
    "text_variables": {},
}
