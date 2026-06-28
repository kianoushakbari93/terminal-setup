#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Ansible module: resolve per-OS path facts (brew prefix, plugin share dir,
font dir) and expose them as Ansible facts for later roles to consume."""
from __future__ import annotations

DOCUMENTATION = r"""
---
module: ts_platform_facts
short_description: Resolve per-OS path facts for the terminal-setup roles.
description:
  - Sets ts_os_family, ts_brew_prefix, ts_share_dir and ts_font_dir as facts so
    fonts/shells/configs roles render correct paths per platform.
options:
  machine:
    description: Override the detected CPU architecture (e.g. arm64, x86_64).
    type: str
    required: false
author:
  - Terminal Setup
"""

RETURN = r"""
ansible_facts:
  description: The resolved per-OS path facts.
  type: dict
  returned: always
"""

import platform

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import ts_packages as pkg


def main():
    module = AnsibleModule(
        argument_spec=dict(machine=dict(type="str", required=False, default=None)),
        supports_check_mode=True,
    )
    machine = module.params["machine"] or platform.machine()
    try:
        os_family = pkg.detect_os_family(platform.system())
        prefix = pkg.brew_prefix(os_family, machine)
        paths = pkg.resolve_paths(os_family, prefix)
    except pkg.UnsupportedPlatform as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(
        changed=False,
        ansible_facts=dict(
            ts_os_family=os_family,
            ts_brew_prefix=paths.brew_prefix,
            ts_share_dir=paths.share_dir,
            ts_font_dir=paths.font_dir,
        ),
    )


if __name__ == "__main__":
    main()
