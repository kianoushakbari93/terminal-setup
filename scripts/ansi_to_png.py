#!/usr/bin/env python3
"""Render ANSI terminal output (e.g. from `tmux capture-pane -e`) to a PNG, using
a real Nerd Font so powerline pills and glyphs render faithfully.

Usage:
    ansi_to_png.py --font <ttf> [--bold <ttf>] [--size 28] [--bg '#1e1e2e'] \
                   --out out.png < input.ansi
"""
from __future__ import annotations

import argparse
import re
import sys

from PIL import Image, ImageDraw, ImageFont

CSI = re.compile(r"\x1b\[([0-9;]*)m")
# Catppuccin Mocha-ish 16-colour palette for basic SGR colours.
BASIC = {
    0: (69, 71, 90), 1: (243, 139, 168), 2: (166, 227, 161), 3: (249, 226, 175),
    4: (137, 180, 250), 5: (203, 166, 247), 6: (148, 226, 213), 7: (205, 214, 244),
}
BRIGHT = {
    0: (88, 91, 112), 1: (243, 139, 168), 2: (166, 227, 161), 3: (249, 226, 175),
    4: (137, 180, 250), 5: (203, 166, 247), 6: (148, 226, 213), 7: (166, 173, 200),
}


def parse_cells(text, default_fg, default_bg):
    """Parse ANSI text into rows of (char, fg, bg, bold) cells."""
    rows = []
    fg, bg, bold = default_fg, default_bg, False
    for line in text.split("\n"):
        row = []
        i = 0
        while i < len(line):
            m = CSI.match(line, i)
            if m:
                fg, bg, bold = apply_sgr(m.group(1), fg, bg, bold, default_fg, default_bg)
                i = m.end()
                continue
            ch = line[i]
            if ch != "\x1b":
                row.append((ch, fg, bg, bold))
            i += 1
        rows.append(row)
    return rows


def apply_sgr(params, fg, bg, bold, dfg, dbg):
    codes = [int(p) if p else 0 for p in params.split(";")]
    i = 0
    while i < len(codes):
        c = codes[i]
        if c == 0:
            fg, bg, bold = dfg, dbg, False
        elif c == 1:
            bold = True
        elif c == 22:
            bold = False
        elif c == 39:
            fg = dfg
        elif c == 49:
            bg = dbg
        elif 30 <= c <= 37:
            fg = BASIC[c - 30]
        elif 40 <= c <= 47:
            bg = BASIC[c - 40]
        elif 90 <= c <= 97:
            fg = BRIGHT[c - 90]
        elif 100 <= c <= 107:
            bg = BRIGHT[c - 100]
        elif c in (38, 48):
            target_is_fg = c == 38
            if i + 1 < len(codes) and codes[i + 1] == 2:  # truecolor
                rgb = (codes[i + 2], codes[i + 3], codes[i + 4])
                i += 4
                fg, bg = (rgb, bg) if target_is_fg else (fg, rgb)
            elif i + 1 < len(codes) and codes[i + 1] == 5:  # 256-colour
                rgb = xterm256(codes[i + 2])
                i += 2
                fg, bg = (rgb, bg) if target_is_fg else (fg, rgb)
        i += 1
    return fg, bg, bold


def xterm256(n):
    if n < 16:
        return BASIC.get(n % 8, (205, 214, 244))
    if n >= 232:
        v = 8 + (n - 232) * 10
        return (v, v, v)
    n -= 16
    r, g, b = n // 36, (n % 36) // 6, n % 6
    conv = lambda x: 0 if x == 0 else 55 + x * 40
    return (conv(r), conv(g), conv(b))


def hexrgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def render(rows, font, bold_font, cell_w, cell_h, default_bg, pad=24):
    width = max((len(r) for r in rows), default=1)
    img = Image.new("RGB", (width * cell_w + 2 * pad, len(rows) * cell_h + 2 * pad), default_bg)
    draw = ImageDraw.Draw(img)
    # Pass 1: backgrounds, extended 1px right so adjacent cells leave no seam
    # (powerline caps connect to their pill body without a dark sliver).
    for y, row in enumerate(rows):
        for x, (ch, fg, bg, bold) in enumerate(row):
            if bg != default_bg:
                px, py = pad + x * cell_w, pad + y * cell_h
                draw.rectangle([px, py, px + cell_w + 1, py + cell_h], fill=bg)
    # Pass 2: glyphs on top (caps drawn in fg fill to the cell edge).
    for y, row in enumerate(rows):
        for x, (ch, fg, bg, bold) in enumerate(row):
            if ch.strip():
                draw.text((pad + x * cell_w, pad + y * cell_h), ch,
                          font=bold_font if bold else font, fill=fg)
    return img


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", required=True)
    ap.add_argument("--bold")
    ap.add_argument("--size", type=int, default=28)
    ap.add_argument("--bg", default="#1e1e2e")
    ap.add_argument("--out", required=True)
    ap.add_argument("--input")
    args = ap.parse_args(argv)

    text = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
    text = text.rstrip("\n")
    font = ImageFont.truetype(args.font, args.size)
    bold_font = ImageFont.truetype(args.bold or args.font, args.size)
    default_bg = hexrgb(args.bg)
    default_fg = (205, 214, 244)

    # Cell width must equal the font's monospace advance (NOT the glyph bbox), so
    # powerline caps fill the cell and connect to their pill body seamlessly.
    cell_w = max(1, round(font.getlength("M")))
    cell_h = int(args.size * 1.34)

    rows = parse_cells(text, default_fg, default_bg)
    img = render(rows, font, bold_font, cell_w, cell_h, default_bg)
    img.save(args.out)
    print(f"wrote {args.out} ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
