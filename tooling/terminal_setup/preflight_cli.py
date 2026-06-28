"""CLI entrypoint for the pre-flight gate.

The playbook runs this before any change-making role. It exits non-zero (halting
the play) when the environment is not ready, after reporting every problem.
"""
from __future__ import annotations

import argparse
import os
from typing import List, Optional

from . import checks as _checks
from . import platform_facts
from . import preflight

# Config files the tool will manage; all must be writable before we start.
MANAGED_TARGETS = [
    "~/.zshrc",
    "~/.bashrc",
    "~/.bash_profile",
    "~/.tmux.conf",
    "~/.config/starship.toml",
]


def build_default_checks() -> List[preflight.Check]:
    # sudo is only required where the native package manager needs it (Linux);
    # macOS provisions the terminal stack via Homebrew without elevation.
    try:
        sudo_required = platform_facts.resolve().os_family == "linux"
    except platform_facts.UnsupportedPlatform:
        sudo_required = True

    result: List[preflight.Check] = [
        _checks.os_supported(),
        _checks.disk_space(),
        _checks.network(),
        _checks.sudo(required=sudo_required),
    ]
    for target in MANAGED_TARGETS:
        result.append(_checks.target_writable(os.path.expanduser(target)))
    return result


def main(argv: Optional[List[str]] = None, checks: Optional[List[preflight.Check]] = None) -> int:
    argparse.ArgumentParser(
        prog="terminal-setup-preflight",
        description="Validate the environment before provisioning.",
    ).parse_args(argv or [])

    report = preflight.run(checks if checks is not None else build_default_checks())
    print(report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
