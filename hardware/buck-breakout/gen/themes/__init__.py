"""The four themed versions of the BUCK//33630 board.

Each theme module provides:
  ID, NAME     short id (used in file names) and display name
  CORNERS      the board outline's corner shapes (kit.outline)
  COLORS       solder mask colour, silkscreen colour and pad finish, for the
               KiCad stackup (what the 3D viewer shows)
  ORDER        what to choose on the board house's order form
  decorate()   draws both sides' silkscreen and any bare-metal accents

The copper (parts, tracks, zones, vias) is identical on all four and on the
standard board: build_pcb.py lays it out, the themes only draw around it.
"""
import importlib

IDS = ["dawnworks", "mahogany", "neon", "parkside"]


def load(theme_id):
    """The theme module for one id, e.g. load("neon")."""
    return importlib.import_module(f"{__name__}.{theme_id}")
