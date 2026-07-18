"""Detect and remove competing prompt frameworks (oh-my-zsh, oh-my-posh).

The tool owns the prompt (Powerlevel10k for zsh, starship for bash); a leftover
framework installation keeps fighting it on every shell launch, so provisioning
can uninstall the frameworks it replaces. Pure logic (no Ansible imports):
detection is injectable so it is unit-testable, and the plan/apply split lets
the Ansible module honour check mode.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Callable, List, Optional

# Lines referencing a removed framework must also leave the rc .local files,
# or every future shell launch errors on sourcing a path that no longer exists.
FRAMEWORK_SIGNATURES = (
    "oh-my-zsh",
    "zsh_theme",     # oh-my-zsh theme selection; inert but tool-owned territory
    "oh-my-posh",
    # Manjaro ships its own Powerlevel10k prompt (manjaro-zsh-prompt sources
    # /usr/share/zsh/p10k.zsh) and zsh config; left in a foreign .zshrc.local
    # they re-source AFTER the tool's ~/.p10k.zsh and override the theme.
    "manjaro-zsh-config",
    "manjaro-zsh-prompt",
)


@dataclass(frozen=True)
class Removal:
    framework: str            # "oh-my-zsh" | "oh-my-posh"
    paths: List[str] = field(default_factory=list)        # to delete
    backup_dirs: List[str] = field(default_factory=list)  # user content to save first
    brew_formula: Optional[str] = None                    # uninstall via brew too


def _default_brew_has(formula: str) -> bool:
    if shutil.which("brew") is None:
        return False
    return (
        subprocess.run(
            ["brew", "list", "--formula", formula], capture_output=True
        ).returncode
        == 0
    )


def detect(
    home: str,
    which_fn: Callable[[str], Optional[str]] = shutil.which,
    brew_has_fn: Callable[[str], bool] = _default_brew_has,
) -> List[Removal]:
    """Detect installed frameworks under ``home`` and plan their removal.

    Only paths inside ``home`` are ever planned for deletion; a system-wide
    binary (e.g. /usr/local/bin/oh-my-posh) is left alone unless Homebrew owns
    it, in which case ``brew uninstall`` handles it.
    """
    home = os.path.expanduser(home)
    removals: List[Removal] = []

    omz_dir = os.path.join(home, ".oh-my-zsh")
    if os.path.isdir(omz_dir):
        custom = os.path.join(omz_dir, "custom")
        removals.append(
            Removal(
                framework="oh-my-zsh",
                paths=[omz_dir],
                backup_dirs=[custom] if os.path.isdir(custom) else [],
            )
        )

    paths: List[str] = []
    binary = which_fn("oh-my-posh")
    if binary and os.path.realpath(binary).startswith(home + os.sep):
        paths.append(binary)
    for leftover in (
        os.path.join(home, ".cache", "oh-my-posh"),
        os.path.join(home, ".poshthemes"),
    ):
        if os.path.exists(leftover):
            paths.append(leftover)
    brew_formula = "oh-my-posh" if brew_has_fn("oh-my-posh") else None
    if paths or brew_formula:
        removals.append(
            Removal(framework="oh-my-posh", paths=paths, brew_formula=brew_formula)
        )

    return removals


@dataclass(frozen=True)
class UninstallResult:
    removed: List[str] = field(default_factory=list)    # framework names
    deleted_paths: List[str] = field(default_factory=list)
    backed_up: List[str] = field(default_factory=list)  # saved dir copies
    brew_uninstalled: List[str] = field(default_factory=list)


def apply(
    removals: List[Removal],
    snapshot_dir: str,
    brew_uninstall_fn: Optional[Callable[[str], None]] = None,
) -> UninstallResult:
    """Execute planned removals: save user-content dirs into ``snapshot_dir``,
    then delete the framework paths and brew formulas."""

    def _brew_uninstall(formula: str) -> None:
        subprocess.run(["brew", "uninstall", formula], capture_output=True, check=True)

    brew_uninstall = brew_uninstall_fn or _brew_uninstall

    removed: List[str] = []
    deleted: List[str] = []
    backed_up: List[str] = []
    brewed: List[str] = []
    for removal in removals:
        for src in removal.backup_dirs:
            dest = os.path.join(
                snapshot_dir, f"{removal.framework}-{os.path.basename(src)}"
            )
            if os.path.exists(src) and not os.path.exists(dest):
                os.makedirs(snapshot_dir, exist_ok=True)
                shutil.copytree(src, dest, symlinks=True)
                backed_up.append(dest)
        for path in removal.paths:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            elif os.path.exists(path) or os.path.islink(path):
                os.remove(path)
            else:
                continue
            deleted.append(path)
        if removal.brew_formula:
            brew_uninstall(removal.brew_formula)
            brewed.append(removal.brew_formula)
        removed.append(removal.framework)
    return UninstallResult(
        removed=removed,
        deleted_paths=deleted,
        backed_up=backed_up,
        brew_uninstalled=brewed,
    )
