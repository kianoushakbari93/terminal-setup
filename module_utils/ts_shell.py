"""Shell-management logic: decide whether the login shell needs changing to zsh.

Pure logic (no Ansible imports); reused by the ``chsh`` role's module/command.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ChshPlan:
    needs_change: bool
    command: Optional[List[str]] = None
    notice: Optional[str] = None


def plan_chsh(current_shell: str, target_shell: str) -> ChshPlan:
    """Plan a default-shell change to zsh.

    Skips when the current login shell is already a zsh (matched by basename, so
    any zsh path counts). Otherwise returns the chsh command plus a notice that
    activation needs a fresh login.
    """
    if os.path.basename(current_shell) == "zsh":
        return ChshPlan(needs_change=False)
    return ChshPlan(
        needs_change=True,
        command=["chsh", "-s", target_shell],
        notice=(
            f"Default shell changed to {target_shell}. "
            "Log out and back in (or open a new login session) to activate it."
        ),
    )
