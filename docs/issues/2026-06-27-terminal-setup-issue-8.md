---
id: terminal-setup-8
title: Dry-run & restore - --check/--diff passthrough, backup manifest, restore path
status: done
type: AFK
blocked_by: [terminal-setup-1]
---

## What to build

Round out the safety story. Ensure `bootstrap.sh --check` cleanly passes Ansible
`--check --diff` so the user previews every change including rendered config diffs without
touching the system. Solidify the backup manifest written by the merge engine, and add a
restore path that reverts managed files from a chosen backup snapshot.

## Acceptance criteria

- [x] `bootstrap.sh --check` runs the full playbook in check mode with `--diff`, showing rendered config diffs and making no changes
- [x] Every run that modifies files writes/updates a manifest mapping original paths → backup paths under the timestamped snapshot
- [x] A documented restore command reverts managed files from a selected snapshot using the manifest
- [x] Restore is safe to re-run and reports clearly what it changed
- [x] Restore fails fast with a clear message if the snapshot or manifest is missing
