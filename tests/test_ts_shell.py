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


def test_linux_elevates_chsh_for_the_target_user():
    # Non-root chsh is an interactive PAM prompt on Linux; the plan must use
    # sudo -n (guaranteed by pre-flight) and name the user explicitly.
    plan = ts_shell.plan_chsh(
        current_shell="/bin/bash",
        target_shell="/home/linuxbrew/.linuxbrew/bin/zsh",
        os_family="linux",
        user="alice",
    )
    assert plan.command == [
        "sudo", "-n", "chsh", "-s", "/home/linuxbrew/.linuxbrew/bin/zsh", "alice",
    ]


def test_unregistered_shell_is_added_to_etc_shells_first():
    plan = ts_shell.plan_chsh(
        current_shell="/bin/bash",
        target_shell="/home/linuxbrew/.linuxbrew/bin/zsh",
        os_family="linux",
        user="alice",
        shell_registered=False,
    )
    assert plan.register_command is not None
    assert plan.register_command[:3] == ["sudo", "-n", "sh"]
    assert "/etc/shells" in plan.register_command[-1]
    assert "/home/linuxbrew/.linuxbrew/bin/zsh" in plan.register_command[-1]


def test_registered_shell_needs_no_etc_shells_edit():
    plan = ts_shell.plan_chsh(
        current_shell="/bin/bash",
        target_shell="/usr/bin/zsh",
        os_family="linux",
        user="alice",
        shell_registered=True,
    )
    assert plan.register_command is None


def test_macos_keeps_plain_chsh():
    plan = ts_shell.plan_chsh(
        current_shell="/bin/bash",
        target_shell="/opt/homebrew/bin/zsh",
        os_family="macos",
    )
    assert plan.command == ["chsh", "-s", "/opt/homebrew/bin/zsh"]
