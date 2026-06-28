"""Behaviour: the bash templates render the Dracula starship prompt with real
powerline triangles and Nerd icons (never stripped empty), palette from vars,
and a clean ble.sh + starship .bashrc. Rendered with Jinja2 + the glyphs filter."""
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

import glyphs

REPO = Path(__file__).resolve().parent.parent
TPL_DIR = REPO / "roles/bash/templates"

# Dracula palette (distinct from zsh's Catppuccin).
DRACULA = {
    "base": "#282a36", "surface": "#44475a", "fg": "#f8f8f2", "comment": "#6272a4",
    "cyan": "#8be9fd", "green": "#50fa7b", "orange": "#ffb86c", "pink": "#ff79c6",
    "purple": "#bd93f9", "red": "#ff5555", "yellow": "#f1fa8c",
}


def render(name, **vars):
    env = Environment(loader=FileSystemLoader(str(TPL_DIR)), keep_trailing_newline=True)
    env.filters["glyph"] = glyphs.glyph
    return env.get_template(name).render(**vars)


def test_starship_renders_real_powerline_triangles():
    out = render("starship.toml.j2", ts_bash_palette=DRACULA)
    cps = {ord(c) for c in out}
    assert 0xE0B0 in cps  # right triangle
    assert 0xE0B2 in cps  # left triangle


def test_starship_palette_is_dracula_from_vars():
    out = render("starship.toml.j2", ts_bash_palette=DRACULA)
    assert "palette = 'dracula'" in out
    assert "#bd93f9" in out  # purple
    assert "#8be9fd" in out  # cyan
    assert "$username" in out


def test_starship_renders_nerd_icons_not_empty():
    out = render("starship.toml.j2", ts_bash_palette=DRACULA)
    cps = {ord(c) for c in out}
    for cp in (0xF007, 0xF023, 0xE0A0, 0xE718, 0xE606, 0xF017, 0xF252):
        assert cp in cps, f"missing glyph {hex(cp)}"


def test_bashrc_loads_blesh_starship_and_completion_at_brew_prefix():
    out = render("bashrc.j2", ts_bash_palette=DRACULA, ts_brew_prefix="/home/linuxbrew/.linuxbrew")
    assert "blesh/ble.sh --noattach" in out
    assert 'eval "$(starship init bash)"' in out
    assert "/home/linuxbrew/.linuxbrew/etc/profile.d/bash_completion.sh" in out
    # ble.sh must attach at the very end.
    assert "ble-attach" in out
    assert out.rstrip().endswith("ble-attach")


def test_bashrc_ble_faces_are_dracula_from_vars():
    out = render("bashrc.j2", ts_bash_palette=DRACULA, ts_brew_prefix="/opt/homebrew")
    assert "ble-face -s command_file        'fg=#50fa7b'" in out  # green
    assert "ble-face -s syntax_error        'fg=#ff5555,bold'" in out  # red


def test_bash_profile_sources_bashrc():
    out = render("bash_profile.j2", ts_bash_palette=DRACULA, ts_brew_prefix="/opt/homebrew")
    assert "~/.bashrc" in out
