"""Behaviour: font_install is a real Ansible module. On this Mac the Meslo Nerd
Font is already present, so it reports ok (not changed) - proving the idempotent
discoverability path without installing anything. Unknown fonts fail clearly."""
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
        ["ansible", "localhost", "-i", "inventory/localhost.yml", "-m", "font_install", "-a", args],
        capture_output=True, text=True, cwd=str(REPO),
    )


def parse(proc):
    out = proc.stdout
    status = out.split("|", 1)[1].split("=>", 1)[0].strip()
    payload = json.loads(out.split("=>", 1)[1])
    return status, payload


def test_already_present_font_is_ok_not_changed():
    proc = run_module("name=meslo")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    status, payload = parse(proc)
    assert status == "SUCCESS"
    assert payload["changed"] is False


def test_unknown_font_fails_clearly():
    proc = run_module("name=comic-sans")
    assert proc.returncode != 0
    assert "comic-sans" in (proc.stdout + proc.stderr)
