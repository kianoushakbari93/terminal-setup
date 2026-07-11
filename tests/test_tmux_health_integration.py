"""Behaviour: a real (isolated-socket) tmux server, loading the rendered config
against the real plugins, passes the full deep-health suite. Non-destructive:
the custom socket never touches the user's own tmux server."""
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

import glyphs
import ts_tmux_health as th
from test_tmux_template import MOCHA
from tooling.terminal_setup import platform_facts

REPO = Path(__file__).resolve().parent.parent
TPL_DIR = REPO / "roles/tmux/templates"
TMUX_BIN = f"{platform_facts.resolve().brew_prefix}/bin/tmux"
PLUGINS = Path.home() / ".tmux/plugins"

pytestmark = pytest.mark.skipif(
    not Path(TMUX_BIN).exists()
    or not (PLUGINS / "tpm").is_dir()
    or not (PLUGINS / "tmux/catppuccin.tmux").exists(),
    reason="needs tmux + tpm + catppuccin plugins",
)


def test_real_tmux_passes_deep_health_suite(tmp_path):
    env = Environment(loader=FileSystemLoader(str(TPL_DIR)), keep_trailing_newline=True)
    env.filters["glyph"] = glyphs.glyph
    conf = tmp_path / "tmux.conf"
    # Render to match this host's provisioned state: the provisioner installs
    # tmux-battery exactly on hosts with a battery, so its presence under the
    # real plugins dir tells us which variant this host runs.
    conf.write_text(env.get_template("tmux.conf.j2").render(
        ts_tmux_palette=MOCHA, ts_tmux_flavor="mocha",
        ts_tmux_has_battery=(PLUGINS / "tmux-battery").is_dir(),
    ))

    results = th.run_tmux_health(
        str(conf), home=str(Path.home()), tmux_bin=TMUX_BIN, socket="ts_pytest_health",
    )
    failed = [r for r in results if not r.ok]
    assert not failed, "; ".join(f"{r.name}: {r.detail}" for r in failed)
