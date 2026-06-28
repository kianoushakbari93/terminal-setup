---
id: terminal-setup-6
title: tmux slice - tpm, catppuccin, battery status bar, deep health probes
status: done
type: AFK
blocked_by: [terminal-setup-1, terminal-setup-2, terminal-setup-3]
---

## What to build

The complete tmux vertical: install tmux and tpm, and the catppuccin/tmux, tmux-sensible,
tmux-yank, and tmux-battery plugins; render `~/.tmux.conf` from a Jinja2 template
(Catppuccin Mocha - window tabs bottom-left with rounded caps, battery/date-time/session
bottom-right, transparent middle following terminal transparency with opaque pills;
palette and flavor factored into vars) through the merge engine using the glyph-safe
filter for the powerline cap glyphs; install plugins non-interactively; and run the deep
tmux health probes including a batteryless-host fallback.

## Acceptance criteria

- [x] tmux + tpm + catppuccin + tmux-battery (and sensible/yank) install and are present under `~/.tmux/plugins`
- [x] `~/.tmux.conf` renders the Catppuccin Mocha bar with palette/flavor from vars; window-cap glyphs render via the glyph-safe filter (decoded and confirmed non-empty)
- [x] Existing `~/.tmux.conf` is backed up and foreign content preserved per the merge engine
- [x] tpm installs declared plugins non-interactively during the run
- [x] Deep tmux health probes pass: server starts and config parses, `status-right` modules (battery / date-time / session) render non-empty, window tabs render with rounded caps, required plugins present
- [x] On a batteryless host the battery module detects absence and falls back to a CPU/spacer module instead of rendering empty
- [x] Re-run is idempotent (`ok`, no new backup)
