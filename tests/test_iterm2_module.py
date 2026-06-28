"""Behaviour: iterm2_config is a real Ansible module. It applies font +
transparency to a plist file, reports CHANGED then ok (idempotent), and surfaces
a restart notice. Operates on a TEMP plist - never the real iTerm2 prefs."""
import json
import plistlib
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    shutil.which("ansible") is None, reason="ansible not installed"
)


def run_module(plist_path, font, transparency):
    args = f"plist_path={plist_path} font='{font}' transparency={transparency}"
    return subprocess.run(
        ["ansible", "localhost", "-i", "inventory/localhost.yml", "-m", "iterm2_config", "-a", args],
        capture_output=True, text=True, cwd=str(REPO),
    )


def parse(proc):
    out = proc.stdout
    status = out.split("|", 1)[1].split("=>", 1)[0].strip()
    payload = json.loads(out.split("=>", 1)[1])
    return status, payload


def test_applies_then_idempotent(tmp_path):
    plist = tmp_path / "iterm2.plist"
    with open(plist, "wb") as fh:
        plistlib.dump({"New Bookmarks": [
            {"Name": "Default", "Normal Font": "Old 12", "Transparency": 0.0}
        ]}, fh, fmt=plistlib.FMT_BINARY)

    first = run_module(plist, "MesloLGSNF-Regular 16", 0.2)
    assert first.returncode == 0, first.stdout + first.stderr
    status, payload = parse(first)
    assert status == "CHANGED"
    assert payload["changed"] is True
    assert "restart iterm2" in payload["notice"].lower()

    # The temp plist now has the new values.
    saved = plistlib.load(open(plist, "rb"))
    assert saved["New Bookmarks"][0]["Normal Font"] == "MesloLGSNF-Regular 16"
    assert saved["New Bookmarks"][0]["Transparency"] == 0.2

    second = run_module(plist, "MesloLGSNF-Regular 16", 0.2)
    status2, payload2 = parse(second)
    assert status2 == "SUCCESS"
    assert payload2["changed"] is False
