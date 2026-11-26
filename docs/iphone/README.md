# LR4 hardware checklist on iPhone (Scriptable)

Runs the checklist offline in Scriptable and keeps your ticks in iCloud Drive.

| File | What it is |
|---|---|
| `lr4-hardware-checklist.html` | The checklist page, fonts included (about 100 KB) |
| `LR4 Hardware.js` | The Scriptable script that opens it and saves your ticks |

## Set up (once)

1. Save both files to **iCloud Drive › Scriptable** (Files app, or the Claude app's
   file card › Save to Files). Keep the names exactly as they are.
2. Open Scriptable. **LR4 Hardware** appears in the script list. Tap it.
3. The checklist opens full screen. Tick items as you go. Each tick is saved to
   `lr4-hardware-state.json` in the same folder. Close with the button at the top.

## Start it from the Home Screen

With Shortcuts (gives a normal app-style icon). For iOS 27.

**A. Make the shortcut**, either by hand or from the ready-made file.

By hand (two actions, nothing to sign):

1. Open Shortcuts and tap **+** to start a new shortcut.
2. Add the **URL** action and type:
   `scriptable:///run?scriptName=LR4%20Hardware`
   (the `%20` is the space in "LR4 Hardware").
3. Add the **Open URLs** action under it. It picks up the URL from step 2 on its own.
4. Name the shortcut **LR4 Hardware**, and pick an icon and colour.

This opens Scriptable and runs the script there, full screen. If you'd rather use
Scriptable's own action instead: add **Run Script**, choose **LR4 Hardware**, expand the
action and turn **Run In App** on.

From the file: `shortcut/LR4 Hardware.shortcut` holds the same two actions (plus a
comment), with a green checklist icon. iPhones only import signed files, so sign it on
the Mac first:

```sh
shortcuts sign --mode people-who-know-me --input ~/Downloads/"LR4 Hardware.shortcut" --output ~/Desktop/"LR4 Hardware.shortcut"
```

Double-click the signed copy on the Desktop and click **Add Shortcut**. iCloud brings it
to the iPhone. (`shortcut/build_lr4_launcher.py` rebuilds the file.)

**B. Put it on the Home Screen** (Apple's steps):

1. In Shortcuts, tap the **•••** button on the LR4 Hardware tile, then tap the **ⓘ**
   button to open **Details**.
2. Tap **Add to Home Screen**.
3. Optional: change the Home Screen name or icon in the "Home Screen Name and Icon" area.
4. Tap **Add**.

Run it once from the Shortcuts app first. iOS asks once whether the shortcut may open
Scriptable; allow it. You can also say "Hey Siri, LR4 Hardware".

An earlier version of these notes said to use Share › Add to Home Screen. That option is
in the shortcut's Details, not the Share sheet.

Or as a Scriptable widget:

1. Long-press the Home Screen › **Edit** › **Add Widget** › **Scriptable**, small size.
2. Long-press the new widget › **Edit Widget**. Set **Script** to **LR4 Hardware** and
   **When Interacting** to **Run Script**.
3. Tapping the widget opens the checklist. The script doesn't draw a widget face, so the
   widget itself stays plain.

An earlier version of these notes said to long-press the script in Scriptable and use
**Details › Add to Home Screen**. That menu isn't there in current Scriptable.

## Good to know

- It works with no internet: the fonts are inside the page.
- Ticks sync through iCloud, so the same script on an iPad shows the same progress.
- To start over, use **Clear ticks** in the page, or delete `lr4-hardware-state.json`.
- The same page also works in a browser. There, ticks are kept in that browser instead.
- If you edit the page, keep the `<!--LR4_BOOT-->` line. The script puts your saved
  ticks there.

## How it was tested

The script was run here against stand-ins for Scriptable's file and web-view APIs in a
Chromium browser: fonts loaded offline, saved ticks came back, new ticks were written,
and a damaged state file was cleaned up. It has not been run on an iPhone yet. If a tick
ever fails to save as you tap it, the script also saves everything when you close the
checklist.
