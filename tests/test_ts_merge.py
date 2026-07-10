"""Behaviour: the config-merge engine owns a marker-delimited block, preserves
foreign user content losslessly into a sibling .local file, and is idempotent.
Tested directly as a pure engine (no Ansible)."""
import os

import ts_merge


BEGIN = "# >>> terminal-setup >>>"
END = "# <<< terminal-setup <<<"


def read(path):
    with open(path) as fh:
        return fh.read()


def test_fresh_target_gets_managed_block_and_guarded_source_line(tmp_path):
    target = tmp_path / ".zshrc"
    result = ts_merge.merge_config(
        target_path=str(target),
        managed_content="export EDITOR=vim",
        backup_root=str(tmp_path / "backups"),
    )

    body = read(target)
    assert BEGIN in body and END in body
    assert "export EDITOR=vim" in body
    # The block sources the .local file, guarded so a missing file is harmless.
    assert ".zshrc.local" in body
    assert result.changed is True
    assert result.backup_path is None  # nothing existed to back up


def test_existing_foreign_content_is_backed_up_and_moved_to_local(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text("export MY_SECRET=42\nalias gs='git status'\n")

    result = ts_merge.merge_config(
        target_path=str(target),
        managed_content="export EDITOR=vim",
        backup_root=str(tmp_path / "backups"),
    )

    # A backup of the original was taken before any write.
    assert result.backup_path is not None
    assert "export MY_SECRET=42" in read(result.backup_path)

    # Foreign user content now lives in the .local file.
    local = read(str(target) + ".local")
    assert "export MY_SECRET=42" in local
    assert "alias gs='git status'" in local

    # The target itself now holds the managed block and sources .local.
    body = read(target)
    assert BEGIN in body and END in body
    assert "export EDITOR=vim" in body
    assert ".zshrc.local" in body
    # Foreign content is no longer inline in the target (it moved to .local).
    assert "MY_SECRET" not in body.split(BEGIN)[0]
    assert result.changed is True


def test_known_tool_signatures_are_scrubbed_not_moved_to_local(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text(
        "\n".join(
            [
                "export KEEP_ME=1",
                "source /opt/homebrew/share/powerlevel10k/powerlevel10k.zsh-theme",
                '[[ -f ~/.p10k.zsh ]] && source ~/.p10k.zsh',
                'eval "$(starship init zsh)"',
                "source ~/.local/share/blesh/ble.sh",
                "alias ll='ls -lh'",
            ]
        )
        + "\n"
    )

    ts_merge.merge_config(
        target_path=str(target),
        managed_content="export EDITOR=vim",
        backup_root=str(tmp_path / "backups"),
        signature_patterns=ts_merge.DEFAULT_SIGNATURES,
    )

    local = read(str(target) + ".local")
    # Genuine user content is preserved...
    assert "export KEEP_ME=1" in local
    assert "alias ll='ls -lh'" in local
    # ...but tool-owned prompt/plugin lines are scrubbed, never duplicated.
    assert "powerlevel10k" not in local
    assert ".p10k.zsh" not in local
    assert "starship init" not in local
    assert "ble.sh" not in local


def test_scrubbing_an_if_guard_takes_the_whole_block_not_just_matching_lines(tmp_path):
    # The common plugin-guard pattern: only the `if` and `source` lines mention
    # the plugin. Dropping just those would strand `fi` and break the shell.
    target = tmp_path / ".zshrc"
    target.write_text(
        "\n".join(
            [
                "export KEEP_ME=1",
                "# Autosuggestions",
                "if [[ -f ~/.zsh/zsh-autosuggestions/zsh-autosuggestions.zsh ]]; then",
                "    source ~/.zsh/zsh-autosuggestions/zsh-autosuggestions.zsh",
                "fi",
                "if command -v tmux >/dev/null 2>&1; then",
                '    if [ -z "$TMUX" ]; then',
                "        tmux attach -t default || tmux new -s default",
                "    fi",
                "fi",
            ]
        )
        + "\n"
    )

    ts_merge.merge_config(
        target_path=str(target),
        managed_content="export EDITOR=vim",
        backup_root=str(tmp_path / "backups"),
        signature_patterns=ts_merge.DEFAULT_SIGNATURES,
    )

    local = read(str(target) + ".local")
    assert "export KEEP_ME=1" in local
    assert "zsh-autosuggestions" not in local
    # No stranded `fi` from the scrubbed guard block...
    assert local.count("fi") == local.count("if")
    # ...and untouched nested user blocks survive whole.
    assert "tmux attach -t default" in local
    # The scrubbed .local must still parse as shell.
    import subprocess

    proc = subprocess.run(
        ["bash", "-n", str(target) + ".local"], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr


def test_scrubbing_a_single_line_if_guard_drops_only_that_line(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text(
        "\n".join(
            [
                "export KEEP_ME=1",
                "if [ -f ~/p10k/powerlevel10k.zsh-theme ]; then source ~/p10k/powerlevel10k.zsh-theme; fi",
                "alias ll='ls -lh'",
            ]
        )
        + "\n"
    )

    ts_merge.merge_config(
        target_path=str(target),
        managed_content="export EDITOR=vim",
        backup_root=str(tmp_path / "backups"),
        signature_patterns=ts_merge.DEFAULT_SIGNATURES,
    )

    local = read(str(target) + ".local")
    assert "powerlevel10k" not in local
    assert "export KEEP_ME=1" in local
    assert "alias ll='ls -lh'" in local


def test_competing_framework_config_is_scrubbed_on_migration(tmp_path):
    # The frameworks role uninstalls oh-my-zsh / oh-my-posh, so migration must
    # not carry their config into .local (sourcing a removed path errors on
    # every shell launch).
    target = tmp_path / ".zshrc"
    target.write_text(
        "\n".join(
            [
                "export KEEP_ME=1",
                'export ZSH="$HOME/.oh-my-zsh"',
                'ZSH_THEME="robbyrussell"',
                "source $ZSH/oh-my-zsh.sh",
                "if command -v oh-my-posh >/dev/null 2>&1; then",
                '    eval "$(oh-my-posh init zsh --config atomic)"',
                "fi",
            ]
        )
        + "\n"
    )

    ts_merge.merge_config(
        target_path=str(target),
        managed_content="export EDITOR=vim",
        backup_root=str(tmp_path / "backups"),
        signature_patterns=ts_merge.DEFAULT_SIGNATURES,
    )

    local = read(str(target) + ".local")
    assert "export KEEP_ME=1" in local
    assert "oh-my-zsh" not in local
    assert "ZSH_THEME" not in local
    assert "oh-my-posh" not in local
    assert local.count("fi") == local.count("if")


def test_tmux_status_bar_theming_is_scrubbed_but_user_bindings_survive(tmp_path):
    # The tool owns the tmux status bar end-to-end; old theme lines left in
    # .local would source after the managed block and override the bar.
    target = tmp_path / ".tmux.conf"
    target.write_text(
        "\n".join(
            [
                "set -g mouse on",
                "bind | split-window -h",
                "set -g status-right '%d/%m %H:%M:%S'",
                "set -g status-left '#[bg=colour39] me'",
                "setw -g window-status-current-format ' #I:#W#F '",
                "setw -g window-status-style 'fg=colour9 bg=colour18'",
                "set -g status-position top",
                "set -g status-justify centre",
            ]
        )
        + "\n"
    )

    ts_merge.merge_config(
        target_path=str(target),
        managed_content="set -g history-limit 50000",
        source_line="source-file -q ~/.tmux.conf.local",
        backup_root=str(tmp_path / "backups"),
        signature_patterns=ts_merge.DEFAULT_SIGNATURES,
    )

    local = read(str(target) + ".local")
    # User behaviour tweaks survive...
    assert "set -g mouse on" in local
    assert "bind | split-window -h" in local
    # ...but every status-bar theming line is scrubbed.
    assert "status-right" not in local
    assert "status-left" not in local
    assert "window-status" not in local
    assert "status-position" not in local
    assert "status-justify" not in local


def test_rerun_with_unchanged_inputs_is_idempotent(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text("export MY_SECRET=42\n")
    backups = tmp_path / "backups"

    kwargs = dict(
        target_path=str(target),
        managed_content="export EDITOR=vim",
        backup_root=str(backups),
    )
    first = ts_merge.merge_config(**kwargs)
    assert first.changed is True

    target_bytes = (target).read_bytes()
    local_bytes = (tmp_path / ".zshrc.local").read_bytes()
    backups_after_first = sorted(p.name for p in backups.iterdir())

    second = ts_merge.merge_config(**kwargs)

    assert second.changed is False
    assert second.backup_path is None
    # Nothing on disk moved.
    assert target.read_bytes() == target_bytes
    assert (tmp_path / ".zshrc.local").read_bytes() == local_bytes
    assert sorted(p.name for p in backups.iterdir()) == backups_after_first


def test_managed_update_preserves_content_outside_markers(tmp_path):
    target = tmp_path / ".zshrc"
    backups = tmp_path / "backups"

    ts_merge.merge_config(
        target_path=str(target),
        managed_content="export EDITOR=vim",
        backup_root=str(backups),
    )

    # User later appends their own line AFTER the managed block.
    with open(target, "a") as fh:
        fh.write("\n# my own tweak\nexport PAGER=less\n")

    result = ts_merge.merge_config(
        target_path=str(target),
        managed_content="export EDITOR=nvim",  # changed
        backup_root=str(backups),
    )

    body = read(target)
    assert "export EDITOR=nvim" in body       # block updated
    assert "export EDITOR=vim" not in body     # old block content gone
    assert "export PAGER=less" in body         # user's outside line preserved
    assert "# my own tweak" in body
    assert result.changed is True
    assert result.backup_path is not None      # change => backup


def test_backup_records_a_manifest_entry(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text("export MY_SECRET=42\n")
    backups = tmp_path / "backups"

    result = ts_merge.merge_config(
        target_path=str(target),
        managed_content="export EDITOR=vim",
        backup_root=str(backups),
    )

    manifest = ts_merge.read_manifest(str(backups))
    # The manifest maps the original path to where it was backed up.
    assert any(
        e.original == str(target) and e.backup == result.backup_path for e in manifest
    )


def test_custom_markers_and_source_line_are_honoured(tmp_path):
    target = tmp_path / "tmux.conf"
    begin = "# --- terminal-setup begin ---"
    end = "# --- terminal-setup end ---"

    kwargs = dict(
        target_path=str(target),
        managed_content="set -g status on",
        begin_marker=begin,
        end_marker=end,
        source_line='source-file ~/.tmux.conf.local',
        backup_root=str(tmp_path / "backups"),
    )
    ts_merge.merge_config(**kwargs)

    body = read(target)
    assert begin in body and end in body
    assert "set -g status on" in body
    assert "source-file ~/.tmux.conf.local" in body
    # Idempotent with the custom markers too.
    assert ts_merge.merge_config(**kwargs).changed is False


def test_verify_passes_for_a_correctly_merged_file(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text("export MY_SECRET=42\n")
    ts_merge.merge_config(
        target_path=str(target),
        managed_content="export EDITOR=vim",
        backup_root=str(tmp_path / "backups"),
    )

    result = ts_merge.verify(str(target), managed_content="export EDITOR=vim")
    assert result.ok is True
    assert result.problems == []


def test_verify_fails_when_block_missing_or_stale(tmp_path):
    target = tmp_path / ".zshrc"
    target.write_text("just some user content, no managed block\n")

    missing = ts_merge.verify(str(target), managed_content="export EDITOR=vim")
    assert missing.ok is False
    assert any("block" in p.lower() for p in missing.problems)

    # Present block but stale managed content.
    ts_merge.merge_config(
        target_path=str(target),
        managed_content="export EDITOR=vim",
        backup_root=str(tmp_path / "backups"),
    )
    stale = ts_merge.verify(str(target), managed_content="export EDITOR=nvim")
    assert stale.ok is False
