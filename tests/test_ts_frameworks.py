"""Behaviour: the framework layer detects oh-my-zsh / oh-my-posh installations,
never plans deletions outside the home directory, and applies removals with the
user's custom content backed up first. Pure logic with injectable probes."""
import os
from pathlib import Path

import ts_frameworks as fw


def make_omz(home: Path, custom=True):
    omz = home / ".oh-my-zsh"
    (omz / "lib").mkdir(parents=True)
    (omz / "oh-my-zsh.sh").write_text("# omz\n")
    if custom:
        (omz / "custom").mkdir()
        (omz / "custom" / "aliases.zsh").write_text("alias mine=1\n")
    return omz


def make_omp(home: Path):
    binary = home / ".local/bin/oh-my-posh"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o755)
    cache = home / ".cache/oh-my-posh"
    cache.mkdir(parents=True)
    return binary


def test_detects_oh_my_zsh_with_custom_content_backup(tmp_path):
    make_omz(tmp_path)
    removals = fw.detect(str(tmp_path), which_fn=lambda _: None, brew_has_fn=lambda _: False)
    assert [r.framework for r in removals] == ["oh-my-zsh"]
    assert removals[0].paths == [str(tmp_path / ".oh-my-zsh")]
    assert removals[0].backup_dirs == [str(tmp_path / ".oh-my-zsh/custom")]


def test_detects_oh_my_posh_binary_and_leftovers_inside_home(tmp_path):
    binary = make_omp(tmp_path)
    removals = fw.detect(
        str(tmp_path), which_fn=lambda _: str(binary), brew_has_fn=lambda _: False
    )
    assert [r.framework for r in removals] == ["oh-my-posh"]
    assert str(binary) in removals[0].paths
    assert str(tmp_path / ".cache/oh-my-posh") in removals[0].paths
    assert removals[0].brew_formula is None


def test_system_wide_binary_outside_home_is_never_deleted(tmp_path):
    removals = fw.detect(
        str(tmp_path),
        which_fn=lambda _: "/usr/local/bin/oh-my-posh",
        brew_has_fn=lambda _: False,
    )
    assert removals == []


def test_brew_owned_oh_my_posh_is_planned_via_brew(tmp_path):
    removals = fw.detect(
        str(tmp_path), which_fn=lambda _: None, brew_has_fn=lambda f: f == "oh-my-posh"
    )
    assert [r.framework for r in removals] == ["oh-my-posh"]
    assert removals[0].brew_formula == "oh-my-posh"


def test_nothing_installed_detects_nothing(tmp_path):
    assert fw.detect(str(tmp_path), which_fn=lambda _: None, brew_has_fn=lambda _: False) == []


def test_apply_backs_up_custom_then_deletes_and_brew_uninstalls(tmp_path):
    home = tmp_path / "home"
    make_omz(home)
    binary = make_omp(home)
    snapshot = tmp_path / "backups" / "20260710T000000Z"
    brewed = []

    removals = fw.detect(
        str(home), which_fn=lambda _: str(binary), brew_has_fn=lambda f: f == "oh-my-posh"
    )
    result = fw.apply(removals, str(snapshot), brew_uninstall_fn=brewed.append)

    assert result.removed == ["oh-my-zsh", "oh-my-posh"]
    assert not (home / ".oh-my-zsh").exists()
    assert not binary.exists()
    assert not (home / ".cache/oh-my-posh").exists()
    # User custom content survived into the snapshot...
    saved = snapshot / "oh-my-zsh-custom" / "aliases.zsh"
    assert saved.read_text() == "alias mine=1\n"
    assert str(snapshot / "oh-my-zsh-custom") in result.backed_up
    # ...and the brew formula went through the injected uninstaller.
    assert brewed == ["oh-my-posh"]


def test_apply_of_empty_plan_changes_nothing(tmp_path):
    result = fw.apply([], str(tmp_path / "snap"), brew_uninstall_fn=lambda _: None)
    assert result.removed == []
    assert not (tmp_path / "snap").exists()
