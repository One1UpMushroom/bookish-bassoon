#!/usr/bin/python3
"""
Build the four themed BUCK//33630 boards: the single board and the 2 x 4
panel for each theme, with design-rule reports and Gerber files.

    /usr/bin/python3 gen/build_themes.py               all four themes
    /usr/bin/python3 gen/build_themes.py neon parkside  just these
    ... --no-panel     skip the panels (faster while designing)
    ... --no-export    skip the Gerber files

Run with the Python that has KiCad 7's pcbnew. Writes:
  kicad/themes/buck33630-<theme>.kicad_pcb          single board
  kicad/themes/buck33630-<theme>-panel.kicad_pcb    panel of eight
  fab/themes/buck33630-<theme>[-panel]-gerbers.zip  files for the board house
  fab/themes/drc-<theme>[-panel].rpt                KiCad's design-rule reports

For every board it also checks that the copper (parts, pads, nets, tracks,
vias, zones) is exactly the standard board's, so a theme can never change
the circuit, and runs gen/silk_check.py, which checks what KiCad's own check
can't see: drawn shapes against each other, the strokes and spacing of the
real-font titles, KiCad's plot in pixels, and that every gold or silver
accent sits over copper (the pixel parts on the single boards only; a panel
is eight copies of the same board). The script stops with an error if any
check fails.
"""
import os
import shutil
import subprocess
import sys
import tempfile

import pcbnew
from pcbnew import FromMM

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_pcb       # noqa: E402
import compare_boards  # noqa: E402
import silk_check      # noqa: E402
import themes          # noqa: E402
from themes import kit  # noqa: E402

ROOT = os.path.join(HERE, "..")
KICAD_T = os.path.join(ROOT, "kicad", "themes")
FAB_T = os.path.join(ROOT, "fab", "themes")
REF_UNIT = os.path.join(ROOT, "kicad", "buck33630.kicad_pcb")
REF_PANEL = os.path.join(ROOT, "kicad", "buck33630-panel.kicad_pcb")
LAYERS = "F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,F.Paste,Edge.Cuts"


def setup(board):
    """Stricter silkscreen rules than the standard board, so KiCad's check
    proves every line of text meets the board houses' minimums: 0.8 mm tall,
    0.15 mm strokes, 0.15 mm from other silkscreen and from bare copper."""
    ds = board.GetDesignSettings()
    ds.m_MinSilkTextHeight = FromMM(0.8)
    ds.m_MinSilkTextThickness = FromMM(0.15)
    ds.m_SilkClearance = FromMM(0.15)


def library_table():
    """The themed boards live one folder down; point KiCad at the footprints."""
    os.makedirs(KICAD_T, exist_ok=True)
    with open(os.path.join(KICAD_T, "fp-lib-table"), "w") as f:
        f.write('(fp_lib_table\n  (lib (name "buck33630")(type "KiCad")'
                '(uri "${KIPRJMOD}/../buck33630.pretty")(options "")'
                '(descr "LMR33630 buck breakout footprints"))\n)\n')


def gerbers(board_path, name):
    """Gerber and drill files, zipped, the same way export.sh makes them."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["kicad-cli", "pcb", "export", "gerbers", board_path, "-o",
                        tmp + "/", "-l", LAYERS, "--subtract-soldermask",
                        "--no-netlist"], check=True, capture_output=True)
        subprocess.run(["kicad-cli", "pcb", "export", "drill", board_path, "-o",
                        tmp + "/", "--format", "excellon", "--excellon-separate-th",
                        "--excellon-units", "mm"], check=True, capture_output=True)
        for f in os.listdir(tmp):
            if f.endswith(".gbrjob"):
                os.remove(os.path.join(tmp, f))
        zpath = os.path.join(FAB_T, f"{name}-gerbers.zip")
        if os.path.exists(zpath):
            os.remove(zpath)
        shutil.make_archive(zpath[:-4], "zip", tmp)
        return zpath


def build_one(theme, panel=True, export=True):
    results = {}
    jobs = [("unit", f"buck33630-{theme.ID}", build_pcb.build_unit, REF_UNIT)]
    if panel:
        jobs.append(("panel", f"buck33630-{theme.ID}-panel", build_pcb.build_panel,
                     REF_PANEL))
    for kind, name, builder, ref in jobs:
        path = os.path.join(KICAD_T, name + ".kicad_pcb")
        builder(out=path, decorate=theme.decorate, corners=theme.CORNERS, setup=setup)
        kit.set_stackup(path, **theme.COLORS)
        counts = build_pcb.drc(path, f"drc-{theme.ID}{'-panel' if kind == 'panel' else ''}.rpt",
                               fab=FAB_T)
        diffs = compare_boards.compare(ref, path, quiet=True)
        print(f"  copper vs the standard {kind}: " + ("identical" if not diffs
                                                    else "; ".join(diffs)))
        silk = silk_check.check(path, pixels=(kind == "unit"))
        if export:
            print("  " + os.path.relpath(gerbers(path, name), ROOT))
        results[kind] = (counts, diffs, silk)
    return results


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ids = args or themes.IDS
    library_table()
    os.makedirs(FAB_T, exist_ok=True)
    failed = []
    for tid in ids:
        theme = themes.load(tid)
        print(f"{theme.NAME}:")
        for kind, (counts, diffs, silk) in build_one(theme, "--no-panel" not in sys.argv,
                                                     "--no-export" not in sys.argv).items():
            bad = counts.get("DRC violations", 1) or counts.get("unconnected pads", 1) \
                or counts.get("Footprint errors", 1) or diffs or silk
            if bad:
                failed.append(f"{tid} {kind}")
    print("\nall boards pass" if not failed else "\nFAILED: " + ", ".join(failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
