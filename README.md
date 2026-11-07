# LED Task Lamp Controller

Firmware for a five-channel (R, G, B, warm/amber white, cool white) LED task lamp
built from Adafruit breakout boards and controlled by a single push-button rotary encoder
and a 240×240 color display.

| Part | Role |
|---|---|
| Adafruit **QT Py RP2040** | Microcontroller. Dual-core, 8 hardware PWM slices, 8 MB flash |
| Adafruit **I2C QT rotary encoder** (seesaw; PID 4991, or 5880 pre-soldered) | Encoder, push switch and an RGB "locator" pixel, all over I2C |
| Adafruit **240×240 TFT** (ST7789) | User interface |
| Amber/cool-white + RGB LED arrays | The light. Driven through **external drivers**, never from the GPIO pins |

---

## 1. Wiring

```
                          QT Py RP2040
                   ┌─────────────────────────┐
   Red driver  ◄── │ A0  (GP29)    5V        │
 Green driver  ◄── │ A1  (GP28)    GND       │── common ground
  Blue driver  ◄── │ A2  (GP27)    3V        │── TFT Vin, (encoder via STEMMA)
  Warm driver  ◄── │ A3  (GP26)    MO (GP3)  │──► TFT MOSI (SI)
     TFT TCS   ◄── │ SDA (GP24)    MI (GP4)  │◄── Encoder INT (extra wire)
     TFT D/C   ◄── │ SCL (GP25)    SCK (GP6) │──► TFT SCK
  Cool driver  ◄── │ TX  (GP20)    RX (GP5)  │──► TFT Lite (backlight PWM)
                   │   [STEMMA QT port]──────│──► Rotary encoder breakout
                   └─────────────────────────┘
```

| QT Py pad | GPIO | Connects to | Notes |
|---|---|---|---|
| A0 | GP29 | Red driver PWM/DIM input | PWM slice 6B |
| A1 | GP28 | Green driver | PWM slice 6A |
| A2 | GP27 | Blue driver | PWM slice 5B |
| A3 | GP26 | Warm (amber) white driver | PWM slice 5A |
| TX | GP20 | Cool white driver | PWM slice 2A |
| RX | GP5 | TFT **Lite** | PWM slice 2B: dimmable backlight |
| SCK | GP6 | TFT **SCK** | SPI0 |
| MO | GP3 | TFT **SI / MOSI** | SPI0 |
| MI | GP4 | Encoder breakout **INT** pad | Optional extra wire. Lets the firmware skip I2C reads while the knob is idle |
| SDA | GP24 | TFT **TCS** | Used as a plain GPIO |
| SCL | GP25 | TFT **D/C** | Used as a plain GPIO |
| STEMMA QT | GP22/23 | Encoder breakout | I2C1 (`Wire1`), 400 kHz |
| 3V / GND | | TFT Vin / GND | |
| – | – | TFT **RST**, **CCS**, **SO**, **TE** | Leave unconnected. The display resets itself at power-up, and the microSD slot isn't used (leave it empty) |

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

## 2. Circuit notes (hardware limits to respect)

You're sizing the drivers. These are the constraints the firmware assumes:

* **The GPIOs only provide a logic signal.** RP2040 pins are 3.3 V and rated for a few
  mA. Each channel needs a driver stage:
  * **Constant-voltage arrays/strips (12/24 V with on-board resistors):** use a low-side
    N-MOSFET per channel that is *fully on at 3.3 V gate drive* (look for R<sub>DS(on)</sub>
    specified at V<sub>GS</sub> = 2.5 V or 4.5 V). Add about 100 Ω in series with the gate
    and 100 kΩ from gate to source.
  * **High-power LEDs/COBs:** use constant-current buck drivers with a PWM **DIM** input,
    and check that the DIM "high" threshold accepts 3.3 V logic.
* **Match the PWM frequency to the driver.** The setting is under *Settings ▸ PWM freq*.
  The default is 2 kHz. Many CC drivers accept only 100 Hz–1 kHz on DIM (Mean Well LDD
  series, for example); set those to 1000 Hz. MOSFET-switched arrays can run at 1–20 kHz.
  Resolution depends on frequency: about 15 bits at 2 kHz, about 12.7 bits at 20 kHz.
* **Active-low DIM inputs** are handled per channel with *Settings ▸ Channels ▸ (ch) ▸ Invert*.
* **Pull-downs:** fit 10–100 kΩ from each driver input to GND. The pins float during
  reset and USB bootloader mode, and the pull-downs keep the LEDs dark until the firmware
  starts them. The firmware then fades in rather than switching on hard.
* **Grounds:** use one common ground between the LED supply and the QT Py, star-wired.
  Keep LED return currents out of the logic ground path.
* **Logic power:** don't run LED current through the QT Py. Power it from USB or a
  separate 5 V buck converter. If you feed its 5V pad while USB may also be connected,
  add a Schottky diode so the two sources can't back-feed each other.
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

**Host tests** (no hardware needed): `make -C test` runs about 4,000 checks of the
color math, light engine, power limiter, gesture decoder and the whole menu UI, including
a 200,000-event random-input fuzz run under AddressSanitizer/UBSan. `make -C test check`
also type-checks the Arduino-facing files against API stubs.

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
    ├── Channels ▸ Red/Green/Blue/Warm/Cool ▸ Test level · Min duty · Trim · Invert
    ├── PWM freq
    ├── Factory reset
    └── Firmware
```

### One-time calibration (recommended)

1. **PWM freq**: set it to suit your drivers (§2).
2. **Channels ▸ each channel**: on this screen the lamp shows *only* that channel at the
   *Test level* (default 0.1 %).
   * Set **Invert** if the LED is lit when it should be dark.
   * Raise **Min duty** until the LED just starts to glow. This removes the dead zone at
     the bottom of the knob, so the first step above zero is the dimmest real light.
   * Use **Trim** to cap a channel. This is useful for balancing the warm and cool whites,
     or for under-driving an LED that runs hot.
3. **White LEDs**: enter the color temperature of your amber/warm and cool LEDs.
4. **Power**: measure each channel's current at 100 % and enter it, then set **Budget**
   to about 80 % of your supply's rating. The home screen then shows estimated current
   draw. Above the budget, all channels are scaled down together, so the color stays
   the same, and the header shows **LIMIT**.

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
  effects stay smooth even while the display redraws or flash is written. The cores
  exchange one snapshot each way. The mutex is held only for a copy, and core 1 never
  waits on it.
* **Perceptual control, linear mixing.** Every level you set is CIE L\* lightness, so
  equal knob steps look equal from 0.1 % to 100 %. Mixing and cross-fading happen in
  linear light, which is how LED light physically adds up.
* **Deep, smooth dimming.** Hardware PWM runs at the highest resolution the chosen
  frequency allows, and the per-channel *Min duty* floor puts the bottom of the knob
  exactly where your LEDs start to emit.
* **Less stress on the power supply.** The three PWM slices start a third of a period
  apart, and the second channel in each slice is end-aligned. Channels therefore don't
  all switch on at the same instant, which lowers peak current, ripple and EMI. Every
  on/off and mode change ramps instead of stepping, so there are no inrush spikes. The
  power budget keeps total current inside what your supply and drivers can handle.
* **Low idle power.** The engine ticks at 250 Hz only while something is changing, and
  drops to 50 Hz when the light is steady. PWM registers are written only when a value
  changes. The display is drawn into a 23 KB band buffer, and each band is hashed: bands
  that didn't change are never sent over SPI. A brightness change typically re-sends 1–2
  of the 5 bands. The backlight follows the lamp's brightness (less glare at night),
  dims after the timeout and sleeps 10 s later. The display controller then enters its
  sleep mode. The QT Py's own NeoPixel is left unpowered. When the lamp is off, a faint
  amber glow on the encoder shows where the knob is.
* **Flash wear.** Settings are saved only after 5 s without changes, and only if they
  differ (by CRC) from what's stored. The write goes through LittleFS (wear-levelled), to
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

---

## 6. Status

* All hardware-independent logic is covered by the host tests (`make -C test`).
* The hardware layer has been type-checked against stubs of the library APIs but **has not
  yet been compiled with the real arduino-pico toolchain or run on hardware**. Expect to
  confirm the following on the bench:
  * Clockwise turns brighten. If not, use *Knob dir*.
  * The display orientation (`kTftRotation` in `config.h`).
  * INT works: the encoder's red INT LED (on the back) blinks when you turn the knob.
  * No white flash on the display at power-up.
