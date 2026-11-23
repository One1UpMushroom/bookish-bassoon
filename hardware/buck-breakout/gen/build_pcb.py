#!/usr/bin/python3
"""Build the LMR33630 buck breakout with the KiCad 7 pcbnew API: the single
board and the 2 x 4 break-away panel.  Run with the interpreter that has
pcbnew (/usr/bin/python3):

    /usr/bin/python3 gen/build_pcb.py

Outputs kicad/buck33630.kicad_pcb, kicad/buck33630-panel.kicad_pcb and a DRC
report for each in fab/.
All coordinates are millimetres, origin at the board's top-left corner,
x to the right, y down.  The layout is described in ../README.md.
"""
import os
import sys

import pcbnew
from pcbnew import FromMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fplib  # noqa: E402
import art    # noqa: E402

KICAD = os.path.join(HERE, "..", "kicad")
LIB = os.path.join(KICAD, "buck33630.pretty")
OUT = os.path.join(KICAD, "buck33630.kicad_pcb")
OUT_PANEL = os.path.join(KICAD, "buck33630-panel.kicad_pcb")
FAB = os.path.join(HERE, "..", "fab")

# panel: 2 columns x 4 rows = 98.52 x 97.44 mm (inside the 100 x 100 mm
# price tier), 2 mm routed gaps, break-away tabs with 0.5 mm perforations
COLS, ROWS, GAP = 2, 4, 2.0
TAB_W = 5.0
TABS_LONG = (12.5, 35.5)     # tab centres along the long edges (x)
TABS_SHORT = (11.43,)        # tab centres along the short edges (y)
BITE_PITCH, BITE_INSET = 0.8, 0.25

W, H = 48.26, 22.86          # 1.9 in x 0.9 in, header rows 0.8 in apart
ROW_A, ROW_B = 1.27, 21.59   # header row centre lines
CHAMFER = 0.8

F, B = pcbnew.F_Cu, pcbnew.B_Cu


def P(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


# --------------------------------------------------------------- parts ----
# ref: (footprint, x, y, rotation, value, {pad: net})
U1X, U1Y = 17.3, 7.4
L1X, L1Y = 31.0, 11.43
PARTS = {
    "U1":  ("HSOIC-8-1EP_HandSolder_BackHole", U1X, U1Y, 0, "LMR33630ADDAR",
            {1: "GND", 2: "VIN", 3: "EN", 4: "PG", 5: "FB", 6: "VCC",
             7: "BOOT", 8: "SW", 9: "GND"}),
    "L1":  ("L_Universal_10mm-13.5mm", L1X, L1Y, 270, "10-22uH",
            {1: "SW", 2: "VOUT"}),
    "C1":  ("C_1210_HandSolder", 9.75, 5.2, 270, "10u 50V X7R",
            {1: "GND", 2: "VIN"}),
    "C2":  ("C_1210_HandSolder", 9.75, 10.0, 270, "10u 50V X7R",
            {1: "VIN", 2: "GND"}),
    "C3":  ("C_0805-1206_HandSolder", 12.3, 5.55, 270, "220n 50V",
            {1: "GND", 2: "VIN"}),
    "C4":  ("C_Dual_THT-P5.08_or_0805-1206", 22.7, 5.61, 270, "100n",
            {1: "SW", 2: "BOOT"}),
    "C5":  ("C_Dual_THT-P5.08_or_0805-1206", 22.7, 13.14, 270, "1u",
            {1: "VCC", 2: "GND"}),
    "C6":  ("C_1210_HandSolder", 39.9, 9.88, 0, "COUT", {1: "VOUT", 2: "GND"}),
    "C7":  ("C_1210_HandSolder", 39.9, 12.98, 0, "COUT", {1: "VOUT", 2: "GND"}),
    "C8":  ("C_1210_HandSolder", 45.0, 9.88, 0, "COUT", {1: "GND", 2: "VOUT"}),
    "C9":  ("C_1210_HandSolder", 45.0, 12.98, 0, "COUT", {1: "GND", 2: "VOUT"}),
    "C10": ("CP_Radial_D8.0_P3.5", 4.1, 8.0, 0, "47-100u 50V",
            {1: "VIN", 2: "GND"}),
    "D1":  ("D_SMB", 4.4, 14.6, 0, "TVS (opt)", {1: "VIN", 2: "GND"}),
    "R1":  ("R_Axial_0.25W_P7.62_Horizontal", 19.6, 16.11, 270, "RFBT",
            {1: "FB", 2: "VOUT"}),
    "R2":  ("R_Axial_0.25W_P7.62_Horizontal", 17.06, 16.11, 270, "RFBB1",
            {1: "FB", 2: "FBM"}),
    "R3":  ("R_Axial_0.25W_P7.62_Horizontal", 14.52, 16.11, 270, "RFBB2",
            {1: "GND", 2: "FBM"}),
    "R4":  ("R_Axial_0.25W_P2.54_Vertical", 5.08, 18.6, 0, "100k",
            {1: "VIN", 2: "EN"}),
    "R5":  ("R_Axial_0.25W_P2.54_Vertical", 9.3, 18.57, 270, "UVLO (opt)",
            {1: "GND", 2: "EN"}),
    "J1":  ("PinHeader_1x02_P2.54_Row", 1.27, ROW_A, 0, "IN",
            {1: "GND", 2: "VIN"}),
    "J2":  ("PinHeader_1x03_P2.54_Row", 1.27, ROW_B, 0, "IN",
            {1: "GND", 2: "VIN", 3: "EN"}),
    "J3":  ("PinHeader_1x02_P2.54_Row", 44.45, ROW_A, 0, "OUT",
            {1: "VOUT", 2: "GND"}),
    "J4":  ("PinHeader_1x03_P2.54_Row", 41.91, ROW_B, 0, "OUT",
            {1: "PG", 2: "VOUT", 3: "GND"}),
}
NETS = ["GND", "VIN", "SW", "BOOT", "VCC", "FB", "FBM", "EN", "PG", "VOUT"]

# pad positions the routing below relies on: (ref, pad) -> (x, y)
EXPECT = {
    ("U1", 1): (14.45, 5.495), ("U1", 8): (20.15, 5.495),
    ("U1", 5): (20.15, 9.305), ("L1", 1): (31.0, 6.28),
    ("C1", 1): (9.75, 3.6375), ("C2", 1): (9.75, 8.4375),
    ("C4", 2): (22.7, 8.15), ("C5", 1): (22.7, 10.6),
    ("R1", 1): (19.6, 12.3), ("R3", 2): (14.52, 19.92),
    ("R5", 2): (9.3, 19.84), ("C10", 1): (2.35, 8.0),
}

# ------------------------------------------------------------ copper ------
# top-layer pours: (net, priority, [(x, y), ...])
ZONES_TOP = [
    ("GND", 0, [(0, 0), (W, 0), (W, H), (0, H)]),
    ("VIN", 1, [(2.75, 0.45), (4.9, 0.45), (4.9, 4.7), (8.1, 4.7),
                (8.1, 5.95), (13.3, 5.95), (13.3, 7.45), (11.3, 7.45),
                (11.3, 9.25), (8.1, 9.25), (8.1, 6.9), (4.9, 6.9),
                (4.9, 22.4), (2.75, 22.4), (2.75, 20.2), (1.0, 20.2),
                (1.0, 2.9), (2.75, 2.9)]),
    ("SW", 1, [(21.45, 2.2), (24.0, 2.2), (24.0, 3.95), (33.9, 3.95),
               (33.9, 8.6), (28.1, 8.6), (28.1, 5.85), (21.45, 5.85)]),
    ("VOUT", 1, [(37.5, 2.9), (43.3, 2.9), (43.3, 0.45), (45.55, 0.45),
                 (45.55, 2.9), (47.3, 2.9), (47.3, 20.2), (45.55, 20.2),
                 (45.55, 22.4), (43.3, 22.4), (43.3, 20.3), (27.7, 20.3),
                 (27.7, 14.2), (37.5, 14.2)]),
    # ground island between the two columns of output capacitors
    ("GND", 2, [(40.5, 6.0), (44.4, 6.0), (44.4, 16.9), (40.5, 16.9)]),
]

# (net, width, layer, [(x, y), ...])
TRACKS = [
    # hot loop: PGND pin -> C3/C1 ground pads, VIN pin -> VIN island
    ("GND", 0.6, F, [(14.45, 5.495), (13.3, 5.495), (12.6, 4.8), (12.3, 4.2)]),
    ("GND", 0.5, F, [(14.45, 5.495), (16.4, 5.495)]),
    ("VIN", 0.6, F, [(14.45, 6.765), (12.3, 6.765)]),
    # thermal pad heat spreaders, up and down out of the package
    ("GND", 2.4, F, [(U1X, 6.2), (U1X, 1.6)]),
    ("GND", 2.4, F, [(U1X, 8.6), (U1X, 9.7)]),
    # switch node and bootstrap
    ("SW", 0.65, F, [(20.15, 5.495), (21.9, 5.495)]),
    ("BOOT", 0.4, F, [(20.15, 6.765), (22.3, 6.765)]),
    ("VCC", 0.25, F, [(20.15, 8.035), (21.3, 8.035), (21.55, 8.285),
                      (21.55, 9.9), (22.25, 10.6), (22.7, 10.6)]),
    # feedback: pin 5 -> R1/R2, divider midpoint, VOUT sense
    ("FB", 0.25, F, [(20.15, 9.305), (19.6, 9.305), (19.6, 12.3), (17.06, 12.3)]),
    ("FBM", 0.25, F, [(17.06, 19.92), (14.52, 19.92)]),
    ("VOUT", 0.3, F, [(19.6, 19.92), (28.2, 19.92)]),
    # enable: pin 3 -> down the EN/PG channel -> R5, R4, header
    ("EN", 0.2, F, [(14.45, 8.035), (13.3, 8.035), (12.45, 8.885),
                    (12.45, 20.3), (11.9, 20.85), (10.3, 20.85),
                    (9.3, 19.84), (7.6, 19.84), (6.35, 18.6), (6.35, ROW_B)]),
    # power good: pin 4 -> bottom edge -> header
    ("PG", 0.2, F, [(14.45, 9.305), (13.45, 9.305), (13.1, 9.655),
                    (13.1, 21.2), (13.5, 21.6), (41.5, 21.6), (41.91, ROW_B)]),
]

VIAS = [  # ground stitching, 0.3 mm drill / 0.6 mm pad
    (U1X - 0.9, U1Y - 1.15), (U1X + 0.9, U1Y - 1.15),      # in thermal pad
    (U1X - 0.9, U1Y + 1.15), (U1X + 0.9, U1Y + 1.15),
    (U1X - 0.7, 3.4), (U1X + 0.7, 3.4), (U1X - 0.7, 2.0), (U1X + 0.7, 2.0),
    (U1X - 0.7, 10.6), (U1X + 0.7, 10.6),
    (8.9, 2.3), (10.6, 2.3), (12.3, 2.5), (14.2, 3.2),     # input cap grounds
    (9.1, 13.0), (10.4, 13.0),                             # C2 ground
    (7.3, 16.4), (7.9, 12.9),                              # D1 anode
    (41.45, 7.0), (42.45, 7.6), (43.45, 7.0),              # COUT island
    (41.45, 15.9), (42.45, 15.3), (43.45, 15.9),
    (31.0, 10.3), (31.0, 12.6), (26.4, 11.4), (35.6, 11.4),  # under L1
    (25.5, 17.2), (36.0, 6.0),
    (10.8, 15.6), (10.8, 18.0), (22.0, 17.9), (25.4, 12.9),
]


# ------------------------------------------------------------ builder -----
def new_board():
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.m_MinClearance = FromMM(0.2)
    ds.m_TrackMinWidth = FromMM(0.2)
    ds.m_ViasMinSize = FromMM(0.6)
    ds.m_MinThroughDrill = FromMM(0.3)
    ds.m_ViasMinAnnularWidth = FromMM(0.13)
    ds.m_CopperEdgeClearance = FromMM(0.3)
    ds.m_HoleClearance = FromMM(0.25)
    ds.m_HoleToHoleMin = FromMM(0.25)
    ds.m_SilkClearance = FromMM(0.1)
    ds.m_MinResolvedSpokes = 1
    ds.m_MinSilkTextHeight = FromMM(0.7)
    ds.m_MinSilkTextThickness = FromMM(0.1)
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetClearance(FromMM(0.2))
    nc.SetTrackWidth(FromMM(0.25))
    nc.SetViaDiameter(FromMM(0.6))
    nc.SetViaDrill(FromMM(0.3))
    return board


def outline_pts(ox=0.0, oy=0.0, corners=None):
    """The board outline as a list of points, clockwise from the top left.
    corners: None for the standard small chamfers, or a function that takes
    the board's width and height and returns the outline's points (the
    themed boards in gen/themes use this for their own corner shapes)."""
    if corners is not None:
        return [(ox + x, oy + y) for x, y in corners(W, H)]
    c = CHAMFER
    return [(ox + x, oy + y) for x, y in
            [(c, 0), (W - c, 0), (W, c), (W, H - c), (W - c, H), (c, H),
             (0, H - c), (0, c)]]


def edge(board, pts, closed=True):
    seq = list(zip(pts, pts[1:] + pts[:1])) if closed else list(zip(pts, pts[1:]))
    for a, b in seq:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a))
        s.SetEnd(P(*b))
        s.SetWidth(FromMM(0.1))
        s.SetLayer(pcbnew.Edge_Cuts)
        board.Add(s)


def add_unit(board, ox=0.0, oy=0.0, tag="", decorate=None):
    """Place one converter with its top-left corner at (ox, oy).  Net names
    get `tag` appended so the units of a panel stay electrically separate.
    decorate: the function that draws the silkscreen (default art.decorate).
    Everything copper is the same whichever function draws the artwork."""
    def Q(x, y):
        return P(x + ox, y + oy)

    nets = {}
    for n in NETS:
        ni = pcbnew.NETINFO_ITEM(board, n + tag)
        board.Add(ni)
        nets[n] = ni

    for ref, (fpname, x, y, rot, value, padnets) in PARTS.items():
        fp = pcbnew.FootprintLoad(LIB, fpname)
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetFPID(pcbnew.LIB_ID("buck33630", fpname))
        board.Add(fp)
        fp.SetPosition(Q(x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            num = pad.GetNumber()
            if num:
                pad.SetNet(nets[padnets[int(num)]])
        # the routing below assumes these pad positions
        for (r, num), (ex, ey) in EXPECT.items():
            if r != ref:
                continue
            got = [(pcbnew.ToMM(p.GetPosition().x) - ox,
                    pcbnew.ToMM(p.GetPosition().y) - oy)
                   for p in fp.Pads() if p.GetNumber() == str(num)]
            assert any(abs(gx - ex) < 0.01 and abs(gy - ey) < 0.01
                       for gx, gy in got), f"{ref}.{num} at {got}"

    def zone(net, prio, poly, layer):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(nets[net])
        z.SetAssignedPriority(prio)
        z.SetLocalClearance(FromMM(0.25))
        z.SetMinThickness(FromMM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        z.SetThermalReliefGap(FromMM(0.3))
        z.SetThermalReliefSpokeWidth(FromMM(0.5))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in poly:
            ol.Append(FromMM(x + ox), FromMM(y + oy))
        board.Add(z)

    for net, prio, poly in ZONES_TOP:
        zone(net, prio, poly, F)
    zone("GND", 0, [(0, 0), (W, 0), (W, H), (0, H)], B)

    for net, width, layer, path in TRACKS:
        for a, b in zip(path, path[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(Q(*a))
            t.SetEnd(Q(*b))
            t.SetWidth(FromMM(width))
            t.SetLayer(layer)
            t.SetNet(nets[net])
            board.Add(t)

    for x, y in VIAS:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(Q(x, y))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(F, B)
        v.SetDrill(FromMM(0.3))
        v.SetWidth(FromMM(0.6))
        v.SetNet(nets["GND"])
        board.Add(v)

    (decorate or art.decorate)(board, W, H, ox, oy)


def finish(board, path):
    """Filling a board that only exists in memory crashes KiCad 7, so save,
    reload from disk, fill, save again."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    pcbnew.SaveBoard(path, board)
    board = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)


def build_unit(out=OUT, decorate=None, corners=None, setup=None):
    """The single board. The keyword arguments are hooks for the themed
    boards: decorate draws the artwork, corners shapes the outline, setup
    adjusts the new board first (colours, rule limits). Left out, they give
    the standard board."""
    fplib.write_all()
    board = new_board()
    if setup:
        setup(board)
    add_unit(board, decorate=decorate)
    edge(board, outline_pts(corners=corners))
    finish(board, out)


def build_panel(out=OUT_PANEL, decorate=None, corners=None, setup=None):
    board = new_board()
    if setup:
        setup(board)
    shape = pcbnew.SHAPE_POLY_SET()

    def add_poly(pts):
        tmp = pcbnew.SHAPE_POLY_SET()
        tmp.NewOutline()
        for x, y in pts:
            tmp.Append(FromMM(x), FromMM(y))
        shape.BooleanAdd(tmp, pcbnew.SHAPE_POLY_SET.PM_FAST)

    def bite(x, y):
        fp = pcbnew.FootprintLoad(LIB, "MouseBite_NPTH_0.5mm")
        fp.SetReference("MB")
        fp.SetFPID(pcbnew.LIB_ID("buck33630", "MouseBite_NPTH_0.5mm"))
        board.Add(fp)
        fp.SetPosition(P(x, y))

    n_bites = int((TAB_W - 0.5) // BITE_PITCH) + 1
    span = (n_bites - 1) * BITE_PITCH
    offs = [-span / 2 + i * BITE_PITCH for i in range(n_bites)]
    e = 0.02      # overlap so the union merges tab and board

    for r in range(ROWS):
        for c in range(COLS):
            ox, oy = c * (W + GAP), r * (H + GAP)
            add_unit(board, ox, oy, f"/{r * COLS + c + 1}", decorate)
            add_poly(outline_pts(ox, oy, corners))
            if r + 1 < ROWS:                 # tabs to the board below
                for tx in TABS_LONG:
                    x0, x1 = ox + tx - TAB_W / 2, ox + tx + TAB_W / 2
                    add_poly([(x0, oy + H - e), (x1, oy + H - e),
                              (x1, oy + H + GAP + e), (x0, oy + H + GAP + e)])
                    for d in offs:
                        bite(ox + tx + d, oy + H - BITE_INSET)
                        bite(ox + tx + d, oy + H + GAP + BITE_INSET)
            if c + 1 < COLS:                 # tab to the board on the right
                for ty in TABS_SHORT:
                    y0, y1 = oy + ty - TAB_W / 2, oy + ty + TAB_W / 2
                    add_poly([(ox + W - e, y0), (ox + W + GAP + e, y0),
                              (ox + W + GAP + e, y1), (ox + W - e, y1)])
                    for d in offs:
                        bite(ox + W - BITE_INSET, oy + ty + d)
                        bite(ox + W + GAP + BITE_INSET, oy + ty + d)

    shape.Simplify(pcbnew.SHAPE_POLY_SET.PM_FAST)
    for i in range(shape.OutlineCount()):
        rings = [shape.Outline(i)] + [shape.Hole(i, h)
                                      for h in range(shape.HoleCount(i))]
        for ring in rings:
            pts = [(pcbnew.ToMM(ring.CPoint(j).x), pcbnew.ToMM(ring.CPoint(j).y))
                   for j in range(ring.PointCount())]
            edge(board, pts)
    finish(board, out)


def drc(board_path, name, fab=FAB):
    """Run KiCad's design-rule check; write the report to fab/name and return
    the counts it found, e.g. {"DRC violations": 0, ...}."""
    board = pcbnew.LoadBoard(board_path)
    os.makedirs(fab, exist_ok=True)
    rpt = os.path.join(fab, name)
    pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    import re
    found = re.findall(r"\*\* Found (\d+) (.*?) \*\*", open(rpt).read())
    print(f"{os.path.basename(board_path)}: " +
          ", ".join(f"{n} {what}" for n, what in found))
    return {what: int(n) for n, what in found}


if __name__ == "__main__":
    build_unit()
    drc(OUT, "drc-unit.rpt")
    build_panel()
    drc(OUT_PANEL, "drc-panel.rpt")
