# PCB planning notes

Research for when the task lamp's driver stage moves from breadboards to a printed
circuit board. **Nothing here is a layout yet**: the circuit still has additions to come.
These notes collect what to decide, what to watch for, and where to order, so the PCB
work can start quickly once the schematic is frozen.

Compiled November 2026. Prices, fees and tariffs change often; every number below is a
starting point to re-check on the vendor's live quote page.

---

## 1. Decisions the PCB forces on this design

These came out of reviewing the current revision 2 circuit against PCB practice. They are
worth settling in the schematic before any layout starts.

### 1.1 MOSFET voltage rating

The IRLB8721 is a **30 V** part on a **24 V** bus. That is fine on a breadboard with a
regulated supply, but it leaves no room for the protection a PCB should have: a TVS diode
sized for a 24 V supply (standoff about 26–28 V) clamps at roughly 40–45 V during a surge,
well above 30 V. For the PCB, choose **40–60 V** logic-level MOSFETs for all five channels
so the TVS can actually protect them.

### 1.2 Linear-mode MOSFETs for the RGB sinks

The RGB sinks run their MOSFETs partly on, dissipating 0.45–0.65 W each continuously.
Modern high-density trench MOSFETs (the IRLB8721 is one) are optimised for switching and
can suffer **thermal instability in linear mode**, known as the Spirito effect: current
crowds into hot spots on the die at high V<sub>DS</sub> and low current, exactly where these
sinks operate (9–13 V, 50 mA).

* When choosing the PCB part, look at the datasheet **SOA graph's DC line** at 15 V and
  check 0.1 A is comfortably inside it. Parts marketed for "linear mode" or "hot swap" have
  this line drawn honestly; many switching MOSFETs omit DC or extrapolate it.
* Older planar MOSFETs, or a small bipolar transistor in place of the MOSFET, handle linear
  operation better at these low currents.
* The source resistor (the 50 Ω sense) is the feedback the onsemi note says linear MOSFETs
  need, so the topology itself is sound.

### 1.3 The LM3414 becomes practical

The breadboard needed SOIC adapter boards for the LM3414 (SO PowerPAD-8, exposed pad =
PGND). A PCB removes that obstacle, so the full-power RGB option is mostly a matter of
buying three inductors. If the PCB will use the LM3414s:

* Follow the layout section of the TI datasheet (SNVS678F, section 10 and its layout
  figure). TI's own key point: place R<sub>FS</sub> and R<sub>IADJ</sub> right at the FS and IADJ pins.
* Solder the exposed pad to a ground pour, with an array of small vias (0.3 mm) to a
  bottom-side pour. TI's rule of thumb: one via is about 100 °C/W, ten or more in parallel
  is about 10 °C/W.
* Keep the **hot loop** tiny: VIN capacitor, LM3414 VIN/PGND, Schottky diode and LX node
  within a few millimetres, on one side, over unbroken ground.
* Decide early whether the linear sinks stay as a fallback on the same board
  (footprint options) or are replaced outright. Footprint options cost little.

### 1.4 Input protection

The breadboard has none. Standard order for a 24 V input, from the connector inwards:

1. **Fuse** (or PPTC), sized above normal draw: the lamp draws about 1.5 A at most.
2. **TVS diode** after the fuse, so a TVS that fails short blows the fuse. Standoff
   above the supply's highest normal output.
3. **Reverse-polarity protection.** A P-channel MOSFET in the + line with a 12 V zener
   clamping its gate is the simple version. An ideal-diode controller with an N-MOSFET
   (TI LM74700 family) wastes less and also blocks reverse current.
4. Bulk capacitance.

### 1.5 Grounding on one board

On two breadboards, ground discipline was mostly about keeping strip current off the
breadboard. On a PCB:

* Use **one solid ground plane** on the bottom layer, with no analog/digital split.
  Analog Devices' and Würth's guidance agrees that a single plane plus careful placement
  beats split planes for a design like this.
* Route the **strip return current** (about 1 A) straight from the strip connector to the
  MOSFET sources and on to the input connector's ground, through wide copper, away from
  the LM324 and sense resistors.
* Give each **sense resistor a Kelvin connection**: the op-amp's feedback trace leaves
  from the resistor's pad, not from a point along the current path. Take the LM324's
  ground pin to the same point where the three sense resistors return to ground. The
  booklet already asks for this on the breadboard.
* Keep plane cuts to short perpendicular crossings. Return current flows directly under
  its trace, and a slot forces it around.

### 1.6 Heat

* **Linear sinks:** about 2 W total on a small board. A TO-220 standing in free air runs
  around 40 °C above ambient at 0.65 W. An SMD part (DPAK/D2PAK) needs copper: TI's figures
  for a TO-263 package are about 50 °C/W with 0.5 in² of copper and 37 °C/W with 1 in². Plan
  roughly 1 in² of top and bottom copper per sink, stitched with vias. Keep the sinks away
  from the LM324 and the QT Py.
* **Strip MOSFETs:** fully on, they dissipate milliwatts, so no heat measures are needed.
* **RGB stars:** they need an aluminium heatsink whichever driver is used. If custom LED
  boards are ever made, aluminium-core PCBs (MCPCB) are a stock option at JLCPCB and
  others. JLCPCB rates its 1 W/m·K aluminium board for low-power LEDs; for 3 W stars, look
  for a 2–3 W/m·K dielectric.

### 1.7 Connectors and the QT Py

* **QT Py:** mount it on **female headers** rather than soldering it flat, so it can be
  removed for reprogramming or replacement. Its castellated pads allow flat mounting, but
  only commit to that once the design is final. The QT Py shares the Seeed Xiao footprint
  (2 × 7 pads at 0.1 in, rows 0.675 in apart), so a KiCad Xiao footprint is a starting
  point. Check its pad positions against Adafruit's drawing before ordering.
* **Encoder and display:** keep the STEMMA QT cable and the TFT on connectors, so they can
  be mounted where the enclosure wants them.
* **24 V input and strip:** the strip draws about 1 A, so a JST XH (3 A per pin) is
  adequate for the strip leads. JST VH (up to 10 A, derated in multi-pin housings) or a
  5 mm screw terminal suits the 24 V input. Use **different, keyed connectors** for
  input and outputs so nothing can be plugged into the wrong place.
* **RGB stars:** one keyed connector carrying all six string wires (three +, three −) is
  tidier than loose wires.

### 1.8 Make the bring-up checks easy

The booklet's check cards and meter-readings card list every node worth measuring. On the
PCB, give each of those a **labelled test point**: the 12 V and 24 V rails, each op-amp
output, each sense resistor and each pot wiper. A 1 mm pad is enough for a probe tip. Also
plan:

* a jumper or 0 Ω link in each LED channel's path, to isolate a channel without
  desoldering;
* the three current-set pots reachable from above, or replaced by fixed resistors once
  you've settled on currents;
* board name, revision and date on the silkscreen.

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
  input → protection → regulators → drivers in a line, the noisy and hot parts away from
  the op-amp.
* **Clean return paths:** keep the bottom layer as unbroken ground. If a trace must run
  there, keep it short and perpendicular to the current flow above it.
* **Through-hole is fine.** For a few boards, through-hole parts and hand soldering are
  simpler than SMD assembly. Use SMD only where it earns its place (LM3414, possibly
  MOSFETs on copper pours).
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

## 4. KiCad to factory workflow

1. Schematic in KiCad, with manufacturer and supplier part numbers as symbol fields.
2. ERC, then layout with the vendor's DRC rules loaded.
3. Export with the **Fabrication Toolkit** plugin (installed from KiCad's Plugin and
   Content Manager), which JLCPCB recommends. It writes Gerbers, drill files, the BOM and
   the placement (CPL) file in one go. Bouni's **KiCad JLCPCB Tools** plugin adds a search
   of JLCPCB's parts library inside KiCad.
4. Upload the Gerber zip, check the vendor's viewer render, and for assembly upload
   `bom.csv` and `positions.csv`. Check every part's rotation in the vendor's placement
   preview before paying: a rotated IC or diode is the most common assembly mistake.
5. Tag the commit in this repo with the board revision you ordered.

---

## 5. Open questions before layout

* **Where are you based?** It decides the vendor shortlist and how much duty matters.
* Which additions are still coming, and do they add parts to the board (more connectors,
  sensors, a buck converter for logic power)?
* RGB drivers on the PCB: linear sinks, LM3414 bucks, or footprints for both?
* Through-hole, SMD, or mixed? This decides hand assembly versus factory assembly.
* Will the board live inside the lamp's enclosure? Its size, mounting holes and connector
  positions come from the enclosure, so a rough enclosure sketch should come first.

---

## Sources

* Vendor comparisons: [lcamtuf, *Comparing hobby PCB vendors*](https://lcamtuf.substack.com/p/comparing-hobby-pcb-vendors); [Hackaday, *An in-depth comparison of hobby PCB manufacturers* (2023)](https://hackaday.com/2023/10/13/an-in-depth-comparison-of-hobby-pcb-manufacturers); [Hackaday, *Does made in America make sense for PCB prototyping?* (2025)](https://hackaday.com/2025/07/06/does-made-in-america-make-sense-for-pcb-prototyping); [All About Circuits, choosing a PCB manufacturer](https://www.allaboutcircuits.com/technical-articles/guide-to-pcb-design-how-to-choose-a-pcb-manufacturer/)
* JLCPCB: [design guidance and capabilities](https://jlcpcb.com/blog/how-to-design-a-complete-pcb-layout-pcb-layout-engineer-must-know); [assembly pricing](https://jlcpcb.com/help/article/pcb-assembly-price); [assembly FAQ](https://jlcpcb.com/help/article/98-pcb-assembly-faqs); [metal-core PCBs](https://jlcpcb.com/pcb-fabrication/metal-core-pcb); [KiCad BOM/CPL export](https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad); [community cost-optimizing guide (Hack Club)](https://hwdocs.hackclub.dev/user-contrib-guides/jlc-cost-optimizing/)
* KiCad plugins: [Fabrication Toolkit](https://github.com/bennymeg/JLC-Plugin-for-KiCad); [KiCad JLCPCB Tools](https://github.com/Bouni/kicad-jlcpcb-tools)
* Tariffs: [OurPCB, PCB tariffs from China to the US in 2026](https://www.ourpcb.com/blog/china-us-pcb-tariffs-2026); [Plainfreight, US-China tariffs in 2026](https://plainfreight.com/guides/us-china-tariffs-2026); [de minimis suspension](https://www.importcostcalculator.com/de-minimis-800-rule.html)
* LM3414: [TI datasheet, layout section](https://www.ti.com/document-viewer/LM3414/datasheet/layout)
* Thermal: [TI SLPA015, thermal vias](https://ti.com/lit/pdf/slpa015); [TI LM2576 datasheet, TO-263 θJA vs copper area](https://ti.com/document-viewer/LM2576/datasheet/GUID-876257A8-0F2C-47A8-8165-340E871DD683); [Electronic Design, MOSFET cooling with thermal vias](https://www.electronicdesign.com/technologies/thermal-management/article/21188672/enhance-mosfet-cooling-with-thermal-vias); [MPS, thermally optimized two-layer PCB](https://media.monolithicpower.com/mps_cms_document/a/-/a-thermally-optimized-two-layer-auto-pcb_r1.0.pdf)
* Linear-mode MOSFETs: [Nexperia, power MOSFETs in linear mode](https://www.nexperia.com/applications/interactive-app-notes/IAN50006_Power_MOSFETs_in_linear_mode); [onsemi AN-4161](https://onsemi.com/pub/collateral/an-4161.pdf); [Electronic Design, the Spirito effect](https://www.electronicdesign.com/technologies/power/article/21795492/the-spirito-effect-improved-my-designand-i-didnt-even-know-it)
* Grounding and layout: [Analog Devices, reducing ground bounce in DC-DC converters](https://www.analog.com/en/resources/analog-dialogue/articles/reducing-ground-bounce-in-dc-to-dc-converters.html); [Würth Elektronik, PCB layout optimization](https://www.we-online.com/files/pdf1/pcb-board-layout-optimization-v3.pdf); [Electronic Design, mixed-signal layout guidelines](https://www.electronicdesign.com/technologies/analog/article/21263439/analog-devices-basic-guidelines-for-mixedsignal-pcb-layout-design)
* Current sensing: [Analog Devices, shunt pad layout](https://www.analog.com/en/resources/analog-dialogue/articles/optimize-high-current-sensing-accuracy.html); [Stackpole, Kelvin layout](https://stackpole-europe-website.pages.dev/article-kelvin-layout)
* Track width: [mbedded.ninja IPC-2152 calculator](https://ninjacalc.mbedded.ninja/calculators/electronics/pcb-design/track-current-ipc2152); [Sierra Circuits calculator](https://www.protoexpress.com/pcb/trace-width-calculator/)
* Input protection: [TI, reverse polarity protection (SSZTAP4)](https://ti.com/lit/pdf/ssztap4); [protection ordering example](https://industrialmonitordirect.com/blogs/knowledgebase/boat-control-panel-power-supply-protection-circuit-design)
* DFM and assembly: [Altium, PCB design review checklist](https://resources.altium.com/p/pcb-design-and-review-checklist); [Sierra Circuits, design-for-assembly checklist](https://www.protoexpress.com/blog/pcb-design-for-assembly-checklist-important-checks-for-layout-engineers/); [DigiKey, prototyping with solder stencils](https://www.digikey.com/en/blog/prototyping-with-solder-stencils); [All About Circuits, reflow with a stencil](https://www.allaboutcircuits.com/projects/reflow-soldering-its-so-much-easier-with-a-solder-paste-stencil/)
* Components: [Embedded Artistry, detecting counterfeit components](https://embeddedartistry.com/fieldatlas/detecting-counterfeit-electrical-components/); [Supply Chain Connect, authorized distributors](https://www.supplychainconnect.com/counterfeit/article/21263651/why-electronics-buyers-should-always-work-with-authorized-distributors)
* Connectors and QT Py: [JST XH datasheet (DigiKey)](https://www.digikey.be/en/resources/datasheets/jst/xh-connector); [JST VH datasheet](https://www.mouser.lt/datasheet/3/1070/1/eVH.pdf); [Adafruit QT Py ESP32-S3 PCB (Xiao-compatible footprint)](https://github.com/adafruit/Adafruit-QT-Py-ESP32-S3-PCB)
