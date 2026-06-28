---
id: terminal-setup-9
title: README + screenshots - capture live terminal, write the 11-section README
status: done
type: HITL
blocked_by: [terminal-setup-4, terminal-setup-5, terminal-setup-6]
---

## What to build

The user-facing documentation. After the shells and tmux are provisioned, capture real
screenshots of the resulting terminal and write the repo-root `README.md`. HITL because
the screenshots need a human eye to confirm they look right.

Screenshots in `docs/screenshots/` (relative paths): `zsh-p10k.png`, `bash-starship.png`,
`tmux-statusbar.png`, `healthcheck.png`. README sections: (1) What you get, (2) Features,
(3) Supported platforms, (4) Prerequisites, (5) Quick start, (6) What it does step by
step, (7) Flags, (8) Customizing via `group_vars/all.yml`, (9) Your existing config /
backups / `.local` merge, (10) Health checks & troubleshooting, (11) Uninstall / restore.

## Acceptance criteria

- [x] Real screenshots captured from the live terminal after a run and saved under `docs/screenshots/`
- [x] Human confirms the screenshots accurately represent the result
- [x] `README.md` at repo root contains all 11 sections with the screenshots referenced by relative path
- [x] The quick-start shows the single `bootstrap.sh` command and the step-by-step section mirrors the run-flow phases
- [x] Flags, customizing, backup/`.local`, troubleshooting, and uninstall/restore are all documented accurately against the implemented behavior
