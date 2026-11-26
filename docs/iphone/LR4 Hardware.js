// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: deep-green; icon-glyph: tasks;

// LR4 Hardware: opens the LowRider V4 hardware checklist and keeps your ticks
// in iCloud Drive (Scriptable folder), so they survive restarts and sync to
// your other devices.
//
// Needs, in the same Scriptable folder in iCloud Drive:
//   lr4-hardware-checklist.html   the checklist page
// Creates there:
//   lr4-hardware-state.json       your ticks

const PAGE = "lr4-hardware-checklist.html";
const STATE = "lr4-hardware-state.json";
const SAVE_PREFIX = "lr4-save:";

const fm = FileManager.iCloud();
const dir = fm.documentsDirectory();
const pagePath = fm.joinPath(dir, PAGE);
const statePath = fm.joinPath(dir, STATE);

// iCloud may keep a file in the cloud only; fetch it before reading.
async function download(path) {
  if (fm.fileExists(path) && !fm.isFileDownloaded(path)) {
    await fm.downloadFileFromiCloud(path);
  }
}

function readState() {
  if (!fm.fileExists(statePath)) return {};
  try {
    const parsed = JSON.parse(fm.readString(statePath));
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch (e) {
    return {};
  }
}

// Only keep item ids mapped to 1, so a damaged file can't inject anything odd.
function cleanState(obj) {
  const out = {};
  for (const [k, v] of Object.entries(obj || {})) {
    if (/^[a-z0-9-]{1,40}$/.test(k) && v) out[k] = 1;
  }
  return out;
}

function writeState(obj) {
  fm.writeString(statePath, JSON.stringify(cleanState(obj)));
}

async function showMissing() {
  const a = new Alert();
  a.title = "Checklist page not found";
  a.message = "Copy " + PAGE + " into iCloud Drive › Scriptable, then run this again.";
  a.addAction("OK");
  await a.present();
}

async function main() {
  await download(pagePath);
  await download(statePath);
  if (!fm.fileExists(pagePath)) {
    await showMissing();
    return;
  }

  const state = cleanState(readState());
  // JSON is safe inside a script tag once "<" is escaped.
  const boot =
    "<script>window.LR4_HOST='scriptable';window.LR4_STATE=" +
    JSON.stringify(state).replace(/</g, "\\u003c") +
    ";</script>";
  let html = fm.readString(pagePath);
  html = html.includes("<!--LR4_BOOT-->")
    ? html.replace("<!--LR4_BOOT-->", boot)
    : boot + html;
  // The page is a fragment written for a host that adds the document shell.
  if (!/^\s*<!doctype/i.test(html)) {
    html =
      '<!doctype html><html><head><meta charset="utf-8">' +
      '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">' +
      "<style>:root{padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}body{margin:0}[hidden]{display:none!important}</style>" +
      "</head><body>" + html + "</body></html>";
  }

  const wv = new WebView();
  // Each tick arrives as a request to lr4-save:<json>. Save it and stop the navigation.
  wv.shouldAllowRequest = (request) => {
    const url = request.url || "";
    if (url.startsWith(SAVE_PREFIX)) {
      try {
        writeState(JSON.parse(decodeURIComponent(url.slice(SAVE_PREFIX.length))));
      } catch (e) {
        console.error("Could not save ticks: " + e);
      }
      return false;
    }
    return true;
  };

  await wv.loadHTML(html);
  await wv.present(true);

  // Backup save when the checklist is closed, in case a tap's save was missed.
  try {
    const json = await wv.evaluateJavaScript("JSON.stringify(window.__lr4done || {})");
    if (typeof json === "string") writeState(JSON.parse(json));
  } catch (e) {
    console.log("Closing save skipped: " + e);
  }
}

await main();
Script.complete();
