#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Ansible module: set the iTerm2 profile font and window transparency in the
preferences plist idempotently, touching only those keys. Thin wrapper around the
pure ``ts_iterm2`` helper."""
from __future__ import annotations

DOCUMENTATION = r"""
---
module: iterm2_config
short_description: Set the iTerm2 profile font and transparency.
description:
  - Applies a Nerd Font and a window transparency to every iTerm2 profile in the
    preferences plist, modifying only those two keys.
  - iTerm2 must be restarted for the change to apply (it can overwrite the plist
    on quit), so the module returns a restart notice.
options:
  plist_path:
    description: Path to the iTerm2 preferences plist.
    required: true
    type: str
  font:
    description: iTerm2 font string (PostScript name + size, e.g. "MesloLGSNF-Regular 16").
    required: true
    type: str
  transparency:
    description: Window transparency, 0.0 (opaque) to 1.0 (clear).
    required: true
    type: float
author:
  - Terminal Setup
"""

EXAMPLES = r"""
- name: Configure iTerm2 font + transparency
  iterm2_config:
    plist_path: "{{ ansible_user_dir }}/Library/Preferences/com.googlecode.iterm2.plist"
    font: "MesloLGSNF-Regular 16"
    transparency: 0.2
"""

RETURN = r"""
changed:
  description: Whether the plist was modified.
  type: bool
notice:
  description: Restart reminder.
  type: str
"""

import os
import plistlib

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import ts_iterm2

NOTICE = "Restart iTerm2 to apply the new font and transparency."


def main():
    module = AnsibleModule(
        argument_spec=dict(
            plist_path=dict(type="str", required=True),
            font=dict(type="str", required=True),
            transparency=dict(type="float", required=True),
        ),
        supports_check_mode=True,
    )
    p = module.params
    path = os.path.expanduser(p["plist_path"])

    if not os.path.exists(path):
        module.fail_json(msg="iTerm2 preferences not found: %s" % path)

    try:
        with open(path, "rb") as fh:
            plist = plistlib.load(fh)
    except Exception as exc:
        module.fail_json(msg="could not read iTerm2 plist: %s" % exc)

    new, changed = ts_iterm2.apply_settings(plist, font=p["font"], transparency=p["transparency"])

    if changed and not module.check_mode:
        with open(path, "wb") as fh:
            plistlib.dump(new, fh, fmt=plistlib.FMT_BINARY)

    module.exit_json(changed=changed, notice=NOTICE if changed else "")


if __name__ == "__main__":
    main()
