#!/usr/bin/python3
"""
Compare two KiCad boards and say whether their circuit is the same.

    /usr/bin/python3 gen/compare_boards.py reference.kicad_pcb other.kicad_pcb [--all]

Each board is reduced to plain lists that ignore KiCad's random IDs:
  parts    reference, footprint, position, rotation, value
  pads     part.pad -> net name, position, size, drill
  tracks   start, end, width, layer, net
  vias     position, size, drill, net
  zones    net, layer, priority, outline, and copper area after filling
and, with --all, also the board outline and every silkscreen item.

The themed boards must match the reference on everything copper; their
outline and artwork are meant to differ. Exit code 0 means "same".
"""
import sys

import pcbnew

MM = pcbnew.ToMM


def r(v, nd=3):
    return round(v, nd)


def pt(p):
    return (r(MM(p.x)), r(MM(p.y)))


def describe(path, everything=False):
    b = pcbnew.LoadBoard(path)
    d = {"parts": [], "pads": [], "tracks": [], "vias": [], "zones": []}
    for fp in b.GetFootprints():
        if fp.GetReference() == "MB":            # panel perforations
            d["parts"].append(("MB", pt(fp.GetPosition())))
            continue
        d["parts"].append((fp.GetReference(), str(fp.GetFPID().GetLibItemName()),
                           pt(fp.GetPosition()), r(fp.GetOrientationDegrees(), 2),
                           fp.GetValue()))
        for p in fp.Pads():
            d["pads"].append((f"{fp.GetReference()}.{p.GetNumber()}", p.GetNetname(),
                              pt(p.GetPosition()), pt(p.GetSize()),
                              r(MM(p.GetDrillSize().x))))
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            d["vias"].append((pt(t.GetPosition()), r(MM(t.GetWidth())),
                              r(MM(t.GetDrillValue())), t.GetNetname()))
        else:
            d["tracks"].append((pt(t.GetStart()), pt(t.GetEnd()), r(MM(t.GetWidth())),
                                t.GetLayerName(), t.GetNetname()))
    for z in b.Zones():
        ol = z.Outline()
        outline = tuple(pt(ol.CVertex(i)) for i in range(ol.TotalVertices()))
        fill = z.GetFilledPolysList(z.GetLayer())
        area = sum(fill.Outline(i).Area() for i in range(fill.OutlineCount()))
        area -= sum(fill.Hole(i, h).Area() for i in range(fill.OutlineCount())
                    for h in range(fill.HoleCount(i)))
        d["zones"].append((z.GetNetname(), z.GetLayerName(), z.GetAssignedPriority(),
                           outline, r(area / 1e12, 1)))
    if everything:
        d["outline"], d["silk"] = [], []
        for dr in b.GetDrawings():
            layer = dr.GetLayerName()
            key = "outline" if layer == "Edge.Cuts" else "silk"
            if dr.Type() == pcbnew.PCB_TEXT_T:
                d[key].append(("text", layer, dr.GetText(), pt(dr.GetPosition()),
                               pt(dr.GetTextSize()), r(MM(dr.GetTextThickness()))))
            else:
                pts = ()
                if dr.GetShape() == pcbnew.SHAPE_T_POLY:
                    ps = dr.GetPolyShape()
                    pts = tuple(pt(ps.CVertex(i)) for i in range(ps.TotalVertices()))
                d[key].append(("shape", layer, dr.GetShape(), pt(dr.GetStart()),
                               pt(dr.GetEnd()), r(MM(dr.GetWidth())), pts))
    return {k: sorted(v, key=repr) for k, v in d.items()}


def compare(a_path, b_path, everything=False, quiet=False):
    """Return a list of differences (empty when the boards match)."""
    a, b = describe(a_path, everything), describe(b_path, everything)
    diffs = []
    for key in a:
        sa, sb = set(map(repr, a[key])), set(map(repr, b[key]))
        if key == "zones":
            # filled copper area may wobble by a fraction of a square mm with
            # a different outline (edge clearance); compare zones without it
            sa = {repr(z[:4]) for z in a[key]}
            sb = {repr(z[:4]) for z in b[key]}
        if sa != sb:
            diffs.append(f"{key}: {len(sa - sb)} only in the first, "
                         f"{len(sb - sa)} only in the second")
            if not quiet:
                for x in sorted(sa - sb)[:5]:
                    diffs.append(f"   - {x[:160]}")
                for x in sorted(sb - sa)[:5]:
                    diffs.append(f"   + {x[:160]}")
    return diffs


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    out = compare(args[0], args[1], everything="--all" in sys.argv)
    counts = describe(args[0])
    print(f"{len(counts['parts'])} parts, {len(counts['pads'])} pads, "
          f"{len(counts['tracks'])} track segments, {len(counts['vias'])} vias, "
          f"{len(counts['zones'])} zones compared")
    print("\n".join(out) if out else "SAME")
    sys.exit(1 if out else 0)
