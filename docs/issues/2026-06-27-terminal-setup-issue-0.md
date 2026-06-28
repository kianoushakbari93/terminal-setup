---
id: terminal-setup-0
title: Walking skeleton - bootstrap, ansible scaffold, pre-flight gate, trivial healthcheck
status: done
type: AFK
blocked_by: []
---

## What to build

The end-to-end spine that every later slice extends. A single `bootstrap.sh` that, on a
clean macOS or Linux box, installs the minimum prerequisites (git, curl, python3,
Ansible, and Homebrew at the correct prefix per platform), then runs `site.yml`. The
playbook runs a **pre-flight gate** that validates the environment and reports all
problems up front, followed by a single trivial healthcheck that passes. No real configs
or packages yet - this proves the whole pipeline (bootstrap → ansible → pre-flight →
healthcheck) works through every layer.

Includes the repo scaffold: `ansible.cfg`, `site.yml`, `inventory/localhost.yml`,
`group_vars/all.yml` (with per-OS facts: brew prefix, package-manager family), an empty
`library/` and `filter_plugins/`, and the `healthcheck` role harness that aggregates
named pass/fail probes and exits non-zero on any failure.

## Acceptance criteria

- [x] `./bootstrap.sh` on a clean machine installs git/curl/python3/Ansible/Homebrew if missing and is idempotent if present
- [x] Homebrew prefix resolves correctly per platform (`/opt/homebrew` on macOS, `/home/linuxbrew/.linuxbrew` on Linux)
- [x] `site.yml` runs a pre-flight phase that checks OS support, network reachability, sudo availability, disk space, and target-file writability, and reports ALL failures together before making changes
- [x] A failing pre-flight stops the run with clear, specific reasons and makes no changes
- [x] The healthcheck role runs at least one named probe, prints a pass/fail summary, and exits non-zero on failure
- [x] `bootstrap.sh --check` runs the playbook in Ansible check mode without modifying the system
- [x] A second run reports `ok` (not `changed`) for every task
