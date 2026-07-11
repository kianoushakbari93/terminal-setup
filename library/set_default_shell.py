#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Ansible module: set the login shell to zsh idempotently, skipping when it is
already zsh and surfacing a re-login notice otherwise. Wraps ``ts_shell``."""
from __future__ import annotations

DOCUMENTATION = r"""
---
module: set_default_shell
short_description: Set the login shell to zsh idempotently.
description:
  - Runs chsh only when the current login shell is not already a zsh, and
    returns a notice that a fresh login is needed to activate the change.
options:
  target_shell:
    description: Path to the zsh to set as the login shell.
    required: true
    type: str
  current_shell:
    description: Override the detected current login shell.
    type: str
author:
  - Terminal Setup
"""

EXAMPLES = r"""
- name: Make zsh the default shell
  set_default_shell:
    target_shell: /bin/zsh
"""

RETURN = r"""
changed:
  description: Whether the login shell was changed.
  type: bool
notice:
  description: Re-login notice when the shell was changed.
  type: str
"""

import os
import platform
import pwd

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import ts_shell


def _current_user():
    try:
        return pwd.getpwuid(os.getuid())
    except Exception:
        return None


def _current_shell():
    entry = _current_user()
    if entry is not None:
        return entry.pw_shell
    return os.environ.get("SHELL", "")


def _shell_registered(target_shell):
    try:
        with open("/etc/shells", "r") as fh:
            registered = {line.strip() for line in fh if line.strip() and not line.startswith("#")}
    except OSError:
        return False
    return target_shell in registered


def main():
    module = AnsibleModule(
        argument_spec=dict(
            target_shell=dict(type="str", required=True),
            current_shell=dict(type="str", required=False, default=None),
        ),
        supports_check_mode=True,
    )
    current = module.params["current_shell"] or _current_shell()
    target = module.params["target_shell"]
    entry = _current_user()
    plan = ts_shell.plan_chsh(
        current_shell=current,
        target_shell=target,
        os_family="linux" if platform.system() == "Linux" else "macos",
        user=entry.pw_name if entry is not None else None,
        shell_registered=_shell_registered(target),
    )

    if not plan.needs_change:
        module.exit_json(changed=False, msg="login shell is already zsh")

    if module.check_mode:
        module.exit_json(changed=True, notice=plan.notice)

    if plan.register_command:
        rc, out, err = module.run_command(plan.register_command)
        if rc != 0:
            module.fail_json(
                msg="registering %s in /etc/shells failed: %s" % (target, err.strip() or out.strip())
            )

    rc, out, err = module.run_command(plan.command)
    if rc != 0:
        module.fail_json(msg="chsh failed: %s" % (err.strip() or out.strip()))
    module.exit_json(changed=True, notice=plan.notice)


if __name__ == "__main__":
    main()
