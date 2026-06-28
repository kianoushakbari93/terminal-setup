---
id: terminal-setup-1
title: Config merge engine - backup, managed block, .local extraction, idempotency
status: done
type: AFK
blocked_by: [terminal-setup-0]
---

## What to build

The lossless, idempotent config-merge capability, delivered end-to-end through a custom
Python Ansible module `library/config_merge.py` and exercised by the `configs` role
deploying one minimal managed file (a stub `~/.zshrc` with a managed block). This proves
the merge contract through every layer before the real shell slices depend on it.

The module: detects an existing target; takes a timestamped backup under
`~/.terminal-setup/backups/<UTC-timestamp>/` before any write; owns only the content
between `# >>> terminal-setup >>>` and `# <<< terminal-setup <<<` markers; on first run
(no markers) moves every existing line into a sibling `.local` file that the managed
block sources at the end, scrubbing lines matching known tool signatures (powerlevel10k
source, `starship init`, ble.sh, `~/.p10k.zsh`, tmux plugin lines) so prompt/plugin setup
is never duplicated; on subsequent runs rewrites the managed block only if rendered bytes
differ. Returns structured results so messages are precise.

## Acceptance criteria

- [x] `config_merge.py` is a well-formed Ansible module with documented args (target path, managed content, local path, signature patterns) and `changed`/structured return
- [x] An existing file with custom user content is backed up before modification, with a manifest entry recording original path → backup path
- [x] First run with no markers moves all foreign lines into `<target>.local`, which the managed block sources at the end
- [x] Known tool-signature lines are scrubbed during first migration and not duplicated into `.local`
- [x] Re-running with unchanged inputs reports `ok` (not `changed`), creates no new backup, and leaves `.local` untouched
- [x] A health probe verifies: foreign content preserved in `.local`, managed block present and current, and the file sources `.local`
- [x] Custom comment syntax is parameterized so the same engine works for shell, tmux, and TOML files
