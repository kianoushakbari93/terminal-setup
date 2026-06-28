"""Behaviour: package_install is a real Ansible module. Through Ansible it
resolves a logical package and installs it idempotently. tmux is already present
on this dev host, so it must report ok (not changed) - proving the idempotent
path without installing anything new."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    shutil.which("ansible") is None or shutil.which("brew") is None,
    reason="needs ansible + brew",
)


def run_module(args):
    return subprocess.run(
        ["ansible", "localhost", "-i", "inventory/localhost.yml", "-m", "package_install", "-a", args],
        capture_output=True, text=True, cwd=str(REPO),
    )


def parse(proc):
    out = proc.stdout
    status = out.split("|", 1)[1].split("=>", 1)[0].strip()
    payload = json.loads(out.split("=>", 1)[1])
    return status, payload


def test_already_present_package_is_ok_not_changed():
    proc = run_module("name=tmux kind=stack")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    status, payload = parse(proc)
    assert status == "SUCCESS"          # ok, not changed
    assert payload["changed"] is False
    assert payload["manager"] == "brew"
    assert payload["name"] == "tmux"


def test_unsupported_distro_fails_with_clear_message():
    proc = run_module("name=git kind=prereq os_family=linux distro=gentoo")
    assert proc.returncode != 0
    assert "gentoo" in (proc.stdout + proc.stderr)
