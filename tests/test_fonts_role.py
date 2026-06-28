"""Behaviour: the fonts role installs each font idempotently and a health probe
verifies discoverability. Uses Meslo (already present on this Mac) for the real
run, and a --check run to confirm all three are wired without installing."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIXTURE = "tests/fixtures/fonts_only.yml"

pytestmark = pytest.mark.skipif(
    shutil.which("ansible-playbook") is None or shutil.which("brew") is None,
    reason="needs ansible-playbook + brew",
)


def run(extra=None, check=False, tags=None):
    cmd = ["ansible-playbook", "-i", "inventory/localhost.yml", FIXTURE]
    if extra is not None:
        cmd += ["--extra-vars", json.dumps(extra)]
    if check:
        cmd.append("--check")
    if tags:
        cmd += ["--tags", tags]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))


def test_present_font_is_idempotent_and_probe_passes():
    result = run({"ts_fonts": ["meslo"]})
    assert result.returncode == 0, result.stdout + result.stderr
    # Meslo already present -> nothing installed, and the discoverability probe
    # (a check-mode re-run with failed_when changed) passed.
    assert "changed=0" in result.stdout
    assert "failed=0" in result.stdout


def test_all_three_fonts_install_step_is_wired_via_check_mode():
    # --check the install step only (the verify probe legitimately fails in check
    # mode for not-yet-installed fonts). This confirms all three are planned to
    # install without performing any install.
    result = run(
        {"ts_fonts": ["meslo", "jetbrains", "firacode"]}, check=True, tags="fonts_install"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "failed=0" in result.stdout


def test_role_default_lists_all_three_fonts():
    # The role's default ts_fonts must cover all three required fonts.
    defaults = (REPO / "roles/fonts/defaults/main.yml").read_text()
    for f in ("meslo", "jetbrains", "firacode"):
        assert f in defaults
