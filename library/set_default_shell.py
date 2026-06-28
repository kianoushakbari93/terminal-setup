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
import pwd

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import ts_shell


def _current_shell():
    try:
        return pwd.getpwuid(os.getuid()).pw_shell
    except Exception:
        return os.environ.get("SHELL", "")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            target_shell=dict(type="str", required=True),
            current_shell=dict(type="str", required=False, default=None),
        ),
        supports_check_mode=True,
    )
    current = module.params["current_shell"] or _current_shell()
    plan = ts_shell.plan_chsh(current_shell=current, target_shell=module.params["target_shell"])

    if not plan.needs_change:
        module.exit_json(changed=False, msg="login shell is already zsh")

    if module.check_mode:
        module.exit_json(changed=True, notice=plan.notice)

    rc, out, err = module.run_command(plan.command)
    if rc != 0:
        module.fail_json(msg="chsh failed: %s" % (err.strip() or out.strip()))
    module.exit_json(changed=True, notice=plan.notice)


if __name__ == "__main__":
    main()
