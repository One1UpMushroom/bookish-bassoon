#!/usr/bin/python3
"""Regenerates the driver board's KiCad project and checks it.

    /usr/bin/python3 tools/pcb/build.py            # generate, check, export
    /usr/bin/python3 tools/pcb/build.py --no-export

Needs KiCad 7 or newer (its `pcbnew` Python module and `kicad-cli`). Everything
is written to hardware/tasklamp-driver/. The script exits non-zero, and writes
no factory files, unless every check passes.
"""
import copy
import csv
import datetime
import json
import os
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pcbnew  # noqa: E402

import buck_fp  # noqa: E402
import check  # noqa: E402
import design  # noqa: E402
import gen_pcb  # noqa: E402
import gen_sch  # noqa: E402
import verify_fab  # noqa: E402
from kisch import uid  # noqa: E402

PROJECT = gen_sch.PROJECT
REV = 'C'
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'hardware', 'tasklamp-driver')

GERBER_LAYERS = 'F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts'


def say(ok, text):
    print('  %s %s' % ('ok  ' if ok else 'FAIL', text))
    return ok


def generate(date):
    os.makedirs(os.path.join(OUT, 'TaskLamp.pretty'), exist_ok=True)
    sym_lib = os.path.join(OUT, 'TaskLamp.kicad_sym')
    with open(sym_lib, 'w') as f:
        f.write(gen_sch.qtpy_symbol_lib())
    with open(os.path.join(OUT, 'sym-lib-table'), 'w') as f:
        f.write(gen_sch.SYM_LIB_TABLE)
    with open(os.path.join(OUT, 'fp-lib-table'), 'w') as f:
        f.write(gen_sch.FP_LIB_TABLE)
    with open(os.path.join(OUT, 'TaskLamp.pretty', 'QTPy_RP2040_Socket.kicad_mod'), 'w') as f:
        f.write(gen_pcb.qtpy_footprint())
    buck_fp.write_all(os.path.join(OUT, 'TaskLamp.pretty'))
    sch = os.path.join(OUT, PROJECT + '.kicad_sch')
    with open(sch, 'w') as f:
        f.write(gen_sch.build(sym_lib, date, REV))
    pro = copy.deepcopy(gen_pcb.PRO_TEMPLATE)
    pro['meta']['filename'] = PROJECT + '.kicad_pro'
    with open(os.path.join(OUT, PROJECT + '.kicad_pro'), 'w') as f:
        json.dump(pro, f, indent=2)
        f.write('\n')
    # footprints are tied to their schematic symbols, so "Update PCB from Schematic" works
    board = gen_pcb.build(OUT, PROJECT, sym_uuid=lambda ref: uid(PROJECT, 'sym', ref))
    tb = board.GetTitleBlock()
    tb.SetTitle('Task lamp driver board')
    tb.SetRevision(REV)
    tb.SetDate(date)
    pcb = os.path.join(OUT, PROJECT + '.kicad_pcb')
    gen_pcb.write(board, pcb)
    prl = os.path.join(OUT, PROJECT + '.kicad_prl')     # per-user window state, not part of the design
    if os.path.exists(prl):
        os.remove(prl)
    return sch, pcb


def run_checks(sch, pcb):
    ok = True
    print('schematic against design.py')
    problems, n_nets, n_parts = check.compare_schematic(sch)
    ok &= say(not problems, '%d nets and %d parts match' % (n_nets, n_parts))
    for p in problems:
        print('       ' + p)

    print('board against design.py')
    board = pcbnew.LoadBoard(pcb)
    problems, n_nets, n_fps = check.compare_board(board)
    ok &= say(not problems, '%d nets and %d footprints match' % (n_nets, n_fps))
    for p in problems:
        print('       ' + p)
    problems = check.geometry_facts(board)
    ok &= say(not problems, 'outline, socket spacing, terminal pitch, edge margins, vias only on ground, clean ground plane')
    for p in problems:
        print('       ' + p)

    print("KiCad's design-rule check")
    errors, cosmetic, unconnected = check.run_drc(pcb)
    ok &= say(unconnected == 0, '%d unconnected pads' % unconnected)
    ok &= say(not errors, '%d violations' % len(errors))
    for kind, sev, body in errors:
        print('       ' + body.replace('\n', '\n       '))
    kinds = {}
    for kind, _, _ in cosmetic:
        kinds[kind] = kinds.get(kind, 0) + 1
    if kinds:
        print('       not counted: ' + ', '.join('%d %s' % (v, k) for k, v in sorted(kinds.items())))

    print('do the checks notice a planted fault?')
    for name, caught in check.self_test(OUT, PROJECT):
        ok &= say(caught, name)
    return ok


def export(sch, pcb):
    fab = os.path.join(OUT, 'gerbers')
    shutil.rmtree(fab, ignore_errors=True)
    os.makedirs(fab)
    quiet = dict(check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['kicad-cli', 'pcb', 'export', 'gerbers', '-o', fab + '/', '--layers', GERBER_LAYERS,
                    '--no-x2', '--no-netlist', '--subtract-soldermask', pcb], **quiet)
    subprocess.run(['kicad-cli', 'pcb', 'export', 'drill', '-o', fab + '/', '--format', 'excellon',
                    '--excellon-units', 'mm', '--excellon-zeros-format', 'decimal', '--excellon-separate-th',
                    '--generate-map', '--map-format', 'pdf', pcb], **quiet)
    for name in os.listdir(fab):
        if name.endswith('.gbrjob'):
            os.remove(os.path.join(fab, name))
    zpath = os.path.join(OUT, PROJECT + '-gerbers.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(fab)):
            if not name.endswith('.pdf'):
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                z.writestr(info, open(os.path.join(fab, name), 'rb').read())
    subprocess.run(['kicad-cli', 'sch', 'export', 'pdf', '-o', os.path.join(OUT, PROJECT + '-schematic.pdf'), sch],
                   **quiet)
    write_bom()
    return fab, zpath


def write_bom():
    def stem(p):
        # "Gate resistor, red" and "Gate resistor, green" are one line of the BOM
        channel_part = (p['ref'][0] in 'RQ' and p['ref'] not in ('R11', 'R12')) or p['ref'] in ('D1', 'D2', 'D3', 'D4', 'D5')
        return p['note'].rsplit(',', 1)[0] if channel_part else p['note']

    def number(ref):
        return int(''.join(c for c in ref if c.isdigit()))

    groups = {}
    for p in design.parts():
        if not p['ref'].startswith(('H', 'TP')):
            groups.setdefault((p['value'], p['fp'], p['src'], p['mpn'], stem(p)), []).append(p)
    order = 'JFUQLDRC'
    rows = sorted(groups.items(), key=lambda kv: (order.index(kv[1][0]['ref'][0]), number(kv[1][0]['ref'])))
    source = {design.STOCK: 'in stock', design.ORDER: 'to order'}
    with open(os.path.join(OUT, PROJECT + '-bom.csv'), 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['Qty', 'References', 'Value', 'What it is', 'From', 'Part number', 'Footprint'])
        for (value, fp, src, mpn, note), ps in rows:
            refs = sorted((p['ref'] for p in ps), key=number)
            where = 'board in stock, sockets to order' if refs == ['U1'] else source[src]
            w.writerow([len(refs), ' '.join(refs), value, note, where, mpn, fp.split(':')[1]])


def main():
    date = datetime.date.today().isoformat() if '--date' not in sys.argv else sys.argv[sys.argv.index('--date') + 1]
    print('generating %s' % os.path.relpath(OUT, ROOT))
    sch, pcb = generate(date)
    ok = run_checks(sch, pcb)
    if not ok:
        print('\nchecks failed: no factory files written')
        return 1
    if '--no-export' not in sys.argv:
        fab, zpath = export(sch, pcb)
        print('factory files read back')
        problems, notes = verify_fab.verify(pcb, fab, PROJECT)
        for n in notes:
            say(True, n)
        for p in problems:
            ok = say(False, p)
        if not ok:
            os.remove(zpath)
            print('\nfactory files do not match the board: zip removed')
            return 1
        print('wrote %s (%d files) and %s' % (os.path.relpath(fab, ROOT), len(os.listdir(fab)),
                                              os.path.relpath(zpath, ROOT)))
    print('\nall checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
