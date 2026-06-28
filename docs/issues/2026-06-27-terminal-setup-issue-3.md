---
id: terminal-setup-3
title: Fonts - install Meslo + JetBrainsMono + FiraCode Nerd Fonts cross-OS
status: done
type: AFK
blocked_by: [terminal-setup-2]
---

## What to build

A `fonts` role that installs the three Nerd Fonts the prompts and status bar depend on -
MesloLGS NF, JetBrainsMono Nerd Font, and FiraCode Nerd Font - on macOS (via Homebrew
cask) and on Linux (into `~/.local/share/fonts` with a font-cache refresh). End-to-end:
install then verify discoverability with a health probe.

## Acceptance criteria

- [x] All three Nerd Fonts install on macOS via the appropriate cask
- [x] All three Nerd Fonts install on Linux into `~/.local/share/fonts` and `fc-cache` is refreshed
- [x] Re-running with fonts already present reports `ok` (not `changed`)
- [x] A health probe confirms each font is discoverable (e.g. via `fc-list` on Linux, the fonts dir on macOS)
- [x] Failure to download a font fails fast with a clear reason and leaves the system unchanged for that font
