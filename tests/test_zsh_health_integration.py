"""Behaviour: a real interactive zsh, loading the rendered config from a temp
ZDOTDIR, passes the full deep-health suite - clean login, p10k + plugins loaded,
glyphs present, fast startup. Non-destructive: never touches the real ~/.zshrc."""
import shutil
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

import glyphs
import ts_zsh_health as zh
from test_zsh_templates import MOCHA  # reuse the palette fixture
from tooling.terminal_setup import platform_facts

REPO = Path(__file__).resolve().parent.parent
TPL_DIR = REPO / "roles/zsh/templates"
BREW_PREFIX = platform_facts.resolve().brew_prefix  # host-appropriate (macOS/Linux)
PLUGINS_PRESENT = Path(f"{BREW_PREFIX}/share/powerlevel10k/powerlevel10k.zsh-theme").exists()

pytestmark = pytest.mark.skipif(
    shutil.which("zsh") is None or not PLUGINS_PRESENT,
    reason="needs zsh + brew zsh plugins",
)


def _render_zdotdir(dest: Path):
    env = Environment(loader=FileSystemLoader(str(TPL_DIR)), keep_trailing_newline=True)
    env.filters["glyph"] = glyphs.glyph
    ctx = dict(ts_zsh_palette=MOCHA, ts_brew_prefix=BREW_PREFIX)
    (dest / ".zshrc").write_text(env.get_template("zshrc.j2").render(**ctx))
    (dest / ".p10k.zsh").write_text(env.get_template("p10k.zsh.j2").render(**ctx))


def test_real_zsh_passes_deep_health_suite(tmp_path):
    _render_zdotdir(tmp_path)
    results = zh.run_zsh_health(str(tmp_path), threshold_s=5.0)
    failed = [r for r in results if not r.ok]
    assert not failed, "; ".join(f"{r.name}: {r.detail}" for r in failed)
