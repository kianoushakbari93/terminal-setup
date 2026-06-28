"""Resolve OS-specific facts the rest of the tool depends on.

Kept pure (inputs in, dataclass out) so it is trivially testable and reusable
both from Ansible custom modules and from the bootstrap path.
"""
from __future__ import annotations

import platform as _platform
from dataclasses import dataclass


class UnsupportedPlatform(Exception):
    """Raised for an operating system the tool does not support."""


@dataclass(frozen=True)
class PlatformFacts:
    os_family: str          # "macos" | "linux"
    brew_prefix: str        # Homebrew/Linuxbrew install prefix


def resolve(system: str | None = None, machine: str | None = None) -> PlatformFacts:
    """Resolve platform facts.

    Args default to the live host so callers can simply ``resolve()``; tests
    inject ``system``/``machine`` to exercise every platform deterministically.
    """
    system = system if system is not None else _platform.system()
    machine = machine if machine is not None else _platform.machine()

    if system == "Darwin":
        # Apple Silicon -> /opt/homebrew, Intel -> /usr/local
        brew_prefix = "/opt/homebrew" if machine in ("arm64", "aarch64") else "/usr/local"
        return PlatformFacts(os_family="macos", brew_prefix=brew_prefix)

    if system == "Linux":
        return PlatformFacts(os_family="linux", brew_prefix="/home/linuxbrew/.linuxbrew")

    raise UnsupportedPlatform(
        f"Unsupported operating system: {system!r}. "
        "This tool supports macOS (Darwin) and Linux only."
    )
