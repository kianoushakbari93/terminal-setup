#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Ansible module: run the deep tmux health suite against a rendered config and
fail the play if any probe fails. Thin wrapper around ``ts_tmux_health``."""
from __future__ import annotations

DOCUMENTATION = r"""
---
module: tmux_health
short_description: Verify a deployed tmux config is healthy.
description:
  - Boots an isolated tmux server (custom socket) from the given config and
    checks that it parses, the status-right modules render non-empty, the window
    tabs have rounded caps, and the required plugins are present.
options:
  conf_path:
    description: Path to the tmux config to test.
    required: true
    type: str
  home:
    description: HOME whose ~/.tmux/plugins the config loads.
    required: true
    type: str
  tmux_bin:
    description: tmux executable to run.
    type: str
    default: tmux
author:
  - Terminal Setup
"""

EXAMPLES = r"""
- name: Verify the tmux config
  tmux_health:
    conf_path: "{{ ansible_user_dir }}/.tmux.conf"
    home: "{{ ansible_user_dir }}"
"""

RETURN = r"""
probes:
  description: Per-probe name/ok/detail results.
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import ts_tmux_health as th


def main():
    module = AnsibleModule(
        argument_spec=dict(
            conf_path=dict(type="str", required=True),
            home=dict(type="str", required=True),
            tmux_bin=dict(type="str", default="tmux"),
        ),
        supports_check_mode=True,
    )
    p = module.params
    if module.check_mode:
        module.exit_json(changed=False, probes=[])

    results = th.run_tmux_health(p["conf_path"], home=p["home"], tmux_bin=p["tmux_bin"])
    probes = [dict(name=r.name, ok=r.ok, detail=r.detail) for r in results]
    failed = [r for r in results if not r.ok]
    if failed:
        module.fail_json(
            msg="tmux health checks failed: "
            + "; ".join(f"{r.name} ({r.detail})" for r in failed),
            probes=probes,
        )
    module.exit_json(changed=False, probes=probes)


if __name__ == "__main__":
    main()
