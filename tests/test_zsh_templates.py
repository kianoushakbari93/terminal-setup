"""Behaviour: the zsh templates render the Catppuccin Mocha pill prompt with real
powerline/Nerd glyphs (never stripped to empty) and palette values sourced from
vars. Rendered with Jinja2 + the glyphs filter, exactly as Ansible does."""
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

import glyphs

REPO = Path(__file__).resolve().parent.parent
TPL_DIR = REPO / "roles/zsh/templates"

# Catppuccin Mocha palette (the values the prompt is built from).
MOCHA = {
    "rosewater": "#f5e0dc", "flamingo": "#f2cdcd", "pink": "#f5c2e7", "mauve": "#cba6f7",
    "red": "#f38ba8", "maroon": "#eba0ac", "peach": "#fab387", "yellow": "#f9e2af",
    "green": "#a6e3a1", "teal": "#94e2d5", "sky": "#89dceb", "sapphire": "#74c7ec",
    "blue": "#89b4fa", "lavender": "#b4befe", "text": "#cdd6f4", "subtext1": "#bac2de",
    "subtext0": "#a6adc8", "overlay2": "#9399b2", "overlay1": "#7f849c", "overlay0": "#6c7086",
    "surface2": "#585b70", "surface1": "#45475a", "surface0": "#313244",
    "base": "#1e1e2e", "mantle": "#181825", "crust": "#11111b",
}


def render(name, **vars):
    # Match Ansible's Jinja settings (trim_blocks=True) so block-tag newline
    # handling is faithful - otherwise template bugs slip through.
    env = Environment(
        loader=FileSystemLoader(str(TPL_DIR)),
        keep_trailing_newline=True, trim_blocks=True, lstrip_blocks=False,
    )
    env.filters["glyph"] = glyphs.glyph
    return env.get_template(name).render(**vars)


def test_p10k_renders_real_powerline_caps_not_empty():
    out = render("p10k.zsh.j2", ts_zsh_palette=MOCHA, ts_brew_prefix="/opt/homebrew")
    cps = {ord(c) for c in out}
    # Round pill caps must be present as real codepoints.
    assert 0xE0B4 in cps
    assert 0xE0B6 in cps
    assert 0xE0B5 in cps
    assert 0xE0B7 in cps


def test_p10k_renders_prompt_and_status_glyphs():
    out = render("p10k.zsh.j2", ts_zsh_palette=MOCHA, ts_brew_prefix="/opt/homebrew")
    cps = {ord(c) for c in out}
    assert 0x276F in cps  # prompt char
    assert 0x2718 in cps  # error cross
    assert 0xE0A0 in cps  # restored git branch icon


def test_p10k_palette_values_come_from_vars():
    out = render("p10k.zsh.j2", ts_zsh_palette=MOCHA, ts_brew_prefix="/opt/homebrew")
    assert "#cba6f7" in out  # mauve
    assert "#89b4fa" in out  # blue (dir background)
    # Structure is preserved.
    assert "POWERLEVEL9K_LEFT_SEGMENT_SEPARATOR" in out
    assert "POWERLEVEL9K_LEFT_PROMPT_ELEMENTS" in out


def test_trailing_setopt_and_unset_stay_on_separate_lines():
    # Regression: trim_blocks must not merge the setopt line into the unset line.
    out = render("p10k.zsh.j2", ts_zsh_palette=MOCHA, ts_brew_prefix="/opt/homebrew")
    assert "setopt ${p10k_config_opts[@]}\n'builtin' 'unset' 'p10k_config_opts'" in out
    assert "p10k_config_opts[@]}'builtin'" not in out  # the merged-line bug


def test_zshrc_sources_p10k_and_plugins_at_brew_prefix():
    out = render("zshrc.j2", ts_zsh_palette=MOCHA, ts_brew_prefix="/home/linuxbrew/.linuxbrew")
    assert "/home/linuxbrew/.linuxbrew/share/powerlevel10k/powerlevel10k.zsh-theme" in out
    assert "/home/linuxbrew/.linuxbrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh" in out
    assert "/home/linuxbrew/.linuxbrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" in out


def test_zshrc_has_instant_prompt_and_compinit():
    out = render("zshrc.j2", ts_zsh_palette=MOCHA, ts_brew_prefix="/opt/homebrew")
    assert "p10k-instant-prompt" in out
    assert "compinit" in out


def test_zshrc_highlight_styles_are_catppuccin_from_vars():
    out = render("zshrc.j2", ts_zsh_palette=MOCHA, ts_brew_prefix="/opt/homebrew")
    # Valid command green, unknown red, flags sky - all from the palette.
    assert "ZSH_HIGHLIGHT_STYLES[command]='fg=#a6e3a1'" in out
    assert "ZSH_HIGHLIGHT_STYLES[unknown-token]='fg=#f38ba8,bold'" in out
    assert "ZSH_HIGHLIGHT_STYLES[double-hyphen-option]='fg=#89dceb'" in out


def test_zshrc_exports_brew_path_before_tmux_autostart():
    # A fresh login shell has no brew prefix on PATH; if the tmux auto-start
    # runs first, `tmux` is not found and the session never starts.
    out = render("zshrc.j2", ts_zsh_palette=MOCHA, ts_brew_prefix="/opt/homebrew")
    assert out.index("/opt/homebrew/bin") < out.index("tmux attach")
