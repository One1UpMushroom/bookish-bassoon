"""Checks for the generated KiCad project. Used by build.py; needs `pcbnew`.

Three independent questions:
  1. Does the schematic say what design.py says?   (netlist exported by kicad-cli)
  2. Does the board say what design.py says?       (pad nets read back with pcbnew)
  3. Is the board complete and legal?              (KiCad's own design-rule check)
and one about the checks themselves: when a fault is planted, do they notice?
"""
import copy
import json
import os
import re
import shutil
import subprocess
import tempfile

import pcbnew

import design
import gen_pcb
from sexpr import child, children, parse

# Violations that say nothing about the copper: the library table of this
# headless machine, and silkscreen cosmetics that are reviewed by eye instead.
COSMETIC = {'lib_footprint_issues', 'lib_footprint_mismatch', 'silk_overlap', 'silk_over_copper',
            'silk_edge_clearance'}


def schematic_netlist(sch_path):
    out = os.path.join(tempfile.mkdtemp(prefix='tlnet'), 'sch.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', out, sch_path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    net = parse(open(out).read())
    nets = {}
    for n in children(child(net, 'nets'), 'net'):
        name = child(n, 'name')[1].lstrip('/')
        if name.startswith('unconnected-'):     # a pin left open on purpose (the buck's PG)
            continue
        nets[name] = sorted('%s.%s' % (child(x, 'ref')[1], child(x, 'pin')[1]) for x in children(n, 'node'))
    comps = {}
    for c in children(child(net, 'components'), 'comp'):
        fp = child(c, 'footprint')
        comps[child(c, 'ref')[1]] = (child(c, 'value')[1], fp[1] if fp else '')
    return nets, comps


def compare_schematic(sch_path):
    problems = []
    nets, comps = schematic_netlist(sch_path)
    want = design.netlist()
    for name in sorted(set(nets) | set(want)):
        if nets.get(name) != want.get(name):
            problems.append('net %s: schematic %s, design %s' % (name, nets.get(name), want.get(name)))
    for part in design.parts():
        got = comps.get(part['ref'])
        if got != (part['value'], part['fp']):
            problems.append('part %s: schematic %s, design %s' % (part['ref'], got, (part['value'], part['fp'])))
    for ref in set(comps) - {p['ref'] for p in design.parts()}:
        problems.append('part %s is in the schematic but not in the design' % ref)
    return problems, len(nets), len(comps)


def board_nets(board):
    nets = {}
    fps = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        fps[ref] = str(fp.GetFPID().GetUniStringLibId())
        for pad in fp.Pads():
            if pad.GetNumber() and pad.GetNetname():
                nets.setdefault(pad.GetNetname(), set()).add('%s.%s' % (ref, pad.GetNumber()))
    return {k: sorted(v) for k, v in nets.items()}, fps


def compare_board(board):
    problems = []
    nets, fps = board_nets(board)
    want = design.netlist()
    for name in sorted(set(nets) | set(want)):
        if nets.get(name) != want.get(name):
            problems.append('net %s: board %s, design %s' % (name, nets.get(name), want.get(name)))
    for part in design.parts():
        if fps.get(part['ref']) != part['fp']:
            problems.append('part %s: board footprint %s, design %s' % (part['ref'], fps.get(part['ref']), part['fp']))
    for ref in set(fps) - {p['ref'] for p in design.parts()}:
        problems.append('footprint %s is on the board but not in the design' % ref)
    return problems, len(nets), len(fps)


def run_drc(board_path):
    """Returns (errors, cosmetic, unconnected): lists of (type, severity, text), and a count."""
    board = pcbnew.LoadBoard(board_path)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    rpt = board_path + '.drc.txt'
    pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    text = open(rpt).read()
    os.remove(rpt)
    errors, cosmetic = [], []
    for block in re.split(r'\n(?=\[)', text):
        m = re.match(r'\[(\w+)\]: (.*)\n\s+(.*); Severity: (\w+)', block)
        if not m:
            continue
        kind, sev = m.group(1), m.group(4)
        body = re.sub(r'\(([\d.]+) mm, ([\d.]+) mm\)',
                      lambda g: '(%.2f, %.2f)' % (float(g.group(1)) - gen_pcb.OX, float(g.group(2)) - gen_pcb.OY),
                      block.split('\n** ')[0].strip())
        (cosmetic if kind in COSMETIC else errors).append((kind, sev, body))
    m = re.search(r'Found (\d+) unconnected pads', text)
    unconnected = int(m.group(1)) if m else -1
    for block in re.split(r'\n(?=\[)', text.split('unconnected pads **')[-1]):
        m2 = re.match(r'\[(\w+)\]: (.*)', block)
        if m2 and m2.group(1) == 'unconnected_items' and not any(block.strip().startswith(e[2][:40]) for e in errors):
            pass
    return errors, cosmetic, unconnected


def drc_of_variant(project_dir, project, **faults):
    """Build a deliberately broken copy of the board in a scratch directory and check it."""
    tmp = tempfile.mkdtemp(prefix='tlfault')
    try:
        shutil.copytree(os.path.join(project_dir, 'TaskLamp.pretty'), os.path.join(tmp, 'TaskLamp.pretty'))
        pro = copy.deepcopy(gen_pcb.PRO_TEMPLATE)
        pro['meta']['filename'] = project + '.kicad_pro'
        json.dump(pro, open(os.path.join(tmp, project + '.kicad_pro'), 'w'))
        board = gen_pcb.build(tmp, project, **faults)
        path = os.path.join(tmp, project + '.kicad_pcb')
        loaded = gen_pcb.write(board, path)
        errors, _, unconnected = run_drc(path)
        return errors, unconnected, compare_board(loaded)[0]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def self_test(project_dir, project):
    """Plant four faults, one at a time; every one must be reported."""
    results = []
    lane = gen_pcb.LANE_PWM0
    # 1. a stray track joining the red PWM line to the 24 V trunk
    errors, unconnected, _ = drc_of_variant(project_dir, project,
                                            extra_tracks=[('PWM_R', 0.4, [(gen_pcb.X0, lane), (gen_pcb.TRUNK_X, lane)], 0)])
    results.append(('short between PWM_R and +24V', any(e[0] in ('shorting_items', 'clearance', 'tracks_crossing')
                                                         for e in errors)))
    # 2. a track 0.05 mm from its neighbour (no contact, just too close)
    errors, unconnected, _ = drc_of_variant(project_dir, project,
                                            extra_tracks=[('PWM_G', 0.4, [(36.0, lane + 0.45), (42.0, lane + 0.45)], 0)])
    results.append(('track 0.05 mm from another net', any(e[0] == 'clearance' for e in errors)))
    # 3. one route left out
    errors, unconnected, _ = drc_of_variant(project_dir, project, drop_route=len(gen_pcb.routes()) - 1)
    results.append(('missing route', unconnected > 0))
    # 4. two pads with their nets exchanged
    _, _, parity = drc_of_variant(project_dir, project, swap_pads=(('J3', '2'), ('J3', '3')))
    results.append(('red and green swapped at the terminal', len(parity) > 0))
    return results


def geometry_facts(board):
    """Dimensions that must hold for the parts to fit; returns a list of problems."""
    problems = []
    mm = pcbnew.ToMM
    box = board.GetBoardEdgesBoundingBox()
    w, h = mm(box.GetWidth()), mm(box.GetHeight())
    if abs(w - gen_pcb.W) > 0.15 or abs(h - gen_pcb.H) > 0.15:
        problems.append('board outline is %.2f x %.2f mm, expected %.2f x %.2f' % (w, h, gen_pcb.W, gen_pcb.H))

    def pad(ref, num):
        fp = board.FindFootprintByReference(ref)
        p = next(p for p in fp.Pads() if p.GetNumber() == num)
        return mm(p.GetPosition().x) - gen_pcb.OX, mm(p.GetPosition().y) - gen_pcb.OY

    # QT Py: rows 15.24 mm apart, 2.54 mm pitch, pads 1 and 14 level with each other
    a, b, c = pad('U1', '1'), pad('U1', '14'), pad('U1', '7')
    if abs(b[0] - a[0] - 15.24) > 0.01 or abs(b[1] - a[1]) > 0.01 or abs(c[1] - a[1] - 15.24) > 0.01:
        problems.append('QT Py socket rows are not 15.24 mm apart / 7 pins long: %r %r %r' % (a, b, c))
    # the USB end of the module must reach the board edge: pad 1 is 2.73 mm from the module's end
    if a[1] - 2.73 > 1.5:
        problems.append('QT Py USB socket is %.2f mm in from the board edge' % (a[1] - 2.73))
    for ref, n in (('J1', 2), ('J2', 3), ('J3', 4)):
        xs = sorted(pad(ref, str(i + 1))[0] for i in range(n))
        if any(abs(q - p - 5.08) > 0.01 for p, q in zip(xs, xs[1:])):
            problems.append('%s pins are not on a 5.08 mm pitch' % ref)
    # every pad at least 1 mm inside the outline
    for fp in board.GetFootprints():
        for p in fp.Pads():
            x, y = mm(p.GetPosition().x) - gen_pcb.OX, mm(p.GetPosition().y) - gen_pcb.OY
            r = max(mm(p.GetSize().x), mm(p.GetSize().y)) / 2
            if min(x - r, y - r, gen_pcb.W - x - r, gen_pcb.H - y - r) < 1.0:
                problems.append('pad %s.%s is within 1 mm of the board edge' % (fp.GetReference(), p.GetNumber()))
    vias = [t for t in board.GetTracks() if t.GetClass() == 'PCB_VIA']
    other = [v for v in vias if v.GetNetname() != 'GND']
    if other:
        problems.append('%d vias on nets other than GND; only ground stitching is meant to have vias' % len(other))
    bottom = [t for t in board.GetTracks() if t.GetClass() != 'PCB_VIA' and t.GetLayer() == pcbnew.B_Cu]
    if bottom:
        problems.append('%d tracks on the bottom layer; it is meant to be an unbroken ground plane' % len(bottom))
    return problems
