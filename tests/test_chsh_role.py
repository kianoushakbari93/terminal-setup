"""Behaviour: the chsh role sets zsh as the default shell idempotently. This dev
host already uses zsh, so the role must report ok (not changed) - proving the
skip-when-already-zsh path without modifying the login shell."""
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIXTURE = "tests/fixtures/chsh_only.yml"

pytestmark = pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="ansible-playbook not installed"
)


def test_skips_when_already_zsh():
    proc = subprocess.run(
        ["ansible-playbook", "-i", "inventory/localhost.yml", FIXTURE],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # Already zsh on this host -> nothing changed.
    assert "changed=0" in proc.stdout
    assert "failed=0" in proc.stdout
