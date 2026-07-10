"""Behaviour: ts_platform_facts resolves per-OS path variables and exposes them
as Ansible facts so later roles (fonts, shells, configs) can consume them."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tooling.terminal_setup import platform_facts

REPO = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    shutil.which("ansible") is None, reason="ansible not installed"
)


def test_module_sets_per_os_path_facts():
    proc = subprocess.run(
        ["ansible", "localhost", "-i", "inventory/localhost.yml", "-m", "ts_platform_facts"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout.split("=>", 1)[1])
    facts = payload["ansible_facts"]
    # The module must agree with the pure resolver for whatever host runs the
    # suite (macOS or Linux), so derive the expectations from it.
    expected = platform_facts.resolve()
    assert facts["ts_os_family"] == expected.os_family
    assert facts["ts_brew_prefix"] == expected.brew_prefix
    assert facts["ts_share_dir"] == expected.brew_prefix + "/share"
    if expected.os_family == "macos":
        assert facts["ts_font_dir"].endswith("Library/Fonts")
    else:
        assert facts["ts_font_dir"].endswith(".local/share/fonts")
