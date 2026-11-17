#!/bin/bash
# Export fabrication files and board renders for the unit board and the panel.
#   gen/export.sh        (run from hardware/buck-breakout, needs KiCad 7+)
set -e
cd "$(dirname "$0")/.."
LAYERS=F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,F.Paste,Edge.Cuts
for name in buck33630 buck33630-panel; do
  out=fab/$name; rm -rf "$out"; mkdir -p "$out"
  kicad-cli pcb export gerbers kicad/$name.kicad_pcb -o "$out/" -l $LAYERS \
      --subtract-soldermask --no-netlist >/dev/null
  kicad-cli pcb export drill kicad/$name.kicad_pcb -o "$out/" --format excellon \
      --excellon-separate-th --excellon-units mm >/dev/null
  rm -f "$out"/*.gbrjob
  (cd fab && rm -f $name-gerbers.zip && zip -q -j $name-gerbers.zip $name/* && rm -rf $name)
done

# renders: black solder mask look.  Each side is composited from four plots
# (copper, mask openings, bare-board/holes, silkscreen + outline) because
# kicad-cli does not let us choose the drawing order.
theme_dir="$HOME/.config/kicad/7.0/colors"; mkdir -p "$theme_dir"
cp gen/buckdark.json "$theme_dir/buckdark.json"
tmp=$(mktemp -d)
r() {  # r board out side(F|B) zoom [--mirror]
  local b="kicad/$1.kicad_pcb" o="$tmp/$2" z="$4" m="$5"
  local common="--page-size-mode 2 --exclude-drawing-sheet $m"
  kicad-cli pcb export svg "$b" -o "$o-cu.svg"   -l "$3.Cu"   -t buckdark $common >/dev/null
  kicad-cli pcb export svg "$b" -o "$o-bw.svg"   -l "$3.Cu"   --black-and-white $common >/dev/null
  kicad-cli pcb export svg "$b" -o "$o-mask.svg" -l "$3.Mask" -t buckdark $common >/dev/null
  kicad-cli pcb export svg "$b" -o "$o-silk.svg" -l "$3.SilkS,Edge.Cuts" -t buckdark $common >/dev/null
  rsvg-convert -z "$z" -b '#07090c' "$o-cu.svg" -o "$o-cu.png"
  rsvg-convert -z "$z" -b white "$o-bw.svg" -o "$o-bw.png"
  rsvg-convert -z "$z" "$o-mask.svg" -o "$o-mask.png"
  rsvg-convert -z "$z" "$o-silk.svg" -o "$o-silk.png"
  # where there is no copper (bare board, drilled holes) paint the board colour
  convert "$o-bw.png" -colorspace gray -alpha off "$o-a.png"
  convert "$o-bw.png" -fill '#07090c' -colorize 100 "$o-a.png" \
      -compose CopyOpacity -composite "$o-bare.png"
  convert "$o-cu.png" "$o-mask.png" -compose over -composite \
      "$o-bare.png" -compose over -composite \
      "$o-silk.png" -compose over -composite -strip "img/$2.png"
}
r buck33630 board-top F 12
r buck33630 board-bottom B 12 --mirror
r buck33630-panel panel-top F 4.5
r buck33630-panel panel-bottom B 4.5 --mirror
rm -rf "$tmp"
ls -la fab/*.zip img/*.png
