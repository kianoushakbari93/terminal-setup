"""Behaviour: the packages role installs each entry via the resolved manager,
is idempotent, and a health probe confirms the package resolves on PATH. Uses
tmux (already present) so the test never installs new software."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIXTURE = "tests/fixtures/packages_only.yml"

pytestmark = pytest.mark.skipif(
    shutil.which("ansible-playbook") is None or shutil.which("brew") is None,
    reason="needs ansible-playbook + brew",
)


def apply_role(ts_packages):
    extra = json.dumps({"ts_packages": ts_packages})
    return subprocess.run(
        ["ansible-playbook", "-i", "inventory/localhost.yml", FIXTURE, "--extra-vars", extra],
        capture_output=True, text=True, cwd=str(REPO),
    )


def test_role_default_is_a_safe_noop():
    result = subprocess.run(
        ["ansible-playbook", "-i", "inventory/localhost.yml", FIXTURE],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "changed=0" in result.stdout


def test_role_installs_idempotently_and_probe_confirms_on_path():
    pkgs = [{"name": "tmux", "kind": "stack", "check": "tmux"}]
    result = apply_role(pkgs)
    assert result.returncode == 0, result.stdout + result.stderr
    # tmux already present -> nothing installed.
    assert "changed=0" in result.stdout
    # The on-PATH health probe ran and passed (play succeeded with failed=0).
    assert "failed=0" in result.stdout
