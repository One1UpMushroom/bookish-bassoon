"""Footprints for the 5 V buck converter, written into the project library (TaskLamp.pretty).

Ported from the LMR33630 breakout (branch Branchy, hardware/buck-breakout/gen/fplib.py):
pads sized for a soldering iron, and a plated hole through the IC's thermal pad so it can be
soldered from the back. The inductor land is new: the breakout's 12.5 mm inductor does not
fit this board, so it takes a 7 mm part (Bourns SRP7028A).
"""
import os

SILK_W = 0.15


def _hdr(name, descr, smd):
    return [f'(footprint "{name}" (version 20221018) (generator tasklamp_gen)',
            '  (layer "F.Cu")',
            f'  (descr "{descr}")',
            f'  (attr {"smd" if smd else "through_hole"})',
            '  (fp_text reference "REF**" (at 0 0) (layer "F.Fab")'
            ' (effects (font (size 0.8 0.8) (thickness 0.12))))',
            f'  (fp_text value "{name}" (at 0 0) (layer "F.Fab") hide'
            ' (effects (font (size 0.8 0.8) (thickness 0.12))))']


def line(x1, y1, x2, y2, layer="F.SilkS", w=SILK_W):
    return (f'  (fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})'
            f' (stroke (width {w}) (type solid)) (layer "{layer}"))')


def rect(x1, y1, x2, y2, layer="F.CrtYd", w=0.05):
    return (f'  (fp_rect (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})'
            f' (stroke (width {w}) (type solid)) (fill none) (layer "{layer}"))')


def circle(cx, cy, r, layer="F.SilkS", w=SILK_W, fill="none"):
    return (f'  (fp_circle (center {cx:.3f} {cy:.3f}) (end {cx + r:.3f} {cy:.3f})'
            f' (stroke (width {w}) (type solid)) (fill {fill}) (layer "{layer}"))')


def smd(num, x, y, w, h, rr=0.2, paste=True):
    layers = '"F.Cu" "F.Paste" "F.Mask"' if paste else '"F.Cu" "F.Mask"'
    return (f'  (pad "{num}" smd roundrect (at {x:.4f} {y:.4f}) (size {w} {h})'
            f' (layers {layers}) (roundrect_rratio {rr}))')


def tht(num, x, y, dia, drill):
    return (f'  (pad "{num}" thru_hole circle (at {x:.4f} {y:.4f})'
            f' (size {dia} {dia}) (drill {drill}) (layers "*.Cu" "*.Mask"))')


def brackets(hx, hy, n=1.0):
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(line(sx * hx, sy * hy, sx * (hx - n), sy * hy))
            out.append(line(sx * hx, sy * hy, sx * hx, sy * (hy - n)))
    return out


def fp_ic():
    """HSOIC-8 / SO PowerPAD-8 (TI DDA), long pads for an iron, plated hole in the thermal pad."""
    name = "HSOIC-8-1EP_HandSolder_BackHole"
    s = _hdr(name, "TI DDA0008 SO PowerPAD-8, 1.27 mm pitch, 2.0 mm pads; thermal pad has a 1.6 mm plated"
                   " hole for soldering from the bottom side", True)
    ys = (-1.905, -0.635, 0.635, 1.905)
    for i, y in enumerate(ys):
        s.append(smd(i + 1, -2.85, y, 2.0, 0.65, 0.25))
        s.append(smd(8 - i, 2.85, y, 2.0, 0.65, 0.25))
    s.append('  (pad "9" thru_hole rect (at 0 0) (size 2.6 3.1) (drill 1.6)'
             ' (layers "*.Cu" "*.Mask") (zone_connect 2))')
    s.append(line(-1.95, -2.65, 1.95, -2.65))
    s.append(line(-1.95, 2.65, 1.95, 2.65))
    s.append(circle(-2.85, -2.75, 0.2, fill="solid"))
    s.append(rect(-1.95, -2.45, 1.95, 2.45, "F.Fab", 0.1))
    s.append(rect(-3.88, -2.5, 3.88, 2.5))
    return name, s


def fp_inductor():
    """Bourns SRP7028A (7.3 x 6.6 mm body, terminals at the ends of the long side). Pads run
    past the body so an iron can reach them; check against the maker's land drawing."""
    name = "L_Bourns_SRP7028A_HandSolder"
    s = _hdr(name, "Shielded SMD power inductor 7.3 x 6.6 mm (Bourns SRP7028A), hand-solder pads", True)
    s.append(smd(1, -3.4, 0, 3.0, 3.6, 0.1))
    s.append(smd(2, 3.4, 0, 3.0, 3.6, 0.1))
    s += brackets(3.65, 3.3, 1.2)
    s.append(rect(-3.65, -3.3, 3.65, 3.3, "F.Fab", 0.1))
    s.append(rect(-5.2, -3.6, 5.2, 3.6))
    return name, s


def fp_c1210():
    name = "C_1210_HandSolder"
    s = _hdr(name, "1210 (3225) capacitor, hand-solder pads", True)
    s.append(smd(1, -1.5625, 0, 1.325, 2.7))
    s.append(smd(2, 1.5625, 0, 1.325, 2.7))
    s.append(line(-0.6, -1.4, 0.6, -1.4))
    s.append(line(-0.6, 1.4, 0.6, 1.4))
    s.append(rect(-1.6, -1.25, 1.6, 1.25, "F.Fab", 0.1))
    s.append(rect(-2.3, -1.45, 2.3, 1.45))
    return name, s


def fp_chip(kind):
    name = "%s_0805-1206_HandSolder" % kind
    s = _hdr(name, "Takes either an 0805 or a 1206 chip %s" % ("capacitor" if kind == "C" else "resistor"), True)
    s.append(smd(1, -1.35, 0, 1.7, 1.8))
    s.append(smd(2, 1.35, 0, 1.7, 1.8))
    s.append(rect(-1.6, -0.8, 1.6, 0.8, "F.Fab", 0.1))
    s.append(rect(-2.3, -1.05, 2.3, 1.05))
    return name, s


def fp_c_dual():
    """Small capacitor: radial through-hole (5.08 mm lead pitch) OR an 0805/1206 chip on the
    pads between the holes."""
    name = "C_Dual_THT-P5.08_or_0805-1206"
    s = _hdr(name, "Radial ceramic 5.08 mm pitch, or 0805/1206 chip between the holes", False)
    for n, sx in ((1, -1), (2, 1)):
        s.append(tht(n, sx * 2.54, 0, 1.6, 0.8))
        s.append(smd(n, sx * 1.3, 0, 1.6, 1.6, 0.15, paste=False))
    s.append(line(-1.6, -1.2, 1.6, -1.2))
    s.append(line(-1.6, 1.2, 1.6, 1.2))
    s.append(rect(-2.5, -1.25, 2.5, 1.25, "F.Fab", 0.1))
    s.append(rect(-3.4, -1.3, 3.4, 1.3))
    return name, s


def write_all(pretty_dir):
    os.makedirs(pretty_dir, exist_ok=True)
    for fn in (fp_ic, fp_inductor, fp_c1210, lambda: fp_chip("C"), lambda: fp_chip("R"), fp_c_dual):
        name, s = fn()
        with open(os.path.join(pretty_dir, name + ".kicad_mod"), "w") as f:
            f.write("\n".join(s) + "\n)\n")
