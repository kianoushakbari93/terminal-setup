"""Behaviour: the iterm2 role applies font+transparency on macOS, skips on
--skip-iterm2, no-ops on non-macOS, and is idempotent. Operates on a TEMP plist
- never the real iTerm2 prefs."""
import json
import plistlib
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIXTURE = "tests/fixtures/iterm2_only.yml"

pytestmark = pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="ansible-playbook not installed"
)


def make_plist(tmp):
    path = tmp / "iterm2.plist"
    with open(path, "wb") as fh:
        plistlib.dump({"New Bookmarks": [
            {"Name": "Default", "Normal Font": "Old 12", "Transparency": 0.0}
        ]}, fh, fmt=plistlib.FMT_BINARY)
    return path


def apply(plist, **over):
    extra = {"ts_iterm2_plist": str(plist)}
    extra.update(over)
    return subprocess.run(
        ["ansible-playbook", "-i", "inventory/localhost.yml", FIXTURE, "--extra-vars", json.dumps(extra)],
        capture_output=True, text=True, cwd=str(REPO),
    )


def test_applies_and_prints_restart_notice_on_macos(tmp_path):
    plist = make_plist(tmp_path)
    proc = apply(plist)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "changed=1" in proc.stdout
    assert "Restart iTerm2" in proc.stdout  # notice printed
    saved = plistlib.load(open(plist, "rb"))
    assert saved["New Bookmarks"][0]["Normal Font"] == "MesloLGSNF-Regular 16"


def test_rerun_is_idempotent(tmp_path):
    plist = make_plist(tmp_path)
    apply(plist)
    second = apply(plist)
    assert "changed=0" in second.stdout


def test_skip_iterm2_skips_the_role(tmp_path):
    plist = make_plist(tmp_path)
    proc = apply(plist, skip_iterm2=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "changed=0" in proc.stdout
    # Plist untouched.
    saved = plistlib.load(open(plist, "rb"))
    assert saved["New Bookmarks"][0]["Normal Font"] == "Old 12"


def test_non_macos_is_a_clean_noop(tmp_path):
    plist = make_plist(tmp_path)
    proc = apply(plist, ts_is_macos=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "changed=0" in proc.stdout
    saved = plistlib.load(open(plist, "rb"))
    assert saved["New Bookmarks"][0]["Normal Font"] == "Old 12"
