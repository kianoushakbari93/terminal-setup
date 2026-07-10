"""Behaviour: the zsh role deploys ~/.zshrc and ~/.p10k.zsh through the merge
engine (foreign content preserved in .local), renders real glyphs, passes the
deep health probe, and is idempotent. Deploys into a temp dir - never the real
home."""
import json
import shutil
from pathlib import Path

import pytest

from tooling.terminal_setup import platform_facts

REPO = Path(__file__).resolve().parent.parent
FIXTURE = "tests/fixtures/zsh_only.yml"
BREW_PREFIX = platform_facts.resolve().brew_prefix  # host-appropriate (macOS/Linux)
PLUGINS_PRESENT = Path(f"{BREW_PREFIX}/share/powerlevel10k/powerlevel10k.zsh-theme").exists()

pytestmark = pytest.mark.skipif(
    shutil.which("ansible-playbook") is None or not PLUGINS_PRESENT,
    reason="needs ansible-playbook + brew zsh plugins",
)


def apply(tmp, health=True, run=None):
    import subprocess
    extra = {
        "ts_zsh_rc": str(tmp / ".zshrc"),
        "ts_zsh_p10k": str(tmp / ".p10k.zsh"),
        "ts_zsh_zdotdir": str(tmp),
        "ts_backup_root": str(tmp / "backups"),
        "ts_zsh_health_check": health,
    }
    return subprocess.run(
        ["ansible-playbook", "-i", "inventory/localhost.yml", FIXTURE,
         "--extra-vars", json.dumps(extra)],
        capture_output=True, text=True, cwd=str(REPO),
    )


def test_deploys_glyphs_preserves_foreign_and_is_healthy(tmp_path):
    # Pre-existing user content must survive into .local.
    (tmp_path / ".zshrc").write_text("export MY_CUSTOM=1\n")

    first = apply(tmp_path)
    assert first.returncode == 0, first.stdout + first.stderr

    zshrc = (tmp_path / ".zshrc").read_text()
    assert ">>> terminal-setup >>>" in zshrc
    assert "powerlevel10k.zsh-theme" in zshrc
    assert "export MY_CUSTOM=1" in (tmp_path / ".zshrc.local").read_text()

    p10k = (tmp_path / ".p10k.zsh").read_text(encoding="utf-8")
    assert 0xE0B4 in {ord(c) for c in p10k}  # real glyph survived deployment

    # The deep zsh health probe ran and passed (play succeeded with failed=0).
    assert "failed=0" in first.stdout


def test_rerun_is_idempotent(tmp_path):
    apply(tmp_path, health=False)
    second = apply(tmp_path, health=False)
    assert second.returncode == 0, second.stdout + second.stderr
    assert "changed=0" in second.stdout
