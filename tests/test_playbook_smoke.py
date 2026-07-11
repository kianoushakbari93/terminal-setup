"""Behaviour: the walking-skeleton playbook runs end to end - pre-flight gate
then health suite - succeeds on a ready host, is idempotent, and supports check
mode. These are slower integration tests that shell out to ansible-playbook."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PLAYBOOK = ["-i", "inventory/localhost.yml", "site.yml"]

# A session sandbox: redirect every install/deploy here so the full-pipeline
# smoke run is exercised for real WITHOUT mutating the host (no package/font
# installs, no real ~/.zshrc rewrite, no chsh).
SANDBOX = Path(tempfile.mkdtemp(prefix="ts-smoke-"))
SANDBOX_VARS = {
    "ts_fonts": [],
    # never touch the host's real terminal-emulator font in the smoke run
    "ts_terminal_font_configure": False,
    "ts_packages": [],
    # frameworks: detect/remove under the sandbox HOME, never the real one.
    "ts_frameworks_home": str(SANDBOX),
    "ts_zsh_rc": str(SANDBOX / ".zshrc"),
    "ts_zsh_p10k": str(SANDBOX / ".p10k.zsh"),
    "ts_zsh_zdotdir": str(SANDBOX),
    # bash: deploy into the sandbox; skip ble.sh install (point at real one) and
    # the deep bash health probe (sandbox HOME has no ble.sh).
    "ts_bash_rc": str(SANDBOX / ".bashrc"),
    "ts_bash_profile": str(SANDBOX / ".bash_profile"),
    "ts_starship_toml": str(SANDBOX / ".config/starship.toml"),
    "ts_bash_home": str(SANDBOX),
    "ts_blesh_dir": str(Path.home() / ".local/share/blesh"),
    "ts_bash_health_check": False,
    # tmux: deploy into the sandbox; skip tpm install and the health probe.
    "ts_tmux_conf": str(SANDBOX / ".tmux.conf"),
    "ts_tmux_install_plugins": False,
    "ts_tmux_health_check": False,
    # never change the host's real login shell in the smoke run
    "ts_chsh_enabled": False,
    # the sandbox never provisioned the live HOME, so skip the deep probes
    "ts_healthcheck_deep": False,
    # never touch the real iTerm2 prefs in the smoke run
    "skip_iterm2": True,
    "ts_backup_root": str(SANDBOX / "backups"),
}

pytestmark = pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="ansible-playbook not installed"
)


def ap(*args):
    return subprocess.run(
        ["ansible-playbook", *PLAYBOOK, "-e", json.dumps(SANDBOX_VARS), *args],
        capture_output=True, text=True, cwd=str(REPO),
    )


def test_playbook_passes_syntax_check():
    proc = ap("--syntax-check")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_playbook_runs_preflight_and_healthcheck_and_succeeds():
    proc = ap()
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 0, combined
    assert "pre-flight: all checks passed" in combined
    assert "health-check summary" in combined


def test_playbook_is_idempotent_on_second_run():
    ap()  # ensure first run has happened
    proc = ap()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # Read-only gate/health tasks must not report changes.
    assert "changed=0" in proc.stdout


def test_check_mode_runs_without_error():
    proc = ap("--check", "--diff")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_check_mode_with_default_fonts_does_not_error():
    # Even when fonts are not yet installed, --check must not fail: the post-
    # install verify probe is meaningless in check mode and must be skipped.
    proc = subprocess.run(
        ["ansible-playbook", *PLAYBOOK, "--check"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "failed=0" in proc.stdout
