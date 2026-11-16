# Parts to order for the driver board

Everything else on the board is already in the component inventory. This is one Digi-Key
order of about $17 before shipping, plus the circuit boards themselves from PCBWay
(see [`hardware/README.md`](../hardware/README.md)).

Stock and prices could not be checked live when this list was made (November 2026); the
figures come from search snapshots. Each line names an alternative that fits the same
holes, in case something is out of stock.

## The order

| Qty | Part | What it does | Link | About |
|---|---|---|---|---|
| 1 | Murata **OKI-78SR-5/1.5-W36-C** | Makes 5 V for the QT Py from the 24 V supply. A switching module with the pinout of a 7805, 7–36 V in, no heatsink | [Digi-Key](https://www.digikey.com/en/products/detail/murata-power-solutions-inc/OKI-78SR-5-1-5-W36-C/2259781) | $6.00 |
| 2 | Sullins **PPTC071LFBN-RC** | 1×7 sockets, so the QT Py plugs in and can be taken out | [Digi-Key](https://www.digikey.com/en/products/detail/sullins-connector-solutions/PPTC071LFBN-RC/810146) | $0.60 each |
| 1 | On Shore **OSTTC022162** | 2-way screw terminal, 5.08 mm: 24 V in | [Digi-Key](https://www.digikey.com/en/products/detail/on-shore-technology-inc/OSTTC022162/614558) | $0.70 |
| 1 | On Shore **OSTTC032162** | 3-way screw terminal: white strip | [Digi-Key](https://www.digikey.com/en/products/detail/on-shore-technology-inc/OSTTC032162/614559) | $1.00 |
| 1 | On Shore **OSTTC042162** | 4-way screw terminal: RGB strip | [Digi-Key](https://www.digikey.com/en/products/detail/on-shore-technology-inc/OSTTC042162/614560) | $1.50 |
| 1 | Keystone **3568** | Holder for a mini blade fuse | [Digi-Key](https://www.digikey.com/en/products/detail/keystone-electronics/3568/2137306) | $1.17 |
| 5 | Littelfuse **0297002.WXNV** | 2 A mini blade fuse: one to fit, four spare | [Digi-Key search](https://www.digikey.com/en/products/result?keywords=0297002.WXNV) | $0.35 each |
| 2 | Vishay **SB560-E3/54** | Schottky diode, 60 V 5 A. Stops a reversed supply from reaching anything. One to fit, one spare | [Digi-Key](https://www.digikey.com/en/products/detail/vishay-general-semiconductor-diodes-division/SB560-E3-54/1023532) | $0.60 each |
| 2 | Littelfuse **P6KE30A** | TVS diode. Clamps voltage spikes on the 24 V rail. One to fit, one spare | [Digi-Key](https://www.digikey.com/en/products/detail/littelfuse-inc/P6KE30A/285939) | $0.50 each |

## If a line is out of stock

| Part | Any of these fits the same footprint |
|---|---|
| 5 V converter | Traco **TSR 1-2450**, Recom **R-78K5.0-1.0**, CUI **VXO7805-1000**. Any "78xx replacement" switching module with pins IN-GND-OUT at 2.54 mm, rated for at least 28 V in and 0.5 A out |
| Screw terminals | Any 5.08 mm (0.2 in) pitch block with 2, 3 and 4 ways: Phoenix Contact **1715721**, **1715734**, **1715747** (MKDS 1,5 series); TE **282837-2**, **-3**, **-4** |
| Sockets | Any single-row 2.54 mm female header with 7 positions, or a longer one cut down |
| Fuse | Any **Mini (ATM)** blade fuse, 2 A, from a car-parts shop. Not the larger "ATO/ATC" size |
| Schottky | **SB540**, **SB550**, **1N5822**, **SR560**: any axial Schottky of 3 A or more and 40 V or more in a DO-201 body |
| TVS | **P6KE27A** to **P6KE33A**, or the larger **1.5KE30A** (its thicker leads also fit) |

## Already in the inventory

| Qty | Part | Where on the board |
|---|---|---|
| 5 | IRLB8721 MOSFET (Q-004) | Q1–Q5, one per colour |
| 6 | 1N5819 Schottky (D-002) | D1–D5 clamp diodes, D6 feed to the QT Py |
| 5 | 220 Ω resistor (R-006) | R1–R5 gate resistors |
| 5 | 100 kΩ resistor (R-014) | R6–R10 gate pull-downs |
| 2 | 100 µF 50 V electrolytic (C-044) | C1, C2 |
| 1 | 10 µF 50 V electrolytic (C-038) | C4 |
| 1 | 0.1 µF ceramic (C-021) | C5 |
| 8 pins | Male header strip (E-007) | J4, to the display and the encoder |
| 1 | QT Py RP2040, with its header pins | U1 |

## Worth having, not required

* **M3 standoffs and screws** (four) to mount the board. The holes are 3.2 mm, on a
  88.9 × 50.8 mm (3.5 × 2.0 in) rectangle.
* **Female-to-female jumper wires** (eight) for the run from J4 to the display and encoder,
  unless you solder those wires.
* A **24 V supply of 1.5 A (36 W) or more**, if the one you have is smaller. The lamp draws
  about 1.0 A with every channel at 100 %.

## Why these parts

* **A switching converter, not a 7805.** The inventory has no inductors, so nothing in it
  can make 5 V from 24 V efficiently. A 7805 would turn about 2 W into heat to deliver
  0.5 W, and need a heatsink. This module wastes about a tenth of a watt.
* **A fuse.** The board's copper is sized for the fuse, not for whatever the supply can
  deliver into a short.
* **The Schottky.** Screw terminals can be wired backwards once. The diode costs half a
  volt and half a watt; without it a reversed supply would destroy the converter and the
  capacitors.
* **The TVS.** Plugging in a live 24 V lead can ring well above 24 V for a moment. The TVS
  holds the rail down so the converter never sees more than it is rated for.
* **Sockets.** The QT Py is the one part worth being able to pull out: to reflash it away
  from the lamp, or to replace it.
