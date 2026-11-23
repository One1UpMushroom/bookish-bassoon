# LED Task Lamp Controller

Firmware and a driver board for a five-channel LED task lamp (red, green, blue, warm
white, cool white), built from two 24 V LED strips and Adafruit breakout boards, and
controlled by a single push-button rotary encoder and a 240×240 color display.

| Part | Role |
|---|---|
| Adafruit **QT Py RP2040** | Microcontroller. Dual-core, 8 hardware PWM slices, 8 MB flash |
| Adafruit **I2C QT rotary encoder** (seesaw; PID 4991, or 5880 pre-soldered) | Encoder, push switch and an RGB "locator" pixel, all over I2C |
| Adafruit **240×240 TFT** (ST7789) | User interface |
| 1 m tunable-white strip (2700 K + 6500 K) and 0.8 m RGB strip, both 24 V | The light: about 15 W of white and 9 W of colour |
| **Driver board** ([`hardware/`](hardware/README.md)) | Carries the QT Py, makes its 5 V from the 24 V supply, and switches each strip colour with a MOSFET |

---

## 1. Wiring

```
                          QT Py RP2040
                   ┌─────────────────────────┐
     Red gate  ◄── │ A0  (GP29)    5V        │◄── 5 V from the board's converter
   Green gate  ◄── │ A1  (GP28)    GND       │── common ground
    Blue gate  ◄── │ A2  (GP27)    3V        │── TFT Vin, (encoder via STEMMA)
    Warm gate  ◄── │ A3  (GP26)    MO (GP3)  │──► TFT MOSI (SI)
     TFT TCS   ◄── │ SDA (GP24)    MI (GP4)  │◄── Encoder INT (extra wire)
     TFT D/C   ◄── │ SCL (GP25)    SCK (GP6) │──► TFT SCK
    Cool gate  ◄── │ TX  (GP20)    RX (GP5)  │──► TFT Lite (backlight PWM)
                   │   [STEMMA QT port]──────│──► Rotary encoder breakout
                   └─────────────────────────┘
```

| QT Py pad | GPIO | Connects to | Notes |
|---|---|---|---|
| A0 | GP29 | Red MOSFET gate (through 220 Ω) | PWM slice 6B |
| A1 | GP28 | Green MOSFET gate | PWM slice 6A |
| A2 | GP27 | Blue MOSFET gate | PWM slice 5B |
| A3 | GP26 | Warm white MOSFET gate | PWM slice 5A |
| TX | GP20 | Cool white MOSFET gate | PWM slice 2A |
| RX | GP5 | TFT **Lite** | PWM slice 2B: dimmable backlight |
| SCK | GP6 | TFT **SCK** | SPI0 |
| MO | GP3 | TFT **SI / MOSI** | SPI0 |
| MI | GP4 | Encoder breakout **INT** pad | Optional extra wire. Lets the firmware skip I2C reads while the knob is idle |
| SDA | GP24 | TFT **TCS** | Used as a plain GPIO |
| SCL | GP25 | TFT **D/C** | Used as a plain GPIO |
| STEMMA QT | GP22/23 | Encoder breakout | I2C1 (`Wire1`), 400 kHz |
| 3V / GND | | TFT Vin / GND | |
| 5V | | The board's 5 V converter, through a diode | USB may be connected at the same time |
| – | – | TFT **RST**, **CCS**, **SO**, **TE** | Leave unconnected. The display resets itself at power-up, and the microSD slot isn't used (leave it empty) |

On the driver board the LED pins and the 5 V feed are copper. The only wires are the
eight from the board's **J4** header (seven to the TFT, one to the encoder's INT pad),
the encoder's STEMMA QT cable, the 24 V supply and the two strips.

This uses all 11 pads, and every LED channel gets its own hardware PWM output.
If you don't run the INT wire, the firmware notices within a couple of knob turns and
falls back to plain polling. The pin
choice is deliberate: R+G and B+WW share PWM slices, so the firmware can phase-offset
them (see §5). Pin numbers live in `firmware/TaskLamp/config.h`.

**Encoder and I2C notes (from the Adafruit guides):**
* Clockwise turns increase values. The breakout's 45° encoder counts backwards, and the
  firmware compensates. *Settings ▸ Knob dir* flips it if your encoder differs.
* Touching the back of the encoder board can register as a button press. Insulate it
  from fingers and metal in the enclosure.
* Keep the STEMMA QT cable short (about 15 cm or less). Plug it in before powering up:
  I2C isn't designed for hot-plugging, although the firmware does retry every 2 s.
* With several encoders on one cable, Adafruit suggests powering their VIN separately
  if they misbehave.

**More controls without more pins:** the STEMMA QT port can be daisy-chained. A
**second rotary encoder breakout** with its A0 jumper cut (address 0x37) is detected
automatically. It becomes a dedicated **brightness knob**, and its click becomes
**power on/off**, working from any screen. This is the most worthwhile add-on for
day-to-day use. (The second knob has no INT wire, so it's simply polled.)

---

## 2. The driver board

The strips are never driven from the GPIO pins. The board in
[`hardware/`](hardware/README.md) does that, and also powers the QT Py from the lamp's
24 V supply:

* **24 V input**: a 2 A fuse, a Schottky diode against a supply wired backwards, a TVS
  diode against spikes, and bulk capacitors.
* **5 V for the QT Py** from a small switching converter, through a diode to the 5V pad.
  USB can be plugged in while the lamp is powered.
* **Five identical switches**: a logic-level MOSFET per colour (IRLB8721), its gate driven
  straight from the QT Py pin through 220 Ω, a 100 kΩ pull-down, and a 1N5819 from the
  strip wire back to +24 V.

`hardware/README.md` has the schematic, the files to send to PCBWay, the build order and
the power-up checks. [`docs/driver-build.html`](docs/driver-build.html) is the same build
as a step-by-step picture booklet. The parts not already in the inventory are listed with
links in [`docs/parts-to-order.md`](docs/parts-to-order.md).

What the firmware assumes about that hardware:

* **A high pin means light.** Each pin switches its MOSFET on directly.
* **The pull-downs keep the lamp dark** whenever the pins are not driven: during reset,
  in USB bootloader mode, or with the QT Py unplugged. The firmware then fades in rather
  than switching on hard.
* **PWM frequency.** The default is 2 kHz, under *Settings ▸ PWM freq* (500 Hz to 20 kHz).
  Lower frequencies dim further down; higher ones move any flicker beyond what a camera
  picks up. Resolution depends on frequency and on the CPU speed chosen in the Tools
  menu: 15–16 bits at 2 kHz, about 13 bits at 20 kHz.
* **The bottom of the dimming range.** A MOSFET gate driven through a resistor needs a
  fraction of a microsecond before the strip lights, so the very shortest pulses give no
  light. *Min duty* (§4) sets where light starts; the default is an estimate.
* **Currents.** The defaults are the catalogue figures for these strips: about 0.13 A per
  RGB colour and 0.30 A per white, 1.0 A with everything at 100 %.
* **The 3V rail** (QT Py regulator, 500 mA available) feeds the TFT and the encoder,
  tens of mA in total.
* **Display glass:** the 1.54" panel's backlight can slowly peel away from the TFT if
  nothing holds it. Plan a clear cover or window in the enclosure (or tape the edges).

---

## 3. Building and flashing

**Arduino IDE**
1. Boards Manager: install **Raspberry Pi Pico/RP2040** by Earle F. Philhower III.
2. Board: **Adafruit QT Py RP2040** (not the *Picoprobe* or *pico-debug* variants).
   *Flash Size*: pick an option **with** a filesystem (FS) of at least 64 KB. The default,
   "8MB (no FS)", leaves nowhere to store settings; the lamp then shows "No flash FS:
   settings not saved" on the home screen.
3. Library Manager: install **Adafruit seesaw Library**, **Adafruit ST7735 and ST7789 Library**
   and **Adafruit GFX Library**.
4. Open `firmware/TaskLamp/TaskLamp.ino` and upload. If the port doesn't appear, hold
   BOOT, tap RST, and keep holding BOOT until the RPI-RP2 drive appears.

**PlatformIO**: `pio run -t upload` (see `platformio.ini`).

**Host tests** (no hardware needed): `make -C test` runs about 4,100 checks of the
color math, light engine, power limiter, gesture decoder and the whole menu UI, including
a 200,000-event random-input fuzz run under AddressSanitizer/UBSan. `make -C test check`
also type-checks the Arduino-facing files against API stubs.

**Checked against the real toolchain:** the sketch compiles without warnings
(`-Wall -Wextra`) and links into a complete image with arduino-pico 6.3.2 (GCC 16.1),
Adafruit seesaw 1.7.9, Adafruit ST7735 and ST7789 1.12.0, Adafruit GFX 1.13.0 and Adafruit
BusIO 1.17.4. The image is about 392 KB of flash and 22 KB of static RAM.
`tools/rp2040_build_check.sh` repeats that build outside the Arduino IDE.

---

## 4. Using the lamp

### Gestures

| On the **home** screen | |
|---|---|
| **Turn** | Master brightness, 0.1–100 % on a perceptual scale. Steps are finer below 5 %, and spinning faster takes bigger steps |
| **Press + turn** | Quick parameter for the current mode: color temperature (White), hue (Color), speed (Sweep/Flash), period (Breathe/Rainbow), flicker (Candle) |
| **Click** | Open the menu. When the lamp is off: turn on |
| **Double-click** | Cycle through favorites |
| **Hold** (0.6 s) | Lamp on/off, with a smooth fade |

| In **menus** | |
|---|---|
| **Turn** | Move the selection, or change the value while editing |
| **Click** | Open a submenu, start editing a value, or confirm the edit |
| **Hold** | Go back. While editing: cancel and restore the old value |

When the screen is asleep, the first click only wakes it. Turning and holding work
immediately, so you can dim or switch off the lamp in the dark without looking.

### Modes

| Mode | What it does |
|---|---|
| **White** | Color temperature between your warm and cool LEDs, mixed in mired space for even steps |
| **Color** | Hue and saturation. The white part of pastel colors is produced by the white LEDs, which is more efficient and renders color better |
| **Mixer** | All five channels set independently |
| **Sweep** | Up to 8 programmable color steps, each with its own hold and fade time. Repeat, ping-pong or play once; linear or smooth easing; global speed 25–400 % |
| **Flash** | Color A/B flasher: on time, off time, flashes per burst, pause between bursts, speed. Hard-capped at 25 Hz |
| **Breathe** | Slow breathing of the base color, with an adjustable low point |
| **Rainbow** | Continuous hue rotation, with adjustable period and saturation |
| **Candle** | Natural-looking flicker of the base color |

*Breathe* and *Candle* animate the **base color**: the last White/Color/Mixer setting
you used. You can also change it in their *Adjust* menu. While you edit a sweep step or
a flash color, the lamp shows that color live. **Capture light** copies the current
base color into the step.

> ⚠️ Flashing light at 3–30 Hz can trigger seizures in people with photosensitive
> epilepsy. Use the Flash mode with care.

### Menu map

```
Menu
├── Mode ▸ White · Color · Mixer · Sweep · Flash · Breathe · Rainbow · Candle
├── Adjust ▸ (parameters of the current mode; Sweep ▸ Steps ▸ Step n ▸ R G B Warm Cool Hold Fade)
├── Favorites ▸ recall 1-6 · Save current ▸ slot 1-6
├── Sleep: Off / 5 / 15 / 30 / 60 / 90 min / 2 hr (fades out over the last 5 min)
└── Settings
    ├── Transition (fade time for on/off and mode changes)
    ├── White LEDs ▸ Warm LED K · Cool LED K · Max output · Pastel->W
    ├── Display ▸ Brightness · Follow lamp · Timeout · Knob glow
    ├── Knob dir
    ├── Power ▸ Budget · R/G/B/WW/CW current at 100 %
    ├── Channels ▸ Red/Green/Blue/Warm/Cool ▸ Test level · Min duty · Trim
    ├── PWM freq
    ├── Factory reset
    └── Firmware
```

### One-time calibration (recommended)

1. **Channels ▸ each channel**: on this screen the lamp shows *only* that channel at the
   *Test level* (default 0.1 %). Test and preview screens stay up for 10 minutes instead of
   the usual 30 s, so there is time to take a meter reading.
   * Set **Min duty** so the strip just glows at the test level: lower it until the light
     goes out, then back up one step. The defaults (0.12 % for red, 0.16 % for the others)
     come from simulating the driver board. This puts the dimmest real light on the first
     step of the knob.
   * Use **Trim** to cap a channel. This is useful for balancing the warm and cool whites.
2. **White LEDs**: the color temperatures of the warm and cool LEDs. The defaults, 2700 K
   and 6500 K, match the strip in this build.
3. **Power**: the defaults are catalogue figures. Measure each channel's current at 100 %
   and enter it, then set **Budget** to about 80 % of your supply's rating. The home
   screen shows the estimated current draw. Above the budget, all channels are scaled
   down together, so the color stays the same, and the header shows **LIMIT**.
4. **PWM freq**: leave it at 2 kHz unless a camera shows banding (raise it) or you want
   deeper dimming (lower it). Changing it moves the *Min duty* point, so redo step 1.

---

## 5. How the firmware works (and why it's efficient)

```
 core 0 ─ UI ──────────────────────────────┐       core 1 ─ light ───────────────────────────┐
 encoder (I2C, error-checked) → gestures   │       LightEngine: mode/effect → linear RGBWW    │
 → menus/home → Settings + Runtime ────────┼─copy─►  soft start, crossfade, sleep fade        │
 display (banded, change-only)             │       OutputStage: trim → power cap → min duty │
 flash save (debounced, atomic)            │◄──────  PwmBank: 16-bit HW PWM, phase-staggered│
 watchdog (fed only if both cores alive)   │status   backlight glide                         │
```

* **Two cores.** Core 1 does nothing but compute light and write PWM, so fades and
  effects stay smooth while the display redraws. The cores exchange one snapshot each way.
  The mutex is held only for a copy, and core 1 never waits on it. The one thing that does
  pause core 1 is a flash write: the RP2040 can't run code from flash while erasing it, so
  the core is held for a few tens of ms. The hardware PWM keeps running, so a steady light
  shows nothing. See *Flash wear* for how effects are kept clear of it.
* **Perceptual control, linear mixing.** Every level you set is CIE L\* lightness, so
  equal knob steps look equal from 0.1 % to 100 %. Mixing and cross-fading happen in
  linear light, which is how LED light physically adds up.
* **Deep, smooth dimming.** Hardware PWM runs at the highest resolution the chosen
  frequency allows, and the per-channel *Min duty* floor puts the bottom of the knob
  exactly where each strip starts to emit.
* **Less stress on the power supply.** The three PWM slices start a third of a period
  apart, and the second channel in each slice is end-aligned. Channels therefore don't
  all switch on at the same instant, which lowers peak current, ripple and EMI. Every
  on/off and mode change ramps instead of stepping, so there are no inrush spikes. The
  power budget keeps total current inside what your supply can deliver.
* **Low idle power.** The engine ticks at 250 Hz only while something is changing, and
  drops to 50 Hz when the light is steady. PWM registers are written only when a value
  changes. The display is drawn into a 23 KB band buffer, and each band is hashed: bands
  that didn't change are never sent over SPI. A brightness change typically re-sends 1–2
  of the 5 bands. The backlight follows the lamp's brightness (less glare at night),
  dims after the timeout and sleeps 10 s later. The display controller then enters its
  sleep mode. The QT Py's own NeoPixel is left unpowered. When the lamp is off, a faint
  amber glow on the encoder shows where the knob is.
* **Flash wear.** Settings are saved only after 5 s without changes, and only if they
  differ (by CRC) from what's stored. While an effect is running the wait is 30 s, or
  until the light is steady or off, so the short pause a flash write causes doesn't land
  in the middle of a sweep. The write goes through LittleFS (wear-levelled), to
  a temporary file followed by an atomic rename, so a power cut can't corrupt them. On
  load, the data is CRC-checked and every field is range-clamped.
* **Interrupt-driven input.** With INT wired, an idle knob costs one GPIO read per poll.
  I2C is used only when the encoder signals a change, while the button is held, for half
  a second after activity, and in a 4 Hz safety poll. An edge latch catches even short
  INT pulses.
* **Robust input.** Encoder reads check for I2C errors, so a loose cable can't look like
  a held button. A missing encoder is retried every 2 s. The switch is debounced, and the
  hardware watchdog reboots the board if either core ever stalls.
* **Clean power-up.** The backlight is held dark until the first frame is ready, so the
  display's power-up noise is never shown.
* **Display sleep timing.** The ST7789 needs 120 ms between going to sleep and waking, and
  5 ms before its next command. The driver enforces both, so touching the knob at the
  instant the screen dozes off can't leave it dark.

### Source map (`firmware/TaskLamp/`)

| File | Contents | Hardware-free? |
|---|---|---|
| `TaskLamp.ino` | Startup, core 0/core 1 loops, encoder I/O | – |
| `config.h` | Pins and timing | ✓ |
| `color.*` | CIE lightness, HSV, CCT mixing | ✓ |
| `settings.*` | Persistent settings, defaults, sanitizing, CRC, save scheduler | ✓ |
| `engine.*` | Modes, effects, fades, sleep timer, previews | ✓ |
| `output.*` | Trim, power budget, duty floor → PWM levels | ✓ |
| `input.*` | Click / double / long / press-turn gestures, acceleration, INT gating | ✓ |
| `ui.*` | Home screen, menu system, display power policy | ✓ |
| `painter.h` | Drawing interface used by the UI | ✓ |
| `display.*` | ST7789 driver, banded change-only rendering | – |
| `pwm_hw.*` | RP2040 PWM setup and phase staggering | – |
| `storage.*` | LittleFS load/save | – |

Outside the firmware: `hardware/` (the driver board's KiCad project and factory files),
`tools/pcb/` (the generator and checks that produce it) and `tools/rp2040_build_check.sh`
(full build with the real core and libraries).

---

## 6. Status

* All hardware-independent logic is covered by the host tests (`make -C test`).
* The whole sketch builds and links cleanly with the real arduino-pico toolchain and the
  current Adafruit libraries (§3). That was last run on 1.2.0; 1.2.1 changes only default
  values, and the host tests compile it.
* Firmware 1.1 ran on a breadboard build: the display, the encoder and the two white
  channels worked there. **Firmware 1.2.1 has not yet been run on hardware.** It differs
  in its defaults and in dropping one menu option, not in how it drives the pins.
* The driver board passes KiCad's design-rule check, 17 circuit simulations and 22 checks
  of its factory files (`hardware/tasklamp-driver/test-report.md`), but **no board has been
  built yet**. Its power-up section lists
  what to measure on the first one.
* Still worth confirming on the bench:
  * Clockwise turns brighten. If not, use *Knob dir*.
  * The display orientation (`kTftRotation` in `config.h`).
  * INT works: the encoder's red INT LED (on the back) blinks when you turn the knob.
  * No white flash on the display at power-up.
