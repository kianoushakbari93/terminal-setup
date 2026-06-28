---
id: terminal-setup-4
title: zsh slice - Powerlevel10k, plugins, glyph-safe templates, chsh, deep health probes
status: done
type: AFK
blocked_by: [terminal-setup-1, terminal-setup-2, terminal-setup-3]
---

## What to build

The complete zsh vertical: install zsh and the zsh stack (powerlevel10k,
zsh-autosuggestions, zsh-syntax-highlighting) via the package layer; introduce the
glyph-safe filter plugin `filter_plugins/glyphs.py` that injects powerline (U+E0Bx) and
Nerd Font glyphs by explicit codepoint so templating never strips them to empty; render
`~/.zshrc` and `~/.p10k.zsh` from Jinja2 templates (Catppuccin Mocha pill prompt, palette
factored into vars) through the merge engine; set zsh as the default shell via `chsh`
(skip if already zsh, print a log-out/in notice where needed); and run the deep zsh health
probes.

This reproduces the current zsh look exactly while being templated and merge-safe.

## Acceptance criteria

- [x] zsh and the zsh plugins install via the package layer and resolve at their per-OS paths
- [x] `filter_plugins/glyphs.py` injects powerline/Nerd glyphs by codepoint; a probe decodes the deployed config and confirms the expected glyphs are present (not empty)
- [x] `~/.zshrc` and `~/.p10k.zsh` render the Catppuccin Mocha pill prompt with palette values sourced from vars
- [x] Existing zsh config is backed up and foreign content preserved in `~/.zshrc.local` per the merge engine
- [x] `chsh` sets zsh as the default shell, skips when already zsh, and prints a re-login notice when activation is deferred
- [x] Deep zsh health probes pass: clean login with zero unexpected stderr, p10k loads and emits expected pill glyphs, autosuggestions + syntax-highlighting active, compinit cache builds, referenced binaries resolve, startup time under threshold
- [x] Re-run is idempotent (`ok`, no new backup)
