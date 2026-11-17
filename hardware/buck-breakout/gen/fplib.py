#!/usr/bin/env python3
"""Footprint library for the LMR33630 buck breakout.

Writes hand-solder-friendly footprints as KiCad .kicad_mod files into
../kicad/buck33630.pretty/.  Pure Python, no KiCad needed.

Every footprint is drawn in its own local frame (mm, y down).  Silkscreen is
kept minimal here; the board script adds labels where there is room.
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "kicad", "buck33630.pretty")
SILK_W = 0.15


def _hdr(name, descr, smd):
    return [f'(footprint "{name}" (version 20221018) (generator buckgen)',
            '  (layer "F.Cu")',
            f'  (descr "{descr}")',
            f'  (attr {"smd" if smd else "through_hole"})',
            '  (fp_text reference "REF**" (at 0 0) (layer "F.Fab") hide'
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


def tht(num, x, y, dia, drill, shape="circle", extra=""):
    return (f'  (pad "{num}" thru_hole {shape} (at {x:.4f} {y:.4f})'
            f' (size {dia} {dia}) (drill {drill}) (layers "*.Cu" "*.Mask"){extra})')


def brackets(hx, hy, n=1.0, layer="F.SilkS"):
    """Four corner brackets of a box +-hx by +-hy."""
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(line(sx * hx, sy * hy, sx * (hx - n), sy * hy, layer))
            out.append(line(sx * hx, sy * hy, sx * hx, sy * (hy - n), layer))
    return out


def fp_ic():
    """HSOIC-8 / SO PowerPAD-8 (TI DDA), long pads for an iron, and a plated
    hole in the thermal pad so the pad can be soldered from the back."""
    s = _hdr("HSOIC-8-1EP_HandSolder_BackHole",
             "TI DDA0008 SO PowerPAD-8, 1.27 mm pitch, 2.0 mm pads; thermal pad"
             " has a 1.6 mm plated hole for soldering from the bottom side", True)
    ys = (-1.905, -0.635, 0.635, 1.905)
    for i, y in enumerate(ys):
        s.append(smd(i + 1, -2.85, y, 2.0, 0.65, 0.25))
        s.append(smd(8 - i, 2.85, y, 2.0, 0.65, 0.25))
    # thermal pad: 2.6 x 3.1 land on both sides with a 1.6 mm plated hole
    s.append('  (pad "9" thru_hole rect (at 0 0) (size 2.6 3.1) (drill 1.6)'
             ' (layers "*.Cu" "*.Mask") (zone_connect 2))')
    s.append(line(-1.95, -2.65, 1.95, -2.65))
    s.append(line(-1.95, 2.65, 1.95, 2.65))
    s.append(circle(-2.85, -2.75, 0.2, fill="solid"))
    s.append(rect(-1.95, -2.45, 1.95, 2.45, "F.Fab", 0.1))
    s.append(rect(-3.88, -2.5, 3.88, 2.5))
    return "HSOIC-8-1EP_HandSolder_BackHole", s


def fp_inductor():
    """Fits 10 x 10 to 13.5 x 12.5 mm shielded SMD power inductors
    (Bourns SRP1265A / SRR1260, TDK SLF12575, Wurth WE-PD 1260 ...)."""
    s = _hdr("L_Universal_10mm-13.5mm",
             "Universal land for 10-13.5 mm shielded SMD power inductors;"
             " pads reach past the body for an iron", True)
    s.append(smd(1, -5.15, 0, 4.5, 5.6, 0.08))
    s.append(smd(2, 5.15, 0, 4.5, 5.6, 0.08))
    s += brackets(6.75, 6.25, 1.6)
    s.append(rect(-6.75, -6.25, 6.75, 6.25, "F.Fab", 0.1))
    s.append(rect(-7.45, -6.3, 7.45, 6.3))
    return "L_Universal_10mm-13.5mm", s


def fp_c1210():
    s = _hdr("C_1210_HandSolder", "1210 (3225) capacitor, hand-solder pads", True)
    s.append(smd(1, -1.5625, 0, 1.325, 2.7))
    s.append(smd(2, 1.5625, 0, 1.325, 2.7))
    s.append(line(-0.6, -1.4, 0.6, -1.4))
    s.append(line(-0.6, 1.4, 0.6, 1.4))
    s.append(rect(-1.6, -1.25, 1.6, 1.25, "F.Fab", 0.1))
    s.append(rect(-2.3, -1.45, 2.3, 1.45))
    return "C_1210_HandSolder", s


def fp_c0805_1206():
    s = _hdr("C_0805-1206_HandSolder",
             "Takes either an 0805 or a 1206 chip capacitor", True)
    s.append(smd(1, -1.35, 0, 1.7, 1.8))
    s.append(smd(2, 1.35, 0, 1.7, 1.8))
    s.append(rect(-1.6, -0.8, 1.6, 0.8, "F.Fab", 0.1))
    s.append(rect(-2.3, -1.05, 2.3, 1.05))
    return "C_0805-1206_HandSolder", s


def fp_c_dual():
    """Small capacitor: radial through-hole (5.08 mm lead pitch) OR an
    0805/1206 chip on the pads between the holes."""
    s = _hdr("C_Dual_THT-P5.08_or_0805-1206",
             "Radial ceramic 5.08 mm pitch, or 0805/1206 chip between the holes",
             False)
    for n, sx in ((1, -1), (2, 1)):
        s.append(tht(n, sx * 2.54, 0, 1.6, 0.8))
        s.append(smd(n, sx * 1.3, 0, 1.6, 1.6, 0.15, paste=False))
    s.append(line(-1.6, -1.2, 1.6, -1.2))
    s.append(line(-1.6, 1.2, 1.6, 1.2))
    s.append(rect(-2.5, -1.25, 2.5, 1.25, "F.Fab", 0.1))
    s.append(rect(-3.4, -1.3, 3.4, 1.3))
    return "C_Dual_THT-P5.08_or_0805-1206", s


def fp_cp8():
    s = _hdr("CP_Radial_D8.0_P3.5",
             "Radial electrolytic up to 8 mm diameter, 3.5 mm pitch"
             " (2.5 mm parts splay to fit); pad 1 = +", False)
    s.append(tht(1, -1.75, 0, 1.7, 0.9, "rect"))
    s.append(tht(2, 1.75, 0, 1.7, 0.9))
    s.append(circle(0, 0, 4.0, "F.Fab", 0.1))
    s.append(circle(0, 0, 4.05, "F.CrtYd", 0.05))
    return "CP_Radial_D8.0_P3.5", s


def fp_r_h():
    s = _hdr("R_Axial_0.25W_P7.62_Horizontal",
             "1/4 W axial resistor lying flat, 7.62 mm pitch", False)
    s.append(tht(1, -3.81, 0, 1.6, 0.8))
    s.append(tht(2, 3.81, 0, 1.6, 0.8))
    s.append(line(-2.7, -1.1, 2.7, -1.1))
    s.append(line(-2.7, 1.1, 2.7, 1.1))
    s.append(rect(-3.15, -1.25, 3.15, 1.25, "F.Fab", 0.1))
    s.append(rect(-4.65, -1.26, 4.65, 1.26))
    return "R_Axial_0.25W_P7.62_Horizontal", s


def fp_r_v():
    s = _hdr("R_Axial_0.25W_P2.54_Vertical",
             "1/4 W axial resistor standing up, 2.54 mm pitch", False)
    s.append(tht(1, -1.27, 0, 1.6, 0.8))
    s.append(tht(2, 1.27, 0, 1.6, 0.8))
    s.append(circle(-1.27, 0, 1.25, "F.Fab", 0.1))
    s.append(rect(-2.55, -1.28, 2.1, 1.28))
    return "R_Axial_0.25W_P2.54_Vertical", s


def fp_smb():
    s = _hdr("D_SMB", "SMB / DO-214AA diode, pad 1 = cathode", True)
    s.append(smd(1, -2.15, 0, 2.5, 2.3, 0.15))
    s.append(smd(2, 2.15, 0, 2.5, 2.3, 0.15))
    s.append(line(-3.6, -1.45, 1.2, -1.45))
    s.append(line(-3.6, 1.45, 1.2, 1.45))
    s.append(line(-3.6, -1.45, -3.6, 1.45))
    s.append(rect(-2.3, -1.9, 2.3, 1.9, "F.Fab", 0.1))
    s.append(rect(-3.5, -2.0, 3.5, 2.0))
    return "D_SMB", s


def fp_header(n):
    s = _hdr(f"PinHeader_1x{n:02d}_P2.54_Row",
             f"1x{n} 2.54 mm header row (also takes a 2.54 mm screw terminal"
             " or wires)", False)
    for i in range(n):
        s.append(tht(i + 1, i * 2.54, 0, 1.7, 1.0))
    s.append(rect(-1.27, -1.27, (n - 1) * 2.54 + 1.27, 1.27, "F.Fab", 0.1))
    s.append(rect(-1.3, -1.3, (n - 1) * 2.54 + 1.3, 1.3))
    return f"PinHeader_1x{n:02d}_P2.54_Row", s


def fp_mousebite():
    s = _hdr("MouseBite_NPTH_0.5mm", "Break-away perforation hole", False)
    s[3] = '  (attr exclude_from_pos_files exclude_from_bom)'
    s.append('  (pad "" np_thru_hole circle (at 0 0) (size 0.5 0.5) (drill 0.5)'
             ' (layers "*.Cu" "*.Mask"))')
    return "MouseBite_NPTH_0.5mm", s


def write_all():
    os.makedirs(OUT, exist_ok=True)
    names = []
    for fn in (fp_ic, fp_inductor, fp_c1210, fp_c0805_1206, fp_c_dual, fp_cp8,
               fp_r_h, fp_r_v, fp_smb, lambda: fp_header(2), lambda: fp_header(3),
               fp_mousebite):
        name, s = fn()
        with open(os.path.join(OUT, name + ".kicad_mod"), "w") as f:
            f.write("\n".join(s) + "\n)\n")
        names.append(name)
    return names


if __name__ == "__main__":
    for n in write_all():
        print("wrote", n)
