"""CLI entrypoint for the health suite.

Runs at the end of a provisioning run. Exits non-zero (failing the play) if any
probe fails. Registers the deep zsh / bash / tmux probes (the same engines the
per-role verify tasks run) plus the python-runtime probe, so the final gate
re-proves the whole terminal in one summary.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from . import healthcheck as hc
from . import platform_facts

# The deep probe engines live in module_utils/ (shared with the Ansible
# modules); they import each other flatly, so the directory itself goes on the
# path.
_MODULE_UTILS = Path(__file__).resolve().parents[2] / "module_utils"
if str(_MODULE_UTILS) not in sys.path:
    sys.path.insert(0, str(_MODULE_UTILS))

import ts_bash_health  # noqa: E402
import ts_tmux_health  # noqa: E402
import ts_zsh_health  # noqa: E402


def _python_runtime_probe() -> hc.ProbeResult:
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (3, 8)
    return hc.ProbeResult(ok, f"python {major}.{minor}" if ok else f"python {major}.{minor} too old")


def build_default_probes() -> List:
    """The full suite for the live host: python runtime plus the deep shell
    probes against the user's real HOME and the stack binaries."""
    home = os.path.expanduser("~")
    brew_bin = Path(platform_facts.resolve().brew_prefix) / "bin"
    return [
        hc.Probe("python runtime", _python_runtime_probe),
        hc.ProbeGroup(
            "zsh",
            lambda: ts_zsh_health.run_zsh_health(home, zsh_bin=str(brew_bin / "zsh")),
        ),
        hc.ProbeGroup(
            "bash",
            lambda: ts_bash_health.run_bash_health(home, bash_bin=str(brew_bin / "bash")),
        ),
        hc.ProbeGroup(
            "tmux",
            lambda: ts_tmux_health.run_tmux_health(
                os.path.join(home, ".tmux.conf"), home, tmux_bin=str(brew_bin / "tmux")
            ),
        ),
    ]


def main(argv: Optional[List[str]] = None, probes: Optional[List[hc.Probe]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="terminal-setup-healthcheck",
        description="Verify the provisioned terminal is healthy.",
    )
    parser.add_argument(
        "--no-deep",
        action="store_true",
        help="skip the deep zsh/bash/tmux probes (sandboxed runs that never "
        "provisioned the live HOME)",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if probes is None:
        probes = build_default_probes()
        if args.no_deep:
            probes = [p for p in probes if not isinstance(p, hc.ProbeGroup)]

    report = hc.run(probes)
    print(report.render())
    return report.exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
