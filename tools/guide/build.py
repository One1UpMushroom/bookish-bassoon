#!/usr/bin/env python3
"""Builds docs/driver-build.html from the verified layout in layout.py.

    python3 tools/guide/build.py

Refuses to write the page if the breadboard placement does not implement the
schematic (see layout.verify).
"""
import html
import pathlib
import sys

import layout as L
from draw import (BOARD_TOP, BOARD_W, NICE, P, WIRE, badge, board_symbol, f, halo, hx, hy, letters,
                  part_svg, pt, ruler, tag, view_rows, wire, wire_halo, wire_path)
from pages import BEFORE, CHECK1, CHECK2, CHECK3, CSS, HEAD, LEDTEST, REFERENCE, SCRIPT

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "driver-build.html"

# step key, board, first row, last row, short title, one-line hint, inset key
STEPS = [
    ("bag", 1, "Board A", "Strip switches"),
    ("A1", "A", 1, 6, "Link the rails", "Red rail to red rail, blue rail to blue rail. On this board both red rails carry 24 V.", None),
    ("A2", "A", 1, 17, "Two MOSFETs", "Printed side faces column a. Left leg (G) goes in the lowest row number.", "to220"),
    ("A3", "A", 1, 17, "Gate resistors", "220 Ω feeds each gate. 100 kΩ holds it low while the QT Py boots.", None),
    ("A4", "A", 1, 17, "Clamp diodes", "The stripe end goes into the red + rail. A reversed diode shorts the supply.", "diode"),
    ("A5", "A", 1, 17, "Bulk capacitors", "Stripe (short leg) into the blue − rail. 50 V parts only.", "ecap"),
    ("A6", "A", 1, 17, "Ground links", "Ties each MOSFET's source row to the blue rail beside it.", None),
    ("bag", 2, "Board A", "Current-set pots"),
    ("A7", "A", 13, 30, "Three pots", "Outer legs are the track ends, the middle leg is the wiper. Shafts point off the board.", "pot"),
    ("A8", "A", 13, 30, "Pot grounds", "One outer leg of each pot goes to a blue rail.", None),
    ("bag", 3, "Board B", "12 V and the op-amp"),
    ("B1", "B", 23, 30, "Link the rails", "On this board the red rails carry 12 V. Never join them to Board A's red rails.", None),
    ("B2", "B", 1, 10, "12 V regulator", "L7812 printed side faces column a. The 10 µF stripe goes into the blue rail.", "to220"),
    ("B3", "B", 9, 21, "LM324", "Notch toward row 1, so pin 1 sits in e12. Then power, ground and the spare amplifier.", "dip"),
    ("bag", 4, "Board B", "Red current sink"),
    ("B4a", "B", 4, 16, "Link and MOSFET", "Fit the link first: it joins rows 9 and 10, right in front of the MOSFET. Printed side faces column a.", "to220"),
    ("B4b", "B", 4, 16, "Gate parts", "100 Ω from op-amp pin 1 to the gate. 100 kΩ holds the gate low at power-up.", None),
    ("B4c", "B", 4, 16, "Sense resistors", "Two 100 Ω side by side make 50 Ω. They set the 66 mA ceiling.", None),
    ("B4d", "B", 4, 16, "Feedback", "1 kΩ from the source row to pin 2. 1 nF from pin 1 to pin 2.", None),
    ("B4e", "B", 4, 16, "Bias and reference", "1 MΩ to the red rail keeps the LEDs fully dark at 0%. 100 kΩ holds pin 3 low if a wire falls out.", None),
    ("bag", 5, "Board B", "Green and blue sinks"),
    ("B5a", "B", 14, 27, "Links and MOSFETs", "Links first, then the MOSFETs. Both printed sides face column a. Keep the gap between the two: the metal tabs are live.", "to220"),
    ("B5b", "B", 14, 27, "Gate parts", "100 Ω from pins 7 and 8 to the gates. 100 kΩ from each gate to a blue rail.", None),
    ("B5c", "B", 14, 27, "Sense resistors", "Four 100 Ω: two per channel.", None),
    ("B5d", "B", 14, 27, "Feedback", "1 kΩ and 1 nF per channel.", None),
    ("B5e", "B", 14, 27, "Bias and reference", "1 MΩ to a red rail, 100 kΩ to a blue rail, per channel.", None),
    ("bag", 6, "Both boards", "Hook-up and first light"),
    ("C1", "AB", 1, 30, "Join the boards", "24 V and ground go across. The three pot wipers go to op-amp pins 3, 5 and 10.", None),
    ("check", "CONTROLLER"),
    ("C2", "A", 1, 30, "QT Py", "Five PWM wires and ground. The pin map is the one the firmware already uses.", "qtpy"),
    ("C3", "A", 1, 18, "24 V supply", "Unplug the supply first. Two thick wires carry the strip current back to the supply's − terminal.", None),
    ("check", CHECK1),
    ("C4", "A", 1, 18, "LED strip", "The strip's + lead goes straight to the supply's + terminal, not through the board.", None),
    ("check", CHECK2),
    ("check", LEDTEST),
    ("C5", "AB2", 1, 30, "RGB strings", "Each colour: four dies in series from Board A's red rail to that colour's drain row on Board B.", None),
    ("check", CHECK3),
]

# Where the flag of an off-board wire sits: wire id -> {board: (side, row, text)}
FLAGS = {
    "Q_A3": {"A": ("L", 2, "A3")}, "Q_TX": {"A": ("R", 7.8, "TX")},
    "Q_A0": {"A": ("M", 15.2, "A0")}, "Q_A1": {"A": ("M", 17.3, "A1")}, "Q_A2": {"A": ("M", 23.2, "A2")},
    "Q_G": {"A": ("R", 30.0, "GND")},
    "S_24": {"A": ("R", 3, "+24V")}, "S_gW": {"A": ("L", 10.6, "PSU−")}, "S_gC": {"A": ("R", 16.6, "PSU−")},
    "T_ww": {"A": ("L", 4.6, "WW−")}, "T_cw": {"A": ("R", 11.0, "CW−")},
    "L_aR": {"A": ("R", 23.6, "R+")}, "L_aG": {"A": ("R", 25.0, "G+")}, "L_aB": {"A": ("R", 26.4, "B+")},
    "L_kR": {"B": ("L", 8, "R−")}, "L_kG": {"B": ("L", 22, "G−")}, "L_kB": {"B": ("R", 22, "B−")},
    "X_24": {"A": ("R", 9.4, "B·j2"), "B": ("R", 2, "A·R+")},
    "X_gnd": {"A": ("R", 28.2, "B·L−"), "B": ("L", 1, "A·R−")},
    "X_refR": {"A": ("M", 19.2, "B·c14"), "B": ("L", 12, "A·c18")},
    "X_refG": {"A": ("M", 21.3, "B·c16"), "B": ("L", 18.6, "A·h20")},
    "X_refB": {"A": ("M", 25.6, "B·h16"), "B": ("R", 13.6, "A·c26")},
}

ORDER = [s[0] for s in STEPS if s[0] not in ("bag", "check")]


def step_rank(key):
    return ORDER.index(key)


def hole_text(board, hole, with_board=False):
    col, row = L.parse(hole)
    if col in L.RAILS:
        side = "left" if col[0] == "L" else "right"
        t = f"{side} {'+' if col[1] == '+' else '−'} rail"
    else:
        t = f"{col}{row}"
    return f"{board}·{t}" if with_board else t


def end_text(end, here):
    if end[0] == "ext":
        return end[1].replace(" -", " −")
    return hole_text(end[0], end[1], with_board=end[0] != here)


def flag_xy(board_side, row, ml, mr):
    if board_side == "L":
        return -ml * P + 4, hy(row), "start"
    if board_side == "R":
        return (BOARD_W + mr) * P - 4, hy(row), "end"
    return (hx("e") + hx("f")) / 2, hy(row), "middle"


def wire_geom(w, board, ml, mr):
    """Path of a wire as seen on one board, plus where its flag goes."""
    ends = [w.a, w.b]
    local = [e for e in ends if e[0] == board]
    if len(local) == 2:
        return wire_path(pt(local[0][1]), pt(local[1][1])), None
    if not local:
        return None, None
    x1, y1 = pt(local[0][1])
    side, row, text = FLAGS[w.id][board]
    fx, fy, anchor = flag_xy(side, row, ml, mr)
    tw = 7.0 * len(text) + 10
    ex = fx + (tw if anchor == "start" else -tw if anchor == "end" else (-tw / 2 if x1 < fx else tw / 2))
    d = f"M{f(x1)},{f(y1)}C{f((x1 + ex) / 2)},{f(y1)} {f((x1 + ex) / 2)},{f(fy)} {f(ex)},{f(fy)}"
    return d, (fx, fy, text, anchor)


def mid(p):
    pts = [pt(h) for h in p.pins.values()]
    if p.kind == "to220":
        return pts[0][0] - 0.16 * P, pts[2][1] + 1.25 * P
    if p.kind == "dip14":
        ys = sorted(q[1] for q in pts)
        return (hx("e") + hx("f")) / 2, ys[0] + 0.5 * P
    if p.kind == "pot":
        left = L.parse(p.pins["1"])[0] in L.LEFT
        return pts[1][0] + (-2.6 if left else 2.6) * P, pts[0][1] - 0.4 * P
    if p.kind == "ecap":
        return (pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2
    # two-leg parts: just past the first leg, so the body and its markings stay visible
    (x1, y1), (x2, y2) = pts[0], pts[1]
    d = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5 or 1
    return x1 + (x1 - x2) / d * 0.98 * P, y1 + (y1 - y2) / d * 0.98 * P


def diagram(board, key, r0, r1, ml=0.7, mr=0.7, label=None, show_new=True, k0=0):
    """One board at the moment step `key` has just been done."""
    rank = step_rank(key)
    old_p = [p for p in L.parts if p.board == board and step_rank(p.step) < rank]
    new_p = [p for p in L.parts if p.board == board and p.step == key] if show_new else []
    if not show_new:
        old_p = [p for p in L.parts if p.board == board and step_rank(p.step) <= rank]
    old_w = [w for w in L.wires if step_rank(w.step) < rank or (not show_new and w.step == key)]
    new_w = [w for w in L.wires if w.step == key] if show_new else []

    x0 = -ml * P
    y0, y1 = view_rows(r0, r1)
    w, h = (BOARD_W + ml + mr) * P, y1 - y0
    o = [f'<svg viewBox="{f(x0)} {f(y0)} {f(w)} {f(h)}" class="bb" role="img" aria-label="{html.escape(label or "")}">']
    o.append(f'<use href="#bb{board}"/>')
    cls = "old" if show_new else "all"
    o.append(f'<g class="{cls}">')
    for p in old_p:
        o.append(part_svg(p))
    for wv in old_w:
        d, _ = wire_geom(wv, board, ml, mr)
        if d:
            o.append(wire(d, wv.color, wv.thick))
    o.append("</g>")
    keys = {}
    if show_new:
        letters_ = "ABCDEFGHJKLMNPQRSTUVWXYZ"
        k = k0
        for p in new_p:
            o.append(halo(p))
        geoms = []
        for wv in new_w:
            d, flag = wire_geom(wv, board, ml, mr)
            if d:
                o.append(wire_halo(d, wv.thick))
                geoms.append((wv, d, flag))
        for p in new_p:
            o.append(part_svg(p))
        for wv, d, flag in geoms:
            o.append(wire(d, wv.color, wv.thick))
        o.append(ruler(r0, r1))
        for p in new_p:
            keys[p.id] = letters_[k]
            x, y = mid(p)
            o.append(badge(x, y, letters_[k]))
            k += 1
        for wv, d, flag in geoms:
            keys[wv.id] = letters_[k]
            if flag:
                fx, fy, text, anchor = flag
                o.append(tag(fx, fy, text, anchor))
                local = [e for e in (wv.a, wv.b) if e[0] == board][0]
                x, y = pt(local[1])
                o.append(badge(x, y - 0.95 * P, letters_[k]))
            else:
                (xa, ya), (xb, yb) = pt(wv.a[1]), pt(wv.b[1])
                o.append(badge((xa + xb) / 2, (ya + yb) / 2, letters_[k]))
            k += 1
    else:
        o.append(ruler(r0, r1))
    o.append("</svg>")
    return "".join(o), keys


def overview(key, highlight=True, label=""):
    """Both boards side by side with the board-to-board wires drawn through."""
    rank = step_rank(key)
    gap = 5.5
    bw = BOARD_W * P
    off = {"A": 0, "B": (BOARD_W + gap) * P}
    w, h = (2 * BOARD_W + gap + 1.4) * P, (L.ROWS + 4.3) * P
    o = [f'<svg viewBox="{f(-0.7 * P)} {f(-2.4 * P)} {f(w)} {f(h)}" class="bb ov" role="img" aria-label="{html.escape(label)}">']
    for b in "AB":
        o.append(f'<g transform="translate({f(off[b])},0)"><use href="#bb{b}"/>')
        o.append(f'<text x="{f(bw / 2)}" y="{f(-1.1 * P)}" text-anchor="middle" class="bt2">Board {b}</text>')
        o.append(f'<g class="{"old" if highlight else "all"}">')
        for p in L.parts:
            if p.board == b and step_rank(p.step) <= rank:
                o.append(part_svg(p))
        for wv in L.wires:
            if step_rank(wv.step) <= rank and wv.a[0] == b and wv.b[0] == b:
                o.append(wire(wire_path(pt(wv.a[1]), pt(wv.b[1])), wv.color, wv.thick))
        o.append("</g></g>")
    cross = [wv for wv in L.wires if {wv.a[0], wv.b[0]} == {"A", "B"} and step_rank(wv.step) <= rank]
    keys = {}
    for n, wv in enumerate(cross):
        a, b = (wv.a, wv.b) if wv.a[0] == "A" else (wv.b, wv.a)
        (xa, ya), (xb, yb) = pt(a[1]), pt(b[1])
        xb += off["B"]
        sag = (3.2 + 1.5 * n) * P
        d = f"M{f(xa)},{f(ya)}C{f(xa + sag)},{f(ya + sag * 0.5)} {f(xb - sag)},{f(yb + sag * 0.5)} {f(xb)},{f(yb)}"
        if highlight and wv.step == key:
            o.append(wire_halo(d))
        o.append(wire(d, wv.color, wv.thick))
        if highlight and wv.step == key:
            letter = "ABCDEFGH"[n]
            keys[wv.id] = letter
            o.append(badge((xa + xb) / 2, (ya + yb) / 2 + sag * 0.375, letter))
    o.append("</svg>")
    return "".join(o), keys


# --------------------------------------------------------------------------
# Parts boxes
# --------------------------------------------------------------------------
def icon(kind, value="", color=None):
    """Small picture of one part for the parts box."""
    from draw import ceramic, diode, dip14, ecap, pot, resistor, staple, to220
    if kind == "res":
        return f'<svg viewBox="0 0 64 22" class="ic-s">{resistor((4, 11), (60, 11), value)}</svg>'
    if kind == "cap":
        return f'<svg viewBox="0 0 40 22" class="ic-s">{ceramic((6, 11), (34, 11), value)}</svg>'
    if kind == "diode":
        return f'<svg viewBox="0 0 64 22" class="ic-s">{diode((4, 11), (60, 11))}</svg>'
    if kind == "ecap":
        r = 28 if value == "100u" else 21
        return f'<svg viewBox="0 0 60 60" class="ic-m">{ecap((30 - 8, 30), (30 + 8, 30), value)}</svg>'
    if kind == "to220":
        names = ["I", "G", "O"] if value == "L7812" else ["G", "D", "S"]
        return f'<svg viewBox="0 0 44 76" class="ic-t">{to220([(20, 22), (20, 38), (20, 54)], names)}</svg>'
    if kind == "dip14":
        return ('<svg viewBox="0 0 76 128" class="ic-d"><g transform="translate(-126,-180)">'
                + dip14([(hx("e"), hy(12 + i)) for i in range(7)] + [(hx("f"), hy(12 + i)) for i in range(7)]) + "</g></svg>")
    if kind == "pot":
        return f'<svg viewBox="0 0 100 110" class="ic-p">{pot([(84, 23), (84, 55), (84, 87)], True)}</svg>'
    if kind == "staple":
        return f'<svg viewBox="0 0 40 22" class="ic-s">{staple((12, 11), (28, 11))}</svg>'
    if kind == "wire":
        return f'<svg viewBox="0 0 64 22" class="ic-s">{wire("M6,11C22,2 42,20 58,11", color)}</svg>'
    if kind == "thick":
        return f'<svg viewBox="0 0 64 22" class="ic-s">{wire("M6,11C22,2 42,20 58,11", color, True)}</svg>'
    return ""


KIND_NAME = {"to220": "", "dip14": "", "pot": "pot", "ecap": "electrolytic", "cap": "ceramic", "diode": "Schottky",
             "res": "", "staple": "wire link, 0.1 in"}
WIRE_NAME = {"red": "red", "black": "black", "orange": "orange", "yellow": "yellow", "white": "white",
             "pink": "pink", "lime": "green", "sky": "blue", "amber": "amber", "ice": "pale blue"}


def part_name(p):
    v = NICE.get(p.value, p.value)
    if p.kind == "ecap":
        return f"{v} 50 V"
    if p.kind == "pot":
        return "10 kΩ pot"
    if p.kind == "staple":
        return "wire link"
    return v


def parts_box(new_p, new_w):
    groups = {}
    for p in new_p:
        groups.setdefault((p.kind, p.value, p.inv), []).append(p)
    cells = []
    for (kind, value, inv), ps in groups.items():
        name = part_name(ps[0])
        sub = f'<span class="inv">{inv}</span>' if inv else ""
        cells.append(f'<div class="pc">{icon(kind, value)}<b>{len(ps)}x</b><span>{name}</span>{sub}</div>')
    wg = {}
    for w in new_w:
        wg.setdefault((w.color, w.thick), []).append(w)
    for (color, thick), ws in wg.items():
        name = f"{WIRE_NAME[color]} {'thick wire' if thick else 'jumper'}"
        cells.append(f'<div class="pc">{icon("thick" if thick else "wire", color=color)}<b>{len(ws)}x</b><span>{name}</span></div>')
    return '<div class="need">' + "".join(cells) + "</div>"


def placements(board, new_p, new_w, keys):
    rows = []
    for p in new_p:
        if p.id not in keys:
            continue
        if p.kind == "to220":
            where = " · ".join(f"{n} {hole_text(p.board, h)}" for n, h in p.pins.items())
        elif p.kind == "dip14":
            where = "pin 1 e12 … pin 7 e18 · pin 14 f12 … pin 8 f18"
        elif p.kind == "pot":
            where = " · ".join(hole_text(p.board, p.pins[n]) for n in ("1", "W", "3")) + " (wiper in the middle)"
        elif p.kind == "ecap":
            where = f"+ {hole_text(p.board, p.pins['+'])} · stripe {hole_text(p.board, p.pins['-'])}, level with row {L.parse(p.pins['+'])[1]}"
        elif p.kind == "diode":
            where = f"{hole_text(p.board, p.pins['A'])} → stripe end in the {hole_text(p.board, p.pins['K'])}"
        else:
            hs = list(p.pins.values())
            where = f"{hole_text(p.board, hs[0])} → {hole_text(p.board, hs[1])}"
        tagb = f'{p.board}·' if board == "AB" else ""
        rows.append(f'<li><b class="k">{keys[p.id]}</b><span class="what">{part_name(p)}</span><span class="mono">{tagb}{where}</span></li>')
    for w in new_w:
        if w.id not in keys:
            continue
        here = board if board in "AB" else "?"
        a, b = end_text(w.a, here), end_text(w.b, here)
        name = f"{WIRE_NAME[w.color]}{' thick' if w.thick else ''} wire"
        rows.append(f'<li><b class="k">{keys[w.id]}</b><span class="what">{name}</span><span class="mono">{a} → {b}</span></li>')
    return '<ol class="put">' + "".join(rows) + "</ol>"


INSETS = {
    "to220": ('<svg viewBox="0 0 150 120" class="ins"><rect x="46" y="6" width="58" height="26" rx="3" fill="#C3C9CF" stroke="#7F8891"/>'
              '<circle cx="75" cy="18" r="6" fill="#F4F0E6" stroke="#7F8891"/><rect x="46" y="28" width="58" height="42" rx="3" fill="#2A2D31"/>'
              '<text x="75" y="46" text-anchor="middle" class="it">printed</text><text x="75" y="60" text-anchor="middle" class="it">side</text>'
              '<path d="M57,70v32M75,70v32M93,70v32" stroke="#A9B0B7" stroke-width="4" stroke-linecap="round"/>'
              '<text x="57" y="116" text-anchor="middle" class="iq">1</text><text x="75" y="116" text-anchor="middle" class="iq">2</text><text x="93" y="116" text-anchor="middle" class="iq">3</text></svg>',
              "Facing the print, leg 1 is on the left. Leg 1 always goes in the lowest row number, so the print faces column a."),
    "diode": ('<svg viewBox="0 0 150 60" class="ins"><path d="M8,30H142" stroke="#B7BDC3" stroke-width="4" stroke-linecap="round"/>'
              '<rect x="42" y="16" width="66" height="28" rx="4" fill="#26282B"/><rect x="90" y="16" width="10" height="28" fill="#D7DBDF"/>'
              '<text x="128" y="20" text-anchor="middle" class="iq">+ rail</text><text x="20" y="20" text-anchor="middle" class="iq">row</text></svg>',
              "The silver stripe marks the end that goes into the red + rail."),
    "ecap": ('<svg viewBox="0 0 150 96" class="ins"><rect x="44" y="6" width="62" height="56" rx="6" fill="#22315C"/>'
             '<rect x="86" y="6" width="20" height="56" rx="6" fill="#DDE3EA"/><text x="96" y="40" text-anchor="middle" class="pm">−</text>'
             '<path d="M62,62v28M92,62v20" stroke="#A9B0B7" stroke-width="4" stroke-linecap="round"/>'
             '<text x="52" y="92" text-anchor="end" class="iq">long +</text><text x="102" y="92" class="iq">short −</text></svg>',
             "The stripe and the short leg are −. Reversed electrolytics on 24 V can burst."),
    "pot": ('<svg viewBox="0 0 150 96" class="ins"><circle cx="75" cy="36" r="30" fill="#AEB6BF" stroke="#6E7781"/><circle cx="75" cy="36" r="10" fill="#D9DDE2" stroke="#8A929B"/>'
            '<path d="M55,64v24M75,66v22M95,64v24" stroke="#A9B0B7" stroke-width="4" stroke-linecap="round"/>'
            '<text x="40" y="92" text-anchor="end" class="iq">end</text><text x="75" y="80" text-anchor="middle" class="it2">W</text><text x="110" y="92" class="iq">end</text></svg>',
            "Any 10 kΩ pot works. One end leg gets the QT Py wire, the middle leg (wiper) goes to Board B, the other end leg goes to a blue rail. If your pot's legs land in other rows, move those three wires to match."),
    "dip": ('<svg viewBox="0 0 150 96" class="ins"><rect x="50" y="8" width="50" height="80" rx="4" fill="#2A2D31"/><path d="M67,8a8,8 0 0 0 16,0z" fill="#73797F"/>'
            '<circle cx="59" cy="20" r="3.4" fill="#E9ECEF"/><path d="M38,20H50M38,32H50M38,44H50M38,56H50M38,68H50M38,80H50M100,20H112M100,32H112M100,44H112M100,56H112M100,68H112M100,80H112" stroke="#C3C9CF" stroke-width="4"/>'
            '<text x="32" y="24" text-anchor="end" class="iq">pin 1</text><text x="118" y="24" class="iq">pin 14</text></svg>',
            "The notch and the dot mark pin 1. Press the chip fully home so all 14 legs seat."),
    "qtpy": ('<svg viewBox="0 0 170 132" class="ins"><rect x="42" y="14" width="86" height="104" rx="10" fill="#1F2328"/><rect x="66" y="6" width="38" height="20" rx="4" fill="#C3C9CF"/>'
             + "".join(f'<circle cx="46" cy="{34 + 13 * i}" r="4.2" fill="#E0B341"/><text x="36" y="{37.5 + 13 * i}" text-anchor="end" class="iq">{n}</text>'
                       for i, n in enumerate(["A0", "A1", "A2", "A3", "SDA", "SCL", "TX"]))
             + "".join(f'<circle cx="124" cy="{34 + 13 * i}" r="4.2" fill="#E0B341"/><text x="134" y="{37.5 + 13 * i}" class="iq">{n}</text>'
                       for i, n in enumerate(["5V", "GND", "3V", "MO", "MI", "SCK", "RX"]))
             + '<text x="85" y="72" text-anchor="middle" class="it">QT Py</text><text x="85" y="86" text-anchor="middle" class="it">USB up</text></svg>',
             "Pads as seen from above with the USB-C socket at the top. Only A0–A3, TX and GND come to these boards."),
}


def controller_card():
    """The controller itself: QT Py to display and encoder. Connections by name, not a breadboard layout."""
    left = ["A0", "A1", "A2", "A3", "SDA", "SCL", "TX"]
    right = ["5V", "GND", "3V", "MO", "MI", "SCK", "RX"]
    y = lambda i: 62 + 19 * i
    gold = lambda cx, cy: f'<circle cx="{cx}" cy="{cy}" r="4.6" fill="#E0B341" stroke="#7A5C12" stroke-width="0.8"/>'
    # display pins on its right edge, fed by nested loops from the QT Py's right-hand pads (no crossings)
    loops = [("Lite", 296, "RX", "orange", 270), ("SCK", 318, "SCK", "yellow", 282), ("SI", 340, "MO", "lime", 294),
             ("Vin", 362, "3V", "red", 306), ("GND", 384, "GND", "black", 318)]
    o = ['<svg viewBox="0 0 380 476" class="ctl" role="img" aria-label="Controller wiring: QT Py pads GND, 3V, MO, SCK and RX go to the display pins GND, Vin, SI, SCK and Lite; SDA and SCL go to TCS and D/C; MI goes to the encoder INT pad; a STEMMA QT cable joins the QT Py and the encoder; A0 to A3 and TX go to Board A.">']
    # boards
    o.append('<rect x="172" y="28" width="36" height="24" rx="4" fill="#C3C9CF" stroke="#7F8891"/>')
    o.append('<rect x="140" y="40" width="100" height="156" rx="10" fill="#1F2328"/>')
    o.append('<rect x="176" y="190" width="28" height="16" rx="2" fill="#D9DDE2" stroke="#8A929B"/>')
    o.append('<rect x="100" y="270" width="156" height="140" rx="8" fill="#24384A" stroke="#0F1113"/>')
    o.append('<rect x="150" y="288" width="58" height="58" rx="3" fill="#0E1620" stroke="#5D7A93"/>')
    o.append('<rect x="100" y="424" width="156" height="42" rx="8" fill="#24384A" stroke="#0F1113"/>')
    o.append('<circle cx="124" cy="445" r="13" fill="#C3C9CF" stroke="#7F8891"/><circle cx="124" cy="445" r="5" fill="#8A929B"/>')
    o.append('<rect x="94" y="432" width="12" height="14" rx="2" fill="#D9DDE2" stroke="#8A929B"/>')
    # wires
    for name, col in (("A0", "pink"), ("A1", "lime"), ("A2", "sky"), ("A3", "yellow"), ("TX", "white")):
        o.append(wire(f"M148,{y(left.index(name))}H126", col))
    o.append(wire("M148,138H38V318H100", "sky"))     # SDA -> TCS
    o.append(wire("M148,157H50V296H100", "white"))   # SCL -> D/C
    for pin, py, pad, col, vx in loops:
        o.append(wire(f"M232,{y(right.index(pad))}H{vx}V{py}H256", col))
    o.append(wire("M232,138H248", "violet"))         # MI -> encoder INT (flagged, not routed)
    o.append(wire("M256,456H272", "violet"))
    o.append(wire("M190,206V236", "black", True))    # STEMMA QT cable
    o.append(wire("M94,439H78", "black", True))
    # pads and labels
    for i, n_ in enumerate(left):
        o.append(gold(148, y(i)) + f'<text x="158" y="{y(i) + 3.3}" class="it">{n_}</text>')
    for i, n_ in enumerate(right):
        o.append(gold(232, y(i)) + f'<text x="222" y="{y(i) + 3.3}" text-anchor="end" class="it">{n_}</text>')
    for pin, py, pad, col, vx in loops:
        o.append(gold(256, py) + f'<text x="246" y="{py + 3.3}" text-anchor="end" class="it">{pin}</text>')
    o.append(gold(100, 296) + '<text x="110" y="299.3" class="it">D/C</text>')
    o.append(gold(100, 318) + '<text x="110" y="321.3" class="it">TCS</text>')
    o.append(gold(256, 456) + '<text x="246" y="459.3" text-anchor="end" class="it">INT</text>')
    o.append('<text x="190" y="22" text-anchor="middle" class="iq">USB-C</text>')
    o.append('<text x="179" y="314" text-anchor="middle" class="it">240 ×</text><text x="179" y="327" text-anchor="middle" class="it">240</text>')
    o.append('<text x="110" y="284" class="it">Display</text>')
    o.append('<text x="110" y="362" class="it">leave open:</text><text x="110" y="376" class="it">3Vo · SO · RST</text><text x="110" y="390" class="it">CCS · TE</text>')
    o.append('<text x="146" y="448.3" class="it">Encoder</text>')
    o.append(tag(122, 90, "Board A", "end") + tag(122, 176, "Board A", "end"))
    o.append(tag(252, 138, "INT", "start") + tag(276, 456, "MI", "start"))
    o.append(tag(190, 248, "encoder") + tag(74, 439, "QT Py", "end"))
    o.append("</svg>")
    rows = [("red", "QT Py 3V → display Vin"), ("black", "GND → GND"), ("lime", "MO → SI (MOSI)"),
            ("yellow", "SCK → SCK"), ("orange", "RX → Lite (backlight)"), ("sky", "SDA → TCS"),
            ("white", "SCL → D/C"), ("violet", "MI → encoder INT pad (optional)")]
    lst = "".join(f'<li><b class="k dot" style="background:{WIRE[c]}"></b><span class="mono">{t}</span></li>' for c, t in rows)
    return ('<section class="sheet" id="controller"><span class="where">Reference · if the controller is not wired yet</span>'
            '<h3>QT Py, display and encoder</h3>'
            '<figure class="traybox">' + "".join(o) + '</figure>'
            f'<ol class="put two-col">{lst}</ol>'
            '<p class="hint">The encoder plugs into the QT Py with a STEMMA QT cable of 15 cm or less. Power the QT Py from USB-C. '
            'Wire colours here are only a suggestion. This is the pin map the firmware expects; the README has it as a table.</p></section>')


def step_html(n, key, board, r0, r1, title, hint, inset):
    new_p = [p for p in L.parts if p.step == key]
    new_w = [w for w in L.wires if w.step == key]
    figs = []
    keys = {}
    if board == "AB":
        svg, keys = overview(key, True, f"Step {n}: both boards with the linking wires highlighted")
        figs.append(svg)
    elif board == "AB2":
        sa, ka = diagram("A", key, 19, 30, 0.7, 3.4, f"Step {n} on Board A")
        sb, kb = diagram("B", key, 5, 25, 3.4, 3.4, f"Step {n} on Board B", k0=len(ka))
        # letters must stay unique across the two pictures
        figs += [sa, sb]
        keys = {**ka, **kb}
    else:
        wide = key.startswith("C")
        svg, keys = diagram(board, key, r0, r1, 3.4 if wide else 0.7, 3.4 if wide else 0.7,
                            f"Step {n} on Board {board}: {title}")
        figs.append(svg)
    box = parts_box(new_p, new_w)
    lst = placements(board if board in "AB" else "AB", new_p, new_w, keys)
    ins = ""
    if inset:
        pic, text = INSETS[inset]
        ins = f'<aside class="tip{" wide" if inset == "qtpy" else ""}">{pic}<p>{text}</p></aside>'
    where = {"A": "Board A", "B": "Board B", "AB": "Both boards", "AB2": "Both boards"}[board]
    plates = "".join(f'<figure class="plate{" scroll" if board == "AB" else ""}">{s}</figure>' for s in figs)
    return (f'<article class="step" id="step-{n}"><header><span class="num">{n}</span>'
            f'<div class="ttl"><span class="where">{where}</span><h3>{title}</h3></div>'
            f'<label class="done"><input type="checkbox" id="done-{n}"><span>Done</span></label></header>'
            f'<div class="cols"><div class="side">{box}{ins}</div><div class="main">{plates}</div></div>'
            f'{lst}<p class="hint">{hint}</p></article>')


def main():
    errs, nets = L.verify()
    if errs:
        for e in errs:
            print("ERROR", e)
        sys.exit("layout does not implement the schematic; page not written")

    body = []
    n = 0
    bag_nav = []
    for s in STEPS:
        if s[0] == "bag":
            _, num, where, name = s
            bag_nav.append((num, name))
            body.append(f'<header class="bag" id="bag-{num}"><span class="bagno">{num}</span>'
                        f'<div><span class="where">{where}</span><h2>{name}</h2></div></header>')
        elif s[0] == "check":
            body.append(controller_card() if s[1] == "CONTROLLER" else s[1])
        else:
            n += 1
            body.append(step_html(n, *s))
    total = n

    cover, _ = overview(ORDER[-1], False, "Both finished breadboards: Board A with the strip switches and pots, Board B with the regulator, op-amp and three current sinks")
    comp = sum(1 for p in L.parts if p.kind != "staple")
    nav = "".join(f'<a href="#bag-{num}"><b>{num}</b>{name}</a>' for num, name in bag_nav)

    # parts list
    inv_have = {"Q-004": 19, "VR-006": 5, "IC-001": 12, "D-002": 25, "E-041": 10, "R-005": 50, "R-006": 50,
                "R-008": 50, "R-011": 50, "R-014": 25, "R-017": 25, "C-011": 10, "C-021": 10, "C-024": 10,
                "C-038": 16, "C-044": 6}
    rows = []
    order = ["to220", "dip14", "diode", "pot", "res", "cap", "ecap"]
    bom = {}
    for p in L.parts:
        if p.kind == "staple":
            continue
        bom.setdefault((p.kind, p.value, p.inv), []).append(p)
    for (kind, value, inv), ps in sorted(bom.items(), key=lambda kv: (order.index(kv[0][0]), kv[0][1])):
        extra = 1 if (kind, value) == ("res", "220") else 0
        note = " (+1 for the LED test)" if extra else ""
        rows.append(f'<div class="pc big">{icon(kind, value)}<b>{len(ps)}x</b><span>{part_name(ps[0])}{note}</span>'
                    f'<span class="inv">{inv} · have {inv_have[inv]}</span></div>')
    partlist = '<div class="need all">' + "".join(rows) + "</div>"

    page = HEAD.format(css=CSS, defs=board_symbol("bbA", "24", "A") + board_symbol("bbB", "12", "B"),
                       cover=cover, comp=comp, total=total, nav=nav, before=BEFORE, partlist=partlist,
                       steps="".join(body), reference=REFERENCE, script=SCRIPT)
    OUT.write_text(page)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(page) / 1024:.0f} KB, {total} steps, {comp} components, {len(nets)} nets verified")


if __name__ == "__main__":
    main()
