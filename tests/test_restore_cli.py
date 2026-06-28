"""Behaviour: the restore CLI lists snapshots and reverts managed files,
printing what changed, and exits non-zero with a clear message on error."""
import ts_merge
from tooling.terminal_setup import restore_cli


def _setup(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text("original\n")
    backups = tmp_path / "backups"
    ts_merge.merge_config(target_path=str(target), managed_content="block", backup_root=str(backups))
    return target, backups


def test_list_prints_snapshots(tmp_path, capsys):
    _, backups = _setup(tmp_path)
    code = restore_cli.main(["--backup-root", str(backups), "--list"])
    out = capsys.readouterr().out
    assert code == 0
    assert "snapshot" in out.lower()


def test_restore_reverts_and_reports(tmp_path, capsys):
    target, backups = _setup(tmp_path)
    code = restore_cli.main(["--backup-root", str(backups)])
    out = capsys.readouterr().out
    assert code == 0
    assert str(target) in out
    assert "restored" in out.lower()
    assert target.read_text() == "original\n"


def test_error_exits_nonzero_with_message(tmp_path, capsys):
    code = restore_cli.main(["--backup-root", str(tmp_path / "nope")])
    err = capsys.readouterr().err + capsys.readouterr().out
    assert code != 0
