"""Concrete pre-flight checks.

Each factory returns a :class:`preflight.Check`. External effects (network,
sudo, disk) are taken as injectable probes with sensible live defaults, so the
checks are deterministic under test and real on a host.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
from typing import Callable, Optional

from . import platform_facts
from .preflight import Check, CheckResult


def os_supported(system: Optional[str] = None, machine: Optional[str] = None) -> Check:
    def _run() -> CheckResult:
        try:
            platform_facts.resolve(system=system, machine=machine)
        except platform_facts.UnsupportedPlatform as exc:
            return CheckResult(False, str(exc))
        return CheckResult(True)

    return Check("os", _run)


def target_writable(path: str) -> Check:
    """A target config file is writable if it exists and is writable, or its
    nearest existing ancestor directory is writable (so we can create it)."""
    def _run() -> CheckResult:
        if os.path.exists(path):
            ok = os.access(path, os.W_OK)
            return CheckResult(ok, "" if ok else f"{path} exists but is not writable")
        ancestor = os.path.dirname(os.path.abspath(path))
        while ancestor and not os.path.exists(ancestor):
            ancestor = os.path.dirname(ancestor)
        ok = bool(ancestor) and os.access(ancestor, os.W_OK)
        return CheckResult(
            ok, "" if ok else f"{path} is not writable (no writable parent directory)"
        )

    return Check("writable", _run)


def disk_space(
    path: str = "/",
    min_bytes: int = 500_000_000,
    free_bytes_fn: Optional[Callable[[str], int]] = None,
) -> Check:
    probe = free_bytes_fn or (lambda p: shutil.disk_usage(p).free)

    def _run() -> CheckResult:
        free = probe(path)
        if free < min_bytes:
            return CheckResult(
                False,
                f"insufficient disk space at {path}: need "
                f"{min_bytes // 1_000_000}MB, have {free // 1_000_000}MB",
            )
        return CheckResult(True)

    return Check("disk", _run)


def _default_network_probe(host: str) -> bool:
    try:
        socket.create_connection((host, 443), timeout=3).close()
        return True
    except OSError:
        return False


def network(host: str = "github.com", probe_fn: Optional[Callable[[str], bool]] = None) -> Check:
    probe = probe_fn or _default_network_probe

    def _run() -> CheckResult:
        if probe(host):
            return CheckResult(True)
        return CheckResult(False, f"network unreachable: cannot reach {host}")

    return Check("network", _run)


def _default_sudo_probe() -> bool:
    if os.geteuid() == 0:
        return True
    try:
        return subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0
    except OSError:
        return False


def sudo(required: bool = True, probe_fn: Optional[Callable[[], bool]] = None) -> Check:
    """Check sudo availability, but only enforce it when the run needs it.

    The terminal stack needs no elevation on macOS (Homebrew); on Linux the
    native package manager does. When ``required`` is False this passes
    regardless of sudo availability.
    """
    probe = probe_fn or _default_sudo_probe

    def _run() -> CheckResult:
        if not required or probe():
            return CheckResult(True)
        return CheckResult(
            False,
            "sudo is required but unavailable - run where you can elevate, or "
            "cache credentials first with `sudo -v`",
        )

    return Check("sudo", _run)
