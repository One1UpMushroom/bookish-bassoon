#!/usr/bin/env python3
"""
Build script: "LR4 Hardware" launcher shortcut.

One job: open Scriptable and run the "LR4 Hardware" script, which shows the
LowRider V4 hardware checklist full screen. Uses only Apple's built-in
Open URLs action, so the file can be generated and signed (Scriptable's own
"Run Script" action can't go into a generated file).

Run:   python3 build_lr4_launcher.py
Then:  sign it on the Mac (see ../README.md) and add it to the Home Screen.
"""
import os
import sys

# Let Python find the builder in the apple-shortcuts skill's scripts folder.
sys.path.insert(0, "/root/.claude/skills/synced/fd2cb7cd-9c3a-4400-9897-16e152f50a47_6be5107e-14c5-4f18-96db-909fcdcbcd50/apple-shortcuts/scripts")
from shortcut_kit import Shortcut  # noqa: E402

# Not shown on Apple Watch: the watch cannot open Scriptable.
sc = Shortcut("LR4 Hardware", glyph="checklist", color="green", show_in=[])
sc.comment("LR4 Hardware: opens Scriptable and runs the script of the same name, "
           "which shows the LowRider V4 hardware checklist. The script must be "
           "named exactly 'LR4 Hardware' in Scriptable.")

# Scriptable's URL scheme: scriptable:///run?scriptName=<URL-encoded name>.
# Opening it switches to Scriptable and runs the script there, full screen.
# Step 1: the link that tells Scriptable which script to run.
link = sc.add("url", WFURLActionURL="scriptable:///run?scriptName=LR4%20Hardware")
# Step 2: open it, which switches to Scriptable and runs the script.
sc.add("openurl", WFInput=link)

shortcut_path, xml_path = sc.save(folder=os.path.dirname(os.path.abspath(__file__)))
print("wrote", shortcut_path)
