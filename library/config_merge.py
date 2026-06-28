#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Ansible module: idempotently install a marker-delimited managed block into a
config file while preserving the user's foreign content in a sibling .local
file. Thin wrapper around the pure ``ts_merge`` engine in module_utils."""
from __future__ import annotations

DOCUMENTATION = r"""
---
module: config_merge
short_description: Merge a managed block into a config file, preserving user content.
description:
  - Owns the content between marker lines, rewriting it idempotently.
  - On first migration, moves foreign user content into a sibling C(.local) file
    that the managed block sources, scrubbing known tool-signature lines.
  - Backs up the original (with a manifest) before any modifying write.
options:
  target_path:
    description: Path to the config file to manage.
    required: true
    type: str
  managed_content:
    description: The body of the managed block (without markers).
    required: true
    type: str
  begin_marker:
    description: Opening marker line.
    type: str
    default: "# >>> terminal-setup >>>"
  end_marker:
    description: Closing marker line.
    type: str
    default: "# <<< terminal-setup <<<"
  local_suffix:
    description: Suffix for the sibling foreign-content file.
    type: str
    default: ".local"
  source_line:
    description: Line the block uses to source the .local file (defaults to a
      POSIX-shell guarded source).
    type: str
    required: false
  signature_patterns:
    description: Substrings identifying tool-owned lines to scrub on migration.
    type: list
    elements: str
  backup_root:
    description: Directory under which timestamped backups and the manifest live.
    type: str
    default: "~/.terminal-setup/backups"
author:
  - Terminal Setup
"""

EXAMPLES = r"""
- name: Install the managed zsh block
  config_merge:
    target_path: ~/.zshrc
    managed_content: |
      source /opt/homebrew/share/powerlevel10k/powerlevel10k.zsh-theme
"""

RETURN = r"""
changed:
  description: Whether the target was modified.
  type: bool
  returned: always
backup_path:
  description: Path the original was backed up to, if a backup was taken.
  type: str
  returned: when changed and a prior file existed
local_path:
  description: Path of the sibling .local file.
  type: str
  returned: always
actions:
  description: Human-readable list of what the module did.
  type: list
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import ts_merge


def main():
    module = AnsibleModule(
        argument_spec=dict(
            target_path=dict(type="str", required=True),
            managed_content=dict(type="str", required=True),
            begin_marker=dict(type="str", default=ts_merge.DEFAULT_BEGIN),
            end_marker=dict(type="str", default=ts_merge.DEFAULT_END),
            local_suffix=dict(type="str", default=".local"),
            source_line=dict(type="str", required=False, default=None),
            signature_patterns=dict(type="list", elements="str", default=list(ts_merge.DEFAULT_SIGNATURES)),
            backup_root=dict(type="str", default="~/.terminal-setup/backups"),
        ),
        supports_check_mode=True,
    )
    p = module.params
    try:
        result = ts_merge.merge_config(
            target_path=p["target_path"],
            managed_content=p["managed_content"],
            begin_marker=p["begin_marker"],
            end_marker=p["end_marker"],
            local_suffix=p["local_suffix"],
            source_line=p["source_line"],
            signature_patterns=p["signature_patterns"],
            backup_root=p["backup_root"],
            check_mode=module.check_mode,
        )
    except Exception as exc:  # surface a precise, structured error
        module.fail_json(msg="config_merge failed: %s" % exc)

    diff = {"before": result.before_content, "after": result.after_content}

    # In check mode nothing was written, so there is no deployed file to verify;
    # just preview the diff.
    if module.check_mode:
        module.exit_json(
            changed=result.changed, diff=diff,
            local_path=result.local_path, target_path=result.target_path,
        )

    # Self-verify the post-merge invariants (the health-probe check), so a bad
    # deploy fails loudly instead of silently shipping a broken config.
    check = ts_merge.verify(
        p["target_path"],
        managed_content=p["managed_content"],
        begin_marker=p["begin_marker"],
        end_marker=p["end_marker"],
        local_suffix=p["local_suffix"],
    )
    if not check.ok:
        module.fail_json(
            msg="config_merge verification failed for %s: %s"
            % (p["target_path"], "; ".join(check.problems)),
            changed=result.changed,
            backup_path=result.backup_path,
        )

    module.exit_json(
        changed=result.changed,
        backup_path=result.backup_path,
        local_path=result.local_path,
        target_path=result.target_path,
        actions=result.actions,
        diff=diff,
        verified=True,
    )


if __name__ == "__main__":
    main()
