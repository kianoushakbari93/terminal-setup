#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Ansible module: run the deep bash health suite against a HOME and fail the
play if any probe fails. Thin wrapper around the ``ts_bash_health`` engine."""
from __future__ import annotations

DOCUMENTATION = r"""
---
module: bash_health
short_description: Verify a deployed bash config is healthy.
description:
  - Launches a real interactive bash (under a PTY) with the given HOME and checks
    that it loads cleanly with ble.sh, starship and bash-completion, sources its
    aliases and .local file, has prompt glyphs, and starts quickly.
options:
  home:
    description: HOME directory holding the .bashrc / starship.toml to test.
    required: true
    type: str
  bash_bin:
    description: bash executable to run (must be bash 4+ for ble.sh).
    type: str
    default: bash
  threshold_s:
    description: Maximum acceptable startup time, in seconds.
    type: float
    default: 2.0
author:
  - Terminal Setup
"""

EXAMPLES = r"""
- name: Verify the home bash config
  bash_health:
    home: "{{ ansible_user_dir }}"
"""

RETURN = r"""
probes:
  description: Per-probe name/ok/detail results.
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import ts_bash_health as bh


def main():
    module = AnsibleModule(
        argument_spec=dict(
            home=dict(type="str", required=True),
            bash_bin=dict(type="str", default="bash"),
            threshold_s=dict(type="float", default=2.0),
        ),
        supports_check_mode=True,
    )
    p = module.params
    if module.check_mode:
        module.exit_json(changed=False, probes=[])

    results = bh.run_bash_health(p["home"], bash_bin=p["bash_bin"], threshold_s=p["threshold_s"])
    probes = [dict(name=r.name, ok=r.ok, detail=r.detail) for r in results]
    failed = [r for r in results if not r.ok]
    if failed:
        module.fail_json(
            msg="bash health checks failed: "
            + "; ".join(f"{r.name} ({r.detail})" for r in failed),
            probes=probes,
        )
    module.exit_json(changed=False, probes=probes)


if __name__ == "__main__":
    main()
