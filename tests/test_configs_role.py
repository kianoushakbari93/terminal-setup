"""Behaviour: the configs role deploys every entry in ts_managed_configs through
the merge engine and is idempotent. Defaults to an empty list so a real run is a
safe no-op until later slices populate it."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIXTURE = "tests/fixtures/configs_only.yml"

pytestmark = pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="ansible-playbook not installed"
)


def apply_role(managed_configs):
    extra = json.dumps({"ts_managed_configs": managed_configs})
    return subprocess.run(
        ["ansible-playbook", "-i", "inventory/localhost.yml", FIXTURE, "--extra-vars", extra],
        capture_output=True, text=True, cwd=str(REPO),
    )


def test_role_default_is_a_safe_noop():
    # No ts_managed_configs supplied -> empty default -> nothing changes.
    result = subprocess.run(
        ["ansible-playbook", "-i", "inventory/localhost.yml", FIXTURE],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "changed=0" in result.stdout


def test_role_deploys_managed_file_and_is_idempotent(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text("export MY_SECRET=42\n")
    entry = [{
        "target": str(target),
        "content": "export EDITOR=vim",
        "backup_root": str(tmp_path / "backups"),
    }]

    first = apply_role(entry)
    assert first.returncode == 0, first.stdout + first.stderr
    assert "changed=1" in first.stdout
    assert ">>> terminal-setup >>>" in target.read_text()
    assert "export MY_SECRET=42" in (tmp_path / ".zshrc.local").read_text()

    second = apply_role(entry)
    assert second.returncode == 0, second.stdout + second.stderr
    assert "changed=0" in second.stdout
