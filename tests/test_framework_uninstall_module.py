"""Behaviour: framework_uninstall is a real Ansible module. Against a temp HOME
it removes oh-my-zsh (backing up custom/), scrubs framework references from the
rc .local files, and is idempotent - all without touching the real home."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    shutil.which("ansible") is None, reason="ansible not installed"
)


def run_module(args):
    return subprocess.run(
        ["ansible", "localhost", "-i", "inventory/localhost.yml",
         "-m", "framework_uninstall", "-a", args],
        capture_output=True, text=True, cwd=str(REPO),
    )


def parse(proc):
    out = proc.stdout
    status = out.split("|", 1)[1].split("=>", 1)[0].strip()
    payload = json.loads(out.split("=>", 1)[1])
    return status, payload


def seed_home(home: Path):
    omz = home / ".oh-my-zsh"
    (omz / "custom").mkdir(parents=True)
    (omz / "oh-my-zsh.sh").write_text("# omz\n")
    (omz / "custom" / "mine.zsh").write_text("alias mine=1\n")
    (home / ".zshrc.local").write_text(
        "export KEEP=1\n"
        'export ZSH="$HOME/.oh-my-zsh"\n'
        'ZSH_THEME="robbyrussell"\n'
        "source $ZSH/oh-my-zsh.sh\n"
        "alias ll='ls -l'\n"
    )


def test_removes_framework_scrubs_locals_and_backs_up(tmp_path):
    seed_home(tmp_path)
    proc = run_module(f"home={tmp_path} backup_root={tmp_path}/backups")
    status, payload = parse(proc)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert status == "CHANGED"
    assert payload["removed"] == ["oh-my-zsh"]
    assert not (tmp_path / ".oh-my-zsh").exists()

    # References gone, user content intact.
    local = (tmp_path / ".zshrc.local").read_text()
    assert "oh-my-zsh" not in local
    assert "ZSH_THEME" not in local
    assert "export KEEP=1" in local
    assert "alias ll='ls -l'" in local

    # custom/ survived into the snapshot; the scrubbed .local was backed up too.
    snapshots = list((tmp_path / "backups").glob("*/oh-my-zsh-custom/mine.zsh"))
    assert snapshots and snapshots[0].read_text() == "alias mine=1\n"
    assert list((tmp_path / "backups").glob("*/.zshrc.local"))


def test_rerun_is_idempotent(tmp_path):
    seed_home(tmp_path)
    run_module(f"home={tmp_path} backup_root={tmp_path}/backups")
    status, payload = parse(run_module(f"home={tmp_path} backup_root={tmp_path}/backups"))
    assert status == "SUCCESS"
    assert payload["changed"] is False


def test_clean_home_is_a_clean_noop(tmp_path):
    status, payload = parse(run_module(f"home={tmp_path} backup_root={tmp_path}/backups"))
    assert status == "SUCCESS"
    assert payload["changed"] is False
    assert payload["removed"] == []
