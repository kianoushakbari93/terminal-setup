#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Ansible module: run the deep zsh health suite against a ZDOTDIR and fail the
play if any probe fails. Thin wrapper around the ``ts_zsh_health`` engine."""
from __future__ import annotations

DOCUMENTATION = r"""
---
module: zsh_health
short_description: Verify a deployed zsh config is healthy.
description:
  - Launches a real interactive zsh (under a PTY) against the given ZDOTDIR and
    checks that it loads cleanly with Powerlevel10k, autosuggestions and syntax
    highlighting, that prompt glyphs are present, and that startup is fast.
options:
  zdotdir:
    description: Directory holding the .zshrc / .p10k.zsh to test.
    required: true
    type: str
  zsh_bin:
    description: zsh executable to run.
    type: str
    default: zsh
  threshold_s:
    description: Maximum acceptable startup time, in seconds.
    type: float
    default: 2.0
author:
  - Terminal Setup
"""

EXAMPLES = r"""
- name: Verify the home zsh config
  zsh_health:
    zdotdir: "{{ ansible_user_dir }}"
"""

RETURN = r"""
probes:
  description: Per-probe name/ok/detail results.
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import ts_zsh_health as zh


def main():
    module = AnsibleModule(
        argument_spec=dict(
            zdotdir=dict(type="str", required=True),
            zsh_bin=dict(type="str", default="zsh"),
            threshold_s=dict(type="float", default=2.0),
        ),
        supports_check_mode=True,
    )
    p = module.params
    if module.check_mode:
        module.exit_json(changed=False, probes=[])

    results = zh.run_zsh_health(p["zdotdir"], zsh_bin=p["zsh_bin"], threshold_s=p["threshold_s"])
    probes = [dict(name=r.name, ok=r.ok, detail=r.detail) for r in results]
    failed = [r for r in results if not r.ok]
    if failed:
        module.fail_json(
            msg="zsh health checks failed: "
            + "; ".join(f"{r.name} ({r.detail})" for r in failed),
            probes=probes,
        )
    module.exit_json(changed=False, probes=probes)


if __name__ == "__main__":
    main()
