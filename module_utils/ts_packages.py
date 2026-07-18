"""Cross-OS package layer: select the right package manager per platform,
resolve logical package names to concrete ones, and build probe/install commands.

Strategy: the native package manager (apt/dnf/pacman) installs only base
prerequisites; the terminal stack is installed uniformly via Homebrew/Linuxbrew.

Pure logic (no Ansible imports) so it is unit-testable and reusable by the
``package_install`` module via ``ansible.module_utils``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional

# distro -> native package manager
_DISTRO_NATIVE = {
    "ubuntu": "apt",
    "debian": "apt",
    "fedora": "dnf",
    "rhel": "dnf",
    "centos": "dnf",
    "rocky": "dnf",
    "almalinux": "dnf",
    "arch": "pacman",
    "archlinux": "pacman",
    "manjaro": "pacman",
    "endeavouros": "pacman",
}


class UnsupportedPlatform(Exception):
    """Raised for an OS/distro the package layer does not support."""


def detect_os_family(system: str) -> str:
    """Map a platform.system() value to our os_family."""
    if system == "Darwin":
        return "macos"
    if system == "Linux":
        return "linux"
    raise UnsupportedPlatform(
        f"Unsupported operating system: {system!r}. Supported: macOS, Linux."
    )


def brew_prefix(os_family: str, machine: str) -> str:
    """Resolve the Homebrew/Linuxbrew install prefix for a platform."""
    if os_family == "macos":
        return "/opt/homebrew" if machine in ("arm64", "aarch64") else "/usr/local"
    if os_family == "linux":
        return "/home/linuxbrew/.linuxbrew"
    raise UnsupportedPlatform(f"Unsupported OS family: {os_family!r}.")


@dataclass(frozen=True)
class Managers:
    native: str   # brew | apt | dnf | pacman  (prerequisites)
    stack: str    # brew                        (terminal stack, Linuxbrew on Linux)


@dataclass(frozen=True)
class Resolution:
    manager: str
    name: str


def select_managers(os_family: str, distro: str | None = None) -> Managers:
    if os_family == "macos":
        return Managers(native="brew", stack="brew")
    if os_family == "linux":
        key = (distro or "").lower()
        native = _DISTRO_NATIVE.get(key)
        if native is None:
            raise UnsupportedPlatform(
                f"Unsupported Linux distro: {distro!r}. "
                "Supported: Debian/Ubuntu (apt), Fedora/RHEL (dnf), Arch (pacman)."
            )
        return Managers(native=native, stack="brew")
    raise UnsupportedPlatform(
        f"Unsupported OS family: {os_family!r}. Supported: macos, linux."
    )


def resolve(
    logical: str,
    kind: str,
    os_family: str,
    distro: Optional[str] = None,
    package_map: Optional[Dict[str, Dict[str, str]]] = None,
) -> Resolution:
    """Resolve a logical package to (manager, concrete name).

    ``kind`` is "stack" (installed via Homebrew/Linuxbrew) or "prereq"
    (installed via the platform's native manager).
    """
    if kind == "stack":
        # The stack always installs via Homebrew/Linuxbrew; the distro (and its
        # native manager) is irrelevant, so an unknown distro must not block it.
        if os_family not in ("macos", "linux"):
            raise UnsupportedPlatform(
                f"Unsupported OS family: {os_family!r}. Supported: macos, linux."
            )
        manager = "brew"
    elif kind == "prereq":
        manager = select_managers(os_family, distro).native
    else:
        raise ValueError(f"Unknown package kind: {kind!r} (expected 'stack' or 'prereq')")

    overrides = (package_map or {}).get(logical, {})
    name = overrides.get(manager, logical)
    return Resolution(manager=manager, name=name)


_IS_INSTALLED = {
    "brew": lambda name: ["brew", "list", "--formula", name],
    "apt": lambda name: ["dpkg", "-s", name],
    "dnf": lambda name: ["rpm", "-q", name],
    "pacman": lambda name: ["pacman", "-Q", name],
}

_INSTALL = {
    "brew": lambda name: ["brew", "install", name],
    "apt": lambda name: ["apt-get", "install", "-y", name],
    "dnf": lambda name: ["dnf", "install", "-y", name],
    "pacman": lambda name: ["pacman", "-S", "--noconfirm", name],
}

_NEEDS_SUDO = {"brew": False, "apt": True, "dnf": True, "pacman": True}


def _require_manager(manager: str) -> None:
    if manager not in _INSTALL:
        raise UnsupportedPlatform(
            f"Unsupported package manager: {manager!r}. "
            "Supported: brew, apt, dnf, pacman."
        )


def is_installed_cmd(manager: str, name: str, brew_bin: Optional[str] = None):
    """Build the is-installed probe. ``brew_bin`` pins brew to an absolute path
    so the probe works when the caller's PATH lacks the brew prefix (fresh
    installs, re-runs before re-login)."""
    _require_manager(manager)
    cmd = _IS_INSTALLED[manager](name)
    if manager == "brew" and brew_bin:
        cmd[0] = brew_bin
    return cmd


def install_cmd(manager: str, name: str, brew_bin: Optional[str] = None):
    """Build the install command; ``brew_bin`` as in ``is_installed_cmd``."""
    _require_manager(manager)
    cmd = _INSTALL[manager](name)
    if manager == "brew" and brew_bin:
        cmd[0] = brew_bin
    return cmd


def needs_sudo(manager: str) -> bool:
    _require_manager(manager)
    return _NEEDS_SUDO[manager]


@dataclass(frozen=True)
class Paths:
    brew_prefix: str
    share_dir: str   # where brew-installed plugins live (zsh-*, powerlevel10k, ...)
    font_dir: str    # where Nerd Fonts are installed


def resolve_paths(os_family: str, brew_prefix: str, home: Optional[str] = None) -> Paths:
    home = home if home is not None else os.path.expanduser("~")
    if os_family == "macos":
        font_dir = os.path.join(home, "Library", "Fonts")
    elif os_family == "linux":
        font_dir = os.path.join(home, ".local", "share", "fonts")
    else:
        raise UnsupportedPlatform(f"Unsupported OS family: {os_family!r}.")
    return Paths(
        brew_prefix=brew_prefix,
        share_dir=os.path.join(brew_prefix, "share"),
        font_dir=font_dir,
    )
