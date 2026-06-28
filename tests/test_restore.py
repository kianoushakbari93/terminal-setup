"""Behaviour: restore reverts managed files from a backup snapshot using the
manifest the merge engine writes. Pure logic, tested against temp dirs."""
import pytest

import ts_merge  # module_utils: writes backups + manifest
from tooling.terminal_setup import restore


def _merge(target, content, backups):
    return ts_merge.merge_config(
        target_path=str(target), managed_content=content, backup_root=str(backups),
    )


def test_manifest_filename_contract_matches_writer():
    # restore (reader) and ts_merge (writer) must agree on the manifest filename.
    assert restore.MANIFEST_NAME == ts_merge.MANIFEST_NAME


def test_restore_reverts_a_merged_file_to_its_original(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text("original user content\n")
    backups = tmp_path / "backups"

    _merge(target, "export EDITOR=vim", backups)  # backs up original, rewrites target
    assert "original user content" not in target.read_text()  # changed by merge

    result = restore.restore(str(backups))

    assert target.read_text() == "original user content\n"  # reverted
    originals = [e.original for e in result.entries]
    assert str(target) in originals


def test_lists_snapshots_and_restores_latest_then_specific(tmp_path):
    from datetime import datetime
    target = tmp_path / ".zshrc"
    target.write_text("v0\n")
    backups = tmp_path / "backups"

    # Two merges at distinct timestamps -> two snapshots.
    _merge_at(target, "blockA", backups, datetime(2026, 1, 1, 10, 0, 0))
    _merge_at(target, "blockB", backups, datetime(2026, 1, 1, 11, 0, 0))

    snaps = restore.list_snapshots(str(backups))
    assert len(snaps) == 2
    assert snaps == sorted(snaps)

    # Latest snapshot's backup is the blockA-era file.
    restore.restore(str(backups))
    assert "blockA" in target.read_text()

    # Restoring the earliest snapshot brings back the very first content (v0).
    restore.restore(str(backups), snapshot=snaps[0])
    assert target.read_text() == "v0\n"


def _merge_at(target, content, backups, when):
    return ts_merge.merge_config(
        target_path=str(target), managed_content=content,
        backup_root=str(backups), now=when,
    )


def test_restore_is_idempotent(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text("original\n")
    backups = tmp_path / "backups"
    _merge(target, "block", backups)

    first = restore.restore(str(backups))
    assert any(e.changed for e in first.entries)  # reverted something

    second = restore.restore(str(backups))
    assert all(not e.changed for e in second.entries)  # nothing left to revert
    assert target.read_text() == "original\n"


def test_restore_errors_when_backup_root_missing(tmp_path):
    with pytest.raises(restore.RestoreError):
        restore.restore(str(tmp_path / "does-not-exist"))


def test_restore_errors_when_no_snapshots(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    with pytest.raises(restore.RestoreError) as exc:
        restore.restore(str(backups))
    assert "no backup snapshots" in str(exc.value)


def test_restore_errors_on_unknown_snapshot(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text("x\n")
    backups = tmp_path / "backups"
    _merge(target, "block", backups)
    with pytest.raises(restore.RestoreError) as exc:
        restore.restore(str(backups), snapshot="20990101T000000Z")
    assert "not found" in str(exc.value)
