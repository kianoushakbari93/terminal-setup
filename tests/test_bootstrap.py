"""Behaviour: bootstrap.sh is the single entry point. We exercise its argument
handling, --check passthrough, and idempotent prerequisite detection in a dry
run that never installs anything or runs Ansible for real."""
import os
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BOOTSTRAP = REPO / "bootstrap.sh"


def run(args, dry_run=True):
    env = dict(os.environ)
    if dry_run:
        env["TS_BOOTSTRAP_DRY_RUN"] = "1"
    return subprocess.run(
        ["bash", str(BOOTSTRAP), *args],
        capture_output=True, text=True, env=env, cwd=str(REPO),
    )


def test_help_exits_zero_and_prints_usage():
    proc = run(["--help"], dry_run=False)
    assert proc.returncode == 0
    assert "Usage" in proc.stdout


def test_dry_run_plan_passes_check_through_to_ansible():
    proc = run(["--check"])
    assert proc.returncode == 0
    assert "ansible-playbook" in proc.stdout
    assert "--check" in proc.stdout


def test_dry_run_plan_without_check_has_no_check_flag():
    proc = run([])
    assert proc.returncode == 0
    assert "ansible-playbook" in proc.stdout
    assert "--check" not in proc.stdout


def test_dry_run_reports_already_present_prerequisites_as_skipped():
    # git and python3 exist on any dev box; bootstrap must detect, not reinstall.
    proc = run([])
    assert "git: present" in proc.stdout
    assert "python3: present" in proc.stdout
    # Nothing destructive should have run.
    assert "Installing" not in proc.stdout


def test_unknown_flag_fails_with_usage():
    proc = run(["--frobnicate"], dry_run=False)
    assert proc.returncode != 0
    assert "Usage" in (proc.stdout + proc.stderr)


def test_restore_lists_and_reverts_via_bootstrap(tmp_path):
    # Build a real backup snapshot with the merge engine.
    import sys
    sys.path.insert(0, str(REPO / "module_utils"))
    import ts_merge
    target = tmp_path / ".zshrc"
    target.write_text("original\n")
    backups = tmp_path / "backups"
    ts_merge.merge_config(target_path=str(target), managed_content="block", backup_root=str(backups))
    assert "original" not in target.read_text()

    # --restore --list shows the snapshot.
    listing = subprocess.run(
        ["bash", str(BOOTSTRAP), "--restore", "--backup-root", str(backups), "--list"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert listing.returncode == 0, listing.stdout + listing.stderr
    assert "snapshot" in listing.stdout.lower()

    # --restore reverts the file.
    rev = subprocess.run(
        ["bash", str(BOOTSTRAP), "--restore", "--backup-root", str(backups)],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert rev.returncode == 0, rev.stdout + rev.stderr
    assert target.read_text() == "original\n"


def test_dry_run_reports_install_plan_for_missing_prerequisite(tmp_path):
    # Build a bin dir holding every prerequisite except ansible-playbook, so
    # exactly that one reads as missing regardless of the host's real layout
    # (system dirs may or may not carry ansible-playbook).
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("bash", "dirname"):  # real binaries the script needs to run
        (bin_dir / tool).symlink_to(shutil.which(tool))
    for tool in ("brew", "git", "curl", "python3"):  # presence-only stubs
        stub = bin_dir / tool
        stub.write_text("#!/bin/sh\nexit 0\n")
        stub.chmod(0o755)

    env = dict(os.environ)
    env["TS_BOOTSTRAP_DRY_RUN"] = "1"
    env["PATH"] = str(bin_dir)
    proc = subprocess.run(
        [str(bin_dir / "bash"), str(BOOTSTRAP)],
        capture_output=True, text=True, env=env, cwd=str(REPO),
    )
    assert proc.returncode == 0
    assert "ansible-playbook: missing" in proc.stdout
    assert "would install" in proc.stdout.lower()
    assert "ansible" in proc.stdout.lower()
    # Still no real installation in dry run.
    assert "Installing" not in proc.stdout
