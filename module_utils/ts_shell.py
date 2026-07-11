"""Shell-management logic: decide whether the login shell needs changing to zsh.

Pure logic (no Ansible imports); reused by the ``chsh`` role's module/command.
"""
from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ChshPlan:
    needs_change: bool
    command: Optional[List[str]] = None
    register_command: Optional[List[str]] = None
    notice: Optional[str] = None


def plan_chsh(
    current_shell: str,
    target_shell: str,
    os_family: str = "macos",
    user: Optional[str] = None,
    shell_registered: bool = True,
) -> ChshPlan:
    """Plan a default-shell change to zsh.

    Skips when the current login shell is already a zsh (matched by basename, so
    any zsh path counts). Otherwise returns the chsh command plus a notice that
    activation needs a fresh login.

    ``chsh`` for a non-root user is interactive (PAM password prompt) and
    refuses shells missing from /etc/shells, so a provisioning run cannot use
    it directly. On Linux the plan therefore elevates with ``sudo -n`` (the
    pre-flight gate guarantees passwordless sudo there) and, when the target
    shell is not yet registered (``shell_registered=False``), first appends it
    to /etc/shells.
    """
    if os.path.basename(current_shell) == "zsh":
        return ChshPlan(needs_change=False)

    register_command = None
    if not shell_registered:
        register_command = [
            "sudo", "-n", "sh", "-c",
            "printf '%s\\n' {} >> /etc/shells".format(shlex.quote(target_shell)),
        ]

    if os_family == "linux":
        command = ["sudo", "-n", "chsh", "-s", target_shell]
        if user:
            command.append(user)
    else:
        command = ["chsh", "-s", target_shell]

    return ChshPlan(
        needs_change=True,
        command=command,
        register_command=register_command,
        notice=(
            f"Default shell changed to {target_shell}. "
            "Log out and back in (or open a new login session) to activate it."
        ),
    )
