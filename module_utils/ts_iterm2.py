"""iTerm2 preferences helper.

Sets the profile font and window transparency on every iTerm2 profile in the
preferences plist, idempotently and touching only those two keys. Pure logic
(operates on a plist dict) so it is fully unit-testable without touching the real
preferences file.
"""
from __future__ import annotations

import copy
from typing import Tuple

FONT_KEY = "Normal Font"
TRANSPARENCY_KEY = "Transparency"
PROFILES_KEY = "New Bookmarks"


def apply_settings(plist: dict, font: str, transparency: float) -> Tuple[dict, bool]:
    """Return (new_plist, changed) with ``font`` and ``transparency`` applied to
    every profile. Only the two target keys are modified."""
    new = copy.deepcopy(plist)
    changed = False
    for profile in new.get(PROFILES_KEY, []):
        if profile.get(FONT_KEY) != font:
            profile[FONT_KEY] = font
            changed = True
        if profile.get(TRANSPARENCY_KEY) != transparency:
            profile[TRANSPARENCY_KEY] = transparency
            changed = True
    return new, changed
