// Renders the factory files themselves (not the KiCad board) to pictures.
//
//   npm install pcb-stackup@4 playwright      (once, anywhere on NODE_PATH)
//   node tools/pcb/render.js
//
// Reads hardware/tasklamp-driver/gerbers and writes img/board-top.png,
// img/board-bottom.png and img/schematic.png beside it. Because the pictures come
// from the Gerber and drill files, they show what the factory will make.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const pcbStackup = require('pcb-stackup');
const { chromium } = require('playwright');

const root = path.join(__dirname, '..', '..', 'hardware', 'tasklamp-driver');
const fab = path.join(root, 'gerbers');
const img = path.join(root, 'img');

async function png(page, svg, out, width, background) {
  const m = svg.match(/viewBox="([-\d.e ]+)"/);
  const vb = m[1].trim().split(/\s+/).map(Number);
  const height = Math.round((width * vb[3]) / vb[2]);
  await page.setViewportSize({ width, height });
  await page.setContent(
    `<body style="margin:0;background:${background}"><img id="i" style="display:block;width:${width}px;height:${height}px"></body>`);
  await page.evaluate((d) => new Promise((r) => {
    const i = document.getElementById('i'); i.onload = r; i.src = 'data:image/svg+xml;base64,' + d;
  }), Buffer.from(svg).toString('base64'));
  await page.screenshot({ path: out });
}

(async () => {
  fs.mkdirSync(img, { recursive: true });
  const files = fs.readdirSync(fab).filter((f) => /\.(g[a-z0-9]+|drl)$/i.test(f));
  const stackup = await pcbStackup(
    files.map((f) => ({ filename: f, gerber: fs.createReadStream(path.join(fab, f)) })),
    { color: { fr4: '#5d5a4a', cu: '#c9b26b', cf: '#d8b24a', sm: 'rgba(8, 84, 44, 0.86)', ss: '#f4f4ee', sp: '#999', out: '#000' } });
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: 1 });
  await png(page, stackup.top.svg, path.join(img, 'board-top.png'), 1930, 'transparent');
  await png(page, stackup.bottom.svg, path.join(img, 'board-bottom.png'), 1930, 'transparent');
  const tmp = fs.mkdtempSync(path.join(require('os').tmpdir(), 'tlsch'));
  execFileSync('kicad-cli', ['sch', 'export', 'svg', '--exclude-drawing-sheet', '-o', tmp,
    path.join(root, 'tasklamp-driver.kicad_sch')], { stdio: 'ignore' });
  const sch = fs.readFileSync(path.join(tmp, 'tasklamp-driver.svg'), 'utf8');
  await png(page, sch, path.join(img, 'schematic.png'), 2200, '#ffffff');
  await browser.close();
  console.log('wrote', fs.readdirSync(img).join(', '));
})().catch((e) => { console.error(e); process.exit(1); });
