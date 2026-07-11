"""Behaviour: the package layer selects the right manager per platform, resolves
logical package names to concrete ones, and builds correct probe/install
commands. Pure logic, unit-tested directly."""
import pytest

import ts_packages as pkg


def test_macos_uses_brew_for_both_native_and_stack():
    m = pkg.select_managers(os_family="macos")
    assert m.native == "brew"
    assert m.stack == "brew"


def test_linux_uses_native_pm_for_prereqs_and_brew_for_stack():
    assert pkg.select_managers(os_family="linux", distro="ubuntu").native == "apt"
    assert pkg.select_managers(os_family="linux", distro="debian").native == "apt"
    assert pkg.select_managers(os_family="linux", distro="fedora").native == "dnf"
    assert pkg.select_managers(os_family="linux", distro="arch").native == "pacman"
    # The terminal stack always comes from Homebrew (Linuxbrew) on Linux.
    assert pkg.select_managers(os_family="linux", distro="ubuntu").stack == "brew"


def test_unsupported_distro_raises_clear_error():
    with pytest.raises(pkg.UnsupportedPlatform) as exc:
        pkg.select_managers(os_family="linux", distro="gentoo")
    assert "gentoo" in str(exc.value)


# logical -> per-manager concrete name overrides
PKG_MAP = {
    "fd": {"apt": "fd-find", "dnf": "fd-find"},
    "tmux": {},
}


def test_stack_package_resolves_to_brew_on_any_os():
    r_mac = pkg.resolve("tmux", kind="stack", os_family="macos", package_map=PKG_MAP)
    r_lin = pkg.resolve("tmux", kind="stack", os_family="linux", distro="ubuntu", package_map=PKG_MAP)
    assert r_mac.manager == "brew" and r_mac.name == "tmux"
    assert r_lin.manager == "brew" and r_lin.name == "tmux"


def test_stack_package_needs_no_distro_even_on_unknown_linux():
    # The stack installs via Linuxbrew regardless of distro, so an unknown (or
    # unspecified) distro must not block a stack resolution on Linux.
    r_none = pkg.resolve("tmux", kind="stack", os_family="linux", package_map=PKG_MAP)
    r_gentoo = pkg.resolve("tmux", kind="stack", os_family="linux", distro="gentoo", package_map=PKG_MAP)
    assert r_none.manager == "brew" and r_none.name == "tmux"
    assert r_gentoo.manager == "brew" and r_gentoo.name == "tmux"


def test_prereq_package_resolves_to_native_manager():
    r = pkg.resolve("git", kind="prereq", os_family="linux", distro="fedora", package_map=PKG_MAP)
    assert r.manager == "dnf"
    assert r.name == "git"  # no override -> logical name


def test_concrete_name_uses_map_override_for_the_chosen_manager():
    r = pkg.resolve("fd", kind="prereq", os_family="linux", distro="ubuntu", package_map=PKG_MAP)
    assert r.manager == "apt"
    assert r.name == "fd-find"  # apt override applied


def test_is_installed_command_per_manager():
    assert pkg.is_installed_cmd("brew", "tmux") == ["brew", "list", "--formula", "tmux"]
    assert pkg.is_installed_cmd("apt", "tmux") == ["dpkg", "-s", "tmux"]
    assert pkg.is_installed_cmd("dnf", "tmux") == ["rpm", "-q", "tmux"]
    assert pkg.is_installed_cmd("pacman", "tmux") == ["pacman", "-Q", "tmux"]


def test_install_command_per_manager():
    assert pkg.install_cmd("brew", "tmux") == ["brew", "install", "tmux"]
    assert pkg.install_cmd("apt", "tmux")[:3] == ["apt-get", "install", "-y"]
    assert pkg.install_cmd("dnf", "tmux") == ["dnf", "install", "-y", "tmux"]
    assert pkg.install_cmd("pacman", "tmux") == ["pacman", "-S", "--noconfirm", "tmux"]


def test_native_managers_need_sudo_but_brew_does_not():
    assert pkg.needs_sudo("brew") is False
    for m in ("apt", "dnf", "pacman"):
        assert pkg.needs_sudo(m) is True


def test_unknown_manager_commands_raise():
    with pytest.raises(pkg.UnsupportedPlatform):
        pkg.install_cmd("zypper", "tmux")


def test_paths_derive_share_and_font_dirs_per_os():
    mac = pkg.resolve_paths(os_family="macos", brew_prefix="/opt/homebrew")
    assert mac.brew_prefix == "/opt/homebrew"
    assert mac.share_dir == "/opt/homebrew/share"
    assert mac.font_dir.endswith("Library/Fonts")

    lin = pkg.resolve_paths(os_family="linux", brew_prefix="/home/linuxbrew/.linuxbrew")
    assert lin.share_dir == "/home/linuxbrew/.linuxbrew/share"
    assert lin.font_dir.endswith(".local/share/fonts")


def test_brew_commands_can_pin_an_absolute_brew_path():
    # The invoking shell may not have the brew prefix on PATH; a pinned path
    # keeps probe and install working regardless.
    brew = "/home/linuxbrew/.linuxbrew/bin/brew"
    assert pkg.is_installed_cmd("brew", "tmux", brew_bin=brew) == [
        brew, "list", "--formula", "tmux",
    ]
    assert pkg.install_cmd("brew", "tmux", brew_bin=brew) == [brew, "install", "tmux"]


def test_native_manager_commands_ignore_brew_bin():
    assert pkg.is_installed_cmd("apt", "tmux", brew_bin="/x/brew") == ["dpkg", "-s", "tmux"]
