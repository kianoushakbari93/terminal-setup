"""Behaviour: the bash role deploys .bashrc, .bash_profile and starship.toml
through the merge engine (foreign content preserved in .local), renders real
glyphs, passes the deep health probe, and is idempotent. Deploys into a temp
dir - never the real home."""
import json
import os
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIXTURE = "tests/fixtures/bash_only.yml"
BREW_BASH = "/opt/homebrew/bin/bash"
REAL_BLESH = Path.home() / ".local/share/blesh"

pytestmark = pytest.mark.skipif(
    shutil.which("ansible-playbook") is None or not Path(BREW_BASH).exists()
    or shutil.which("starship") is None or not (REAL_BLESH / "ble.sh").exists(),
    reason="needs ansible-playbook + brew bash + starship + ble.sh",
)


def apply(tmp, health=True):
    import subprocess
    # Pre-symlink ble.sh so the role's idempotent check skips installation.
    blesh_dir = tmp / ".local/share/blesh"
    blesh_dir.parent.mkdir(parents=True, exist_ok=True)
    if not blesh_dir.exists():
        os.symlink(REAL_BLESH, blesh_dir)
    extra = {
        "ts_bash_rc": str(tmp / ".bashrc"),
        "ts_bash_profile": str(tmp / ".bash_profile"),
        "ts_starship_toml": str(tmp / ".config/starship.toml"),
        "ts_bash_home": str(tmp),
        "ts_blesh_dir": str(blesh_dir),
        "ts_bash_bin": BREW_BASH,
        "ts_backup_root": str(tmp / "backups"),
        "ts_bash_health_check": health,
    }
    return subprocess.run(
        ["ansible-playbook", "-i", "inventory/localhost.yml", FIXTURE,
         "--extra-vars", json.dumps(extra)],
        capture_output=True, text=True, cwd=str(REPO),
    )


def test_deploys_glyphs_preserves_foreign_and_is_healthy(tmp_path):
    (tmp_path / ".bashrc").write_text("export MY_CUSTOM=1\n")

    first = apply(tmp_path)
    assert first.returncode == 0, first.stdout + first.stderr

    bashrc = (tmp_path / ".bashrc").read_text()
    assert ">>> terminal-setup >>>" in bashrc
    assert "starship init bash" in bashrc
    assert "export MY_CUSTOM=1" in (tmp_path / ".bashrc.local").read_text()

    toml = (tmp_path / ".config/starship.toml").read_text(encoding="utf-8")
    assert 0xE0B0 in {ord(c) for c in toml}  # real triangle survived

    assert "failed=0" in first.stdout  # deep bash health probe passed


def test_rerun_is_idempotent(tmp_path):
    apply(tmp_path, health=False)
    second = apply(tmp_path, health=False)
    assert second.returncode == 0, second.stdout + second.stderr
    assert "changed=0" in second.stdout
