"""CLI entrypoint for the health suite.

Runs at the end of a provisioning run. Exits non-zero (failing the play) if any
probe fails. Slice 0 ships the harness plus a minimal real probe; later slices
register the deep zsh/bash/tmux/font probes here.
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import healthcheck as hc


def _python_runtime_probe() -> hc.ProbeResult:
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (3, 8)
    return hc.ProbeResult(ok, f"python {major}.{minor}" if ok else f"python {major}.{minor} too old")


def build_default_probes() -> List[hc.Probe]:
    return [hc.Probe("python runtime", _python_runtime_probe)]


def main(argv: Optional[List[str]] = None, probes: Optional[List[hc.Probe]] = None) -> int:
    argparse.ArgumentParser(
        prog="terminal-setup-healthcheck",
        description="Verify the provisioned terminal is healthy.",
    ).parse_args(argv or [])

    report = hc.run(probes if probes is not None else build_default_probes())
    print(report.render())
    return report.exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
