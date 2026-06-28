"""Behaviour: the tmux template renders the Catppuccin Mocha status bar with real
rounded window-cap glyphs (never stripped empty), palette/flavor from vars, and a
transparent bar background. Rendered with Jinja2 + the glyphs filter."""
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

import glyphs

REPO = Path(__file__).resolve().parent.parent
TPL_DIR = REPO / "roles/tmux/templates"

MOCHA = {
    "mauve": "#cba6f7", "text": "#cdd6f4", "crust": "#11111b",
    "overlay2": "#9399b2", "surface0": "#313244", "surface1": "#45475a",
    "fg": "#cdd6f4",
}


def render(name, **vars):
    env = Environment(loader=FileSystemLoader(str(TPL_DIR)), keep_trailing_newline=True)
    env.filters["glyph"] = glyphs.glyph
    return env.get_template(name).render(**vars)


def ctx(**over):
    base = dict(ts_tmux_palette=MOCHA, ts_tmux_flavor="mocha", ts_tmux_has_battery=True)
    base.update(over)
    return base


def test_window_caps_render_real_rounded_glyphs():
    out = render("tmux.conf.j2", **ctx())
    cps = {ord(c) for c in out}
    assert 0xE0B6 in cps  # left half-circle cap
    assert 0xE0B4 in cps  # right half-circle cap
    assert 0xF0A4C in cps  # zoom flag icon


def test_palette_and_flavor_come_from_vars():
    out = render("tmux.conf.j2", **ctx())
    assert "@catppuccin_flavor 'mocha'" in out
    assert "#cba6f7" in out  # mauve (current tab)
    assert "#9399b2" in out  # overlay2 (inactive tab)


def test_status_background_is_transparent():
    out = render("tmux.conf.j2", **ctx())
    assert 'set -g  status-bg                    "default"' in out
    assert "status-position bottom" in out
    assert "status-justify left" in out


def test_battery_module_used_when_host_has_battery():
    out = render("tmux.conf.j2", **ctx(ts_tmux_has_battery=True))
    assert "@catppuccin_status_battery" in out


def test_batteryless_host_falls_back_to_cpu_spacer():
    out = render("tmux.conf.j2", **ctx(ts_tmux_has_battery=False))
    # No battery module (it would render empty); a CPU/load spacer instead.
    assert "@catppuccin_status_battery" not in out
    assert "load average" in out
