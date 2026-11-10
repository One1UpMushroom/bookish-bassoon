"""Static pieces of the build booklet: styles, cover, checks and reference."""

CSS = r"""
/* Layout: one column of step cards, each with a parts box beside (or above) a plan view of the board.
   Pale instruction-page ground, a yellow title band, heavy rounded numerals. */
:root {
  --paper: #C9DFEE; --card: #E8F2F9; --box: #FFFFFF; --box-line: #0E1D2B;
  --tray: #FFFFFF; --tray-ink: #0E1D2B; --tray-muted: #446075; --tray-line: #0E1D2B;
  --ink: #0E1D2B; --muted: #446075; --rule: #A5C1D5;
  --band: #FFD500; --band-ink: #141414; --accent: #C8102E; --new: #FF5A1F;
  --check: #FFE873; --check-ink: #1D1700; --check-line: #0E1D2B; --ok: #156C38; --stop: #B3261E;
  --display: "Rubik", "Arial Rounded MT Bold", "Helvetica Neue", system-ui, sans-serif;
  --body: "Nunito Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #0A141D; --card: #12222F; --box: #1B3142; --box-line: #7C9AB1;
    --tray: #D5E3EE; --tray-ink: #0E1D2B; --tray-muted: #3D586C; --tray-line: #7C9AB1;
    --ink: #E4EEF6; --muted: #9AB3C6; --rule: #2B465B;
    --band: #FFD500; --band-ink: #141414; --accent: #FF7468; --new: #FF6A2B;
    --check: #332A00; --check-ink: #FFE98A; --check-line: #C7AB1B; --ok: #62D08C; --stop: #FF8A80;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --paper: #0A141D; --card: #12222F; --box: #1B3142; --box-line: #7C9AB1;
  --tray: #D5E3EE; --tray-ink: #0E1D2B; --tray-muted: #3D586C; --tray-line: #7C9AB1;
  --ink: #E4EEF6; --muted: #9AB3C6; --rule: #2B465B;
  --band: #FFD500; --band-ink: #141414; --accent: #FF7468; --new: #FF6A2B;
  --check: #332A00; --check-ink: #FFE98A; --check-line: #C7AB1B; --ok: #62D08C; --stop: #FF8A80;
  color-scheme: dark;
}
body { background: var(--paper); color: var(--ink); font-family: var(--body); font-size: 16px; line-height: 1.5; }
.defs { position: absolute; width: 0; height: 0; overflow: hidden; }
.page {
  max-width: 820px; margin: 0 auto;
  padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px));
  padding-block: 20px 72px; display: grid; gap: 18px;
}
h1, h2, h3 { font-family: var(--display); margin: 0; line-height: 1.1; text-wrap: balance; }
h1 { font-weight: 800; font-size: clamp(30px, 7.4vw, 50px); letter-spacing: -.01em; }
h2 { font-weight: 800; font-size: clamp(22px, 5vw, 30px); }
h3 { font-weight: 600; font-size: 19px; }
p { margin: 0; max-width: 64ch; }
a { color: var(--accent); }
:focus-visible { outline: 3px solid var(--new); outline-offset: 2px; }
.mono { font: 500 13px/1.45 var(--mono); }
.where { font: 600 11.5px/1 var(--mono); letter-spacing: .07em; text-transform: uppercase; color: var(--muted); }

/* cover */
.cover { border-radius: 16px; overflow: hidden; background: var(--card); }
.band { background: var(--band); color: var(--band-ink); padding: 18px 18px 16px; display: grid; gap: 10px; }
.band .where { color: var(--band-ink); opacity: .75; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chips span { background: var(--band-ink); color: var(--band); border-radius: 999px; padding: 4px 12px; font: 600 13px/1.4 var(--display); }
.chips b { font-weight: 800; }
.hero { padding: 14px 10px 10px; }
.lede { padding: 4px 18px 18px; font-size: 17px; }

.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.facts > div { background: var(--card); border-radius: 14px; padding: 14px 16px; display: grid; gap: 4px; align-content: start; min-width: 0; }
.facts .v { font: 800 21px/1.15 var(--display); }
.facts p { font-size: 14.5px; color: var(--muted); }

.bags { display: flex; flex-wrap: wrap; gap: 8px; }
.bags a { display: inline-flex; align-items: center; gap: 8px; text-decoration: none; color: var(--ink); background: var(--card); border-radius: 999px; padding: 5px 14px 5px 5px; font: 600 14px/1.2 var(--display); }
.bags b { background: var(--band); color: var(--band-ink); width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; font-weight: 800; }

section.sheet { background: var(--card); border-radius: 16px; padding: 18px; display: grid; gap: 14px; min-width: 0; }
.legend { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px 18px; }
.legend > div { display: grid; grid-template-columns: 44px 1fr; gap: 10px; align-items: start; font-size: 14.5px; min-width: 0; }
.legend .sw { width: 44px; height: 30px; border-radius: 8px; display: grid; place-items: center; font: 600 12px var(--mono); }
.sw.new { border: 4px solid var(--new); }
.sw.old { background: #F4F0E6; color: #8a8372; }
.sw.hole { background: #F4F0E6; color: #3A3A36; }
.sw.rail { background: linear-gradient(90deg, #D9342B 0 50%, #2B62D9 50% 100%); }
.sw.stop { background: var(--check); color: var(--check-ink); border: 2px solid var(--check-line); }

/* bag headers */
.bag { display: flex; align-items: center; gap: 14px; margin-top: 22px; scroll-margin-top: 12px; }
.bagno { flex: none; width: 58px; height: 58px; border-radius: 14px; background: var(--band); color: var(--band-ink); display: grid; place-items: center; font: 800 32px/1 var(--display); }
.bag div { display: grid; gap: 5px; }

/* steps */
.step { background: var(--card); border-radius: 16px; padding: 16px; display: grid; gap: 14px; min-width: 0; scroll-margin-top: 12px; }
.step > header { display: flex; align-items: center; gap: 14px; }
.num { font: 800 56px/0.9 var(--display); letter-spacing: -.03em; }
.ttl { display: grid; gap: 5px; min-width: 0; }
.done { margin-left: auto; display: inline-flex; align-items: center; gap: 7px; font: 600 13px/1 var(--display); color: var(--muted); cursor: pointer; padding: 6px 10px; border: 2px solid var(--rule); border-radius: 999px; }
.done input { width: 18px; height: 18px; margin: 0; accent-color: var(--ok); }
.step.is-done { opacity: .62; }
.step.is-done .done { color: var(--ok); border-color: var(--ok); }
.cols { display: grid; gap: 14px; min-width: 0; }
.side { display: grid; gap: 12px; align-content: start; min-width: 0; }
.main { min-width: 0; display: grid; gap: 10px; }
@media (min-width: 740px) { .cols { grid-template-columns: 236px 1fr; align-items: start; } }

.need { background: var(--tray); color: var(--tray-ink); border: 2px solid var(--tray-line); border-radius: 14px; padding: 10px 12px; display: grid; grid-template-columns: repeat(auto-fill, minmax(138px, 1fr)); gap: 10px 14px; }
.need.all { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); }
.pc { display: grid; grid-template-columns: auto 1fr; align-items: center; column-gap: 8px; row-gap: 1px; min-width: 0; }
.pc svg { grid-row: 1 / span 3; }
.pc b { font: 800 17px/1 var(--display); }
.pc span { font-size: 13.5px; line-height: 1.25; }
.pc .inv { font: 500 11px/1.3 var(--mono); color: var(--tray-muted); }
.ic-s { width: 54px; height: 19px; } .ic-m { width: 40px; height: 40px; } .ic-t { width: 26px; height: 45px; }
.ic-d { width: 30px; height: 50px; } .ic-p { width: 46px; height: 50px; }

.tip { background: var(--tray); color: var(--tray-ink); border-radius: 14px; padding: 8px 10px; display: grid; grid-template-columns: 96px 1fr; gap: 10px; align-items: center; }
.tip p { font-size: 13px; line-height: 1.35; }
.ins { width: 96px; height: auto; display: block; }
.tip.wide { grid-template-columns: 1fr; justify-items: center; }
.tip.wide .ins { width: 190px; }

.plate { margin: 0; min-width: 0; }
.plate.scroll { overflow-x: auto; }
.bb { display: block; width: 100%; height: auto; max-width: 500px; margin-inline: auto; }
.bb.ov { max-width: 780px; }
.plate.scroll .bb { min-width: 660px; }
.old { opacity: .38; }
.hl { stroke: var(--new); stroke-linecap: round; }
.hf { fill: var(--new); fill-opacity: .2; stroke: var(--new); stroke-width: 3.5; }
.bn { font: 500 6.2px var(--mono); fill: #A39C86; }
.bl { font: 600 9.5px var(--mono); fill: #6A6451; }
.bp { font: 700 11px var(--mono); fill: #D9342B; } .bm { font: 700 11px var(--mono); fill: #2B62D9; }
.pl { font: 700 8.5px var(--body); fill: #FFFFFF; } .pm { font: 800 13px var(--body); fill: #22315C; }
.ic { font: 600 8.5px var(--mono); fill: #C9CED3; } .pk { font: 700 9.5px var(--mono); fill: #1E242B; }
.tg { fill: #FFFFFF; stroke: #14181D; stroke-width: 1.2; } .tt { font: 700 9.5px var(--mono); fill: #14181D; }
.bd { fill: #14181D; stroke: #FFFFFF; stroke-width: 1.4; } .bt { font: 800 9px var(--display); fill: #FFFFFF; }
.bt2 { font: 800 15px var(--display); fill: var(--ink); }
.it { font: 600 9px var(--body); fill: #E9ECEF; } .it2 { font: 700 10px var(--mono); fill: #1E242B; }
.iq { font: 600 10px var(--mono); fill: var(--tray-ink); }

.put { list-style: none; margin: 0; padding: 0; display: grid; gap: 7px; }
.put li { display: grid; grid-template-columns: 22px minmax(84px, max-content) 1fr; gap: 9px; align-items: baseline; font-size: 14.5px; min-width: 0; }
.k { width: 22px; height: 22px; border-radius: 50%; background: var(--ink); color: var(--card); display: grid; place-items: center; font: 800 12px/1 var(--display); align-self: center; }
.what { font-weight: 700; }
.hint { color: var(--muted); font-size: 14.5px; }

/* stop-and-check cards */
.check { background: var(--check); color: var(--check-ink); border: 2px solid var(--check-line); border-radius: 16px; padding: 16px; display: grid; gap: 12px; min-width: 0; }
.check > header { display: flex; align-items: center; gap: 12px; }
.check .stopno { flex: none; width: 46px; height: 46px; border-radius: 50%; border: 3px solid currentColor; display: grid; place-items: center; font: 800 20px/1 var(--display); }
.check .where { color: inherit; opacity: .8; }
.check ol { margin: 0; padding-left: 22px; display: grid; gap: 9px; font-size: 15px; }
.check li { max-width: 66ch; }
.read { font: 600 13px/1 var(--mono); border: 2px solid currentColor; border-radius: 6px; padding: 2px 6px; white-space: nowrap; }
.check .tablewrap { background: transparent; border-color: currentColor; }
.check th { background: transparent; color: inherit; } .check td, .check th { border-color: currentColor; }

.tablewrap { overflow-x: auto; border: 2px solid var(--rule); border-radius: 12px; background: var(--box); }
table { border-collapse: collapse; width: 100%; font-size: 14.5px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 8px 12px; vertical-align: top; border-bottom: 1px solid var(--rule); }
tr:last-child td { border-bottom: 0; }
th { font: 600 11.5px/1.3 var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--muted); white-space: nowrap; }
td.was { color: var(--muted); }

figure.schem { margin: 0; border: 2px solid var(--rule); border-radius: 12px; background: var(--box); min-width: 0; }
.scroll { overflow-x: auto; padding: 12px 8px 2px; }
figure.schem svg { display: block; width: 100%; min-width: 620px; height: auto; color: var(--ink); }
figcaption { border-top: 1px solid var(--rule); padding: 9px 14px 11px; font-size: 14px; color: var(--muted); }
figcaption b { color: var(--ink); }
.sch line, .sch polyline, .sch path { stroke: currentColor; stroke-width: 1.6; fill: none; stroke-linecap: round; stroke-linejoin: round; }
.sch .sig { stroke: var(--accent); }
.sch rect.r { fill: var(--box); stroke: currentColor; stroke-width: 1.6; }
.sch rect.box { fill: var(--card); stroke: currentColor; stroke-width: 1.4; }
.sch polygon { fill: var(--box); stroke: currentColor; stroke-width: 1.6; stroke-linejoin: round; }
.sch polygon.solid, .sch circle.dot { fill: currentColor; stroke: none; }
.sch text { fill: currentColor; font: 500 12px var(--mono); stroke: none; }
.sch text.lbl { fill: var(--muted); font-size: 11.5px; }
.sch text.pin { fill: var(--muted); font-size: 10.5px; }
.sch text.ttl { font: 600 14px var(--display); }
.sch .thick { stroke-width: 3; }
ul.plain { margin: 0; padding-left: 20px; display: grid; gap: 6px; max-width: 66ch; }
.two { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
.two > * { min-width: 0; }
@media (prefers-reduced-motion: no-preference) { .step { transition: opacity .2s; } }
"""

HEAD = """<title>Task Lamp Driver Build</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=Nunito+Sans:wght@400;600;700&family=Rubik:wght@600;800&display=swap">
<style>{css}</style>
<svg class="defs" aria-hidden="true" focusable="false"><defs>{defs}</defs></svg>

<div class="page">

<header class="cover">
  <div class="band">
    <span class="where">Build booklet · driver stage · revision 2</span>
    <h1>Task Lamp Driver Build</h1>
    <div class="chips"><span><b>5</b> channels</span><span><b>{comp}</b> parts</span><span><b>{total}</b> steps</span><span><b>2</b> breadboards</span><span><b>24 V</b></span></div>
  </div>
  <figure class="plate hero">{cover}</figure>
  <p class="lede">Everything on these two boards comes from your inventory. The strip runs at full power. The RGB stars run at up to 66 mA per colour, which the circuit cannot exceed whatever the pots or a loose wire do.</p>
</header>

<div class="facts">
  <div><span class="where">Strip, 1.6 m · WW + CW</span><span class="v">Full power</span><p>One IRLB8721 per channel, driven straight from the QT Py pin. Four parts each.</p></div>
  <div><span class="where">RGB stars · R, G, B</span><span class="v">0–66 mA each</span><p>LM324 current sinks. Full 310 mA needs the LM3414 version at the end.</p></div>
  <div><span class="where">Not in the inventory</span><span class="v">24 V ≥ 3 A supply</span><p>Class 2, with a screw-terminal jack. Plus a second half-size breadboard and 22 AWG wire.</p></div>
</div>

<nav class="bags" aria-label="Bags">{nav}<a href="#reference"><b>i</b>Why it changed</a></nav>

{before}

<section class="sheet">
  <span class="where">Parts for both boards</span>
  <h2>What goes in</h2>
  {partlist}
  <p class="hint">The codes are the IDs in your inventory sheet. Check each resistor with a meter before it goes in: brown, red and orange bands are easy to mix up on blue bodies. Wire links are 0.1 in staples bent from a resistor leg offcut.</p>
</section>

{steps}

{reference}

</div>
{script}
"""

BEFORE = """<section class="sheet">
  <span class="where">Before bag 1</span>
  <h2>How to read the pictures</h2>
  <div class="legend">
    <div><span class="sw hole">c7</span><span><b>Holes have names.</b> Column letter, then row number, as printed on the board. Rows 1–30, columns a–e on the left, f–j on the right.</span></div>
    <div><span class="sw new"></span><span><b>Orange outline:</b> add this now. Each new piece has a letter that matches the list under the picture.</span></div>
    <div><span class="sw old">old</span><span><b>Faded:</b> already on the board from earlier steps.</span></div>
    <div><span class="sw rail"></span><span><b>Rails:</b> go by the red + and blue − lines on your board, not by which side they are drawn on. Any hole on a rail is the same connection. If your rails have gaps, use the nearest hole.</span></div>
    <div><span class="sw stop">!</span><span><b>Yellow cards:</b> stop and measure before going on.</span></div>
    <div><span class="sw hole">▮</span><span><b>Printed sides face column a.</b> Every MOSFET and the regulator sit the same way round, with the metal tab toward column j. Tabs are live: keep them apart.</span></div>
  </div>
  <p class="hint">Unplug the 24 V supply before you move any wire. Board A's red rails carry 24 V and Board B's carry 12 V, so the two red rails are never joined to each other.</p>
</section>"""

CHECK1 = """<article class="check" id="check-1">
  <header><span class="stopno">!</span><div><span class="where">Stop and check · no LEDs connected yet</span><h3>First power-up</h3></div></header>
  <p>Plug the QT Py into USB, then plug in the 24 V supply. On the lamp choose <b>Menu ▸ Mode ▸ Mixer</b>, then in <b>Menu ▸ Adjust</b> set Brightness to 100%. Measure with the black probe on a blue rail.</p>
  <ol>
    <li><b>Nothing gets warm</b> in the first minute. If something does, unplug and look at the diode and capacitor stripes first.</li>
    <li>Board A red rail: <span class="read">23–25.5 V</span> Board B red rail: <span class="read">11.5–12.5 V</span></li>
    <li><b>Strip gates.</b> Warm at 100%: the resistor leg in A·c6 reads <span class="read">3.1–3.3 V</span> Warm at 0%: <span class="read">0 V</span> Same for Cool at A·h12.</li>
    <li><b>Set the RGB currents now, with nothing to damage.</b> Red at 100%: measure the resistor leg in B·a14 (op-amp pin 3) and turn the red pot until it reads <span class="read">2.50 V</span> That presets 50 mA. Do the same for Green at B·a16 and Blue at B·j16. The pot cannot go past 3.3 V, which is 66 mA.</li>
    <li><b>Op-amp alive.</b> With Red at 100% the resistor leg in B·c12 (pin 1) reads <span class="read">10–11 V</span> and at 0% <span class="read">under 0.1 V</span> Same for Green at B·c18 and Blue at B·h18.</li>
    <li><b>Fail-safe.</b> Unplug the QT Py's USB cable. Both strip gates must read <span class="read">0 V</span></li>
  </ol>
  <div class="tablewrap"><table>
    <thead><tr><th>Pin 3 / 5 / 10 reads</th><th>1.0 V</th><th>1.5 V</th><th>2.0 V</th><th>2.5 V</th><th>3.0 V</th><th>3.3 V</th></tr></thead>
    <tbody><tr><td>LED current</td><td>20 mA</td><td>30 mA</td><td>40 mA</td><td>50 mA</td><td>60 mA</td><td>66 mA</td></tr></tbody>
  </table></div>
</article>"""

CHECK2 = """<article class="check" id="check-2">
  <header><span class="stopno">!</span><div><span class="where">Stop and check · strip connected</span><h3>Is 3.3 V enough for your MOSFET?</h3></div></header>
  <ol>
    <li>Warm at 100%, Cool at 0%: the strip lights warm. Swap them: it lights cool.</li>
    <li>With Warm at 100%, measure across the warm MOSFET: red probe on the diode leg in A·a7, black probe on the thick wire in A·a8. <span class="read">under 0.10 V</span> means it is fully on. Above 0.3 V, swap in another IRLB8721. You have 19.</li>
    <li>Repeat for Cool between A·j13 and A·j14.</li>
    <li>If your meter has a 10 A range, put it in series with the strip's + lead and note the current at Warm 100% and at Cool 100%. The firmware wants those two numbers later.</li>
    <li>After five minutes at 100% both MOSFETs should be barely warm.</li>
  </ol>
</article>"""

LEDTEST = """<article class="check" id="check-leds">
  <header><span class="stopno">?</span><div><span class="where">Before the RGB strings · the mystery stars</span><h3>Find each die and its + side</h3></div></header>
  <p>Only R and B are printed on your stars. This test finds the green pads and each die's polarity at about 10 mA.</p>
  <ol>
    <li>Take a 220 Ω resistor. Connect the QT Py's <b>5V</b> pad through it to one pad of a pair, and the other pad of the pair to <b>GND</b>.</li>
    <li>No light: swap the two leads. Never use more than 5 V here. An LED only survives about 5 V the wrong way round.</li>
    <li>Mark the + pad and the colour of all three pairs on all four stars.</li>
    <li>Wire each colour as one chain: Board A red rail → star 1 + … star 1 − → star 2 + … and so on, ending with star 4 − → that colour's drain row on Board B.</li>
    <li>Tape or bolt the stars to a piece of aluminium. At 50 mA each star makes about 0.4 W.</li>
  </ol>
</article>"""

CHECK3 = """<article class="check" id="check-3">
  <header><span class="stopno">!</span><div><span class="where">Stop and check · everything connected</span><h3>First colour</h3></div></header>
  <ol>
    <li>Red at 100%, the rest at 0%: all four red dies light. Measure across a red sense resistor, from the leg in B·a9 to the blue rail. It reads your preset, <span class="read">2.5 V = 50 mA</span></li>
    <li>Dark and 0 V means a die is the wrong way round or a joint in the chain is open.</li>
    <li>Repeat for Green at B·a23 and Blue at B·j23.</li>
    <li>Run all three at 100% for five minutes. The three MOSFETs get hot: about 0.65 W on red and 0.45 W on green and blue at 50 mA. You should still be able to touch them briefly.</li>
    <li>Enter the firmware settings in the reference section, then calibrate Min duty on each channel.</li>
  </ol>
</article>"""

REFERENCE = """<header class="bag" id="reference"><span class="bagno">i</span><div><span class="where">Reference</span><h2>Why it changed, and the numbers</h2></div></header>

<section class="sheet">
  <span class="where">Old guide against this one</span>
  <h3>The strip switch was redesigned. The RGB sink was re-scaled.</h3>
  <div class="tablewrap"><table>
    <thead><tr><th></th><th>Revision 1</th><th>This build</th></tr></thead>
    <tbody>
      <tr><td>Strip MOSFET</td><td class="was">IRFZ44N, needs 10 V on the gate</td><td>IRLB8721, logic-level, new in your inventory</td></tr>
      <tr><td>Strip gate drive</td><td class="was">LM339 + BC547 + diode from a 12 V rail</td><td>Straight from the 3.3 V pin through 220 Ω</td></tr>
      <tr><td>Parts per strip channel</td><td class="was">8, plus a shared comparator, 12 V rail and divider</td><td>4</td></tr>
      <tr><td>RGB sense resistor</td><td class="was">2.5 Ω, so the reference was 0–143 mV</td><td>50 Ω, so the reference is 0–3.3 V</td></tr>
      <tr><td>RGB turn-on delay at 2 kHz</td><td class="was">26–54 µs, 5–11% of every cycle</td><td>About 5 µs, 1% of a cycle</td></tr>
      <tr><td>A loose pot leg gives</td><td class="was">Up to 1.3 A through the LEDs</td><td>66 mA at most, or zero</td></tr>
      <tr><td>RGB maximum on the breadboard</td><td class="was">52 mA</td><td>66 mA</td></tr>
      <tr><td>Components</td><td class="was">66</td><td>46</td></tr>
    </tbody>
  </table></div>
  <p class="hint">The delay figures come from a time-step model of the LM324 loop (<span class="mono">tools/sink_sim.py</span>), not from a scope. The old sink ramped its gate with a millivolt-sized reference, so the LEDs stayed dark for the first part of every PWM pulse, and for longer the lower you set the pot. With the pot at maximum the RGB channels would not have lit below 5% duty, and at half setting not below 11%.</p>
</section>

<section class="sheet">
  <span class="where">Schematics</span>
  <h3>Strip switch, build twice</h3>
  <figure class="schem">
    <div class="scroll">
    <svg class="sch" viewBox="0 0 640 290" role="img" aria-label="Strip switch: QT Py pin through 220 ohms to the gate of an IRLB8721, 10k from gate to ground, source to ground, drain to the strip's warm return, strip plus on 24 volts, and a 1N5819 from drain to 24 volts.">
      <text x="112" y="154" text-anchor="end">A3 · GP26</text>
      <line class="sig" x1="118" y1="150" x2="160" y2="150"/><rect class="r" x="160" y="143" width="50" height="14"/><line class="sig" x1="210" y1="150" x2="300" y2="150"/>
      <text class="lbl" x="185" y="136" text-anchor="middle">220 Ω</text>
      <circle class="dot" cx="255" cy="150" r="3"/>
      <line x1="255" y1="150" x2="255" y2="172"/><rect class="r" x="248" y="172" width="14" height="40"/><line x1="255" y1="212" x2="255" y2="240"/>
      <line x1="245" y1="240" x2="265" y2="240"/><line x1="249" y1="245" x2="261" y2="245"/><line x1="253" y1="250" x2="257" y2="250"/>
      <text class="lbl" x="242" y="196" text-anchor="end">10 kΩ</text>
      <line class="thick" x1="300" y1="130" x2="300" y2="170"/>
      <line class="thick" x1="310" y1="125" x2="310" y2="137"/><line class="thick" x1="310" y1="144" x2="310" y2="156"/><line class="thick" x1="310" y1="163" x2="310" y2="175"/>
      <polyline points="310,131 340,131 340,100"/><polyline points="310,169 340,169 340,240"/>
      <line x1="340" y1="150" x2="321" y2="150"/><polygon class="solid" points="312,150 321,145 321,155"/>
      <line x1="330" y1="240" x2="350" y2="240"/><line x1="334" y1="245" x2="346" y2="245"/><line x1="338" y1="250" x2="342" y2="250"/>
      <text class="ttl" x="352" y="154">IRLB8721</text><text class="pin" x="352" y="170">G · D · S facing the print</text>
      <text class="lbl" x="352" y="262">thick wire to supply −</text>
      <rect class="box" x="312" y="50" width="56" height="50" rx="3"/><text x="340" y="72" text-anchor="middle">WW</text><text class="pin" x="340" y="88" text-anchor="middle">strip</text>
      <line x1="340" y1="50" x2="340" y2="30"/><line x1="320" y1="30" x2="480" y2="30"/><text x="490" y="34">+24 V</text>
      <circle class="dot" cx="340" cy="115" r="3"/><polyline points="340,115 430,115 430,96"/>
      <polygon points="420,96 440,96 430,76"/><line x1="420" y1="76" x2="440" y2="76"/><line x1="430" y1="76" x2="430" y2="30"/><circle class="dot" cx="430" cy="30" r="3"/>
      <text class="lbl" x="446" y="92">1N5819</text>
    </svg>
    </div>
    <figcaption><b>Shown for warm white.</b> Cool white is the same from <span class="mono">TX · GP20</span>. With the QT Py unpowered, booting or in bootloader mode the pin floats, the 10 kΩ holds the gate at 0 V and the strip stays dark. The IRLB8721 is a 30 V part, so use it on a regulated 24 V supply and nothing higher.</figcaption>
  </figure>

  <h3>Current sink, build three times</h3>
  <figure class="schem">
    <div class="scroll">
    <svg class="sch" viewBox="0 0 800 360" role="img" aria-label="Current sink: QT Py pin to the top of a 10k pot whose other end is grounded; wiper to the LM324 plus input with 100k to ground; output through 100 ohms to the IRLB8721 gate with 100k to ground; source to a 50 ohm sense resistor; sense fed back through 1k to the minus input with 1 nanofarad from output to minus input and 1 megohm from 12 volts; drain to four LED dies in series from 24 volts.">
      <text x="92" y="104" text-anchor="end">A0 · GP29</text>
      <polyline class="sig" points="98,100 150,100 150,120"/>
      <rect class="r" x="143" y="120" width="14" height="70"/><line x1="150" y1="190" x2="150" y2="300"/>
      <line x1="140" y1="300" x2="160" y2="300"/><line x1="144" y1="305" x2="156" y2="305"/><line x1="148" y1="310" x2="152" y2="310"/>
      <text class="lbl" x="136" y="150" text-anchor="end">10 kΩ</text><text class="lbl" x="136" y="164" text-anchor="end">pot</text>
      <line class="sig" x1="168" y1="155" x2="340" y2="155"/><polygon class="solid" points="159,155 168,150 168,160"/>
      <circle class="dot" cx="250" cy="155" r="3"/>
      <line x1="250" y1="155" x2="250" y2="176"/><rect class="r" x="243" y="176" width="14" height="40"/><line x1="250" y1="216" x2="250" y2="240"/>
      <line x1="240" y1="240" x2="260" y2="240"/><line x1="244" y1="245" x2="256" y2="245"/><line x1="248" y1="250" x2="252" y2="250"/>
      <text class="lbl" x="236" y="200" text-anchor="end">100 kΩ</text>
      <polygon points="340,130 340,230 440,180"/>
      <text x="347" y="159">+</text><text x="347" y="209">−</text><text class="lbl" x="366" y="184">LM324</text>
      <text class="pin" x="332" y="149" text-anchor="end">3</text><text class="pin" x="332" y="199" text-anchor="end">2</text><text class="pin" x="446" y="173">1</text>
      <line x1="440" y1="180" x2="490" y2="180"/><circle class="dot" cx="470" cy="180" r="3"/>
      <rect class="r" x="490" y="173" width="40" height="14"/><text class="lbl" x="510" y="166" text-anchor="middle">100 Ω</text>
      <line x1="530" y1="180" x2="580" y2="180"/><circle class="dot" cx="555" cy="180" r="3"/>
      <line x1="555" y1="180" x2="555" y2="194"/><rect class="r" x="548" y="194" width="14" height="32"/><line x1="555" y1="226" x2="555" y2="236"/>
      <line x1="545" y1="236" x2="565" y2="236"/><line x1="549" y1="241" x2="561" y2="241"/><line x1="553" y1="246" x2="557" y2="246"/>
      <text class="lbl" x="542" y="214" text-anchor="end">100 kΩ</text>
      <line class="thick" x1="580" y1="160" x2="580" y2="200"/>
      <line class="thick" x1="590" y1="155" x2="590" y2="167"/><line class="thick" x1="590" y1="174" x2="590" y2="186"/><line class="thick" x1="590" y1="193" x2="590" y2="205"/>
      <polyline points="590,161 620,161 620,92"/><polyline points="590,199 620,199 620,276"/>
      <line x1="620" y1="180" x2="601" y2="180"/><polygon class="solid" points="592,180 601,175 601,185"/>
      <text class="ttl" x="632" y="185">IRLB8721</text>
      <circle class="dot" cx="620" cy="264" r="3"/>
      <rect class="r" x="613" y="276" width="14" height="40"/><line x1="620" y1="316" x2="620" y2="330"/>
      <line x1="610" y1="330" x2="630" y2="330"/><line x1="614" y1="335" x2="626" y2="335"/><line x1="618" y1="340" x2="622" y2="340"/>
      <text class="lbl" x="634" y="292">50 Ω</text><text class="lbl" x="634" y="307">= 2 × 100 Ω side by side</text>
      <line x1="620" y1="264" x2="530" y2="264"/><rect class="r" x="490" y="257" width="40" height="14"/><text class="lbl" x="510" y="288" text-anchor="middle">1 kΩ</text>
      <polyline points="490,264 316,264 316,205 340,205"/>
      <line x1="470" y1="180" x2="470" y2="216"/><line x1="460" y1="216" x2="480" y2="216"/><line x1="460" y1="224" x2="480" y2="224"/><line x1="470" y1="224" x2="470" y2="264"/>
      <circle class="dot" cx="470" cy="264" r="3"/><text class="lbl" x="456" y="224" text-anchor="end">1 nF</text>
      <circle class="dot" cx="400" cy="264" r="3"/>
      <line x1="400" y1="264" x2="400" y2="282"/><rect class="r" x="393" y="282" width="14" height="32"/><line x1="400" y1="314" x2="400" y2="328"/>
      <text class="lbl" x="412" y="302">1 MΩ</text><text x="400" y="344" text-anchor="middle">+12 V</text>
      <polygon points="608,70 632,70 620,92"/><line x1="608" y1="92" x2="632" y2="92"/><line x1="620" y1="70" x2="620" y2="40"/>
      <line x1="636" y1="74" x2="648" y2="64"/><line x1="640" y1="84" x2="652" y2="74"/>
      <line x1="620" y1="40" x2="700" y2="40"/><text x="710" y="44">+24 V</text>
      <text class="lbl" x="660" y="92">4 dies in series</text>
    </svg>
    </div>
    <figcaption><b>Shown for red on amplifier 1</b> (pins 3, 2, 1). Green uses A1 · GP28 on pins 5, 6, 7. Blue uses A2 · GP27 on pins 10, 9, 8. Current = (pin 3 voltage − 12 mV) ⁄ 50 Ω. The reference is the PWM pin's own 3.3 V scaled by the pot, so it can never exceed 3.3 V and the current can never exceed 66 mA. The 100 kΩ pulls pin 3 to ground if the wiper wire comes out.</figcaption>
  </figure>
</section>

<section class="sheet">
  <span class="where">Heat on Board B</span>
  <h3>Why 66 mA is the breadboard ceiling</h3>
  <p>From 24 V, each sink burns the voltage its string does not use. A bare TO-220 handles about 1 W before it gets too hot for a breadboard, and the sense resistors are quarter-watt parts.</p>
  <div class="tablewrap"><table>
    <thead><tr><th>Pot setting</th><th>Red MOSFET</th><th>Green, blue MOSFET</th><th>Each sense resistor</th></tr></thead>
    <tbody>
      <tr><td>50 mA (2.5 V)</td><td>0.65 W</td><td>0.45 W</td><td>0.06 W</td></tr>
      <tr><td>66 mA (pot at maximum)</td><td>0.81 W</td><td>0.55 W</td><td>0.11 W</td></tr>
    </tbody>
  </table></div>
  <p class="hint">Figures assume about 8.4 V across the red string and 12.4 V across green and blue. They are at 100% duty; dimming scales them down.</p>
</section>

<section class="sheet">
  <span class="where">Firmware</span>
  <h3>Settings for this hardware</h3>
  <div class="tablewrap"><table>
    <thead><tr><th>Menu</th><th>Set to</th><th>Why</th></tr></thead>
    <tbody>
      <tr><td>Channels ▸ each ▸ Invert</td><td>Off</td><td>All five drivers switch on with a high pin.</td></tr>
      <tr><td>White LEDs ▸ Warm LED / Cool LED</td><td>2700 K / 6500 K</td><td>From the strip datasheet. Firmware 1.1 defaults to these.</td></tr>
      <tr><td>PWM freq</td><td>2.0 kHz</td><td>Keeps the RGB turn-on delay near 1% of a cycle.</td></tr>
      <tr><td>Power ▸ WW, CW @100%</td><td>Your readings from the strip check</td><td>Makes the current estimate and the budget accurate.</td></tr>
      <tr><td>Power ▸ R, G, B @100%</td><td>50 mA, or your preset</td><td>What each sink draws from 24 V.</td></tr>
      <tr><td>Power ▸ Budget</td><td>2400 mA</td><td>80% of a 3 A supply.</td></tr>
      <tr><td>Channels ▸ each ▸ Min duty</td><td>Raise until the LED just glows at Test level 0.1%</td><td>Expect about 0.1% on the strip and 1–2% on RGB.</td></tr>
    </tbody>
  </table></div>
  <p class="hint">The pin map did not change: A0, A1, A2 are red, green, blue; A3 is warm; TX is cool.</p>
</section>

<section class="sheet">
  <span class="where">Later · full RGB power</span>
  <h3>The LM3414 route is unchanged</h3>
  <p>Linear sinks from 24 V waste more than half the power as heat, so 310 mA per colour still means either a heatsink on each sink MOSFET or your 25 LM3414 buck drivers. The switch-mode circuit from revision 1 stands as it was. It has not been re-checked in this revision.</p>
  <ul class="plain">
    <li><b>To buy:</b> three shielded inductors of 100–150 µH with at least 0.6 A saturation current, and three SOIC-8 adapter boards with a centre thermal pad.</li>
    <li><b>Per colour, from inventory:</b> LM3414 (IC-023), 1N5819, 10 kΩ on IADJ for 312 mA, 47 kΩ on FS for about 425 kHz, 1 kΩ in series with DIM and 10 kΩ from DIM to ground, 1 µF on VCC, 10 µF at VIN.</li>
    <li><b>Wiring:</b> string + on 24 V, string − through the inductor to LX, 1N5819 from LX up to 24 V. Build it on perfboard and check the pinout against TI's datasheet figure before soldering.</li>
    <li>The PWM wires then go to the DIM inputs and the firmware stays as it is.</li>
  </ul>
</section>"""

SCRIPT = """<script>
(function () {
  var KEY = "tasklamp-driver-build-r2";
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { state = {}; }
  var boxes = document.querySelectorAll(".done input");
  function paint(box) { box.closest(".step").classList.toggle("is-done", box.checked); }
  boxes.forEach(function (box) {
    if (state[box.id]) { box.checked = true; }
    paint(box);
    box.addEventListener("change", function () {
      paint(box);
      state[box.id] = box.checked;
      try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
    });
  });
})();
</script>"""
