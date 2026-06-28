"""Behaviour: config_merge is a real Ansible module. Through Ansible it merges a
target, reports CHANGED the first time and ok (not changed) on a clean re-run."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    shutil.which("ansible") is None, reason="ansible not installed"
)


def run_module(target, managed, backup_root):
    args = f"target_path={target} managed_content='{managed}' backup_root={backup_root}"
    return subprocess.run(
        ["ansible", "localhost", "-i", "inventory/localhost.yml", "-m", "config_merge", "-a", args],
        capture_output=True, text=True, cwd=str(REPO),
    )


def parse(proc):
    # ad-hoc prints:  "localhost | CHANGED => { json }"  or  "| SUCCESS => {...}"
    out = proc.stdout
    status = out.split("|", 1)[1].split("=>", 1)[0].strip()
    payload = json.loads(out.split("=>", 1)[1])
    return status, payload


def test_module_merges_then_is_idempotent(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text("export MY_SECRET=42\n")
    backups = tmp_path / "backups"

    first = run_module(target, "export EDITOR=vim", backups)
    assert first.returncode == 0, first.stdout + first.stderr
    status1, payload1 = parse(first)
    assert status1 == "CHANGED"
    assert payload1["changed"] is True
    assert payload1["backup_path"]  # original was backed up
    # The module self-verifies the merge invariants (the health-probe check).
    assert payload1["verified"] is True

    # Foreign content preserved in .local; managed block in the target.
    assert "export MY_SECRET=42" in (tmp_path / ".zshrc.local").read_text()
    assert ">>> terminal-setup >>>" in target.read_text()

    second = run_module(target, "export EDITOR=vim", backups)
    status2, payload2 = parse(second)
    assert status2 == "SUCCESS"          # ad-hoc reports ok (not changed)
    assert payload2["changed"] is False


def test_check_mode_previews_diff_without_writing(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text("export MY_SECRET=42\n")
    backups = tmp_path / "backups"
    before = target.read_text()

    args = f"target_path={target} managed_content='export EDITOR=vim' backup_root={backups}"
    proc = subprocess.run(
        ["ansible", "localhost", "-i", "inventory/localhost.yml", "-C", "--diff",
         "-m", "config_merge", "-a", args],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    status, payload = parse(proc)
    assert status == "CHANGED"            # would change
    assert payload["changed"] is True
    # A diff was produced (before/after).
    assert "diff" in payload or "--- " in proc.stdout
    # But nothing was actually written, and no backup taken.
    assert target.read_text() == before
    assert not backups.exists()
