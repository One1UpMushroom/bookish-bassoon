# LowRider V4 hardware checklist

The control hardware for the LowRider V4 with the Neon Noir FigUI screen. It covers the
controller, the motion electronics, power, router control, the touchscreen and the
safety hardware. It doesn't cover the machine's printed and mechanical parts; those are
in V1 Engineering's own LR4 bill of materials.

Facts come from V1 Engineering's [LR4 docs](https://docs.v1e.com/lowrider/) and
[Jackpot3 docs](https://docs.v1e.com/electronics/jackpot3/), read in November 2026.
**Check** marks a value that wasn't stated there and needs confirming before you buy.
The design decisions behind the screen are in
[`superpowers/specs/2026-11-25-neon-noir-figui-design.md`](superpowers/specs/2026-11-25-neon-noir-figui-design.md).

## 1. Controller

- [ ] **Jackpot3 CNC controller** (V1 Engineering or Elecrow, about $76). It comes with 5
      plugs and 6 heat sinks, but **no USB cable**.
      - ESP32-WROOM-32 running FluidNC, with 6 TMC2226 drivers on the board (UART-set
        current, no StallGuard). The LR4 uses 5 of the 6 drivers.
      - It takes 9–24 V DC and needs at least 19 W (24 V × 0.8 A). It has
        reverse-polarity protection.
- [ ] **USB-C data cable**, needed for the first setup and for flashing.
- [ ] **6 heat sinks** fitted on the drivers (they're in the box).
- [ ] **microSD card** for job files: larger than 2 GB, FAT32. V1 says Class 4 works best,
      up to Class 6. Keep file names to 30 characters or fewer.
- [ ] **Enclosure or case** for the board. Keep wires away from the antenna, which
      overhangs the board edge; V1 says never to cross wires over it.
- [ ] **Board fan** (optional). V1 sells a 24 V fan; case fans normally run straight from
      the main supply. **Check** your enclosure's airflow.

## 2. Motion

- [ ] **5 NEMA17 stepper motors** with a shaft of 20 mm or longer. V1's shop listing is a
      76 oz-in motor. **Check** each motor's rated current, because it sets the driver
      current in `config.yaml`.
      - 1 on X (the gantry core)
      - 2 on Y (Y0 left, Y1 right, as you face the machine), so homing can square the gantry
      - 2 on Z (Z0 left, Z1 right), so homing can level it
- [ ] **Motor extension cables and connectors** where the leads don't reach. The Jackpot3
      has open 2.54 mm male headers. V1 says you may need to splice or solder some leads.
- [ ] **Labels** on every motor and endstop lead (X, Y0, Y1, Z0, Z1), at both ends.

## 3. Endstops and probe

- [ ] **5 endstops**, wired **normally closed (NC)**, V1's standard:
      - X
      - Y0 and Y1 (the LR4 homes to Y min)
      - Z0 and Z1
- [ ] **Touch plate** for Z, wired **normally open (NO)**. It plugs into the last input
      (gpio.36). Measure its thickness for the probe setting.
- [ ] **Signal-level check:** the inputs are active low, with 10 kΩ pull-ups on the
      board. They accept 3.3–5 V and no more (since board revision V1). Nothing above
      5 V goes into an input.
- [ ] **Hard limits enabled** in `config.yaml`, as planned. That is what makes the
      "Alarm 1 · Hard limit" screen in the UI happen.

## 4. Power

- [ ] **24 V DC power supply**, V1's kit voltage. The LR4 bill of materials says 36 W or
      more. **Check** the total if you add a fan or use the high-current outputs: each
      output can draw 1 A continuously, or up to 2.5 A briefly.
- [ ] **Mains lead, fuse and switch** for the supply. Mains wiring should be done or
      checked by someone qualified.
- [ ] **24 V lead to the Jackpot3's power plug**, with the polarity checked with a
      multimeter before connecting.

## 5. Router

- [ ] **Router** (V1 designs the LR4 around a trim router). **Check** the model's speed
      range, because it sets the RPM presets in the UI.
- [ ] **Router on/off for now:** a solid-state relay (SSR) rated for the router's mains
      current. Its control input is driven from a Jackpot3 output set to 5 V. V1 calls
      this advanced. **Check** the SSR's input voltage range against 5 V.
- [ ] **Router speed controller**: to be designed later. The UI's ROUTER RPM readout is
      reserved for it.
- [ ] **Router speed detector**: to be designed later. Until it exists, the UI shows
      `---- rpm  NO SENSOR` next to the commanded speed.
- [ ] **Dust collection hose, grounded at one end** (V1's warning), if you use one.

## 6. Touchscreen

- [ ] **Raspberry Pi 4 (2 GB or more) or Raspberry Pi 5.** A Pi 5 is smoother in the 3D
      toolpath viewer.
- [ ] **Raspberry Pi Touch Display 2**, 7", 720 × 1280, mounted in landscape so it runs
      at **1280 × 720**.
- [ ] **Power supply for the Pi:** the official USB-C supply, 5 V 3 A for a Pi 4 or 5 V 5 A
      (27 W) for a Pi 5. There's no battery anywhere in this setup.
- [ ] **microSD card for Raspberry Pi OS**, 16 GB or larger.
- [ ] **Case or mount** that holds the Pi and display together, out of the dust stream.
- [ ] **Network:** the Pi joins the Jackpot3's own Wi-Fi network ("FluidNC"), or both join
      your shop router.
- [ ] **Fonts installed on the Pi:** Oswald, Share Tech Mono and Barlow (all free, OFL).
      This is software, but nothing looks right without it.

## 7. Safety hardware

- [ ] **Hardware emergency stop** that cuts power to the motors and the router. The UI's
      Abort is a software stop and is **not** an emergency stop. The router runs on mains,
      so its cut-off needs a contactor or relay rated for it. Have this circuit designed
      or checked by someone qualified.
- [ ] **Eye and hearing protection** at the machine.
- [ ] **Fire extinguisher** within reach (a jammed bit can scorch material).

## 8. Tools for setup

- [ ] Multimeter, for supply polarity, endstop continuity and motor coil pairs.
- [ ] Small screwdrivers, wire strippers and crimpers for the 2.54 mm connectors.
- [ ] A laptop or phone for the first setup over USB-C or the "FluidNC" Wi-Fi network.

## 9. Before the first power-up

- [ ] Supply polarity measured at the Jackpot3 plug.
- [ ] Each motor's two coil pairs found with the multimeter, and the plugs matched to them.
- [ ] Every NC endstop reads closed at rest and open when pressed.
- [ ] Touch plate reads open at rest and closed when touched to the bit.
- [ ] Motor currents set in `config.yaml` from the motor's rating.
- [ ] Router unplugged, and the bit out, for the first motion tests.
- [ ] Hardware emergency stop tested: it cuts the motors and router, and the machine stays
      off until it's reset.

## 10. Before installing the Neon Noir UI

- [ ] `$LocalFS/Size` run on the Jackpot3, confirming there's room for about 158 KB.
- [ ] The stock `index.html.gz` and `config.yaml` backed up off the board.
- [ ] FigUI's Layout set to **Tablet** on the Pi (on Auto, FigUI picks its desktop layout
      at 1270 px wide or more).
