# Terminal Setup Provisioning Tool - Design

- **Date:** 2026-06-27
- **Status:** Approved (interview + lavish review complete)
- **Owner:** Kianoush
- **Stack:** Ansible + Python, single `bootstrap.sh` entry point

## 1. Goal

One command on a brand-new machine reproduces the exact terminal experience that
currently exists on this Mac - zsh + Powerlevel10k, bash + starship, tmux with the
full Catppuccin status bar, Nerd Fonts, and all supporting CLIs - safely, idempotently,
and verifiably, on both macOS and Linux.

## 2. Current state

The existing configs (`~/.zshrc`, `~/.p10k.zsh`, `~/.bashrc`, `~/.bash_profile`,
`~/.config/starship.toml`, `~/.tmux.conf`) were hand-built on a single Apple Silicon
Mac. They hardcode `/opt/homebrew` paths, have no backup/merge story, are not
reproducible on a clean machine, and have no automated verification. They are the
"golden" end-state this tool must render faithfully.

## 3. Target behavior

A versioned repository with a single `bootstrap.sh`. On a clean box it installs any
missing prerequisites (git/curl, Homebrew, Python, Ansible), then runs an Ansible
playbook that:

1. Validates the environment up front (pre-flight, fail-fast).
2. Installs packages, fonts, shells, plugins, and CLIs.
3. Renders templated configs per-OS, backing up and losslessly merging any
   pre-existing user content.
4. Sets zsh as the default shell and (on macOS) configures iTerm2.
5. Runs a deep functional health suite across zsh and bash under tmux.

Re-running the tool produces zero churn (idempotent): unchanged tasks report `ok`,
not `changed`, and no new backups are created.

## 4. Decisions (locked)

| # | Decision | Choice | Consequence |
|---|----------|--------|-------------|
| 1 | Target platforms | macOS + Linux | Per-OS package maps and path vars; broadest surface |
| 2 | Entry point | Single `bootstrap.sh` | POSIX script self-installs brew/python/ansible, then hands off |
| 3 | Config generation | Jinja2 templates + vars | One source of truth renders correct paths per platform |
| 4 | Merge strategy | Managed block + `.local` | Tool owns a marker block; foreign lines move to `~/.zshrc.local` etc. |
| 5 | Health checks | Deep functional suite | Render/module/timing assertions per shell, under tmux |
| 6 | Fonts | Several Nerd Fonts | MesloLGS NF + JetBrainsMono NF + FiraCode NF |
| 7 | Theming | Reproduce exactly, vars-ready | Current look is default; palettes/flavor factored into a vars file |
| 8 | Linux families | apt + dnf + pacman + Linuxbrew | Native PM for prerequisites only; Linuxbrew for the terminal stack |
| 9 | Scope add-ons | chsh + shells + iTerm2 + CLIs | All four invasive actions are in scope |
| 10 | Failure mode | Fail-fast + pre-flight | Validate env up front; stop at first hard error with remediation |

## 5. Architecture

### 5.1 Run flow

```
bootstrap.sh
  -> ensure git/curl (native PM if missing)
  -> clone repo to ~/.terminal-setup
  -> ensure Homebrew (mac: /opt/homebrew, linux: /home/linuxbrew)
  -> ensure python3 + ansible
  -> ansible-playbook site.yml
       -> [GATE] pre-flight: OS, network, sudo, disk, shells writable
                 (reports ALL problems, exits with backups intact on failure)
       -> role: packages   (brew / apt / dnf / pacman)
       -> role: fonts      (Meslo + JetBrainsMono + FiraCode)
       -> role: shells     (zsh plugins, starship, ble.sh, tpm)
       -> role: configs    (backup -> render .j2 -> merge foreign -> .local)
       -> role: chsh       (default shell -> zsh)
       -> role: iterm2     (macOS only: font + transparency)
       -> [GATE] role: healthcheck (zsh + bash under tmux)
  -> healthy terminal
```

Both gates fail-fast: a failed pre-flight stops before any change; a failed health
check stops at the end with a named, actionable reason. Backups are always left intact.

### 5.2 Repository layout

```
Terminal-setup/
├─ bootstrap.sh                  # the single entry point
├─ ansible.cfg
├─ site.yml                      # top playbook: pre-flight + roles in order
├─ inventory/localhost.yml
├─ group_vars/all.yml            # palettes, fonts, pkg lists, toggles (vars-ready)
├─ roles/
│  ├─ preflight/    packages/    fonts/    shells/
│  ├─ configs/      chsh/        iterm2/   healthcheck/
│  └─ */templates/*.j2   */tasks/main.yml   */defaults/main.yml
├─ library/                      # custom Python Ansible modules
│  ├─ config_merge.py            # backup + managed-block + .local extraction
│  └─ shell_healthcheck.py       # deep functional probes, structured results
├─ filter_plugins/glyphs.py      # inject powerline/Nerd glyphs safely
├─ README.md                     # what it does, how to run, screenshots
├─ docs/designs/                 # this design, then the PRD
├─ docs/screenshots/             # terminal previews used by README
└─ tests/                        # molecule / CI smoke (stretch)
```

### 5.3 Why Python modules

The merge logic and health probes need real parsing, structured error objects, and
precise Unicode handling. In particular, ordinary text-templating tools strip
powerline (U+E0Bx) and Nerd Font glyphs to empty, so glyphs are injected via a
dedicated Python filter plugin using explicit codepoint escapes and then verified.
This is far cleaner as Python modules than as shell-in-YAML, and it produces the
"correct error messages" requirement.

## 6. Configuration strategy

### 6.1 Templating

Every config is a Jinja2 `.j2` template. OS-specific values (Homebrew prefix, plugin
share paths, font install dir, package names) come from variables resolved per-OS in
`group_vars/all.yml` plus role defaults. macOS resolves to `/opt/homebrew`; Linux to
`/home/linuxbrew/.linuxbrew` (Linuxbrew is used uniformly for the terminal stack on
all Linux distros, with the native package manager used only for base prerequisites).

### 6.2 Theming (vars-ready)

The current aesthetic is the default and is reproduced exactly:

- **zsh:** Catppuccin Mocha Powerlevel10k "pill" prompt.
- **bash:** Dracula starship sharp-triangle powerline (deliberately distinct from zsh).
- **tmux:** Catppuccin Mocha status bar - window tabs bottom-left, battery/date-time/
  session bottom-right, transparent middle following terminal transparency, opaque pills.

Palettes and the Catppuccin flavor are factored into variables so they can be changed
later without editing templates. No multi-theme engine is built in v1 (YAGNI).

### 6.3 Merge: lossless and idempotent

The tool owns only the content between markers, rewritten each run:

```
# >>> terminal-setup >>>
  ... rendered prompt / plugins / theme ...
  [[ -f ~/.zshrc.local ]] && source ~/.zshrc.local
# <<< terminal-setup <<<
```

Procedure for each managed file (`.zshrc`, `.bashrc`, `.bash_profile`,
`.tmux.conf`, `starship.toml`):

1. Detect an existing file.
2. Take a timestamped backup before any write.
3. If no markers exist (first run / hand-written config), treat every existing line as
   foreign and move it to the sibling `.local` file (`~/.zshrc.local`,
   `~/.bashrc.local`, etc.), which the managed block sources at the end.
   - During this first migration, lines matching known tool signatures (sourcing
     `powerlevel10k`, `starship init`, ble.sh, `~/.p10k.zsh`, the tmux plugin lines)
     are scrubbed so prompt/plugin setup is never duplicated into `.local`.
4. Render the managed block fresh from the template.
5. On subsequent runs, the managed block is rewritten only if its rendered bytes
   differ; non-marker content is left untouched. A re-run with no changes reports
   `ok` for every task and creates no new backup.

For `tmux.conf` (no native include-at-top idiom like the shells) and `starship.toml`
(TOML, not shell), the same managed-block/`.local` concept applies using the
appropriate comment syntax and a `source-file ~/.tmux.conf.local` (tmux) /
documented include for starship. Foreign content is preserved identically.

### 6.4 Backups and dry run

- **Backups:** every replaced file is copied to
  `~/.terminal-setup/backups/<UTC-timestamp>/` before any write, with a manifest so a
  run is reversible.
- **Dry run:** `bootstrap.sh --check` passes Ansible `--check --diff` so the user can
  preview every change (including the rendered config diff) without touching the system.

## 7. Scope add-ons

- **Set zsh as default shell:** `chsh -s` to zsh (installing zsh first if missing);
  detect and skip if already zsh. On Linux this may require a password and a re-login;
  the tool prints a clear "log out/in to activate" notice.
- **Install shells/tmux themselves:** ensure zsh, bash, and tmux binaries exist via the
  appropriate package manager, not just their configs.
- **iTerm2 (macOS only):** write font + transparency keys via `defaults`, scoped
  narrowly, and instruct a restart (writing the plist while iTerm2 runs can be
  overwritten on quit).
- **CLI niceties:** install supporting CLIs the configs reference (gnu-sed,
  bash-completion@2, fzf, etc.) so no rc-file reference is a dangling pointer.

## 8. Failure handling

- **Pre-flight phase** runs first and reports *all* environment problems up front
  (network reachability, sudo availability, disk space, writable target files,
  required base tools). It does not make changes.
- **Execution** is fail-fast: the first hard error stops the run with a specific,
  human-readable reason and a remediation hint. Backups remain intact, so the user is
  never left with a half-broken shell silently.
- Custom Python modules return structured results so messages are precise rather than
  raw tracebacks.

## 9. Deep health suite (final gate)

Runs non-interactively against a fresh login of each shell, inside a throwaway tmux
server. Each probe is named and prints an actionable reason on failure. Any failure
fails the run.

**zsh:** clean login with zero unexpected stderr; p10k loads and the prompt emits the
expected pill glyphs; autosuggestions and syntax-highlighting active; compinit cache
builds; referenced binaries resolve; startup time under a threshold.

**bash:** clean login with zero unexpected stderr; ble.sh attaches and starship renders
its triangles; bash-completion@2 loaded; `.local` sourced and aliases present; startup
time under a threshold.

**tmux:** server starts and config parses; `status-right` modules render non-empty
(battery / date-time / session); window tabs render with rounded caps; required plugins
present (tpm, catppuccin, battery). On batteryless Linux hosts the battery module
detects absence and falls back to a CPU/spacer module rather than rendering empty.

**environment:** all three Nerd Fonts installed and discoverable; brew prefix on PATH;
default shell is zsh; no dangling references in the rc files.

## 10. README.md (first-class deliverable)

Shipped at the repo root so anyone can understand the project without reading Ansible.
Sections:

1. What you get - hero screenshots of zsh, bash, and the tmux bar after setup.
2. Features - prompts, themes, fonts, plugins, status modules.
3. Supported platforms - macOS (Intel/ARM), Debian/Ubuntu, Fedora/RHEL, Arch.
4. Prerequisites - what bootstrap installs vs what must already exist.
5. Quick start - the one-line `bootstrap.sh` command.
6. What it does, step by step - the ordered phase list mirroring the flow diagram.
7. Flags - `--check` (dry run), `--tags`, `--skip-iterm2`, etc.
8. Customizing - editing `group_vars/all.yml` (palettes, fonts, toggles).
9. Your existing config - backup location and the `.local` merge explained.
10. Health checks and troubleshooting - how to read the pass/fail output.
11. Uninstall / restore - reverting from a backup snapshot.

Screenshots live in `docs/screenshots/` (referenced with relative paths) and are
captured from the live terminal after a real run, not mockups: `zsh-p10k.png`,
`bash-starship.png`, `tmux-statusbar.png`, `healthcheck.png`.

## 11. Risks and open questions (resolved)

- **Q1 - chsh on Linux:** may need a password and a re-login. Decision: perform it,
  then print a clear "log out/in to activate" notice.
- **Q2 - iTerm2 prefs:** writing the plist while iTerm2 runs can be overwritten on
  quit. Decision: write via `defaults`, scope to font + transparency, instruct a
  restart. A `--skip-iterm2` flag is available.
- **Q3 - Linuxbrew + battery:** tmux-battery on a batteryless host shows empty.
  Decision: detect and fall back to a CPU/spacer module.
- **Q4 - testing breadth:** local health suite is the v1 requirement. CI (GitHub
  Actions + molecule containers for apt/dnf/pacman) is a documented stretch in
  `tests/`, not v1 scope.

## 12. Non-goals (v1)

- No multi-theme catalog / theming engine (themes are vars, current look is default).
- No Windows / WSL-specific support.
- No CI matrix in v1 (stretch only).
- No terminal-emulator support beyond iTerm2 on macOS.
```
