---
id: terminal-setup-7
title: iTerm2 (macOS) - font + transparency via defaults, --skip-iterm2 flag
status: done
type: AFK
blocked_by: [terminal-setup-0]
---

## What to build

A macOS-only `iterm2` role that configures iTerm2 to match the setup: set the profile
font to a Nerd Font and enable window transparency, written via `defaults` and scoped
narrowly to those keys. Because writing the plist while iTerm2 is running can be
overwritten on quit, the role instructs a restart. Expose a `--skip-iterm2`
bootstrap/playbook flag, and no-op cleanly on non-macOS hosts.

## Acceptance criteria

- [x] On macOS, the role sets the iTerm2 profile font to a Nerd Font and enables transparency, touching only those keys (via plistlib for the nested per-profile keys that `defaults` cannot reach cleanly)
- [x] The role prints a clear "restart iTerm2 to apply" notice
- [x] `--skip-iterm2` skips the role entirely
- [x] On non-macOS hosts the role is a clean no-op
- [x] Re-running with the keys already set reports `ok` (not `changed`)
