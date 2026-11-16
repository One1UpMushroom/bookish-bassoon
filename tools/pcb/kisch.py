"""A small writer for KiCad 7 schematics.

Symbols are copied out of KiCad's own libraries (derived symbols are flattened
the way eeschema does when it embeds them), placed by coordinate, and wired by
asking for the position of a pin. Nothing here knows about the lamp.
"""
import copy
import uuid

from sexpr import Sym, child, children, dump, parse

KICAD_SYMBOLS = '/usr/share/kicad/symbols/'
NS = uuid.UUID('7b0f6c1e-1c1f-4f0b-9a55-7a61c0de1a4b')


def q(v):
    """Snap a coordinate to 0.1 um so equal positions compare equal."""
    return round(float(v), 4)


def uid(*key):
    return str(uuid.uuid5(NS, '/'.join(str(k) for k in key)))


def S(*items):
    """Build a list node; bare Python strings in tag position become symbols."""
    out = [Sym(items[0])]
    out.extend(items[1:])
    return out


def font(size=1.27, justify=None, hide=False):
    eff = S('effects', S('font', S('size', size, size)))
    if justify:
        eff.append([Sym('justify')] + [Sym(j) for j in justify.split()])
    if hide:
        eff.append(Sym('hide'))
    return eff


class SymbolLibs:
    def __init__(self, extra=None):
        self._libs = {}
        self._extra = extra or {}   # {'Lib': path}

    def _lib(self, lib):
        if lib not in self._libs:
            path = self._extra.get(lib, KICAD_SYMBOLS + lib + '.kicad_sym')
            root = parse(open(path).read())
            self._libs[lib] = {s[1]: s for s in children(root, 'symbol')}
        return self._libs[lib]

    def flattened(self, lib_id):
        """The symbol as eeschema would embed it in a schematic."""
        lib, name = lib_id.split(':')
        syms = self._lib(lib)
        sym = copy.deepcopy(syms[name])
        ext = child(sym, 'extends')
        if ext is not None:
            parent = copy.deepcopy(syms[ext[1]])
            assert child(parent, 'extends') is None, 'two-level inheritance not handled'
            props = {p[1]: p for p in children(sym, 'property')}
            out = [Sym('symbol'), name]
            for node in parent[2:]:
                if isinstance(node, list) and node[0] == 'property':
                    out.append(props.pop(node[1], node))
                elif isinstance(node, list) and node[0] == 'symbol':
                    node[1] = name + node[1][len(ext[1]):]
                    out.append(node)
                else:
                    out.append(node)
            # properties the child adds on top of the parent's
            first_unit = next(i for i, n in enumerate(out) if isinstance(n, list) and n[0] == 'symbol')
            out[first_unit:first_unit] = list(props.values())
            sym = out
        sym[1] = lib_id
        return sym

    def pins(self, lib_id):
        """{number: (x, y, name)} in library coordinates (y up)."""
        sym = self.flattened(lib_id)
        out = {}
        for unit in children(sym, 'symbol'):
            for p in children(unit, 'pin'):
                at = child(p, 'at')
                out[child(p, 'number')[1]] = (float(at[1]), float(at[2]), child(p, 'name')[1])
        return out

    def props(self, lib_id):
        return {p[1]: p[2] for p in children(self.flattened(lib_id), 'property')}


def transform(px, py, rot, mirror):
    """Library coordinates (y up) -> offset on the sheet (y down).

    KiCad rotates first (counter-clockwise on the page) and mirrors afterwards.
    Checked against kicad-cli's netlist for all twelve combinations.
    """
    r = rot % 360
    if r == 90:
        px, py = -py, px
    elif r == 180:
        px, py = -px, -py
    elif r == 270:
        px, py = py, -px
    if mirror == 'y':
        px = -px
    elif mirror == 'x':
        py = -py
    return px, -py


class Schematic:
    def __init__(self, libs, project, title, rev, date, comments=()):
        self.libs = libs
        self.project = project
        self.root_uuid = uid('sheet', project)
        self.items = []
        self.used = {}        # lib_id -> flattened symbol
        self.placed = {}      # ref -> (lib_id, x, y, rot, mirror)
        self.title = (title, rev, date, comments)
        self._n = 0
        self._pwr = 0

    def _id(self, kind):
        self._n += 1
        return uid(self.project, kind, self._n)

    # -- placement ---------------------------------------------------------
    def place(self, ref, lib_id, x, y, rot=0, mirror=None, value='', footprint='',
              ref_at=None, val_at=None, in_bom=True, on_board=True, hide_ref=False, hide_val=False,
              extra_fields=None):
        x, y = q(x), q(y)
        if lib_id not in self.used:
            self.used[lib_id] = self.libs.flattened(lib_id)
        self.placed[ref] = (lib_id, x, y, rot, mirror)
        text_angle = 90 if rot % 180 == 90 else 0   # keeps field text horizontal on the page
        ref_at = ref_at or (2.54, -2.54, 'left')
        val_at = val_at or (2.54, 2.54, 'left')
        node = S('symbol', S('lib_id', lib_id), S('at', x, y, rot))
        if mirror:
            node.append(S('mirror', Sym(mirror)))
        node += [S('unit', 1), S('in_bom', Sym('yes' if in_bom else 'no')),
                 S('on_board', Sym('yes' if on_board else 'no')), S('dnp', Sym('no')),
                 S('uuid', uid(self.project, 'sym', ref))]

        def prop(name, val, at, hide=False, just='left'):
            # KiCad draws field text through the symbol's transform, so on a
            # symbol turned upside down or mirrored left-right, "left" means right.
            if (rot % 360 == 180) != (mirror == 'y'):
                just = {'left': 'right', 'right': 'left'}.get(just, just)
            return S('property', name, val, S('at', q(x + at[0]), q(y + at[1]), text_angle),
                     font(1.27, justify=None if just == 'center' else just, hide=hide))

        node.append(prop('Reference', ref, ref_at, hide=hide_ref, just=ref_at[2]))
        node.append(prop('Value', value, val_at, hide=hide_val, just=val_at[2]))
        node.append(prop('Footprint', footprint, (0, 0), hide=True))
        node.append(prop('Datasheet', self.libs.props(lib_id).get('Datasheet', '~'), (0, 0), hide=True))
        for k, v in (extra_fields or {}).items():
            node.append(prop(k, v, (0, 0), hide=True))
        for num in self.libs.pins(lib_id):
            node.append(S('pin', num, S('uuid', uid(self.project, 'pin', ref, num))))
        node.append(S('instances', S('project', self.project,
                                     S('path', '/' + self.root_uuid, S('reference', ref), S('unit', 1)))))
        self.items.append(node)
        return node

    def pin(self, ref, num):
        lib_id, x, y, rot, mirror = self.placed[ref]
        px, py, _ = self.libs.pins(lib_id)[str(num)]
        dx, dy = transform(px, py, rot, mirror)
        return (q(x + dx), q(y + dy))

    def power(self, lib_id, x, y, rot=0):
        """A power symbol (GND, +24V, PWR_FLAG ...) with its pin at (x, y)."""
        self._pwr += 1
        ref = '#PWR%03d' % self._pwr if 'FLAG' not in lib_id else '#FLG%03d' % self._pwr
        name = lib_id.split(':')[1]
        down = name == 'GND'
        val_at = (0, 3.81 if down else -3.81, 'center')
        if rot == 180:
            val_at = (0, -val_at[1], 'center')
        elif rot == 90:
            val_at = (-3.81 if not down else 3.81, 0, 'center')
        elif rot == 270:
            val_at = (3.81 if not down else -3.81, 0, 'center')
        self.place(ref, lib_id, x, y, rot=rot, value=name, hide_ref=True, val_at=val_at,
                   ref_at=(0, 0, 'center'))

    # -- connections -------------------------------------------------------
    def wire(self, *pts):
        pts = [(q(x), q(y)) for x, y in pts]
        for a, b in zip(pts, pts[1:]):
            if a == b:
                continue
            assert a[0] == b[0] or a[1] == b[1], 'wires are horizontal or vertical: %r %r' % (a, b)
            self.items.append(S('wire', S('pts', S('xy', a[0], a[1]), S('xy', b[0], b[1])),
                                S('stroke', S('width', 0), S('type', Sym('default'))),
                                S('uuid', self._id('wire'))))

    def junction(self, x, y):
        self.items.append(S('junction', S('at', q(x), q(y)), S('diameter', 0), S('color', 0, 0, 0, 0),
                            S('uuid', self._id('junction'))))

    def label(self, name, x, y, angle=0, justify='left bottom'):
        self.items.append(S('label', name, S('at', q(x), q(y), angle), font(1.27, justify=justify),
                            S('uuid', self._id('label'))))

    def noconnect(self, x, y):
        self.items.append(S('no_connect', S('at', x, y), S('uuid', self._id('nc'))))

    def text(self, s, x, y, size=1.5, bold=False):
        f = S('font', S('size', size, size))
        if bold:
            f.append(Sym('bold'))
        self.items.append(S('text', s, S('at', q(x), q(y), 0),
                            S('effects', f, S('justify', Sym('left'), Sym('bottom'))),
                            S('uuid', self._id('text'))))

    def box(self, x1, y1, x2, y2):
        self.items.append(S('rectangle', S('start', x1, y1), S('end', x2, y2),
                            S('stroke', S('width', 0.15), S('type', Sym('dash'))),
                            S('fill', S('type', Sym('none'))), S('uuid', self._id('box'))))

    # -- output ------------------------------------------------------------
    def render(self):
        title, rev, date, comments = self.title
        tb = S('title_block', S('title', title), S('date', date), S('rev', rev))
        for i, c in enumerate(comments):
            tb.append(S('comment', i + 1, c))
        root = S('kicad_sch', S('version', 20230121), S('generator', Sym('eeschema')),
                 S('uuid', self.root_uuid), S('paper', 'A4'), tb,
                 [Sym('lib_symbols')] + list(self.used.values()))
        order = {'junction': 0, 'no_connect': 1, 'wire': 2, 'rectangle': 3, 'text': 4, 'label': 5, 'symbol': 6}
        root += sorted(self.items, key=lambda n: order[str(n[0])])
        root.append(S('sheet_instances', S('path', '/', S('page', '1'))))
        return dump(root) + '\n'
