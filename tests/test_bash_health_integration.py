"""Behaviour: a real interactive bash, loading the rendered config from a temp
HOME, passes the full deep-health suite - clean login, ble.sh + starship +
completion loaded, .local sourced, glyphs present, fast startup. Non-destructive."""
import os
import shutil
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

import glyphs
import ts_bash_health as bh
from test_bash_templates import DRACULA
from tooling.terminal_setup import platform_facts

REPO = Path(__file__).resolve().parent.parent
TPL_DIR = REPO / "roles/bash/templates"
BREW_PREFIX = platform_facts.resolve().brew_prefix  # host-appropriate (macOS/Linux)
BREW_BASH = f"{BREW_PREFIX}/bin/bash"
REAL_BLESH = Path.home() / ".local/share/blesh"

pytestmark = pytest.mark.skipif(
    not Path(BREW_BASH).exists() or shutil.which("starship") is None
    or not (REAL_BLESH / "ble.sh").exists(),
    reason="needs brew bash + starship + ble.sh",
)


def _render_home(home: Path):
    env = Environment(loader=FileSystemLoader(str(TPL_DIR)), keep_trailing_newline=True)
    env.filters["glyph"] = glyphs.glyph
    ctx = dict(ts_bash_palette=DRACULA, ts_brew_prefix=BREW_PREFIX)
    bashrc = env.get_template("bashrc.j2").render(**ctx)
    # Simulate config_merge appending the .local source line.
    bashrc += '\n[[ -f ~/.bashrc.local ]] && source ~/.bashrc.local\n'
    (home / ".bashrc").write_text(bashrc)
    (home / ".config").mkdir(exist_ok=True)
    (home / ".config/starship.toml").write_text(env.get_template("starship.toml.j2").render(**ctx))
    (home / ".bashrc.local").write_text("export TS_PROBE_LOCAL=1\n")
    # Make ble.sh resolvable under this HOME.
    (home / ".local/share").mkdir(parents=True, exist_ok=True)
    os.symlink(REAL_BLESH, home / ".local/share/blesh")


def test_real_bash_passes_deep_health_suite(tmp_path):
    _render_home(tmp_path)
    results = bh.run_bash_health(str(tmp_path), bash_bin=BREW_BASH, threshold_s=5.0)
    failed = [r for r in results if not r.ok]
    assert not failed, "; ".join(f"{r.name}: {r.detail}" for r in failed)
