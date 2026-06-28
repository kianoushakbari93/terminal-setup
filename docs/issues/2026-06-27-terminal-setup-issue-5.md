---
id: terminal-setup-5
title: bash slice - starship, ble.sh, glyph-safe templates, deep health probes
status: done
type: AFK
blocked_by: [terminal-setup-1, terminal-setup-2, terminal-setup-3]
---

## What to build

The complete bash vertical: install bash, starship, and ble.sh, plus bash-completion@2,
via the package layer; render `~/.bashrc`, `~/.bash_profile`, and
`~/.config/starship.toml` from Jinja2 templates (Dracula sharp-triangle starship prompt,
distinct from zsh; ble.sh Dracula faces; palette factored into vars) through the merge
engine, using the glyph-safe filter for the starship powerline triangles and Nerd icons;
and run the deep bash health probes.

## Acceptance criteria

- [x] bash, starship, ble.sh, and bash-completion@2 install via the package layer and resolve at their per-OS paths
- [x] `~/.bashrc`, `~/.bash_profile`, and `~/.config/starship.toml` render the Dracula theme with palette values from vars
- [x] starship triangles and Nerd icons render via the glyph-safe filter; a probe decodes the deployed `starship.toml` and confirms the expected glyphs are present (not empty)
- [x] Existing bash configs are backed up and foreign content preserved in `.local` per the merge engine
- [x] Deep bash health probes pass: clean login with zero unexpected stderr, ble.sh attaches, starship renders triangles, bash-completion@2 loaded, `.local` sourced with aliases present, startup time under threshold
- [x] Re-run is idempotent (`ok`, no new backup)
