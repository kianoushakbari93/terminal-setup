"""Behaviour: chsh planning decides whether to change the login shell to zsh,
skipping when it is already zsh, and surfaces a re-login notice otherwise."""
import ts_shell


def test_skip_when_login_shell_is_already_zsh():
    plan = ts_shell.plan_chsh(current_shell="/bin/zsh", target_shell="/opt/homebrew/bin/zsh")
    assert plan.needs_change is False
    assert plan.command is None


def test_changes_shell_when_not_zsh():
    plan = ts_shell.plan_chsh(current_shell="/bin/bash", target_shell="/opt/homebrew/bin/zsh")
    assert plan.needs_change is True
    assert plan.command == ["chsh", "-s", "/opt/homebrew/bin/zsh"]


def test_change_includes_relogin_notice():
    plan = ts_shell.plan_chsh(current_shell="/usr/bin/bash", target_shell="/usr/bin/zsh")
    assert plan.notice
    assert "log out" in plan.notice.lower() or "re-login" in plan.notice.lower()


def test_already_zsh_at_any_path_is_recognised():
    # A zsh at any path counts as zsh (basename match).
    plan = ts_shell.plan_chsh(current_shell="/usr/local/bin/zsh", target_shell="/opt/homebrew/bin/zsh")
    assert plan.needs_change is False
