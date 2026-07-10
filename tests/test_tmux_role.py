"""Behaviour: the tmux role deploys ~/.tmux.conf through the merge engine
(foreign content preserved in .local), renders real cap glyphs, passes the deep
health probe against the real plugins, and is idempotent. Deploys into a temp
file - never the real ~/.tmux.conf. tpm install is skipped (plugins present)."""
import json
import shutil
from pathlib import Path

import pytest

from tooling.terminal_setup import platform_facts

REPO = Path(__file__).resolve().parent.parent
FIXTURE = "tests/fixtures/tmux_only.yml"
TMUX_BIN = f"{platform_facts.resolve().brew_prefix}/bin/tmux"
PLUGINS = Path.home() / ".tmux/plugins"

pytestmark = pytest.mark.skipif(
    shutil.which("ansible-playbook") is None or not Path(TMUX_BIN).exists()
    or not (PLUGINS / "tmux/catppuccin.tmux").exists(),
    reason="needs ansible-playbook + tmux + catppuccin plugin",
)


def apply(tmp, health=True):
    import subprocess
    extra = {
        "ts_tmux_conf": str(tmp / ".tmux.conf"),
        "ts_tmux_home": str(Path.home()),  # real plugins
        "ts_tmux_bin": TMUX_BIN,
        "ts_backup_root": str(tmp / "backups"),
        "ts_tmux_install_plugins": False,  # plugins already present; defer installs
        "ts_tmux_health_check": health,
    }
    return subprocess.run(
        ["ansible-playbook", "-i", "inventory/localhost.yml", FIXTURE,
         "--extra-vars", json.dumps(extra)],
        capture_output=True, text=True, cwd=str(REPO),
    )


def test_deploys_glyphs_preserves_foreign_and_is_healthy(tmp_path):
    (tmp_path / ".tmux.conf").write_text("set -g mouse off  # my custom setting\n")

    first = apply(tmp_path)
    assert first.returncode == 0, first.stdout + first.stderr

    conf = (tmp_path / ".tmux.conf").read_text(encoding="utf-8")
    assert ">>> terminal-setup >>>" in conf
    assert 0xE0B6 in {ord(c) for c in conf}  # real rounded cap survived
    assert "set -g mouse off  # my custom setting" in (tmp_path / ".tmux.conf.local").read_text()

    assert "failed=0" in first.stdout  # deep tmux health probe passed


def test_rerun_is_idempotent(tmp_path):
    apply(tmp_path, health=False)
    second = apply(tmp_path, health=False)
    assert second.returncode == 0, second.stdout + second.stderr
    assert "changed=0" in second.stdout
