# PCB notes

Background for the task lamp's driver board: the decisions a circuit board forced on the
design and how the finished board settled each one, general two-layer practice, and where
to order. The board itself, with its files and build instructions, is in
[`hardware/`](../hardware/README.md).

The ordering research was compiled in November 2026. Prices, fees and tariffs change
often; every number below is a starting point to re-check on the vendor's live quote page.

---

## 1. Decisions, and what the board does

### 1.1 MOSFET voltage rating

The IRLB8721 is a **30 V** part on a **24 V** rail. The usual advice is to choose 40–60 V
parts, so that a TVS diode sized for a 24 V supply (which clamps at 40 V or so during a
surge) can protect them.

The board keeps the IRLB8721, because with LED strips as the only load that advice does
not bite:

* When a MOSFET is **off**, the LED strings sit between the rail and its drain and take up
  most of any surge voltage; what is left drives at most a few milliamps through the
  strip's own resistors.
* When it is **on**, its drain is at ground.
* The only thing that pushes a drain above the rail is the inductance of the strip wiring
  at turn-off, and a 1N5819 from each drain to the rail clamps that half a volt above it.

The TVS is there for the parts that do see the rail directly: the 5 V converter and the
capacitors. If the board were ever used for a load without LEDs in series (a motor, a
relay), this reasoning would no longer hold and 60 V MOSFETs would be the right change.

### 1.2 Gate drive from 3.3 V

The gates are driven straight from the QT Py pins. The IRLB8721's on-resistance is only
guaranteed at 4.5 V, but its threshold is at most 2.35 V and each channel carries 0.3 A
or less, far below where the last volt of gate drive matters. Rather than add a driver
chip, the board's power-up procedure measures each MOSFET once: under 0.1 V from drain to
source at 100 %.

### 1.3 Input protection

In order from the connector inwards:

1. **Fuse**, 2 A, in a holder for mini blade fuses. The lamp draws about 1 A.
2. **Schottky diode** in series (SB560) against a reversed supply. A P-channel MOSFET or
   an ideal-diode controller would waste less than its 0.45 W, at the cost of three or
   four more parts; one diode was judged the better trade for a hand-built board.
3. **TVS diode** (P6KE30A) across the rail.
4. Bulk capacitance: 100 µF at the input and 100 µF beside the strip terminals.

### 1.4 Logic power

The inventory holds no inductors, so 5 V has to come from either a linear regulator
(about 2 W of heat from 24 V, and a heatsink) or a bought converter. The board uses a
switching module with the 78xx pinout; several makes fit the same three holes. It feeds
the QT Py's 5V pad through a diode, and the QT Py has its own diode from USB, so both
sources can be connected at once.

### 1.5 Grounding

* The whole bottom layer is **one ground plane**, with nothing routed on it.
* Everything else is on the top layer, with **no vias**, so each track's return current
  runs directly beneath it and strip current never shares a path with a signal.
* The top layer has no ground fill. With a full plane underneath it would add nothing but
  slivers between tracks.

### 1.6 Heat

None to manage. A fully-on MOSFET at 0.3 A dissipates a few milliwatts; the input diode
about half a watt; the converter about a tenth.

### 1.7 Connectors and the QT Py

* **QT Py:** on two 1×7 sockets, so it can be removed. The rows are **15.24 mm (0.6 in)**
  apart at 2.54 mm pitch, with the first pad 2.73 mm from the USB end of the 17.78 ×
  20.70 mm module. These figures are read from Adafruit's own board file
  ([Adafruit-QT-Py-RP2040-PCB](https://github.com/adafruit/Adafruit-QT-Py-RP2040-PCB));
  an earlier version of these notes gave 0.675 in for the row spacing, which was wrong.
* **Encoder and display:** off the board, on a pin header and the QT Py's STEMMA QT
  socket, so they can be mounted where the enclosure wants them.
* **24 V input and strips:** 5.08 mm screw terminals, labelled on both sides of the board.
  They are not keyed against each other, so the labels matter; the input terminal is on
  the opposite edge from the strip terminals.

### 1.8 Bring-up

The board has test pads for +5 V and ground, every terminal is a place to put a meter
probe, and each part's value is printed inside its outline. The power-up procedure in
`hardware/README.md` checks the 5 V rail before the QT Py is plugged in.

---

## 2. General PCB best practice (two-layer board)

* **Tool:** KiCad (free, open source). Keep the schematic and board files in this repo
  next to the firmware, so the board revision and the firmware it needs stay together.
* **Rules first:** load the fab house's design rules into the DRC before placing anything.
  JLCPCB's standard two-layer process: 0.127 mm (5 mil) minimum track and space, 0.2 mm
  minimum recommended drill (0.15 mm absolute), 0.13 mm annular ring. Designing at
  0.2 mm track / 0.2 mm space with 0.3 mm vias leaves comfortable margin and works at
  every vendor below.
* **Track width for current:** use an IPC-2152 calculator (Sierra Circuits and DigiKey
  have free ones). For 1 A on 1 oz outer copper with a 10 °C rise, IPC-2221 gives about
  0.3 mm. On this board, simply use 1–2 mm for every 24 V and ground path that carries LED
  current, and pours where possible.
* **Decoupling:** a 100 nF ceramic at every IC supply pin, placed before routing anything
  else, with its via to ground right beside it.
* **Placement before routing:** connectors on edges where the enclosure wants them, power
  input → protection → regulators → drivers in a line.
* **Clean return paths:** keep the bottom layer as unbroken ground. If a trace must run
  there, keep it short and perpendicular to the current flow above it.
* **Through-hole is fine.** For a few boards, through-hole parts and hand soldering are
  simpler than SMD assembly. This board is entirely through-hole.
* **Assembly aids if SMD parts are machine-placed:** three fiducials near the board corners,
  1 mm keep-out around them, and the fab's panel rules for rails and tooling holes.
* **Before ordering:** ERC and DRC clean, Gerbers inspected in a viewer (KiCad's own, or the
  vendor's online viewer), a 1:1 printout to check footprints against real parts, and the
  BOM checked against stock at the chosen supplier.
* **First run:** order the minimum (usually 5 boards). Expect a revision B; add pads for
  optional parts so mistakes can be bodged.

---

## 3. Where to order

### 3.1 Bare boards

| Vendor | Based in | Good for | Watch for |
|---|---|---|---|
| **JLCPCB** | China | Lowest board price, fast, in-house assembly from its own parts stock (LCSC) | Import duties for US buyers (see 3.4); assembly minimums |
| **PCBWay** | China | Widest range of options (flex, thick copper, special finishes), human review of assembly orders | Same import situation as JLCPCB |
| **OSH Park** | USA | Small US-made batches, ENIG finish standard, no customs | Bare boards only, no assembly; higher price, about 2–3 weeks lead time |
| **Aisler** | Germany | EU buyers avoiding customs, good quality | Costs more than the Chinese fabs, though less than OSH Park |
| **Advanced Circuits, Sunstone** | USA | Full-service US fabs, free DFM checks, quick turns | Priced for professional orders |

A 2025 Hackaday comparison shows the scale of the gap: a PCBWay order quoted about €26
delivered in 6–10 business days against $64 and 21 business days at OSH Park for the
same small board. Lcamtuf's hands-on comparison of hobby vendors is a good read on
quality differences.

### 3.2 Assembled boards

* **Hand assembly** suits a first batch of a few boards, especially if most parts are
  through-hole. Add a **stainless solder-paste stencil** to the board order if there are
  SMD parts (a few dollars from most fabs; OSH Stencils in the US also sells framed
  stencils). Paste, place with tweezers, then reflow on a hot plate.
* **JLCPCB assembly:** choose parts from its "basic" library where possible, since they
  carry no feeder fee. "Economic" assembly suits 2–50 boards with one assembled side and a
  setup fee around $8. "Extended" parts add a per-part loading fee; JLCPCB's pages
  disagree on the current amount, so check the quote. Some parts force the more expensive
  "Standard" assembly.
* **PCBWay assembly:** reportedly more flexible on very small quantities, with a human
  checking orders.
* **MacroFab (USA):** US-based assembly network for small runs, with no customs
  involved.

### 3.3 Components

* Buy from **authorized distributors**: Digi-Key, Mouser, Arrow, Farnell/Newark, RS. They
  buy directly from the manufacturer, so counterfeits are very unlikely.
* **LCSC** is JLCPCB's sister company and the natural source when JLCPCB assembles the
  board. It says it sells only genuine parts; that hasn't been independently verified,
  so prefer authorized stock for critical parts bought separately.
* Avoid marketplace sellers (Amazon third-party, eBay, AliExpress) for semiconductors. The
  inventory already notes that the IRFZ44Ns are marketplace parts that need testing before
  trusting their rating.
* Record the manufacturer part number and the distributor part number for every BOM line,
  plus one alternate. JLCPCB's tools want the LCSC number in a symbol field.

### 3.4 Import duties (US buyers)

As of 2026, the US de minimis exemption no longer covers goods from China. Every order,
including a $5 prototype, goes through a customs entry and attracts duty. Sources disagree
on the exact rate stack for PCBs (the base rate is free, with Section 301 tariffs on top;
figures quoted range from 12.5% to 25%). JLCPCB and PCBWay usually collect duty at checkout
for US delivery, so compare the **delivered total** at checkout, not the board price, against
OSH Park, which has no customs at all.

For EU buyers, Aisler avoids customs entirely; orders from China attract VAT and possibly
handling fees.

---

## 4. From this repository to the factory

1. `tools/pcb/design.py` is the circuit. Change it there (and the placement in
   `gen_pcb.py`, the drawing in `gen_sch.py`), then run
   `/usr/bin/python3 tools/pcb/build.py`. It regenerates the KiCad project and writes the
   Gerber zip only if every check passes.
2. Or open `hardware/tasklamp-driver/tasklamp-driver.kicad_pro` in KiCad and edit by hand.
   The footprints are linked to their schematic symbols, so *Update PCB from Schematic*
   works. Hand edits are overwritten the next time `build.py` runs, so pick one way.
3. Upload the zip, compare the vendor's preview with `hardware/tasklamp-driver/img/`, and
   order the minimum quantity first.
4. Tag the commit in this repo with the board revision you ordered.

For a board that a factory also assembles, the **Fabrication Toolkit** KiCad plugin writes
the BOM and placement files JLCPCB wants, and Bouni's **KiCad JLCPCB Tools** searches
JLCPCB's parts library inside KiCad. This board does not need either.

---

## 5. Still open

* **The enclosure.** The board's outline, hole pattern and connector edges were chosen
  without one. If the lamp's base cannot take 96.5 × 59 mm with USB on one long edge and
  the strip terminals on the other, the placement in `gen_pcb.py` is the thing to change.
* **The supply.** Its rating is not recorded anywhere in this repo. It needs 1.5 A or
  more at 24 V; enter 80 % of its rating as the firmware's power budget.
* **Where the boards are ordered from** decides how much import duty matters (3.4).

---

## Sources

* Vendor comparisons: [lcamtuf, *Comparing hobby PCB vendors*](https://lcamtuf.substack.com/p/comparing-hobby-pcb-vendors); [Hackaday, *An in-depth comparison of hobby PCB manufacturers* (2023)](https://hackaday.com/2023/10/13/an-in-depth-comparison-of-hobby-pcb-manufacturers); [Hackaday, *Does made in America make sense for PCB prototyping?* (2025)](https://hackaday.com/2025/07/06/does-made-in-america-make-sense-for-pcb-prototyping); [All About Circuits, choosing a PCB manufacturer](https://www.allaboutcircuits.com/technical-articles/guide-to-pcb-design-how-to-choose-a-pcb-manufacturer/)
* JLCPCB: [design guidance and capabilities](https://jlcpcb.com/blog/how-to-design-a-complete-pcb-layout-pcb-layout-engineer-must-know); [assembly pricing](https://jlcpcb.com/help/article/pcb-assembly-price); [assembly FAQ](https://jlcpcb.com/help/article/98-pcb-assembly-faqs); [metal-core PCBs](https://jlcpcb.com/pcb-fabrication/metal-core-pcb); [KiCad BOM/CPL export](https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad); [community cost-optimizing guide (Hack Club)](https://hwdocs.hackclub.dev/user-contrib-guides/jlc-cost-optimizing/)
* KiCad plugins: [Fabrication Toolkit](https://github.com/bennymeg/JLC-Plugin-for-KiCad); [KiCad JLCPCB Tools](https://github.com/Bouni/kicad-jlcpcb-tools)
* Tariffs: [OurPCB, PCB tariffs from China to the US in 2026](https://www.ourpcb.com/blog/china-us-pcb-tariffs-2026); [Plainfreight, US-China tariffs in 2026](https://plainfreight.com/guides/us-china-tariffs-2026); [de minimis suspension](https://www.importcostcalculator.com/de-minimis-800-rule.html)
* Grounding and layout: [Analog Devices, reducing ground bounce in DC-DC converters](https://www.analog.com/en/resources/analog-dialogue/articles/reducing-ground-bounce-in-dc-to-dc-converters.html); [Würth Elektronik, PCB layout optimization](https://www.we-online.com/files/pdf1/pcb-board-layout-optimization-v3.pdf); [Electronic Design, mixed-signal layout guidelines](https://www.electronicdesign.com/technologies/analog/article/21263439/analog-devices-basic-guidelines-for-mixedsignal-pcb-layout-design)
* Track width: [mbedded.ninja IPC-2152 calculator](https://ninjacalc.mbedded.ninja/calculators/electronics/pcb-design/track-current-ipc2152); [Sierra Circuits calculator](https://www.protoexpress.com/pcb/trace-width-calculator/)
* Input protection: [TI, reverse polarity protection (SSZTAP4)](https://ti.com/lit/pdf/ssztap4); [protection ordering example](https://industrialmonitordirect.com/blogs/knowledgebase/boat-control-panel-power-supply-protection-circuit-design)
* DFM and assembly: [Altium, PCB design review checklist](https://resources.altium.com/p/pcb-design-and-review-checklist); [Sierra Circuits, design-for-assembly checklist](https://www.protoexpress.com/blog/pcb-design-for-assembly-checklist-important-checks-for-layout-engineers/); [DigiKey, prototyping with solder stencils](https://www.digikey.com/en/blog/prototyping-with-solder-stencils); [All About Circuits, reflow with a stencil](https://www.allaboutcircuits.com/projects/reflow-soldering-its-so-much-easier-with-a-solder-paste-stencil/)
* Components: [Embedded Artistry, detecting counterfeit components](https://embeddedartistry.com/fieldatlas/detecting-counterfeit-electrical-components/); [Supply Chain Connect, authorized distributors](https://www.supplychainconnect.com/counterfeit/article/21263651/why-electronics-buyers-should-always-work-with-authorized-distributors)
* QT Py: [Adafruit QT Py RP2040 board files](https://github.com/adafruit/Adafruit-QT-Py-RP2040-PCB)
