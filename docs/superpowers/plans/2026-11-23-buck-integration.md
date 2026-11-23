# Buck Converter Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Murata OKI-78SR module on the lamp driver board with the LMR33630 buck circuit from the `Branchy` branch (`hardware/buck-breakout`), set for 5 V, fed only from the board's 24 V input, then test it.

**Architecture:** The circuit stays generated from `tools/pcb/design.py`. The buck's parts replace U2 and its output capacitors C4/C5; the buck's hand-solder footprints are ported from `buck-breakout/gen/fplib.py` into `TaskLamp.pretty`; its IC-local layout (IC, input caps, boot and VCC caps, SW/BOOT/VCC/FB routing) is transplanted from `buck-breakout/gen/build_pcb.py`, with a smaller inductor and SMD feedback resistors so it fits the 46 × 14 mm band the module left. A top-layer ground pour with stitching vias carries the buck's ground to the bottom plane.

**Tech Stack:** KiCad 7 pcbnew Python API, kicad-cli, ngspice, gerbonara/shapely.

**Spec:** the user's request ("Integrate that circuit into our lamp pcb design. One 24 V input should be the only power input for this board. Test the circuit afterwards.") and `Branchy:hardware/buck-breakout/README.md` (5 V option).

## Global Constraints

- Only power input on the board: J1 (24 V). No input headers from the breakout. EN tied to VIN (datasheet: EN may go to VIN).
- 5 V setting: RFBT 100 kΩ, RFBB 24.9 kΩ 1 % (5.016 V), L 10 µH, COUT 4 × 22 µF 25 V X7R 1210, CIN 2 × 10 µF 50 V X7R 1210 + 220 nF, CBOOT 100 nF, CVCC 1 µF (values from `buck-breakout/gen/values.py` and its BOM).
- Inductor: Bourns SRP7028A-100M (10 µH, Isat 6 A > 5.05 A max current limit, 7.3 × 6.6 mm).
- Keep D6 so the QT Py's USB can never feed the buck's output.
- Board size, outline, holes, theme and every strip-switch position unchanged. Vias allowed only on GND.

## Review Focus

- Loop stability is not simulated (TI publishes no loop model): bench item, as in the breakout's README.
- SW node is a 24 V net: include it in the 24 V clearance test.
- Inductor land is drawn without the datasheet's land drawing to hand: report it as a check before ordering.
- Hand soldering an HSOIC-8 thermal pad: the back hole lets it be soldered from below; say so in the build steps.
- The 5 V test-pad reading changes (5.0 V regulated): update meter tables.

---

### Task 1: Circuit and footprints
**Files:** `tools/pcb/design.py`, `tools/pcb/gen_pcb.py` (footprint writers), `tools/pcb/gen_sch.py` (5 V section), `tools/pcb/build.py` (BOM order incl. L).
- [ ] Replace U2/C4/C5 in `design.py` with U2 LMR33630ADDA, L1, C3–C11, R11–R12; nets SW, BOOT, VCC, FB.
- [ ] Port `fp_ic`, `fp_c1210`, `fp_c0805_1206`, `fp_c_dual` and a 7 mm inductor land into `TaskLamp.pretty`.
- [ ] Redraw the schematic's 5 V section; `build.py` schematic parity passes.

### Task 2: Layout
**Files:** `tools/pcb/gen_pcb.py`, `tools/pcb/check.py`.
- [ ] Place the buck block (IC centre 25.4, 14.45), lower the four PWM lanes by 1.6 mm, move D6/TP1/TP2, reroute QT_5V.
- [ ] Top GND pour, VOUT pour, GND island, stitching vias (0.8/0.4 mm); `geometry_facts` allows GND vias only.
- [ ] `build.py`: board parity, DRC 0, planted faults caught, drill read-back.

### Task 3: Tests
**Files:** `tools/sim/run.py`, `tools/pcb/test_board.py`.
- [ ] Simulation: power stage of the buck at 24 V in (ripple, peak vs current limit, output ripple, efficiency, input-cap current) for 0.1, 0.5 and 3 A; update T1/T5/T7/T10 converter models.
- [ ] Board tests: footprints for SMD parts, SW/BOOT in the 24 V clearance set, pinout check for the LMR33630.
- [ ] Both suites pass.

### Task 4: Docs, booklet, commit
- [ ] Renders, booklet (SMD step first), READMEs, parts list, test report; commit and push.
