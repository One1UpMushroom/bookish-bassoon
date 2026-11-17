#!/bin/bash
# Quick layer previews (PNG) of a board: preview.sh board.kicad_pcb outdir
set -e
B="$1"; O="$2"; mkdir -p "$O"
kicad-cli pcb export svg "$B" -o "$O/top.svg" -l F.Cu,F.SilkS,F.Fab,Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet >/dev/null
kicad-cli pcb export svg "$B" -o "$O/bot.svg" -l B.Cu,B.SilkS,Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet --mirror >/dev/null
for n in top bot; do rsvg-convert -z "${3:-10}" -b white "$O/$n.svg" -o "$O/$n.png"; done
kicad-cli pcb export svg "$B" -o "$O/bsilk.svg" -l B.SilkS,B.Mask,Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet --mirror >/dev/null
rsvg-convert -z "${3:-10}" -b white "$O/bsilk.svg" -o "$O/bsilk.png"
