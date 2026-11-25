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
the Jackpot3. At that size, with Layout set to Tablet, FigUI's landscape tablet layout
puts Position and Jog on the left and the viewer, job controls and collapsed panels on
the right.

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
| Bundle today: **151.9 KB** of FigUI's **178 KB** limit (85.3%) | `scripts/build-esp32.mjs` (the size step of `npm run build:esp32`) on FigUI `9a64e82` (2026-11-18) | About 26 KB of headroom for the whole theme. |
| Jackpot3 storage | Forum report of `$LocalFS/Size` on a 4 MB ESP32: 192 KB total | To be confirmed on this board with `$LocalFS/Size` before installing. |
| No internet in the Jackpot3's access-point mode | V1 docs: phone/Pi joins the "FluidNC" network directly | Google Fonts cannot load at the machine. |
| Themes are CSS variables plus a class on `<html>` | `src/index.css`, `src/store.ts` | A theme is mostly a variable block. Theme rules name each dark theme by class: 14 rules in `index.css` (13 syntax-highlight rules and the `:root:not(…)` guard for light-only variables) and 5 `html:not(…)` guards in `config-studio.css`. The new class goes in each. A missed guard leaks light values such as `--workspace-surface: #f7f9fe` into Neon Noir. |
| The ESP32 build renames class names that contain a hyphen | `vite.config.ts` (`tailwindMangle`, `mangleReservedClasses`) | FigUI lists its theme classes there so they keep their names. `neon-noir` must be added too. |
| State colours are set in code | `stateColor` and `stateBg` in `src/store.ts` | Run, Jog and Home use `info`, Door uses `danger` (red), Check uses `warn`. The Run fill and the amber Door need these two functions changed. |
| `danger` and `warn` mean more than safety in FigUI | 145 `danger` uses across 18 `.tsx` files, 82 `warn` uses across 19 | Mapped straight to safety red and amber, they would also colour the X axis, Zero All and the toolpath palette. See "Safety colours in FigUI". |
| Some colours are hard-coded | `GCodeViewer.tsx` axis colours (`#ef4444`, `#22c55e`, `#60a5fa`), red tool marker, per-tool path palette; `ProbePanel.tsx` diagram axes; 5 Tailwind red/green classes; white text on accent and danger fills (`.btn-primary` and `.btn-danger-solid` in `index.css`, and 6 `text-white` uses: the selected jog step, the Position panel's E-Stop, 3 Settings buttons) | These need theme-aware values. White on chartreuse is 1.30:1 and on red 3.41:1. |
| Touch sizes | `.job-action` is 38 px tall; header buttons 34–40 px; viewer toolbar 40 px (`min-h-10`) | The theme raises every touch target to at least 48 px. |
| 1280 px is at FigUI's desktop threshold | `useActiveLayout` in `src/App.tsx` | In "auto", FigUI picks the desktop layout at 1270 px or wider unless Chromium reports a coarse pointer. Set Layout to Tablet in FigUI's settings on the Pi. |
| A 7" panel is small for 1280 px | Touch Display 2: 7", 16:9, about 155 mm wide | 1 px is about 0.12 mm, so 48 px is about 5.8 mm. Material Design's 48 dp works out to about 9 mm, and gloves need more. See "Open questions". |

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
| `--border` | #2A2F31 | steel-900, decorative dividers only (1.44:1 on void) |
| `--border-strong` | #646B6E | steel-500, every control's edge: 3.59:1 on void, 3.26:1 on asphalt, 2.99:1 on elevated |
| `--text-primary` | #C8CDD0 | fog: 12.16:1 on void, 11.03:1 on asphalt |
| `--text-muted` | #A3AAAD | steel-300: 8.27:1 on void, 7.50:1 on asphalt |
| `--text-dim` | #A3AAAD | steel-300 as well. Units and hints are text, so they need 4.5:1, and steel-500 gives only 3.26:1 on asphalt. The design system keeps steel-500 for edges and icons. |
| `--accent`, `--accent-hover` | #7FFF00 | chartreuse |
| `--ok` | #7FFF00 | chartreuse (Start, Resume, Connected) |
| `--danger` | #FF453A | **safety red** (Alarm, Abort, jog stop): 5.72:1 on void, 5.19:1 on asphalt |
| `--warn` | #FFB000 | **safety amber** (Hold, Door, Pause): 10.64:1 on void, 9.65:1 on asphalt |
| `--info` | #A3AAAD | steel-300 |
| `--ok-solid-text`, `--warn-solid-text` | #0B0D0C | void |
| `--purple`, `--teal` | #C8CDD0 | fog (B and C axes and macro colours; the LR4 has no rotary axes) |

Tailwind reads `accent`, `ok`, `danger`, `warn` and `info` from `-rgb` triplets
(`rgb(var(--ok-rgb) / α)`), so each needs one: `127 255 0`, `255 69 58`, `255 176 0`
and `163 170 173`. The `--jog-*` variables serve only FigUI's rose-style jog view and
take steel values.

Labels on chartreuse, red and amber fills use `void` (15.05:1, 5.72:1, 10.64:1). Where
FigUI hard-codes white on those fills, the theme overrides it to `void`.

Control edges are measured against the surface the control sits on. A control placed
on `--elevated` needs a steel-300 edge (6.89:1), because steel-500 gives 2.99:1 there.

**Safety exception (decided by the owner).** The one-accent rule gives way where safety
is involved. Stop, abort and alarm use red; hold and door use amber, following the usual
machine-safety colour meanings (ISO 3864, IEC 60204-1). The system's magenta is not used
in this UI. Every safety state still carries its word.
The on-screen Abort is a software stop: the machine still needs a hardware emergency
stop that cuts motor and router power.

### Safety colours in FigUI

Mapping `danger` and `warn` straight to red and amber is not enough on its own:

- **Must change**, because they would put red or amber on things that are not stop,
  alarm, hold or door: the DRO's `AXIS_COLOR` (X is `--danger`, Y `--ok`, Z `--info`,
  also used for the per-axis Home icons), the jog keys' `text-danger`, `text-ok` and
  `text-info`, Zero All (`btn-warn` in every dark theme), and the viewer's per-tool
  palette and red tool marker. Axis letters become chartreuse and jog labels fog.
- **Should be red but is amber:** "Abort Homing" uses `btn-warn`.
- **Owner to decide:** errors, warnings, destructive buttons such as Delete, and the
  single-block toggle also use `danger` or `warn`. See "Open questions".

### State display

What the 1280×720 tablet layout shows in each state. Controls follow FigUI's own rules.

| FluidNC state | Badge | Controls |
|---|---|---|
| Idle | chartreuse outline, IDLE | Start (and From line); the axis keys, Zero all and Home all; jog live |
| Run | chartreuse fill, void text, 8 px glow | Pause (amber fill) and Abort; in Position, the axis keys, Zero all and Home all give way to a second Abort; jog locked |
| Jog / Home | chartreuse fill, the word | jog stop and the jog keys stay live while jogging; "Abort Homing" while homing |
| Hold | amber fill, void text, the dot pulses at 1 Hz | Resume and Abort; jog locked. A feed hold stops motion only, so the router keeps turning. |
| Door | amber fill, DOOR, the dot pulses at 1 Hz | Resume once the door is closed |
| Alarm | red fill, void text | Position shows the reason and Clear alarm; Home all; Start unavailable; jog locked |
| Check, Sleep | steel outline, the word | as FigUI |

FigUI's jog accepts taps only in Idle or Jog (`canJog`). In Run, Hold and Alarm it dims the
jog keys to 40% and ignores taps.

Clear alarm sends `$X`, except for alarms 1, 2, 13 and 16 (hard limit, soft limit, hard
stop, expander reset), which `$X` does not clear. FigUI clears those with a soft reset
after a confirm (`src/lib/alarm.ts`). Position is lost after a hard limit, so the
operator homes before running again. Alarm 1 occurs only if hard limits are enabled in
`config.yaml`.

### Form

- Panels: `cut-corner` 12 px 45° cuts on top-left and bottom-right via `clip-path`, with
  an SVG or pseudo-element frame so the border survives the clip. Radius 0, never more
  than 2 px anywhere.
- Panel titles: Oswald 700, uppercase, +4% letter spacing, chartreuse.
- DRO numbers: Share Tech Mono 48 px, fog, tabular. The axis letter is chartreuse; axes
  are told apart by letter, not by red/green/blue.
- Buttons: 1 px steel-500 edge, sharp corners. Every touch target is at least 48 px;
  Start, Pause, Resume and Abort are 64 px tall. Primary (Start, Resume, selected jog step)
  is solid chartreuse; Pause is solid amber. Abort is a 2 px red outline with red text,
  not a solid red block, so it does not look like an emergency stop (FigUI draws it
  solid). Disabled buttons lose their fill: steel-900 edge, steel-500 label.
- Focus is a 2 px chartreuse ring at 2 px offset. On controls flush with a panel edge it
  sits 4 px inside instead, in void on chartreuse fills, so the corner clip cannot hide it.
- Left column: Position takes the height it needs and Jog takes the rest. FigUI splits
  the column into equal halves, which at 720 px gives Position about 320 px. That is
  less than its rows need, so the panel scrolls, and in Alarm the reason and Clear Alarm
  can end up out of sight. Jog is locked in Alarm, so it can shrink.
- 3D viewer: cut moves chartreuse, rapids steel-500 dashed, completed moves fog, tool
  marker fog so red keeps meaning "stop". Axis gizmo letters stay labelled.
- Router readout, in the DRO footer where FigUI shows `S 0 rpm`:
  `ROUTER ---- rpm  NO SENSOR  SET 18,000`. The large slot is for the measured speed.
  FluidNC reports only the commanded speed (its `S` value), so until the planned router
  speed controller and detector exist, the slot shows dashes and a NO SENSOR tag, never
  a number. A copied or made-up figure would claim the router is turning when it may
  be switched off. SET shows the commanded value at 22 px, and the feed beside it reads
  `FEED 1500 mm/min`. The "Spindle & Overrides" panel is renamed "Router & Overrides".
- Glow: one 8 px chartreuse glow, on two things only: a box-shadow round the filled Run
  badge and a text-shadow on the active tab's label. Never stacked.
- Motion: 120–200 ms ease-out on colour changes; no scanlines. On the Hold and Door
  badge only the dot pulses, so the label stays at 10.64:1. Pulsing the whole badge, as
  the first mock did, dropped the label to 3.85:1 at the dim point. All motion stops
  under `prefers-reduced-motion`.

### Small code changes the look needs

A pure CSS theme cannot do everything above. Each of these is a few lines:

- `src/store.ts`: register the theme (`Theme` type, `DARK_THEME_CLASSES`, `isValidTheme`,
  the default, and the `midnight-dark` fallback in `toggleTheme`), and change
  `stateColor`/`stateBg` for Run, Jog, Home, Door and Check.
- `vite.config.ts`: add `neon-noir` to `mangleReservedClasses`.
- `SettingsPanel.tsx`: add Neon Noir to the theme picker.
- `DRO.tsx`: the router and feed footer, axis colours, the per-axis zero key shows ⊙
  instead of "Z" (a "Z" on the X and Y rows reads as the Z axis), Zero All without
  `btn-warn`, and the job-time Abort button drawn like the other Abort (outline, square
  icon) instead of a solid red block with a power icon. In Alarm, show Zero, Go to zero
  and Zero All as unavailable, because FluidNC rejects G-code and jog commands there
  (FigUI leaves them enabled). Add a one-line recovery hint under the alarm reason.
- `JogPad.tsx`: neutral jog key colours, void text on the selected step, and a
  "JOG LOCKED · RUN" label over the dimmed keys so the reason is in words.
- `locales/en.json`: the Position panel's "E-Stop" button during a job (a soft reset, not
  an emergency stop) becomes "Abort", in its label and tooltip; "Spindle & Overrides"
  becomes "Router & Overrides".
- `Header.tsx` (optional): the machine name where FigUI shows the FluidNC logo.

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

The theme's CSS, the code changes above and the default-theme switch must stay **under
6 KB compressed**, which keeps the bundle near 158 KB of 178 KB. The build already
reports usage. The theme work checks it after each step.

## The work, in order

1. Fork FigUI on GitHub, clone it, and add `docs/NEON-NOIR.md` recording these decisions.
2. Register the `neon-noir` theme: the variable block in `index.css`, the class in the
   14 `index.css` rules and the 5 `config-studio.css` guards, the `store.ts` changes,
   `mangleReservedClasses`, the Settings picker entry, and `neon-noir` as the default.
3. Form layer: cut-corner panels, signage headings, button edges and sizes, disabled
   style, focus rings, state badges, the left-column split.
4. Colours: `stateColor`/`stateBg`, the safety-colour fixes listed above, theme-aware 3D
   viewer colours, and void text where FigUI hard-codes white on fills.
5. The remaining small code changes: router readout, labels, Alarm guards.
6. Check against FigUI's built-in machine simulator (`fluidnc-web-sim.py` and demo mode)
   at 1280×720, phone width and desktop. Screenshots of each state: Idle, Run, Hold,
   Alarm. Run FigUI's own test suite and the contrast pairs above, and try the targets
   with gloves on the real panel.
7. Build `index.html.gz`, confirm the size, and write install steps:
   `$LocalFS/Size` first, back up the stock `index.html.gz`, upload, and roll back by
   re-uploading the stock file.
8. Pi kiosk notes: Chromium kiosk flags, the three fonts, the Jackpot3's address, and
   Layout set to Tablet in FigUI's settings.

## Left to the builder

- Exact `clip-path` frame technique, and whether the frame is CSS or SVG.
- Tailwind class versus plain CSS for each piece, following FigUI's existing style.
- The shade of `--elevated`, as long as fog and steel-300 text keep 4.5:1 on it and no
  control relies on a steel-500 edge against it.

## Calls I made (please check)

- Axes told apart by letter instead of red/green/blue.
- Fonts installed on the Pi instead of embedded in the bundle.
- Neon Noir becomes the default theme; the other four stay.
- Until the speed detector exists, the measured-RPM slot shows dashes and NO SENSOR
  rather than the commanded speed. The plan for the detector and how it reports to the
  UI is a separate later design.
- FigUI's "E-Stop" button in Position renamed "Abort", and Abort drawn as a red outline,
  so neither looks like an emergency stop.
- The JOG LOCKED label, the alarm recovery hint, the unavailable Zero keys in Alarm, the
  ⊙ zero key and the machine name in the header.

## Open questions for the owner

- **Panel size.** On the 7" Touch Display 2, a 48 px target is about 5.8 mm and the
  64 px job buttons about 7.7 mm. Options: a larger 1280×720 panel (same layout, bigger
  targets); a Chromium zoom with `--force-device-scale-factor` (up to 1.125 keeps this
  layout and makes 48 px about 6.5 mm; more than that leaves the page under 640 px tall,
  and FigUI switches to its compact landscape layout, which this mock does not show);
  or accept the sizes after a glove test.
- **Red and amber beyond safety.** FigUI also uses `danger` and `warn` for errors,
  warnings, destructive buttons and single-block mode. Keep them, which reads as
  "red = danger or error, amber = caution", or make them neutral, which is a larger diff?

## Sample

`docs/neon-noir-figui-sample.html` is a static mock of the 1280×720 screen in all four
states (Idle, Run, Hold, Alarm), laid out like FigUI's landscape tablet layout. It is a
picture of the target, not FigUI code.
