#!/usr/bin/env python3
"""
Turn the letters the themed boards use into outlines, saved in glyphs.json,
so building the boards doesn't need the font files or any font software.

    python3 gen/themes/make_glyphs.py path/to/fonts_dir

fonts_dir holds the unpacked npm packages @fontsource/chakra-petch,
@fontsource/jost and @fontsource/oswald (version 5.3.0), each in a folder of
that name with its package/files/*.woff inside, for example:

    npm pack @fontsource/jost@5.3.0 && mkdir jost && tar -xzf fontsource-jost-5.3.0.tgz -C jost

All three fonts are under the SIL Open Font License 1.1; the licence texts are
in fonts/. Needs fontTools (pip install fonttools).

Each letter is stored as its outline: a list of closed loops of points in
"em" units (1.0 = the font size), y pointing UP as fonts do, plus how far
the pen moves on after it (the advance). Curves are flattened into short
straight steps no longer than 0.005 em.
"""
import json
import os
import sys

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/-.:>=+% "
FONTS = {   # key used by the themes: (package folder, file in package/files)
    "chakra-600": ("chakra-petch", "chakra-petch-latin-600-normal.woff"),
    "jost-600": ("jost", "jost-latin-600-normal.woff"),
    "oswald-600": ("oswald", "oswald-latin-600-normal.woff"),
}
STEP = 0.005      # longest straight step when flattening curves, em


class FlattenPen(BasePen):
    """Collects each glyph's loops as lists of points, curves cut into
    short straight steps."""

    def __init__(self, glyphset, upm):
        super().__init__(glyphset)
        self.upm = upm
        self.loops, self.cur = [], []

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _steps(self, pts):
        length = sum(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
                     for a, b in zip(pts, pts[1:]))
        return max(2, int(length / (STEP * self.upm)) + 1)

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        n = self._steps([p0, p1, p2])
        for i in range(1, n + 1):
            t = i / n
            self.cur.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        n = self._steps([p0, p1, p2, p3])
        for i in range(1, n + 1):
            t = i / n
            a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
            self.cur.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                             a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))

    def _closePath(self):
        if len(self.cur) > 2:
            if self.cur[0] == self.cur[-1]:
                self.cur.pop()
            self.loops.append([(round(x / self.upm, 4), round(y / self.upm, 4))
                               for x, y in self.cur])
        self.cur = []

    _endPath = _closePath


def main():
    src = sys.argv[1]
    out = {}
    for key, (pkg, fname) in FONTS.items():
        font = TTFont(os.path.join(src, pkg, "package", "files", fname))
        upm = font["head"].unitsPerEm
        cmap = font.getBestCmap()
        gs = font.getGlyphSet()
        hmtx = font["hmtx"]
        os2 = font["OS/2"]
        glyphs = {}
        for ch in CHARS:
            name = cmap.get(ord(ch))
            if name is None:
                print(f"{key}: no glyph for {ch!r}")
                continue
            pen = FlattenPen(gs, upm)
            gs[name].draw(pen)
            glyphs[ch] = {"adv": round(hmtx[name][0] / upm, 4), "loops": pen.loops}
        out[key] = {"cap": round(os2.sCapHeight / upm, 4), "glyphs": glyphs,
                    "source": f"@fontsource/{pkg} 5.3.0, {fname}, SIL OFL 1.1"}
        print(f"{key}: {len(glyphs)} glyphs, cap height {out[key]['cap']} em")
    with open(os.path.join(HERE, "glyphs.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("wrote", os.path.join(HERE, "glyphs.json"),
          os.path.getsize(os.path.join(HERE, "glyphs.json")) // 1024, "KB")


if __name__ == "__main__":
    main()
