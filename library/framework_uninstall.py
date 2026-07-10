#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Ansible module: uninstall competing prompt frameworks (oh-my-zsh, oh-my-posh)
after backing up their user content, and scrub their references from the rc
.local files so shells never source a removed path. Thin wrapper around the
pure ``ts_frameworks`` logic in module_utils."""
from __future__ import annotations

DOCUMENTATION = r"""
---
module: framework_uninstall
short_description: Uninstall competing prompt frameworks (oh-my-zsh, oh-my-posh).
description:
  - Detects oh-my-zsh and oh-my-posh installations under the given home and
    removes them; the tool's prompts (Powerlevel10k, starship) replace them.
  - User content (oh-my-zsh C(custom/) directory) is copied into a timestamped
    backup snapshot before deletion.
  - Framework references are scrubbed from the rc C(.local) files (with a
    manifest-recorded backup), so no shell ever sources a removed path.
  - Only paths inside the home directory are deleted; a Homebrew-installed
    oh-my-posh is removed via C(brew uninstall).
options:
  home:
    description: Home directory to detect and remove frameworks under.
    type: str
    default: "~"
  backup_root:
    description: Directory under which timestamped backups and the manifest live.
    type: str
    default: "~/.terminal-setup/backups"
  locals_to_scrub:
    description: rc .local files to scrub framework references from (defaults
      to C(.zshrc.local), C(.bashrc.local) and C(.bash_profile.local) under
      I(home)).
    type: list
    elements: str
author:
  - Terminal Setup
"""

EXAMPLES = r"""
- name: Uninstall competing prompt frameworks
  framework_uninstall:
    backup_root: ~/.terminal-setup/backups
"""

RETURN = r"""
changed:
  description: Whether anything was removed or scrubbed.
  type: bool
  returned: always
removed:
  description: Names of the frameworks that were uninstalled.
  type: list
  returned: always
deleted_paths:
  description: Filesystem paths that were deleted.
  type: list
  returned: always
backed_up:
  description: Snapshot copies of user content saved before deletion.
  type: list
  returned: always
brew_uninstalled:
  description: Homebrew formulas that were uninstalled.
  type: list
  returned: always
scrubbed:
  description: rc .local files whose framework references were removed.
  type: list
  returned: always
"""

import os
from datetime import datetime, timezone

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import ts_frameworks, ts_merge


def main():
    module = AnsibleModule(
        argument_spec=dict(
            home=dict(type="str", default="~"),
            backup_root=dict(type="str", default="~/.terminal-setup/backups"),
            locals_to_scrub=dict(type="list", elements="str", default=None),
        ),
        supports_check_mode=True,
    )
    p = module.params
    home = os.path.expanduser(p["home"])
    backup_root = os.path.expanduser(p["backup_root"])
    locals_to_scrub = p["locals_to_scrub"]
    if locals_to_scrub is None:
        locals_to_scrub = [
            os.path.join(home, name)
            for name in (".zshrc.local", ".bashrc.local", ".bash_profile.local")
        ]

    removals = ts_frameworks.detect(home)

    # Plan the .local scrubs (framework references must not outlive the files
    # they source, or every future shell launch reports a missing path).
    scrub_plan = []
    for path in locals_to_scrub:
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            continue
        with open(path) as fh:
            original = fh.read()
        scrubbed = ts_merge._scrub_signatures(
            original, ts_frameworks.FRAMEWORK_SIGNATURES
        ).rstrip("\n")
        if scrubbed != original.rstrip("\n"):
            scrub_plan.append((path, scrubbed + "\n" if scrubbed else ""))

    changed = bool(removals or scrub_plan)
    if module.check_mode or not changed:
        module.exit_json(
            changed=changed,
            removed=[r.framework for r in removals],
            deleted_paths=[path for r in removals for path in r.paths],
            backed_up=[],
            brew_uninstalled=[r.brew_formula for r in removals if r.brew_formula],
            scrubbed=[path for path, _ in scrub_plan],
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    snapshot_dir = os.path.join(backup_root, now.strftime("%Y%m%dT%H%M%SZ"))

    try:
        result = ts_frameworks.apply(removals, snapshot_dir)
    except Exception as exc:  # surface a precise, structured error
        module.fail_json(msg="framework uninstall failed: %s" % exc)

    scrubbed_paths = []
    for path, new_content in scrub_plan:
        ts_merge._backup(path, backup_root, now)
        with open(path, "w") as fh:
            fh.write(new_content)
        scrubbed_paths.append(path)

    module.exit_json(
        changed=True,
        removed=result.removed,
        deleted_paths=result.deleted_paths,
        backed_up=result.backed_up,
        brew_uninstalled=result.brew_uninstalled,
        scrubbed=scrubbed_paths,
    )


if __name__ == "__main__":
    main()
