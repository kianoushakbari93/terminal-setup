#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Ansible module: install a logical package using the right manager for the
host, idempotently. Thin wrapper around the pure ``ts_packages`` resolver."""
from __future__ import annotations

DOCUMENTATION = r"""
---
module: package_install
short_description: Install a logical package via the correct per-OS manager.
description:
  - Resolves a logical package name + kind (stack|prereq) to a concrete name and
    manager (brew/apt/dnf/pacman), then installs it idempotently.
  - The terminal stack is installed via Homebrew/Linuxbrew; prerequisites use the
    native package manager.
options:
  name:
    description: Logical package name.
    required: true
    type: str
  kind:
    description: Either stack (Homebrew/Linuxbrew) or prereq (native manager).
    required: true
    type: str
    choices: [stack, prereq]
  package_map:
    description: Logical -> per-manager concrete-name overrides.
    type: dict
    default: {}
  os_family:
    description: Override the detected OS family (macos|linux).
    type: str
    required: false
  distro:
    description: Linux distro id (ubuntu/debian/fedora/arch/...). Required on Linux.
    type: str
    required: false
author:
  - Terminal Setup
"""

EXAMPLES = r"""
- name: Install tmux from the terminal stack
  package_install:
    name: tmux
    kind: stack
"""

RETURN = r"""
changed:
  description: Whether the package was installed by this run.
  type: bool
manager:
  description: The resolved package manager.
  type: str
name:
  description: The resolved concrete package name.
  type: str
"""

import os
import platform

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import ts_packages as pkg


def _detect_os_family():
    system = platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Linux":
        return "linux"
    return system


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            kind=dict(type="str", required=True, choices=["stack", "prereq"]),
            package_map=dict(type="dict", default={}),
            os_family=dict(type="str", required=False, default=None),
            distro=dict(type="str", required=False, default=None),
        ),
        supports_check_mode=True,
    )
    p = module.params
    os_family = p["os_family"] or _detect_os_family()

    try:
        res = pkg.resolve(
            p["name"], kind=p["kind"], os_family=os_family,
            distro=p["distro"], package_map=p["package_map"],
        )
        # Pin brew to its absolute path: the invoking shell may not have the
        # brew prefix on PATH (fresh installs, re-runs before re-login).
        brew_bin = os.path.join(
            pkg.brew_prefix(os_family, platform.machine()), "bin", "brew"
        )
        if not os.path.exists(brew_bin):
            brew_bin = None
        probe = pkg.is_installed_cmd(res.manager, res.name, brew_bin=brew_bin)
        install = pkg.install_cmd(res.manager, res.name, brew_bin=brew_bin)
        sudo = pkg.needs_sudo(res.manager)
    except (pkg.UnsupportedPlatform, ValueError) as exc:
        module.fail_json(msg="package resolution failed: %s" % exc)

    rc, _out, _err = module.run_command(probe)
    if rc == 0:
        module.exit_json(changed=False, manager=res.manager, name=res.name)

    if module.check_mode:
        module.exit_json(changed=True, manager=res.manager, name=res.name)

    cmd = (["sudo", "-n"] + install) if sudo else install
    rc, out, err = module.run_command(cmd)
    if rc != 0:
        module.fail_json(
            msg="failed to install %s via %s: %s" % (res.name, res.manager, err.strip() or out.strip()),
            manager=res.manager, name=res.name,
        )
    module.exit_json(changed=True, manager=res.manager, name=res.name)


if __name__ == "__main__":
    main()
