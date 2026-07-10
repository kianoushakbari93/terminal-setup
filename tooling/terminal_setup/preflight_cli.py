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


def build_default_checks(prereq_count: Optional[int] = None) -> List[preflight.Check]:
    # sudo is only required where the native package manager needs it: Linux,
    # and only when the run will actually install prereq-kind packages with it.
    # The Homebrew/Linuxbrew stack and all config deployment run unprivileged,
    # and macOS provisions the terminal stack via Homebrew without elevation.
    # When the caller does not say how many prereq packages the run carries
    # (prereq_count is None), stay conservative and require sudo on Linux.
    try:
        on_linux = platform_facts.resolve().os_family == "linux"
    except platform_facts.UnsupportedPlatform:
        on_linux = True
    sudo_required = on_linux and (prereq_count is None or prereq_count > 0)

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
    parser = argparse.ArgumentParser(
        prog="terminal-setup-preflight",
        description="Validate the environment before provisioning.",
    )
    parser.add_argument(
        "--prereq-count",
        type=int,
        default=None,
        help="Number of prereq-kind packages the run installs via the native "
        "package manager; sudo is only required when this is non-zero on Linux.",
    )
    # argv=None means a real CLI invocation: let argparse read sys.argv.
    args = parser.parse_args(argv)

    report = preflight.run(
        checks if checks is not None else build_default_checks(args.prereq_count)
    )
    print(report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
