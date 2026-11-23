#!/usr/bin/python3
"""Builds docs/driver-build.html, the step-by-step build booklet for the board.

    /usr/bin/python3 tools/pcb/guide.py

The pictures are drawn on the render of the real Gerber files
(hardware/tasklamp-driver/img/board-top.svg, made by render.js), and every part
is placed from the same coordinates the board generator uses, so a part moved
on the board moves in the booklet too.
"""
import base64
import html
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import design  # noqa: E402
import gen_pcb as B  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMG = os.path.join(ROOT, 'hardware', 'tasklamp-driver', 'img')
OUT = os.path.join(ROOT, 'docs', 'driver-build.html')

W, H = B.W, B.H
BLACK, SILVER, GOLD = '#1E242B', '#C9CED3', '#D8B24A'
BAND = {'red': '#D9342B', 'black': '#15181C', 'brown': '#7A4A21', 'orange': '#F08A1C'}
BANDS = {'220': ['red', 'red', 'black', 'black', 'brown'], '100k': ['brown', 'black', 'black', 'orange', 'brown']}


def f(v):
    s = ('%.2f' % v).rstrip('0').rstrip('.')
    return '0' if s == '-0' else s


def rot(dx, dy, deg):
    """A footprint offset turned by KiCad's rotation (counter-clockwise on the page)."""
    r = math.radians(deg)
    return dx * math.cos(r) + dy * math.sin(r), -dx * math.sin(r) + dy * math.cos(r)


# ---------------------------------------------------------------------------
# Where every part is: {ref: (kind, bounding box, draw function arguments)}
# ---------------------------------------------------------------------------
def geometry():
    pl = B.placements()
    g = {}

    def pad(ref, dx, dy=0.0):
        x, y, r = pl[ref]
        ox, oy = rot(dx, dy, r)
        return x + ox, y + oy

    for i in range(5):
        n = i + 1
        for ref, value in (('R%d' % n, '220'), ('R%d' % (n + 5), '100k')):
            g[ref] = ('res', pad(ref, 0), pad(ref, 10.16), value)
        g['D%d' % n] = ('dio', pad('D%d' % n, 0), pad('D%d' % n, 10.16), (2.7, 5.2))
        g['Q%d' % n] = ('fet', pad('Q%d' % n, 0))
    g['D6'] = ('dio', pad('D6', 0), pad('D6', 10.16), (2.7, 5.2))
    g['D7'] = ('dio', pad('D7', 0), pad('D7', 15.24), (5.3, 9.5))
    g['D8'] = ('dio', pad('D8', 0), pad('D8', 12.7), (3.6, 7.6))
    # the 5 V buck converter: surface-mount parts, drawn at their centres
    g['U2'] = ('ic', (pl['U2'][0], pl['U2'][1]))
    g['L1'] = ('ind', (pl['L1'][0], pl['L1'][1]))
    for ref in ('C3', 'C4', 'C8', 'C9', 'C10', 'C11'):
        g[ref] = ('chip', (pl[ref][0], pl[ref][1]), 3.2, 2.5, '#C9A26B', pl[ref][2])
    g['C5'] = ('chip', (pl['C5'][0], pl['C5'][1]), 2.0, 1.25, '#C9A26B', pl['C5'][2])
    for ref in ('R11', 'R12'):
        g[ref] = ('chip', (pl[ref][0], pl[ref][1]), 3.2, 1.6, '#1E242B', pl[ref][2])
    for ref in ('C6', 'C7'):
        g[ref] = ('cer', pad(ref, -2.54), pad(ref, 2.54))
    g['SK1'] = ('strip', (B.QX, B.QY0), 7, 'socket')
    g['SK2'] = ('strip', (B.QX + 15.24, B.QY0), 7, 'socket')
    g['J4'] = ('strip', (pl['J4'][0], pl['J4'][1]), 8, 'header')
    g['F1'] = ('holder', (pl['F1'][0], pl['F1'][1]))
    g['FUSE'] = ('fuse', (pl['F1'][0] + 4.96, pl['F1'][1] + 1.7))
    g['J1'] = ('term', pad('J1', 5.08), 2, 'up')
    g['J3'] = ('term', pad('J3', 0), 4, 'down')
    g['J2'] = ('term', pad('J2', 0), 3, 'down')
    for ref, radius in (('C1', 4.0), ('C2', 4.0)):
        pitch = 3.5 if radius > 3 else 2.0
        g[ref] = ('ecap', pad(ref, 0), pad(ref, pitch), radius)
    g['U1'] = ('qtpy', (B.QX, B.QY0))
    return g


def bbox(item):
    kind = item[0]
    if kind in ('res', 'dio', 'cer'):
        (x1, y1), (x2, y2) = item[1], item[2]
        half = {'res': 1.25, 'cer': 1.25}.get(kind) or item[3][0] / 2
        pad = 1.1 if kind == 'dio' and item[3][0] < 3 else (1.6 if kind == 'dio' else 0.8)
        if abs(x1 - x2) < 0.01:
            return x1 - max(half, pad), min(y1, y2) - pad, x1 + max(half, pad), max(y1, y2) + pad
        return min(x1, x2) - pad, y1 - max(half, pad), max(x1, x2) + pad, y1 + max(half, pad)
    if kind == 'fet':
        x, y = item[1]
        return x - 2.46, y - 3.15, x + 7.54, y + 1.25
    if kind == 'strip':
        (x, y), n = item[1], item[2]
        return x - 1.27, y - 1.27, x + 1.27, y + (n - 1) * 2.54 + 1.27
    if kind == 'holder':
        x, y = item[1]
        return x - 3.04, y - 1.67, x + 12.96, y + 5.07
    if kind == 'fuse':
        x, y = item[1]
        return x - 5.45, y - 1.9, x + 5.45, y + 1.9
    if kind == 'term':
        (x, y), n, entry = item[1], item[2], item[3]
        y0, y1 = (y - 4.6, y + 5.2) if entry == 'up' else (y - 5.2, y + 4.6)
        return x - 2.54, y0, x + (n - 1) * 5.08 + 2.54, y1
    if kind == 'ecap':
        (x1, y1), (x2, y2), r = item[1], item[2], item[3]
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        return cx - r, cy - r, cx + r, cy + r
    if kind == 'ic':
        x, y = item[1]
        return x - 3.9, y - 2.5, x + 3.9, y + 2.5
    if kind == 'ind':
        x, y = item[1]
        return x - 3.65, y - 3.3, x + 3.65, y + 3.3
    if kind == 'chip':
        (x, y), w, h = item[1], item[2], item[3]
        if item[5] % 180 == 90:
            w, h = h, w
        return x - w / 2 - 0.3, y - h / 2 - 0.3, x + w / 2 + 0.3, y + h / 2 + 0.3
    if kind == 'qtpy':
        x, y = item[1]
        return x - 1.27, y - 2.73, x + 16.51, y + 17.97
    raise ValueError(kind)


# ---------------------------------------------------------------------------
# Top views, in board millimetres
# ---------------------------------------------------------------------------
def rect(x, y, w, h, fill, rx=0.0, extra=''):
    return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"%s/>' % (f(x), f(y), f(w), f(h), f(rx), fill, extra)


def line(x1, y1, x2, y2, stroke, w):
    return '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        f(x1), f(y1), f(x2), f(y2), stroke, f(w))


def axial(p1, p2, length, dia, fill, marks):
    """A two-legged part lying between two pads. `marks` are (position 0..1, colour, width)."""
    (x1, y1), (x2, y2) = p1, p2
    vertical = abs(x1 - x2) < 0.01
    s = line(x1, y1, x2, y2, SILVER, 0.6)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    if vertical:
        sign = 1 if y2 > y1 else -1
        s += rect(cx - dia / 2, cy - length / 2, dia, length, fill, min(0.9, dia / 3))
        for pos, col, wd in marks:
            yy = cy + sign * (pos - 0.5) * length
            s += rect(cx - dia / 2, yy - wd / 2, dia, wd, col)
    else:
        sign = 1 if x2 > x1 else -1
        s += rect(cx - length / 2, cy - dia / 2, length, dia, fill, min(0.9, dia / 3))
        for pos, col, wd in marks:
            xx = cx + sign * (pos - 0.5) * length
            s += rect(xx - wd / 2, cy - dia / 2, wd, dia, col)
    return s


def draw(item):
    kind = item[0]
    if kind == 'res':
        marks = [(0.14 + 0.15 * i + (0.1 if i == 4 else 0), BAND[c], 0.55) for i, c in enumerate(BANDS[item[3]])]
        return axial(item[1], item[2], 6.3, 2.5, '#5D9BD5', marks)
    if kind == 'dio':
        dia, length = item[3]
        return axial(item[1], item[2], length, dia, BLACK, [(0.12, SILVER, max(0.6, length * 0.11))])
    if kind == 'cer':
        return axial(item[1], item[2], 5.0, 2.5, '#E0B04A', [])
    if kind == 'fet':
        x, y = item[1]
        s = rect(x - 2.46, y - 3.15, 10.0, 1.27, '#AEB6BD', 0.2)
        s += rect(x - 2.46, y - 1.88, 10.0, 3.13, BLACK, 0.3)
        s += '<circle cx="%s" cy="%s" r="0.45" fill="#6B747C"/>' % (f(x + 2.54), f(y - 2.5))
        for k in range(3):
            s += '<circle cx="%s" cy="%s" r="0.5" fill="%s"/>' % (f(x + 2.54 * k), f(y), SILVER)
        return s
    if kind == 'strip':
        (x, y), n, style = item[1], item[2], item[3]
        s = rect(x - 1.27, y - 1.27, 2.54, n * 2.54, BLACK, 0.25)
        for k in range(n):
            if style == 'socket':
                s += rect(x - 0.55, y + k * 2.54 - 0.55, 1.1, 1.1, '#59626B', 0.15)
            else:
                s += rect(x - 0.4, y + k * 2.54 - 0.4, 0.8, 0.8, GOLD)
        return s
    if kind == 'holder':
        x, y = item[1]
        s = rect(x - 3.04, y - 1.67, 16.0, 6.74, BLACK, 0.5)
        s += rect(x + 0.6, y + 0.8, 8.7, 1.8, '#0D1013', 0.3)
        for px in (x, x + 9.92):
            s += rect(px - 0.9, y - 0.6, 1.8, 4.6, '#8A9299', 0.2)
        return s
    if kind == 'fuse':
        x, y = item[1]
        s = rect(x - 5.45, y - 1.9, 10.9, 3.8, '#9DA3A8', 0.5)
        s += '<text x="%s" y="%s" class="pv" text-anchor="middle">2</text>' % (f(x), f(y + 1.0))
        return s
    if kind == 'term':
        (x, y), n, entry = item[1], item[2], item[3]
        x0, y0, x1, y1 = bbox(item)
        s = rect(x0, y0, x1 - x0, y1 - y0, '#2E9E5B', 0.4)
        lip = y0 if entry == 'up' else y1 - 2.0
        s += rect(x0, lip, x1 - x0, 2.0, '#237A46', 0.4)
        for k in range(n):
            cx = x + k * 5.08
            s += '<circle cx="%s" cy="%s" r="1.7" fill="%s"/>' % (f(cx), f(y), SILVER)
            s += line(cx - 1.1, y - 0.5, cx + 1.1, y + 0.5, '#5B646C', 0.45)
        return s
    if kind == 'ecap':
        (x1, y1), (x2, y2), r = item[1], item[2], item[3]
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        ux, uy = (x2 - x1), (y2 - y1)          # from + toward the negative side
        n = math.hypot(ux, uy)
        ux, uy = ux / n, uy / n
        s = '<circle cx="%s" cy="%s" r="%s" fill="#26365E"/>' % (f(cx), f(cy), f(r))
        a = math.degrees(math.atan2(uy, ux))
        # the stripe: a pale sector on the negative side
        p1 = (cx + r * math.cos(math.radians(a - 38)), cy + r * math.sin(math.radians(a - 38)))
        p2 = (cx + r * math.cos(math.radians(a + 38)), cy + r * math.sin(math.radians(a + 38)))
        s += '<path d="M%s,%s A%s,%s 0 0 1 %s,%s Z" fill="#D5DAE2"/>' % (f(p1[0]), f(p1[1]), f(r), f(r), f(p2[0]), f(p2[1]))
        s += '<circle cx="%s" cy="%s" r="%s" fill="#AEB6BD"/>' % (f(cx), f(cy), f(r * 0.62))
        s += line(cx - r * 0.4, cy, cx + r * 0.4, cy, '#8A9299', 0.25)
        s += line(cx, cy - r * 0.4, cx, cy + r * 0.4, '#8A9299', 0.25)
        return s
    if kind == 'ic':
        x, y = item[1]
        s = ''
        for k in range(4):
            for sx in (-1, 1):
                s += rect(x + sx * 2.85 - 0.75, y - 1.905 + 1.27 * k - 0.22, 1.5, 0.44, SILVER, 0.1)
        s += rect(x - 1.95, y - 2.45, 3.9, 4.9, BLACK, 0.3)
        s += '<circle cx="%s" cy="%s" r="0.35" fill="#6B747C"/>' % (f(x - 1.4), f(y - 1.9))
        return s
    if kind == 'ind':
        x, y = item[1]
        s = rect(x - 3.65, y - 3.3, 7.3, 6.6, '#2A3138', 0.6)
        s += '<circle cx="%s" cy="%s" r="2.4" fill="#3D4750"/>' % (f(x), f(y))
        s += '<text x="%s" y="%s" class="pv" text-anchor="middle">100</text>' % (f(x), f(y + 0.7))
        return s
    if kind == 'chip':
        (x, y), w, h, fill = item[1], item[2], item[3], item[4]
        if item[5] % 180 == 90:
            w, h = h, w
        s = rect(x - w / 2, y - h / 2, w, h, fill, 0.2)
        cap = 0.5
        if w >= h:
            s += rect(x - w / 2, y - h / 2, cap, h, SILVER) + rect(x + w / 2 - cap, y - h / 2, cap, h, SILVER)
        else:
            s += rect(x - w / 2, y - h / 2, w, cap, SILVER) + rect(x - w / 2, y + h / 2 - cap, w, cap, SILVER)
        return s
    if kind == 'qtpy':
        x, y = item[1]
        x0, y0 = x - 1.27, y - 2.73
        s = rect(x0, y0, 17.78, 20.7, '#11161B', 1.2)
        s += rect(x0 + 4.4, y0 - 0.9, 8.94, 7.3, '#AEB6BD', 0.9)
        s += rect(x0 + 5.6, y0 + 9.0, 6.6, 6.6, '#2A3138', 0.4)
        s += rect(x0 + 5.9, y0 + 17.4, 6.0, 3.3, '#D8D2C4', 0.3)
        for k in range(7):
            for px in (x, x + 15.24):
                s += '<circle cx="%s" cy="%s" r="0.6" fill="%s"/>' % (f(px), f(y + 2.54 * k), GOLD)
        s += '<text x="%s" y="%s" class="pw" text-anchor="middle">QT Py</text>' % (f(x + 7.62), f(y0 + 8.2))
        return s
    raise ValueError(kind)


def halo(item):
    x0, y0, x1, y1 = bbox(item)
    return '<rect class="hf" x="%s" y="%s" width="%s" height="%s" rx="1"/>' % (f(x0 - 0.7), f(y0 - 0.7), f(x1 - x0 + 1.4), f(y1 - y0 + 1.4))


def tag(x, y, text):
    w = 1.25 * len(text) + 1.6
    return ('<rect class="tg" x="%s" y="%s" width="%s" height="3.1" rx="0.8"/>'
            '<text class="tt" x="%s" y="%s" text-anchor="middle">%s</text>') % (
        f(x - w / 2), f(y - 1.55), f(w), f(x), f(y + 0.75), html.escape(text))


def plan(geom, placed, new, tags=(), extra='', view=None, cls='bd'):
    """The board from above: parts already fitted, then the new ones with an orange outline."""
    vb = view or (-1.5, -1.5, W + 3, H + 3)
    s = '<svg class="%s" viewBox="%s %s %s %s" role="img" aria-label="Board seen from above">' % ((cls,) + tuple(f(v) for v in vb))
    s += '<use href="#pcb"/>'
    s += ''.join(draw(geom[r]) for r in placed)
    s += ''.join(halo(geom[r]) for r in new)
    s += ''.join(draw(geom[r]) for r in new)
    s += extra
    s += ''.join(tag(x, y, t) for x, y, t in tags)
    return s + '</svg>'


# ---------------------------------------------------------------------------
# Parts-tray pictures
# ---------------------------------------------------------------------------
def icon(kind, arg=None):
    if kind == 'res':
        b = ''.join('<rect x="%s" y="3" width="2.6" height="12" fill="%s"/>' % (f(15 + i * 4.6 + (2.4 if i == 4 else 0)), BAND[c])
                    for i, c in enumerate(BANDS[arg]))
        return ('<svg class="ic-s" viewBox="0 0 56 18"><line x1="1" y1="9" x2="55" y2="9" stroke="#8A9299" stroke-width="1.6"/>'
                '<rect x="11" y="3" width="34" height="12" rx="5" fill="#5D9BD5"/>%s</svg>' % b)
    if kind == 'dio':
        h = {'small': 10, 'mid': 13, 'big': 17}[arg]
        return ('<svg class="ic-s" viewBox="0 0 56 18"><line x1="1" y1="9" x2="55" y2="9" stroke="#8A9299" stroke-width="%s"/>'
                '<rect x="14" y="%s" width="28" height="%s" rx="2.5" fill="%s"/><rect x="17.5" y="%s" width="4" height="%s" fill="%s"/></svg>'
                % ('2.4' if arg == 'big' else '1.6', f(9 - h / 2), h, BLACK, f(9 - h / 2), h, SILVER))
    if kind == 'cer':
        return ('<svg class="ic-m" viewBox="0 0 40 40"><line x1="14" y1="18" x2="14" y2="39" stroke="#8A9299" stroke-width="1.6"/>'
                '<line x1="26" y1="18" x2="26" y2="39" stroke="#8A9299" stroke-width="1.6"/>'
                '<rect x="6" y="3" width="28" height="19" rx="8" fill="#E0B04A"/><text x="20" y="16" text-anchor="middle" class="it2">104</text></svg>')
    if kind == 'ecap':
        hh = 30 if arg == 'big' else 22
        ww = 22 if arg == 'big' else 15
        x0 = 20 - ww / 2
        return ('<svg class="ic-t" viewBox="0 0 40 52"><line x1="15" y1="%s" x2="15" y2="51" stroke="#8A9299" stroke-width="1.6"/>'
                '<line x1="25" y1="%s" x2="25" y2="44" stroke="#8A9299" stroke-width="1.6"/>'
                '<rect x="%s" y="2" width="%s" height="%s" rx="3" fill="#26365E"/><rect x="%s" y="2" width="5" height="%s" rx="2" fill="#D5DAE2"/>'
                '<text x="%s" y="%s" text-anchor="middle" class="it2">−</text></svg>'
                % (hh, hh, f(x0), ww, hh, f(x0 + ww - 5), hh, f(x0 + ww - 2.5), f(hh / 2 + 5)))
    if kind == 'fet':
        return ('<svg class="ic-t" viewBox="0 0 40 52">' + ''.join('<line x1="%d" y1="30" x2="%d" y2="51" stroke="#8A9299" stroke-width="2"/>' % (x, x) for x in (12, 20, 28))
                + '<rect x="6" y="1" width="28" height="12" rx="1.5" fill="#AEB6BD"/><circle cx="20" cy="6.5" r="3" fill="#FFFFFF"/>'
                '<rect x="6" y="11" width="28" height="21" rx="1.5" fill="%s"/><text x="20" y="20" text-anchor="middle" class="it">IRLB</text>'
                '<text x="20" y="28" text-anchor="middle" class="it">8721</text></svg>' % BLACK)
    if kind == 'socket':
        cells = ''.join('<rect x="%s" y="5" width="4.4" height="4.4" rx="0.6" fill="#59626B"/>' % f(3.6 + i * 7) for i in range(7))
        return '<svg class="ic-s" viewBox="0 0 56 18"><rect x="1" y="1" width="54" height="12" rx="2" fill="%s"/>%s</svg>' % (BLACK, cells)
    if kind == 'header':
        pins = ''.join('<rect x="%s" y="1" width="1.8" height="16" fill="%s"/>' % (f(5 + i * 6.3), GOLD) for i in range(8))
        return '<svg class="ic-s" viewBox="0 0 56 18">%s<rect x="2" y="7" width="52" height="6" rx="1" fill="%s"/></svg>' % (pins, BLACK)
    if kind == 'holder':
        return ('<svg class="ic-s" viewBox="0 0 56 18"><rect x="1" y="2" width="54" height="14" rx="3" fill="%s"/>'
                '<rect x="13" y="6.5" width="30" height="5" rx="1.5" fill="#0D1013"/><rect x="8" y="4" width="5" height="10" fill="#8A9299"/>'
                '<rect x="43" y="4" width="5" height="10" fill="#8A9299"/></svg>' % BLACK)
    if kind == 'fuse':
        return ('<svg class="ic-m" viewBox="0 0 40 40"><rect x="9" y="22" width="5" height="16" fill="#8A9299"/><rect x="26" y="22" width="5" height="16" fill="#8A9299"/>'
                '<rect x="4" y="5" width="32" height="20" rx="3" fill="#9DA3A8"/><text x="20" y="20" text-anchor="middle" class="pk">2</text></svg>')
    if kind == 'term':
        n = arg
        w = 12 * n
        x0 = 28 - w / 2
        s = '<svg class="ic-s" viewBox="0 0 56 18"><rect x="%s" y="1" width="%s" height="16" rx="1.5" fill="#2E9E5B"/>' % (f(x0), w)
        for i in range(n):
            s += '<circle cx="%s" cy="6.5" r="3.4" fill="%s"/><line x1="%s" y1="5.5" x2="%s" y2="7.5" stroke="#5B646C" stroke-width="1"/>' % (
                f(x0 + 6 + 12 * i), SILVER, f(x0 + 4 + 12 * i), f(x0 + 8 + 12 * i))
            s += '<rect x="%s" y="11.5" width="5" height="4" rx="0.6" fill="#1B5E38"/>' % f(x0 + 3.5 + 12 * i)
        return s + '</svg>'
    if kind == 'ic':
        legs = ''.join('<rect x="%s" y="%d" width="7" height="2.4" fill="%s"/>' % (f(x), 8 + 7 * k, SILVER)
                       for k in range(4) for x in (3, 30))
        return ('<svg class="ic-m" viewBox="0 0 40 40">%s<rect x="9" y="5" width="22" height="30" rx="1.5" fill="%s"/>'
                '<circle cx="13" cy="9" r="1.6" fill="#6B747C"/></svg>' % (legs, BLACK))
    if kind == 'ind':
        return ('<svg class="ic-m" viewBox="0 0 40 40"><rect x="3" y="5" width="34" height="30" rx="3" fill="#2A3138"/>'
                '<circle cx="20" cy="20" r="10" fill="#3D4750"/><text x="20" y="24" text-anchor="middle" class="it2">100</text></svg>')
    if kind == 'chip':
        fill, w = arg
        return ('<svg class="ic-s" viewBox="0 0 56 18"><rect x="%s" y="4" width="%s" height="10" rx="1" fill="%s"/>'
                '<rect x="%s" y="4" width="4" height="10" fill="%s"/><rect x="%s" y="4" width="4" height="10" fill="%s"/></svg>'
                % (f(28 - w / 2), w, fill, f(28 - w / 2), SILVER, f(28 + w / 2 - 4), SILVER))
    if kind == 'qtpy':
        return ('<svg class="ic-m" viewBox="0 0 40 40"><rect x="5" y="2" width="30" height="36" rx="3" fill="#11161B"/>'
                '<rect x="13" y="0" width="14" height="11" rx="2" fill="#AEB6BD"/><rect x="14" y="17" width="12" height="12" rx="1" fill="#2A3138"/>'
                + ''.join('<circle cx="%d" cy="%s" r="1.2" fill="%s"/>' % (x, f(6 + 4.6 * k), GOLD) for k in range(7) for x in (8, 32)) + '</svg>')
    if kind == 'supply':
        return ('<svg class="ic-m" viewBox="0 0 40 40"><rect x="3" y="9" width="34" height="22" rx="3" fill="#2A3138"/>'
                '<text x="20" y="23.5" text-anchor="middle" class="it">24 V</text></svg>')
    if kind == 'tape':
        cols = {'rgb': ['#D9342B', '#2E9E5B', '#2B62D9'], 'white': ['#F5B83D', '#9FD3F5']}[arg]
        dots = ''.join('<rect x="%s" y="6" width="5" height="6" rx="1" fill="%s"/>' % (f(5 + i * 8), cols[i % len(cols)]) for i in range(6))
        return '<svg class="ic-s" viewBox="0 0 56 18"><rect x="1" y="3.5" width="54" height="11" rx="2" fill="#F4F4EE" stroke="#0E1D2B" stroke-width="1"/>%s</svg>' % dots
    if kind == 'tft':
        return ('<svg class="ic-m" viewBox="0 0 40 40"><rect x="3" y="3" width="34" height="34" rx="3" fill="#11161B"/>'
                '<rect x="7" y="6" width="26" height="26" rx="1" fill="#3D7DD8"/></svg>')
    if kind == 'enc':
        return ('<svg class="ic-m" viewBox="0 0 40 40"><rect x="5" y="5" width="30" height="30" rx="4" fill="#11161B"/>'
                '<circle cx="20" cy="20" r="10" fill="#AEB6BD"/><circle cx="20" cy="20" r="6" fill="#8A9299"/></svg>')
    if kind == 'pcb':
        return ('<svg class="ic-m" viewBox="0 0 40 40"><rect x="1" y="8" width="38" height="24" rx="2.5" fill="#141614"/>'
                + ''.join('<circle cx="%d" cy="%d" r="1.5" fill="#F4F4EE"/>' % (x, y) for x in (5, 35) for y in (12, 28))
                + '<rect x="9" y="24" width="12" height="5" fill="#F4F4EE" opacity=".7"/><rect x="24" y="12" width="7" height="9" fill="#F4F4EE" opacity=".7"/></svg>')
    raise ValueError(kind)


def piece(count, pic, name, where):
    return '<div class="pc">%s<b>%s×</b><span>%s</span><span class="inv">%s</span></div>' % (pic, count, name, where)


TRAY = {
    'r220': lambda n: piece(n, icon('res', '220'), '220 Ω', 'inventory R-006'),
    'r100k': lambda n: piece(n, icon('res', '100k'), '100 kΩ', 'inventory R-014'),
    'd5819': lambda n: piece(n, icon('dio', 'small'), '1N5819', 'inventory D-002'),
    'sb560': lambda n: piece(n, icon('dio', 'big'), 'SB560', 'ordered'),
    'tvs': lambda n: piece(n, icon('dio', 'mid'), 'P6KE30A', 'ordered'),
    'c104': lambda n: piece(n, icon('cer'), '100 nF', 'inventory C-021'),
    'socket': lambda n: piece(n, icon('socket'), '1×7 socket', 'ordered'),
    'header': lambda n: piece(n, icon('header'), '8-pin header', 'cut from E-007'),
    'holder': lambda n: piece(n, icon('holder'), 'Fuse holder', 'ordered'),
    'fuse': lambda n: piece(n, icon('fuse'), '2 A mini fuse', 'ordered'),
    't2': lambda n: piece(n, icon('term', 2), '2-way terminal', 'ordered'),
    't3': lambda n: piece(n, icon('term', 3), '3-way terminal', 'ordered'),
    't4': lambda n: piece(n, icon('term', 4), '4-way terminal', 'ordered'),
    'c100u': lambda n: piece(n, icon('ecap', 'big'), '100 µF 50 V', 'inventory C-044'),
    'buckic': lambda n: piece(n, icon('ic'), 'LMR33630 chip', 'ordered'),
    'ind10u': lambda n: piece(n, icon('ind'), '10 µH inductor', 'ordered'),
    'c10u1210': lambda n: piece(n, icon('chip', ('#C9A26B', 24)), '10 µF 50 V chip', 'ordered'),
    'c22u1210': lambda n: piece(n, icon('chip', ('#C9A26B', 24)), '22 µF 25 V chip', 'ordered'),
    'c220n': lambda n: piece(n, icon('chip', ('#C9A26B', 16)), '220 nF chip', 'ordered'),
    'r100kc': lambda n: piece(n, icon('chip', ('#1E242B', 22)), '100 kΩ 1 % chip', 'ordered'),
    'r249k': lambda n: piece(n, icon('chip', ('#1E242B', 22)), '24.9 kΩ 1 % chip', 'ordered'),
    'c1u': lambda n: piece(n, icon('cer'), '1 µF (105)', 'inventory C-027'),
    'fet': lambda n: piece(n, icon('fet'), 'IRLB8721', 'inventory Q-004'),
    'qtpy': lambda n: piece(n, icon('qtpy'), 'QT Py RP2040', 'you have it'),
    'pcb': lambda n: piece(n, icon('pcb'), 'Driver board', 'from PCBWay'),
    'supply': lambda n: piece(n, icon('supply'), '24 V supply', '1.5 A or more'),
    'rgb': lambda n: piece(n, icon('tape', 'rgb'), 'RGB strip, 0.8 m', 'inventory LED-010'),
    'white': lambda n: piece(n, icon('tape', 'white'), 'White strip, 1 m', 'you have it'),
    'tft': lambda n: piece(n, icon('tft'), 'TFT display', 'you have it'),
    'enc': lambda n: piece(n, icon('enc'), 'Rotary encoder', 'you have it'),
}


def tray(items, cls='need'):
    return '<div class="%s">%s</div>' % (cls, ''.join(TRAY[k](n) for k, n in items))


# ---------------------------------------------------------------------------
# Small "which way round" drawings
# ---------------------------------------------------------------------------
TIP_DIODE = ('<svg class="ins" viewBox="0 0 96 60" role="img" aria-label="Diode stripe to the K end">'
             '<line x1="6" y1="16" x2="90" y2="16" stroke="#8A9299" stroke-width="2"/><rect x="28" y="8" width="40" height="16" rx="3" fill="#1E242B"/>'
             '<rect x="33" y="8" width="7" height="16" fill="#C9CED3"/>'
             '<rect x="6" y="38" width="12" height="12" fill="#D8B24A"/><circle cx="12" cy="44" r="2.6" fill="#fff"/><circle cx="84" cy="44" r="6" fill="#D8B24A"/><circle cx="84" cy="44" r="2.6" fill="#fff"/>'
             '<rect x="28" y="36" width="40" height="16" fill="none" stroke="#0E1D2B" stroke-width="1.6"/><rect x="33" y="36" width="4" height="16" fill="#0E1D2B"/>'
             '<text x="12" y="34" text-anchor="middle" class="it2">K</text>'
             '<path d="M36.5 26 V34" stroke="#FF5A1F" stroke-width="2" fill="none"/></svg>')

TIP_ECAP = ('<svg class="ins" viewBox="0 0 96 60" role="img" aria-label="Capacitor: long leg to plus">'
            '<rect x="8" y="4" width="24" height="34" rx="3" fill="#26365E"/><rect x="26" y="4" width="6" height="34" rx="2" fill="#D5DAE2"/>'
            '<line x1="15" y1="38" x2="15" y2="58" stroke="#8A9299" stroke-width="2"/><line x1="26" y1="38" x2="26" y2="50" stroke="#8A9299" stroke-width="2"/>'
            '<text x="13" y="56" text-anchor="end" class="it2">+</text>'
            '<circle cx="70" cy="30" r="20" fill="#fff" stroke="#0E1D2B" stroke-width="1.6"/><path d="M70 10 A20 20 0 0 1 70 50 Z" fill="#0E1D2B"/>'
            '<rect x="58" y="26" width="8" height="8" fill="#D8B24A"/><circle cx="78" cy="30" r="4" fill="#D8B24A"/>'
            '<text x="50" y="14" text-anchor="middle" class="it2">+</text></svg>')

TIP_FET = ('<svg class="ins" viewBox="0 0 96 60" role="img" aria-label="MOSFET: metal tab toward the resistors">'
           '<rect x="22" y="14" width="52" height="8" fill="#AEB6BD"/><rect x="22" y="22" width="52" height="18" rx="2" fill="#1E242B"/>'
           '<circle cx="35" cy="46" r="3.4" fill="#C9CED3"/><circle cx="48" cy="46" r="3.4" fill="#C9CED3"/><circle cx="61" cy="46" r="3.4" fill="#C9CED3"/>'
           '<text x="48" y="10" text-anchor="middle" class="it2">tab: resistor side</text>'
           '<text x="35" y="58" text-anchor="middle" class="it2">G</text><text x="48" y="58" text-anchor="middle" class="it2">D</text><text x="61" y="58" text-anchor="middle" class="it2">S</text></svg>')

TIP_BANDS = {
    '220': '<svg class="ins" viewBox="0 0 96 30" role="img" aria-label="220 ohm colour bands"><line x1="2" y1="15" x2="94" y2="15" stroke="#8A9299" stroke-width="2"/><rect x="18" y="5" width="60" height="20" rx="8" fill="#5D9BD5"/>%s</svg>'
           % ''.join('<rect x="%s" y="5" width="5" height="20" fill="%s"/>' % (f(26 + i * 8 + (5 if i == 4 else 0)), BAND[c]) for i, c in enumerate(BANDS['220'])),
    '100k': '<svg class="ins" viewBox="0 0 96 30" role="img" aria-label="100 kilohm colour bands"><line x1="2" y1="15" x2="94" y2="15" stroke="#8A9299" stroke-width="2"/><rect x="18" y="5" width="60" height="20" rx="8" fill="#5D9BD5"/>%s</svg>'
            % ''.join('<rect x="%s" y="5" width="5" height="20" fill="%s"/>' % (f(26 + i * 8 + (5 if i == 4 else 0)), BAND[c]) for i, c in enumerate(BANDS['100k'])),
}


def tip(pic, text, wide=False):
    return '<div class="tip%s">%s<p>%s</p></div>' % (' wide' if wide else '', pic, text)


# ---------------------------------------------------------------------------
# Wiring picture: the finished board with what plugs into it
# ---------------------------------------------------------------------------
def wiring(geom, placed):
    pl = B.placements()
    s = ''

    def wire(pts, colour, width=1.1):
        d = 'M' + ' L'.join('%s,%s' % (f(x), f(y)) for x, y in pts)
        return ('<path d="%s" fill="none" stroke="#0E1D2B" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round"/>'
                '<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round"/>') % (
            d, f(width + 0.5), d, colour, f(width))

    def box(x, y, w, h, title, sub=''):
        t = '<rect class="ob" x="%s" y="%s" width="%s" height="%s" rx="2"/>' % (f(x), f(y), f(w), f(h))
        t += '<text class="ot" x="%s" y="%s" text-anchor="middle">%s</text>' % (f(x + w / 2), f(y + h / 2 + (0 if sub else 1.2)), title)
        if sub:
            t += '<text class="os" x="%s" y="%s" text-anchor="middle">%s</text>' % (f(x + w / 2), f(y + h / 2 + 4.2), sub)
        return t

    # 24 V supply above J1
    jx_plus, jx_minus, jy = pl['J1'][0] - 5.08, pl['J1'][0], pl['J1'][1]
    s += box(36, -26, 28, 12, '24 V supply', '1.5 A or more')
    s += wire([(jx_plus, jy - 2), (jx_plus, -14)], '#D9342B', 1.4)
    s += wire([(jx_minus, jy - 2), (jx_minus, -14)], '#2A2F35', 1.4)
    s += '<text class="wl" x="%s" y="-5" text-anchor="end">+</text><text class="wl" x="%s" y="-5">−</text>' % (f(jx_plus - 1.6), f(jx_minus + 1.6))
    # RGB strip under J3
    y_strip = H + 17
    cols = [('#B9BEC4', '+24'), ('#D9342B', 'R'), ('#2E9E5B', 'G'), ('#2B62D9', 'B')]
    s += '<rect class="tape" x="2" y="%s" width="50" height="8" rx="1.5"/>' % f(y_strip)
    for k, (c, _) in enumerate(cols):
        x = B.TRUNK_X + 5.08 * k
        s += wire([(x, B.TY + 3), (x, y_strip + 1.5 + 0.0)], c, 1.2)
    for k in range(5):
        s += '<rect x="%s" y="%s" width="4" height="4" rx="0.6" fill="#F4F4EE" stroke="#0E1D2B" stroke-width="0.3"/>' % (f(30 + k * 4.4 - 22 + 22), f(y_strip + 2))
    s += '<text class="ot" x="27" y="%s" text-anchor="middle">RGB strip, 0.8 m</text>' % f(y_strip + 14)
    # white strip under J2
    cols = [('#B9BEC4', '+24'), ('#F5B83D', 'WW'), ('#9FD3F5', 'CW')]
    s += '<rect class="tape" x="54" y="%s" width="50" height="8" rx="1.5"/>' % f(y_strip)
    for k, (c, _) in enumerate(cols):
        x = B.DROP_X + 5.08 * k
        s += wire([(x, B.TY + 3), (x, y_strip + 1.5)], c, 1.2)
    for k in range(6):
        s += '<rect x="%s" y="%s" width="2.6" height="4" rx="0.5" fill="%s" stroke="#0E1D2B" stroke-width="0.3"/>' % (
            f(74 + k * 4.6), f(y_strip + 2), '#FFE9B0' if k % 2 == 0 else '#E4F3FF')
    s += '<text class="ot" x="79" y="%s" text-anchor="middle">White strip, 1 m</text>' % f(y_strip + 14)
    # display and encoder to the right of J4
    jx, jy0 = pl['J4'][0], pl['J4'][1]
    s += box(112, -4, 32, 26, 'TFT display')
    s += box(112, 34, 32, 22, 'Encoder')
    for k in range(8):
        y = jy0 + 2.54 * k
        is_int = design.J4_LABELS[k] == 'INT'
        ty = 36.5 if is_int else 0.5 + (k if k < 2 else k - 1) * 2.9
        s += wire([(jx + 1.2, y), (jx + 9 + (k % 4) * 1.6, y), (jx + 9 + (k % 4) * 1.6, ty + 0.0), (112, ty)],
                  '#7C4DFF' if is_int else ['#D9342B', '#F08A1C', None, '#E6C229', '#2E9E5B', '#2B62D9', '#B9BEC4', '#2A2F35'][k], 0.7)
    # STEMMA QT cable from the QT Py's lower end to the encoder
    qx, qy = B.QX + 7.62, B.QY0 + 17.97
    d = 'M%s,%s C%s,%s %s,%s 112,49' % (f(qx), f(qy), f(qx), f(qy + 22), f(100), f(49))
    s += '<path d="%s" fill="none" stroke="#0E1D2B" stroke-width="2.6" stroke-linecap="round"/><path d="%s" fill="none" stroke="#F4F4EE" stroke-width="1.9" stroke-linecap="round"/>' % (d, d)
    s += tag(104, 62, 'STEMMA QT cable')
    s += tag(jx + 12, 31.5, '8 wires from J4')
    view = (-4, -30, 152, H + 68)
    return plan(geom, placed, [], extra=s, view=view, cls='bd wide')


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
CSS = r"""
/* Layout: one column of step cards, each with a parts box beside (or above) a plan view of the board.
   Pale instruction-page ground, a yellow title band, heavy rounded numerals. */
:root {
  --paper: #C9DFEE; --card: #E8F2F9; --box: #FFFFFF;
  --tray: #FFFFFF; --tray-ink: #0E1D2B; --tray-muted: #446075; --tray-line: #0E1D2B;
  --ink: #0E1D2B; --muted: #446075; --rule: #A5C1D5;
  --band: #FFD500; --band-ink: #141414; --accent: #C8102E; --new: #FF5A1F;
  --check: #FFE873; --check-ink: #1D1700; --check-line: #0E1D2B; --ok: #156C38;
  --display: "Rubik", "Arial Rounded MT Bold", "Helvetica Neue", system-ui, sans-serif;
  --body: "Nunito Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #0A141D; --card: #12222F; --box: #1B3142;
    --tray: #D5E3EE; --tray-ink: #0E1D2B; --tray-muted: #3D586C; --tray-line: #7C9AB1;
    --ink: #E4EEF6; --muted: #9AB3C6; --rule: #2B465B;
    --band: #FFD500; --band-ink: #141414; --accent: #FF7468; --new: #FF6A2B;
    --check: #332A00; --check-ink: #FFE98A; --check-line: #C7AB1B; --ok: #62D08C;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --paper: #0A141D; --card: #12222F; --box: #1B3142;
  --tray: #D5E3EE; --tray-ink: #0E1D2B; --tray-muted: #3D586C; --tray-line: #7C9AB1;
  --ink: #E4EEF6; --muted: #9AB3C6; --rule: #2B465B;
  --band: #FFD500; --band-ink: #141414; --accent: #FF7468; --new: #FF6A2B;
  --check: #332A00; --check-ink: #FFE98A; --check-line: #C7AB1B; --ok: #62D08C;
  color-scheme: dark;
}
body { background: var(--paper); color: var(--ink); font-family: var(--body); font-size: 16px; line-height: 1.5; }
.defs { position: absolute; width: 0; height: 0; overflow: hidden; }
.page {
  max-width: 820px; margin: 0 auto;
  padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px));
  padding-block: 20px 72px; display: grid; gap: 18px;
}
h1, h2, h3 { font-family: var(--display); margin: 0; line-height: 1.1; text-wrap: balance; }
h1 { font-weight: 800; font-size: clamp(30px, 7.4vw, 50px); letter-spacing: -.01em; }
h2 { font-weight: 800; font-size: clamp(22px, 5vw, 30px); }
h3 { font-weight: 600; font-size: 19px; }
p { margin: 0; max-width: 64ch; }
a { color: var(--accent); }
:focus-visible { outline: 3px solid var(--new); outline-offset: 2px; }
.where { font: 600 11.5px/1.2 var(--mono); letter-spacing: .07em; text-transform: uppercase; color: var(--muted); }

.cover { border-radius: 16px; overflow: hidden; background: var(--card); }
.band { background: var(--band); color: var(--band-ink); padding: 18px 18px 16px; display: grid; gap: 10px; }
.band .where { color: var(--band-ink); opacity: .75; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chips span { background: var(--band-ink); color: var(--band); border-radius: 999px; padding: 4px 12px; font: 600 13px/1.4 var(--display); }
.chips b { font-weight: 800; }
.hero { padding: 14px 12px 6px; margin: 0; }
.lede { padding: 4px 18px 18px; font-size: 17px; }

.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.facts > div { background: var(--card); border-radius: 14px; padding: 14px 16px; display: grid; gap: 4px; align-content: start; min-width: 0; }
.facts .v { font: 800 21px/1.15 var(--display); }
.facts p { font-size: 14.5px; color: var(--muted); }

.bags { display: flex; flex-wrap: wrap; gap: 8px; }
.bags a { display: inline-flex; align-items: center; gap: 8px; text-decoration: none; color: var(--ink); background: var(--card); border-radius: 999px; padding: 5px 14px 5px 5px; font: 600 14px/1.2 var(--display); }
.bags b { background: var(--band); color: var(--band-ink); min-width: 26px; height: 26px; padding: 0 4px; border-radius: 13px; display: grid; place-items: center; font-weight: 800; box-sizing: border-box; }

section.sheet { background: var(--card); border-radius: 16px; padding: 18px; display: grid; gap: 14px; min-width: 0; scroll-margin-top: 12px; }
.legend { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px 18px; }
.legend > div { display: grid; grid-template-columns: 44px 1fr; gap: 10px; align-items: start; font-size: 14.5px; min-width: 0; }
.legend .sw { width: 44px; height: 30px; border-radius: 8px; display: grid; place-items: center; font: 600 12px var(--mono); box-sizing: border-box; }
.sw.new { border: 4px solid var(--new); }
.sw.old { background: #141614; color: #F4F4EE; }
.sw.top { background: #141614; color: #F4F4EE; }
.sw.stop { background: var(--check); color: var(--check-ink); border: 2px solid var(--check-line); }

.bag { display: flex; align-items: center; gap: 14px; margin-top: 22px; scroll-margin-top: 12px; }
.bagno { flex: none; width: 58px; height: 58px; border-radius: 14px; background: var(--band); color: var(--band-ink); display: grid; place-items: center; font: 800 32px/1 var(--display); }
.bag div { display: grid; gap: 5px; }

.step { background: var(--card); border-radius: 16px; padding: 16px; display: grid; gap: 14px; min-width: 0; scroll-margin-top: 12px; }
.step > header { display: flex; align-items: center; gap: 14px; }
.num { font: 800 56px/0.9 var(--display); letter-spacing: -.03em; }
.ttl { display: grid; gap: 5px; min-width: 0; }
.done { margin-left: auto; display: inline-flex; align-items: center; gap: 7px; font: 600 13px/1 var(--display); color: var(--muted); cursor: pointer; padding: 6px 10px; border: 2px solid var(--rule); border-radius: 999px; }
.done input { width: 18px; height: 18px; margin: 0; accent-color: var(--ok); }
.step.is-done { opacity: .62; }
.step.is-done .done { color: var(--ok); border-color: var(--ok); }
.cols { display: grid; gap: 14px; min-width: 0; }
.step.wide .cols { grid-template-columns: 1fr; }
@media (min-width: 740px) { .step.wide .side { grid-template-columns: 1fr 1fr; align-items: start; } }
.side { display: grid; gap: 12px; align-content: start; min-width: 0; }
.main { min-width: 0; display: grid; gap: 10px; }
@media (min-width: 740px) { .cols { grid-template-columns: 236px 1fr; align-items: start; } }

.need { background: var(--tray); color: var(--tray-ink); border: 2px solid var(--tray-line); border-radius: 14px; padding: 10px 12px; display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px 14px; }
.need.all { grid-template-columns: repeat(auto-fill, minmax(158px, 1fr)); }
.pc { display: grid; grid-template-columns: auto 1fr; align-items: center; column-gap: 8px; row-gap: 1px; min-width: 0; }
.pc svg { grid-row: 1 / span 3; }
.pc b { font: 800 17px/1 var(--display); }
.pc span { font-size: 13.5px; line-height: 1.25; }
.pc .inv { font: 500 11px/1.3 var(--mono); color: var(--tray-muted); }
.ic-s { width: 54px; height: 18px; } .ic-m { width: 40px; height: 40px; } .ic-t { width: 34px; height: 44px; }

.tip { background: var(--tray); color: var(--tray-ink); border-radius: 14px; padding: 8px 10px; display: grid; grid-template-columns: 96px 1fr; gap: 10px; align-items: center; }
.tip p { font-size: 13px; line-height: 1.35; }
.tip.text { grid-template-columns: 1fr; }
.ins { width: 96px; height: auto; display: block; }

.plate { margin: 0; min-width: 0; }
.plate.scroll { overflow-x: auto; }
.bd { display: block; width: 100%; height: auto; }
.plate.scroll .bd { min-width: 640px; }
.hf { fill: var(--new); fill-opacity: .28; stroke: var(--new); stroke-width: .65; }
.tg { fill: #FFFFFF; stroke: #14181D; stroke-width: .25; } .tt { font: 700 2.1px var(--mono); fill: #14181D; }
.pv { font: 800 2.6px var(--display); fill: #14181D; } .pw { font: 700 2px var(--mono); fill: #E9ECEF; }
.ob { fill: var(--box); stroke: var(--ink); stroke-width: .5; } .ot { font: 700 3.3px var(--display); fill: var(--ink); }
.os { font: 500 2.4px var(--mono); fill: var(--muted); } .wl { font: 800 4px var(--display); fill: var(--ink); }
.tape { fill: var(--box); stroke: var(--ink); stroke-width: .5; }
.it { font: 600 7px var(--mono); fill: #E9ECEF; } .it2 { font: 700 9px var(--mono); fill: #1E242B; } .pk { font: 800 13px var(--display); fill: #14181D; }

.hint { color: var(--muted); font-size: 14.5px; }
.say { font-size: 15.5px; }

.check { background: var(--check); color: var(--check-ink); border: 2px solid var(--check-line); border-radius: 16px; padding: 16px; display: grid; gap: 12px; min-width: 0; scroll-margin-top: 12px; }
.check > header { display: flex; align-items: center; gap: 12px; }
.check .stopno { flex: none; width: 46px; height: 46px; border-radius: 50%; border: 3px solid currentColor; display: grid; place-items: center; font: 800 20px/1 var(--display); }
.check .where { color: inherit; opacity: .8; }
.check ol { margin: 0; padding-left: 22px; display: grid; gap: 9px; font-size: 15px; }
.check li { max-width: 66ch; }
.read { font: 600 13px/1 var(--mono); border: 2px solid currentColor; border-radius: 6px; padding: 2px 6px; white-space: nowrap; }

.tablewrap { overflow-x: auto; border: 2px solid var(--rule); border-radius: 12px; background: var(--box); }
table { border-collapse: collapse; width: 100%; font-size: 14.5px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 8px 12px; vertical-align: top; border-bottom: 1px solid var(--rule); }
tr:last-child td { border-bottom: 0; }
th { font: 600 11.5px/1.3 var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--muted); white-space: nowrap; }
td.n { white-space: nowrap; }
figure.schem { margin: 0; border: 2px solid var(--rule); border-radius: 12px; background: #FFFFFF; min-width: 0; overflow: hidden; }
figure.schem .scroll { overflow-x: auto; }
figure.schem img { display: block; width: 100%; min-width: 980px; max-width: none; height: auto; }
figcaption { border-top: 1px solid var(--rule); padding: 9px 14px 11px; font-size: 14px; color: #446075; background: #FFFFFF; }
ul.plain, ol.plain { margin: 0; padding-left: 20px; display: grid; gap: 6px; max-width: 66ch; }
@media (prefers-reduced-motion: no-preference) { .step { transition: opacity .2s; } }
"""

SCRIPT = """<script>
(function () {
  var KEY = 'tasklamp-driver-board-a';
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { state = {}; }
  document.querySelectorAll('.done input').forEach(function (box) {
    var step = box.closest('.step');
    var apply = function () { step.classList.toggle('is-done', box.checked); };
    if (state[box.id]) { box.checked = true; }
    apply();
    box.addEventListener('change', function () {
      apply();
      state[box.id] = box.checked;
      try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* storage unavailable: the tick still shows */ }
    });
  });
})();
</script>"""


def step(num, title, say, need, picture, tips='', scroll=False, wide=False):
    return ('<article class="step%s" id="step-%d"><header><span class="num">%d</span><div class="ttl"><span class="where">Step %d of %d</span><h3>%s</h3></div>'
            '<label class="done"><input type="checkbox" id="done-%d"> Done</label></header>'
            '<div class="cols"><div class="side">%s%s</div><div class="main"><p class="say">%s</p><figure class="plate%s">%s</figure></div></div></article>'
            ) % (' wide' if wide else '', num, num, num, N_STEPS, title, num, need, tips, say, ' scroll' if scroll else '', picture)


N_STEPS = 12


def build():
    geom = geometry()
    board_svg = open(os.path.join(IMG, 'board-top.svg'), 'rb').read()
    schematic = open(os.path.join(IMG, 'schematic.png'), 'rb').read()
    defs = ('<symbol id="pcb" viewBox="0 0 %s %s" overflow="visible"><image href="data:image/svg+xml;base64,%s" x="0" y="0" width="%s" height="%s"/></symbol>'
            % (f(W), f(H), base64.b64encode(board_svg).decode(), f(W), f(H)))
    # <use href="#pcb"> draws the symbol at the size of its viewBox when width/height are given
    use_fix = '<use href="#pcb" x="0" y="0" width="%s" height="%s"/>' % (f(W), f(H))

    channels = range(1, 6)
    r_gate = ['R%d' % n for n in channels]
    r_pull = ['R%d' % (n + 5) for n in channels]
    d_small = ['D%d' % n for n in channels] + ['D6']
    fets = ['Q%d' % n for n in channels]
    buck = ['U2', 'L1', 'C3', 'C4', 'C5', 'C8', 'C9', 'C10', 'C11', 'R11', 'R12']
    order = [buck, r_gate, r_pull, d_small, ['D7', 'D8'], ['SK1', 'SK2', 'J4', 'C6', 'C7'], ['F1', 'J1', 'J3', 'J2'],
             ['C1', 'C2'], fets, ['FUSE']]
    everything = [r for group in order for r in group]

    def pic(i, tags=()):
        placed = [r for group in order[:i] for r in group]
        return plan(geom, placed, order[i], tags).replace('<use href="#pcb"/>', use_fix)

    gx = B.gx
    steps = []
    steps.append(step(1, 'The 5 V converter',
                      'Eleven small parts that sit flat on their pads, done first while the board is bare and lies flat. Start with the chip: tin one corner pad, place the chip with its dot at the top left, solder that one pin and check the chip is straight, then the other seven. Turn the board over and fill the hole in the middle of its footprint with solder from the back: that joins the chip’s heat pad. Then the inductor, the four 22 µF right of it, the two 10 µF and the 220 nF left of the chip, and the two resistors below it: 24.9 k above, 100 k below. None of them has a right way round except the chip.',
                      tray([('buckic', 1), ('ind10u', 1), ('c22u1210', 4), ('c10u1210', 2), ('c220n', 1), ('r249k', 1), ('r100kc', 1)]),
                      pic(0, [(22.6, 8.4, 'chip'), (38.0, 8.2, '10 µH'), (49.1, 11.4, '22 µF ×4'), (14.6, 21.6, '10 µF ×2'), (24.0, 24.6, '24.9 k, 100 k')]),
                      '<div class="tip text"><p>The values are not printed beside these parts: there is no room. Go by this picture, and keep each kind in its own dish until it is on the board. A flux pen helps; the pads are long so a normal iron tip reaches them.</p></div>'))
    steps.append(step(2, 'Gate resistors',
                      'Five 220 Ω resistors, one for each colour. They sit in the positions printed <b>220</b>. Either way round. Bend the legs close to the body: the holes are 10 mm apart.',
                      tray([('r220', 5)]), pic(1),
                      tip(TIP_BANDS['220'], 'Red, red, black, black, brown. Check one with a meter before soldering: it reads 220 Ω.')))
    steps.append(step(3, 'Pull-down resistors',
                      'Five 100 kΩ resistors, each beside a 220 Ω, in the positions printed <b>100k</b>. They hold the strips dark whenever the QT Py is not driving them.',
                      tray([('r100k', 5)]), pic(2),
                      tip(TIP_BANDS['100k'], 'Brown, black, black, orange, brown. On a blue body the orange band is easy to take for red, so measure: 100 kΩ.')))
    steps.append(step(4, 'Six small diodes',
                      'Six 1N5819, in the positions printed <b>5819</b>. The five beside the MOSFETs have their stripe at the top. The sixth lies flat, stripe to the right.',
                      tray([('d5819', 6)]), pic(3, [(54.9, 24.2, 'stripe right')]),
                      tip(TIP_DIODE, 'The stripe goes to the end marked <b>K</b>, where the outline has its band and the pad is square.')))
    steps.append(step(5, 'Two input diodes',
                      'The big SB560 lies along the top edge, stripe to the left. The P6KE30A stands down the left edge, stripe toward the top.',
                      tray([('sb560', 1), ('tvs', 1)]), pic(4, [(17.8, 9.4, 'SB560'), (9.6, 24.0, 'P6KE30A')]),
                      tip(TIP_DIODE, 'Same rule: stripe to <b>K</b>. The SB560 stops a supply wired backwards. Fitted backwards itself, it stops everything.')))
    steps.append(step(6, 'Sockets, header, two small capacitors',
                      'Push both sockets onto the QT Py’s pins, lower the pair into the board and solder them with the QT Py still in place. They end up straight and the right distance apart. Then the 8-pin header, and the two small capacitors right of the converter chip: 100 nF at the top, 1 µF below. Either way round.',
                      tray([('socket', 2), ('header', 1), ('c104', 1), ('c1u', 1)]), pic(5, [(33.9, 8.6, '100 nF'), (33.9, 24.0, '1 µF')]),
                      '<div class="tip text"><p>Pull the QT Py back out when the sockets are soldered. It stays out until the power checks are done.</p></div>'))
    steps.append(step(7, 'Fuse holder and screw terminals',
                      'The 2-way terminal is the 24 V input at the top. The 4-way takes the RGB strip, the 3-way the white strip. Turn each so its wire openings face the nearest edge of the board.',
                      tray([('holder', 1), ('t2', 1), ('t4', 1), ('t3', 1)]),
                      pic(6, [(50.0, 13.0, '2-way'), (17.8, 46.2, '4-way'), (63.5, 46.2, '3-way')]),
                      '<div class="tip text"><p>Hold each part flat against the board while you solder its first pin. A terminal that sits crooked puts strain on its joints every time a screw is tightened.</p></div>'))
    steps.append(step(8, 'Two big capacitors',
                      'Electrolytic capacitors have a right way round. The long leg goes in the hole marked <b>+</b>. The pale stripe down the can ends up over the filled half of the printed circle.',
                      tray([('c100u', 2)]), pic(7, [(11.9, 20.0, '100 µF'), (50.2, 47.2, '100 µF')]),
                      tip(TIP_ECAP, 'Long leg to <b>+</b>, stripe over the filled half. A reversed electrolytic on 24 V fails, sometimes loudly.')))
    steps.append(step(9, 'Five MOSFETs',
                      'IRLB8721 only. Other parts in your drawers have the same shape, so read the printing on each one. Metal tab toward the resistors, printed face toward the screw terminals. Leave them standing straight: the tabs are connected to the strips and must not touch each other.',
                      tray([('fet', 5)]), pic(8),
                      tip(TIP_FET, '<b>Pick the best five first.</b> Clip G and D together. 9 V battery: + through a 1 kΩ resistor to G and D, − to S. The meter from G to S reads about 2.0–2.2 V. Measure every one you have, fit the five lowest, and set aside any above 2.6 V.')))
    steps.append(step(10, 'The fuse',
                      'Push the 2 A fuse into its holder. The soldering is finished: look over the back of the board once for joints that touch their neighbours, above all the three pins of each MOSFET.',
                      tray([('fuse', 1)]), pic(9, [(36.0, 10.2, '2 A')])))

    check1 = ('<article class="check" id="check-1"><header><span class="stopno">!</span><div><span class="where">Stop and check · nothing plugged in</span><h3>First power-up</h3></div></header>'
              '<p>No QT Py, no strips, no display. Connect the 24 V supply to the input terminal: <b>+</b> and <b>−</b> are printed beside it. Black probe on the <b>GND</b> test pad.</p><ol>'
              '<li><b>Nothing gets warm</b> in the first minute. If something does, unplug and look at the diode stripes and the capacitors first.</li>'
              '<li>Either <b>+24</b> screw: <span class="read">23–24 V</span> That is the supply less the half volt the SB560 takes.</li>'
              '<li>The <b>+5V</b> test pad: <span class="read">4.9–5.1 V</span> If it reads anything else, stop here. The next thing to be plugged in is the QT Py, and this is the voltage it gets.</li>'
              '<li>Top-right hole of the QT Py socket, marked <b>5V</b>: <span class="read">4.6–5.0 V</span></li>'
              '</ol></article>')

    all_placed = everything
    wiring_pic = wiring(geom, all_placed + ['U1']).replace('<use href="#pcb"/>', use_fix)
    steps11 = step(11, 'Supply and strips',
                   'Unplug the supply first. Screw the RGB strip’s four wires and the white strip’s three wires into their terminals. Go by the letters printed on the strip at its cut line, since wire colours vary between makers.',
                   tray([('supply', 1), ('rgb', 1), ('white', 1)]), wiring_pic,
                   '<div class="tip text"><p>Cut the strips only on the marked copper pads. The RGB strip can be cut every 100 mm, so 800 mm is eight segments. The display and encoder in the picture are for step 12.</p></div>',
                   scroll=True, wide=True)
    check2 = ('<article class="check" id="check-2"><header><span class="stopno">!</span><div><span class="where">Stop and check · strips connected, QT Py still out</span><h3>Everything stays dark</h3></div></header>'
              '<p>Plug the supply back in.</p><ol>'
              '<li><b>No colour lights, not even faintly.</b> The 100 kΩ resistors are holding all five MOSFETs off.</li>'
              '<li>A colour that lights fully has a solder bridge between the middle and right pins of its MOSFET. A faint glow means a 100 kΩ is missing or badly soldered.</li>'
              '</ol></article>')
    steps12 = step(12, 'QT Py, display and encoder',
                   'Unplug the supply again. Plug in the QT Py with its USB socket toward the edge of the board. Run eight wires from J4 as the table below shows, and plug the encoder’s cable into the socket on the end of the QT Py.',
                   tray([('qtpy', 1), ('tft', 1), ('enc', 1)]),
                   '<div class="tablewrap"><table><thead><tr><th>J4 pin</th><th>Goes to</th></tr></thead><tbody>'
                   '<tr><td class="n">3V</td><td>TFT <b>Vin</b></td></tr><tr><td class="n">MOSI</td><td>TFT <b>SI</b></td></tr>'
                   '<tr><td class="n">INT</td><td>Encoder board <b>INT</b> pad</td></tr><tr><td class="n">SCK</td><td>TFT <b>SCK</b></td></tr>'
                   '<tr><td class="n">LITE</td><td>TFT <b>Lite</b></td></tr><tr><td class="n">CS</td><td>TFT <b>TCS</b></td></tr>'
                   '<tr><td class="n">DC</td><td>TFT <b>D/C</b></td></tr><tr><td class="n">GND</td><td>TFT <b>GND</b></td></tr></tbody></table></div>',
                   '<div class="tip text"><p>The QT Py needs firmware 1.2.1. Load it over USB before or after it goes into the board. USB and the 24 V supply can be connected at the same time.</p></div>')
    check3 = ('<article class="check" id="check-3"><header><span class="stopno">!</span><div><span class="where">Stop and check · everything connected</span><h3>First light</h3></div></header>'
              '<p>Plug in the supply. The display starts and the lamp fades up.</p><ol>'
              '<li><b>One colour at a time.</b> In <b>Menu ▸ Settings ▸ Channels</b> open Red, Green, Blue, Warm and Cool in turn. Only that colour lights. If another one does, two wires are swapped at the terminal.</li>'
              '<li><b>Is each MOSFET fully on?</b> In <b>Menu ▸ Mode ▸ Mixer</b> set one colour to 100 %. Red probe on that colour’s screw, black on <b>GND</b>: <span class="read">under 0.10 V</span> Simulated, a typical part reads about 0.004 V. The gates are driven from 3.3 V and the datasheet only promises 4.5 V, so each one is checked once. One that reads higher gets swapped for another from the bag.</li>'
              '<li>A colour that never lights: its MOSFET is in backwards, or its 220 Ω is not soldered.</li>'
              '<li>After five minutes with everything at 100 %, the MOSFETs are cold and the SB560 is warm. That is normal.</li>'
              '</ol></article>')
    calibrate = ('<section class="sheet" id="calibrate"><span class="where">Once, when it all works</span><h3>Calibrate</h3><ol class="plain">'
                 '<li><b>Settings ▸ Channels ▸ each colour ▸ Min duty.</b> The lamp shows only that colour at its dimmest. Lower Min duty until the light goes out, then go back up one step. It starts at 0.12 % for red and 0.16 % for the others, from a simulation of this board, so expect to end up near there.</li>'
                 '<li><b>Settings ▸ Power.</b> The currents already entered are catalogue figures: 133 mA for each RGB colour, 300 mA for each white. If you can measure the real ones, enter them. Set Budget to about 80 % of your supply’s rating.</li>'
                 '</ol></section>')

    n_stock = sum(1 for p in design.parts() if p['src'] == design.STOCK) + 1      # + the QT Py itself
    all_tray = tray([('pcb', 1), ('r220', 5), ('r100k', 5), ('d5819', 6), ('sb560', 1), ('tvs', 1), ('c104', 1), ('socket', 2),
                     ('header', 1), ('holder', 1), ('fuse', 1), ('t2', 1), ('t4', 1), ('t3', 1), ('c100u', 2), ('c1u', 1),
                     ('buckic', 1), ('ind10u', 1), ('c22u1210', 4), ('c10u1210', 2), ('c220n', 1), ('r249k', 1), ('r100kc', 1),
                     ('fet', 5), ('qtpy', 1)], 'need all')

    order_rows = [
        ('2', 'Texas Instruments LMR33630ADDAR', '5 V buck converter chip (one spare)', 'https://www.digikey.com/en/products/result?keywords=LMR33630ADDAR'),
        ('1', 'Bourns SRP7028A-100M', '10 µH inductor', 'https://www.digikey.com/en/products/result?keywords=SRP7028A-100M'),
        ('3', 'Murata GRM32ER71H106KA12L', '10 µF 50 V 1210 capacitor (one spare)', 'https://www.digikey.com/en/products/result?keywords=GRM32ER71H106KA12L'),
        ('5', 'Murata GRM32ER71E226KE15L', '22 µF 25 V 1210 capacitor (one spare)', 'https://www.digikey.com/en/products/result?keywords=GRM32ER71E226KE15L'),
        ('2', 'KEMET C0805C224K5RACTU', '220 nF 50 V 0805 capacitor', 'https://www.digikey.com/en/products/result?keywords=C0805C224K5RACTU'),
        ('2', 'Yageo RC1206FR-07100KL', '100 kΩ 1 % 1206 resistor', 'https://www.digikey.com/en/products/result?keywords=RC1206FR-07100KL'),
        ('2', 'Yageo RC1206FR-0724K9L', '24.9 kΩ 1 % 1206 resistor', 'https://www.digikey.com/en/products/result?keywords=RC1206FR-0724K9L'),
        ('2', 'Sullins PPTC071LFBN-RC', '1×7 sockets for the QT Py', 'https://www.digikey.com/en/products/detail/sullins-connector-solutions/PPTC071LFBN-RC/810146'),
        ('1', 'On Shore OSTTC022162', '2-way screw terminal', 'https://www.digikey.com/en/products/detail/on-shore-technology-inc/OSTTC022162/614558'),
        ('1', 'On Shore OSTTC032162', '3-way screw terminal', 'https://www.digikey.com/en/products/detail/on-shore-technology-inc/OSTTC032162/614559'),
        ('1', 'On Shore OSTTC042162', '4-way screw terminal', 'https://www.digikey.com/en/products/detail/on-shore-technology-inc/OSTTC042162/614560'),
        ('1', 'Keystone 3568', 'Mini blade fuse holder', 'https://www.digikey.com/en/products/detail/keystone-electronics/3568/2137306'),
        ('5', 'Littelfuse 0297002.WXNV', '2 A mini blade fuses', 'https://www.digikey.com/en/products/result?keywords=0297002.WXNV'),
        ('2', 'Vishay SB560-E3/54', 'Schottky diode, 60 V 5 A', 'https://www.digikey.com/en/products/detail/vishay-general-semiconductor-diodes-division/SB560-E3-54/1023532'),
        ('2', 'Littelfuse P6KE30A', 'TVS diode', 'https://www.digikey.com/en/products/detail/littelfuse-inc/P6KE30A/285939'),
    ]
    order_table = ''.join('<tr><td class="n">%s</td><td><a href="%s" target="_blank" rel="noopener">%s</a></td><td>%s</td></tr>' % (q, url, html.escape(name), what)
                          for q, name, what, url in order_rows)

    hero = plan(geom, everything + ['U1'], []).replace('<use href="#pcb"/>', use_fix)

    page = []
    page.append('<title>Task Lamp Driver Build</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
                '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
                '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600;700&family=Nunito+Sans:wght@400;600;700&family=Rubik:wght@600;800&display=swap">\n'
                '<style>' + CSS + '</style>\n<svg class="defs" aria-hidden="true" focusable="false"><defs>' + defs + '</defs></svg>\n\n<div class="page">\n')
    page.append('<header class="cover"><div class="band"><span class="where">Build booklet · driver board · revision C</span><h1>Task Lamp Driver Build</h1>'
                '<div class="chips"><span><b>5</b> channels</span><span><b>45</b> parts to solder</span><span><b>%d</b> steps</span><span><b>1</b> board</span><span><b>24 V</b></span></div></div>'
                '<figure class="plate hero">%s</figure>'
                '<p class="lede">One board, one 24 V input. The 5 V converter’s eleven small surface-mount parts go on first, while the board lies flat; everything else is through-hole, low parts before tall ones. Then it is powered up in three stages, so a mistake shows on the meter before it can reach the QT Py or the strips.</p></header>\n'
                % (N_STEPS, hero))
    page.append('<div class="facts">'
                '<div><span class="where">The board</span><span class="v">5 from PCBWay</span><p>Upload <b>tasklamp-driver-gerbers.zip</b>, then choose matte black mask, white silkscreen and ENIG. <a href="#pcbway">Options below.</a></p></div>'
                '<div><span class="where">To buy</span><span class="v">15 lines, about $22</span><p>The converter’s chip, inductor and small parts, sockets, screw terminals, fuse holder and fuses, and two diodes. <a href="#order">Links are below.</a></p></div>'
                '<div><span class="where">From your inventory</span><span class="v">%d parts</span><p>Five IRLB8721, six 1N5819, ten resistors, four capacitors, a pin header and the QT Py.</p></div></div>\n' % n_stock)
    page.append('<nav class="bags" aria-label="Sections"><a href="#step-1"><b>1</b>Soldering</a><a href="#check-1"><b>!</b>Power-up</a>'
                '<a href="#step-11"><b>11</b>Wiring</a><a href="#readings"><b>V</b>Meter readings</a><a href="#order"><b>$</b>Parts to order</a><a href="#schematic"><b>i</b>Schematic</a></nav>\n')
    page.append('<section class="sheet"><span class="where">Before step 1</span><h2>How to read the pictures</h2><div class="legend">'
                '<div><span class="sw top">top</span><span><b>The board is always seen from above</b>, the same way up: USB edge at the top, strip terminals at the bottom.</span></div>'
                '<div><span class="sw new"></span><span><b>Orange outline:</b> fit these now.</span></div>'
                '<div><span class="sw old">old</span><span><b>No outline:</b> already soldered in an earlier step.</span></div>'
                '<div><span class="sw stop">!</span><span><b>Yellow cards:</b> stop and measure before going on.</span></div></div>'
                '<p class="hint">Parts go in from the top and are soldered on the back. Every through-hole position has its value printed inside the outline, so the bare board tells you what goes where; step 1’s picture shows where the converter’s small parts go. Tick <b>Done</b> on a step and the page remembers it on this device.</p></section>\n')
    page.append('<section class="sheet"><span class="where">Everything on the bench</span><h2>What goes in</h2>%s'
                '<p class="hint">The codes are the IDs in your inventory sheet. You also need a soldering iron, solder, side cutters and a multimeter.</p></section>\n' % all_tray)
    page.append('<header class="bag"><span class="bagno">1</span><div><span class="where">Steps 1 to 10</span><h2>Soldering</h2></div></header>\n')
    page.extend(s + '\n' for s in steps)
    page.append('<header class="bag"><span class="bagno">2</span><div><span class="where">Three stages</span><h2>Power-up and wiring</h2></div></header>\n')
    page.extend([check1 + '\n', steps11 + '\n', check2 + '\n', steps12 + '\n', check3 + '\n', calibrate + '\n'])
    page.append('<header class="bag" id="reference"><span class="bagno">i</span><div><span class="where">Reference</span><h2>Numbers, parts and the schematic</h2></div></header>\n')
    page.append('<section class="sheet" id="readings"><span class="where">Black probe on the GND test pad</span><h3>What the meter should read</h3>'
                '<div class="tablewrap"><table><thead><tr><th>Where</th><th>Reading</th><th>If not</th></tr></thead><tbody>'
                '<tr><td>Input terminal, + to −</td><td class="n">24 V</td><td>Supply or its wiring</td></tr>'
                '<tr><td>Either +24 screw</td><td class="n">23–24 V</td><td>0 V: fuse blown or missing, or the SB560 is backwards</td></tr>'
                '<tr><td>+5V test pad</td><td class="n">4.9–5.1 V</td><td>0 V with 24 V present: a converter pin is unsoldered or bridged, or the chip’s heat pad hole was not filled</td></tr>'
                '<tr><td>QT Py socket, 5V</td><td class="n">4.6–5.0 V</td><td>Lower: D6 is backwards</td></tr>'
                '<tr><td>QT Py socket, 3V, QT Py in</td><td class="n">3.3 V</td><td>The QT Py is not seated</td></tr>'
                '<tr><td>A colour’s screw, that colour at 100 %</td><td class="n">under 0.10 V</td><td>Swap that MOSFET</td></tr>'
                '<tr><td>A colour’s screw, that colour off</td><td class="n">5–24 V</td><td>0 V: a bridge at the MOSFET’s pins. Anything clearly above 0 is fine: the strip’s LEDs hold back part of the 24 V</td></tr>'
                '</tbody></table></div>'
                '<p class="hint">Loads at 100 %: about 0.13 A for each of red, green and blue, 0.30 A for each white, 1.0 A with everything on.</p></section>\n')
    page.append('<section class="sheet" id="order"><span class="where">One Digi-Key order</span><h3>Parts to order</h3>'
                '<div class="tablewrap"><table><thead><tr><th>Qty</th><th>Part</th><th>What it is</th></tr></thead><tbody>%s</tbody></table></div>'
                '<p class="hint">Stock and prices were not checked live; the converter lines open a Digi-Key search for the exact part. If a line is out of stock: the LMR33620ADDAR or LMR33640ADDAR fits the chip’s pads, any shielded 10 µH inductor about 7 × 7 mm rated 4.5 A saturation or more fits the inductor’s, any X7R 1210 capacitor of the same value and voltage works, any 5.08 mm screw terminal with the same number of ways fits, and any Mini (ATM) 2 A blade fuse from a car-parts shop fits the holder.</p></section>\n' % order_table)
    page.append('<section class="sheet" id="pcbway"><span class="where">The circuit board</span><h3>Ordering from PCBWay</h3><ol class="plain">'
                '<li>Choose <b>PCB Instant Quote</b> and upload <b>tasklamp-driver-gerbers.zip</b> from the repository’s <b>hardware/tasklamp-driver</b> folder. The size, 96.5 × 59 mm, and the two layers are read from the file.</li>'
                '<li>Keep FR-4, 1.6 mm thick and 1 oz copper. For the look the board was drawn for, choose <b>solder mask: matte black</b> (plain black if matte isn’t offered), <b>silkscreen: white</b> and <b>surface finish: ENIG</b>. Black and ENIG cost more than green and HASL, and the board works the same with either; the quote shows the difference. Nothing needs a special process.</li>'
                '<li>Quantity 5 is the minimum.</li><li>Compare PCBWay’s preview with the picture at the top of this page before paying.</li></ol>'
                '<p class="hint">The mounting holes are 3.2 mm, for M3 screws, on a 88.9 × 50.8 mm rectangle. No board has been built from these files yet. They pass 22 checks against the board maker’s limits and the circuit (see <b>hardware/tasklamp-driver/test-report.md</b>), but before ordering, print the top layer at full size and hold the fuse holder, converter and terminals against it.</p></section>\n')
    page.append('<section class="sheet" id="schematic"><span class="where">The whole circuit</span><h3>Schematic</h3>'
                '<figure class="schem"><div class="scroll"><img alt="Schematic of the driver board: 24 V input with fuse, Schottky diode and TVS, an LMR33630 buck converter making 5 V for the QT Py through a diode, and five identical MOSFET switches" src="data:image/png;base64,%s"></div>'
                '<figcaption>24 V comes in through the fuse and the SB560. An LMR33630 buck converter makes 5 V for the QT Py. Each colour is one MOSFET with a 220 Ω gate resistor, a 100 kΩ pull-down and a 1N5819 back to +24 V.</figcaption></figure></section>\n'
                % base64.b64encode(schematic).decode())
    page.append('</div>\n' + SCRIPT + '\n')
    return ''.join(page)


if __name__ == '__main__':
    text = build()
    with open(OUT, 'w') as fh:
        fh.write(text)
    print('wrote %s (%d KB)' % (os.path.relpath(OUT, ROOT), len(text) // 1024))
