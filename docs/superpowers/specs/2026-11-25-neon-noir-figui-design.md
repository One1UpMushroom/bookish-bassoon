# Neon Noir Chartreuse theme for FigUI (LowRider V4 / Jackpot3)

Status: draft for approval · 2026-11-25

## Intent

The LowRider V4 runs a stock V1 Engineering Jackpot3 with stock FluidNC firmware.
The machine's control screen should look like the owner's **Neon Noir Chartreuse** design
system, and the UI should be easy to modify later as the owner learns what they want
from it. FigUI is the starting point: a complete, tested replacement for the FluidNC
WebUI that already does everything the machine needs.

The screen it is designed for is a mains-powered **Raspberry Pi with the 7" Touch
Display 2, used in landscape at 1280×720**, running Chromium full screen and pointed at
the Jackpot3.

## Goals

- A fifth FigUI theme, **Neon Noir**, that follows the design system: near-black
  `void`/`asphalt` surfaces, fog body text, one chartreuse (#7FFF00) accent at about 10%
  of the area, red and amber only for safety states (owner's exception), sharp corners with 45° cut corners on
  panels, uppercase Oswald signage headings, Share Tech Mono readouts.
- Made the default theme in this fork; the other four themes stay selectable.
- Tuned for the 1280×720 touch layout first (FigUI's tablet layout), still correct on
  phone and desktop.
- Fits on the Jackpot3's internal storage alongside `config.yaml`.
- Kept as a small, readable diff on top of FigUI, so upstream fixes can be merged in.

## Non-goals

- No firmware changes, no custom board (both dropped earlier in the conversation).
- No new machine features in this round. Feature changes come later, once the machine
  is in use.
- No change to how FigUI talks to FluidNC, how it streams jobs, or how jog, hold and
  abort work.

## Anti-goals (would make it a failure even if it "works")

- Anything that makes a safety control harder to find or slower to hit: feed hold,
  abort, jog stop must stay large and unmistakable.
- State shown by colour alone. Every state keeps its word (IDLE, RUN, HOLD, ALARM).
- Treating the on-screen Abort as an emergency stop.
- Neon paragraphs, stacked glows, or flicker faster than 3 flashes a second.
- A bundle that no longer fits, or that pushes `config.yaml` off the board.

## Constraints found

| Constraint | Source | Effect |
|---|---|---|
| FigUI is GPL-3.0 | FigUI `LICENSE` | Fine for personal use; a shared copy must share its source. |
| Bundle today: **151.9 KB** of FigUI's **178 KB** limit (85.3%) | `npm run build:esp32` on FigUI `9a64e82` (2026-11-18) | About 26 KB of headroom for the whole theme. |
| Jackpot3 storage | Forum report of `$LocalFS/Size` on a 4 MB ESP32: 192 KB total | To be confirmed on this board with `$LocalFS/Size` before installing. |
| No internet in the Jackpot3's access-point mode | V1 docs: phone/Pi joins the "FluidNC" network directly | Google Fonts cannot load at the machine. |
| Themes are CSS variables plus a class on `<html>` | `src/index.css`, `src/store.ts` | A theme is mostly a variable block. Dark-only rules list each dark theme by class (15 places in `index.css`, plus `config-studio.css`), so the new class is added to each list. |
| Some colours are hard-coded | `GCodeViewer.tsx` axis colours (`#ef4444`, `#22c55e`, `#60a5fa`), toolpath colours, 5 Tailwind red/green/blue classes | These need theme-aware values for the look to hold together in the 3D viewer. |

## Approaches considered

1. **Fork FigUI and add a theme** (chosen by the owner). All features and the tested
   machine-control code on day one; the theme is a contained diff. Cost: a large
   codebase to learn, GPL.
2. Write an original UI from scratch with FigUI as reference. Smallest and fully owned,
   but rewrites the controller protocol and safety controls. Weeks of work and more
   risk to the machine.
3. A panel in the stock WebUI's extension feature. Dropped: it cannot restyle the
   interface.

## Design

### Colour mapping (FigUI variable → Neon Noir token)

| FigUI variable | Value | Token |
|---|---|---|
| `--bg` | #0B0D0C | void |
| `--surface` | #16191A | asphalt |
| `--elevated` | #1D2123 | between asphalt and steel-900 (pressed keys, inputs) *(my call)* |
| `--border` | #2A2F31 | steel-900, decorative dividers only |
| `--border-strong` | #646B6E | steel-500, every control's edge (3.59:1) |
| `--text-primary` | #C8CDD0 | fog |
| `--text-muted` | #A3AAAD | steel-300 |
| `--text-dim` | #646B6E | steel-500, units and hints only |
| `--accent` | #7FFF00 | chartreuse |
| `--ok` | #7FFF00 | chartreuse (Start, Connected, Run) |
| `--danger` | #FF453A | **safety red** (Alarm, Abort, jog stop): 5.72:1 on void |
| `--warn` | #FFB000 | **safety amber** (Hold, Door): 10.64:1 on void |
| `--info` | #A3AAAD | steel-300 |

Labels on chartreuse, red and amber fills use `void` (15.05:1, 5.72:1, 10.64:1).

**Safety exception (decided by the owner).** The one-accent rule gives way where safety
is involved. Stop, abort and alarm use red; hold and door use amber, following the usual
machine-safety colour meanings (ISO 3864, IEC 60204-1). The system's magenta is not used
in this UI. Every safety state still carries its word, because amber and chartreuse are
close in lightness (1.41:1) and some colour-blind users cannot tell them apart by hue.
The on-screen Abort is a software stop: the machine still needs a hardware emergency
stop that cuts motor and router power.

### State display

| FluidNC state | Badge |
|---|---|
| Idle | chartreuse outline, IDLE |
| Run / Jog / Home | chartreuse fill, void text, steady glow |
| Hold / Door | amber fill, void text, slow 1 Hz pulse (off under reduced motion) |
| Alarm | red fill, void text, plus the alarm reason in words |

### Form

- Panels: `cut-corner` 12 px 45° cuts on top-left and bottom-right via `clip-path`, with
  an SVG or pseudo-element frame so the border survives the clip. Radius 0, never more
  than 2 px anywhere.
- Panel titles: Oswald 700, uppercase, +4% letter spacing, chartreuse.
- DRO numbers: Share Tech Mono, fog, tabular. The axis letter is chartreuse; axes are told
  apart by letter, not by red/green/blue.
- Buttons: 1 px steel-500 edge, sharp corners, 48 px minimum touch height. Primary
  (Start, selected jog step) is solid chartreuse. Focus is a 2 px chartreuse ring at
  2 px offset.
- 3D viewer: cut moves chartreuse, rapids steel-500 dashed, completed moves fog, tool
  marker fog so red keeps meaning "stop". Axis gizmo letters stay labelled.
- Router readout: `ROUTER 17,940 rpm  set 18,000`. The large number is measured speed
  and the small one is the commanded speed (FluidNC's `S` value). FluidNC reports only
  the commanded speed, so until the planned router speed controller and detector exist,
  the large number shows the commanded value. The "Spindle" panel is renamed "Router".
- Glow: one 8 px chartreuse text-shadow on the state badge and the active tab only.
- Motion: 120–200 ms ease-out; no scanlines.

### Fonts: zero bytes on the ESP32 *(my call)*

Embedding Oswald and Share Tech Mono, even cut down to the characters used, would take
roughly 15–25 KB of the 26 KB headroom. That is too close. Instead:

- The theme's CSS names `Oswald`, `Share Tech Mono` and `Barlow` (body) first, with
  condensed, monospace and system fallbacks.
- The fonts are **installed on the Raspberry Pi** (OFL font files copied into
  `~/.local/share/fonts`). Because this costs nothing on the ESP32, all three of the
  system's faces can be used. The Pi shows the real look, and the ESP32 stores nothing.
- A phone or laptop without them falls back gracefully, and the look still holds through
  colour, cuts and uppercase.
- If the headroom turns out larger on this board, a cut-down Oswald can be embedded later.

### Size budget

The theme's CSS and the default-theme switch must stay **under 6 KB compressed**, which
keeps the bundle near 158 KB of 178 KB. The build already reports usage. The theme work
checks it after each step.

## The work, in order

1. Fork FigUI on GitHub, clone it, and add `docs/NEON-NOIR.md` recording these decisions.
2. Add the `neon-noir` theme class: variables in `index.css`, the class added to each
   dark-theme list, the theme type in `store.ts`, an entry in the Settings theme picker,
   default theme set to `neon-noir`.
3. Form layer: cut-corner panels, signage headings, button edges, focus rings, state badges.
4. Theme-aware colours in the 3D viewer and the 5 hard-coded Tailwind colour classes.
5. Check against FigUI's built-in machine simulator (`fluidnc-web-sim.py` and demo mode)
   at 1280×720, phone width and desktop. Screenshots of each state: Idle, Run, Hold,
   Alarm. Run FigUI's own test suite and the contrast pairs above.
6. Build `index.html.gz`, confirm the size, and write install steps:
   `$LocalFS/Size` first, back up the stock `index.html.gz`, upload, and roll back by
   re-uploading the stock file.
7. Pi kiosk notes: Chromium kiosk flags, the two fonts, the Jackpot3's address.

## Left to the builder

- Exact `clip-path` frame technique, and whether the frame is CSS or SVG.
- Tailwind class versus plain CSS for each piece, following FigUI's existing style.
- The shade of `--elevated`, within the limit that control edges keep 3:1.

## Calls I made (please check)

- Axes told apart by letter instead of red/green/blue.
- Fonts installed on the Pi instead of embedded in the bundle.
- Neon Noir becomes the default theme; the other four stay.
- Red #FF453A and amber #FFB000 as the safety colours.
- Until the speed detector exists, the measured-RPM slot shows the commanded speed.
  The plan for the detector and how it reports to the UI is a separate later design.

## Sample

`docs/neon-noir-figui-sample.html` is a static mock of the 1280×720 screen in all four
states (Idle, Run, Hold, Alarm). It is a picture of the target, not FigUI code.
