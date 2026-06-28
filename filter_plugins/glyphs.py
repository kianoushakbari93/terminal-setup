"""Ansible Jinja2 filter ``glyph``: resolve powerline/Nerd Font glyphs by name to
their real characters.

The catalog stores codepoints as integers (never literal glyphs), so editors and
tooling that silently strip non-ASCII glyphs to empty cannot corrupt this file.
Templates reference glyphs as ``{{ 'right_half_circle' | glyph }}`` and the
rendered output contains the genuine character - the reliable way to get
powerline caps and Nerd icons into config files.
"""
from __future__ import annotations


class UnknownGlyph(Exception):
    """Raised for a glyph name not in the catalog."""


# name -> Unicode codepoint (integers; resolved to chars by glyph()).
_CATALOG = {
    # Powerline caps / separators (round "pill" style)
    "left_half_circle": 0xE0B6,
    "right_half_circle": 0xE0B4,
    "left_half_circle_thin": 0xE0B7,
    "right_half_circle_thin": 0xE0B5,
    # Powerline triangles (reused by bash/tmux slices)
    "left_triangle": 0xE0B2,
    "right_triangle": 0xE0B0,
    # Nerd Font icons
    "git_branch": 0xE0A0,
    # Prompt / status symbols
    "prompt_ok": 0x276F,       # heavy right angle quote
    "prompt_vicmd": 0x276E,    # heavy left angle quote
    "overwrite": 0x25B6,       # black right-pointing triangle
    "cross": 0x2718,           # heavy ballot X (error)
    "ahead": 0x21E1,           # upwards dashed arrow
    "behind": 0x21E3,          # downwards dashed arrow
    # Nerd Font icons (starship modules)
    "user": 0xF007,
    "lock": 0xF023,
    "node": 0xE718,
    "python": 0xE606,
    "golang": 0xE627,
    "rust": 0xE7A8,
    "java": 0xE738,
    "lua": 0xE620,
    "php": 0xE73D,
    "c_lang": 0xE61E,
    "duration": 0xF252,        # hourglass
    "clock": 0xF017,
    "zoom": 0xF0A4C,           # magnify (tmux zoomed-pane flag)
}


def glyph(name: str) -> str:
    try:
        return chr(_CATALOG[name])
    except KeyError:
        raise UnknownGlyph(
            f"Unknown glyph: {name!r}. Known glyphs: {', '.join(sorted(_CATALOG))}."
        )


class FilterModule(object):
    """Ansible filter plugin entry point."""

    def filters(self):
        return {"glyph": glyph}
