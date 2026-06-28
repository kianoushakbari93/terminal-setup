---
id: terminal-setup-2
title: Cross-OS package layer - brew/apt/dnf/pacman/Linuxbrew abstraction
status: done
type: AFK
blocked_by: [terminal-setup-0]
---

## What to build

A reusable `packages` role that abstracts package installation across macOS Homebrew,
Debian/Ubuntu apt, Fedora/RHEL dnf, Arch pacman, and Linuxbrew, plus the per-OS variable
resolution that maps a logical package name to the right concrete name and manager. The
agreed strategy: the native package manager installs only base prerequisites; Linuxbrew
is used uniformly for the terminal stack on all Linux distros. Proven end-to-end by
installing one real package (e.g. `tmux`) on the host and verifying it via a health
probe.

`group_vars/all.yml` (and role defaults) carry the logical→concrete package maps and the
per-OS brew/share path variables that templates will later consume.

## Acceptance criteria

- [x] The role installs a requested logical package on the current host using the correct manager for the detected OS/distro
- [x] Native PM is used only for prerequisites; Linuxbrew is selected for the terminal stack on Linux
- [x] Logical→concrete package name maps live in vars, not inline in tasks
- [x] Per-OS path variables (brew prefix, plugin share dir, font dir) are resolved and available to later roles
- [x] Installing an already-present package reports `ok` (not `changed`)
- [x] A health probe confirms the installed test package resolves on `PATH`
- [x] Unsupported distro fails fast with a clear, specific message
