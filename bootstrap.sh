#!/usr/bin/env bash
# =============================================================================
#  bootstrap.sh - single entry point for the Terminal Setup provisioning tool.
#
#  On a clean macOS or Linux box this:
#    1. ensures prerequisites exist (git, curl, python3, Ansible, Homebrew)
#    2. runs the Ansible playbook (site.yml), which gates on pre-flight and
#       ends with the health suite.
#
#  It is idempotent: anything already present is detected and left alone.
#
#  Flags:
#    --check       preview every change (Ansible --check --diff); no mutations
#    --skip-iterm2 skip the macOS iTerm2 role
#    -h, --help    show this help
#
#  Test seam:
#    TS_BOOTSTRAP_DRY_RUN=1  print the resolved plan and exit, installing
#                            nothing and never invoking Ansible for real.
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN="${TS_BOOTSTRAP_DRY_RUN:-0}"

# Extra args forwarded to ansible-playbook.
ANSIBLE_ARGS=()
CHECK=0

usage() {
  cat <<'EOF'
Usage: bootstrap.sh [--check] [--skip-iterm2] [-h|--help]
       bootstrap.sh --restore [--list] [--snapshot STAMP] [--backup-root DIR]

  --check        Preview every change without modifying the system
                 (passes --check --diff to Ansible).
  --skip-iterm2  Skip the macOS iTerm2 configuration role.
  --restore      Revert managed files from a backup snapshot (everything after
                 --restore is passed to the restore tool). Use --list to see
                 snapshots, --snapshot to pick one (default: latest).
  -h, --help     Show this help and exit.
EOF
}

log()  { printf '%s\n' "$*"; }
err()  { printf '%s\n' "$*" >&2; }

RESTORE_ARGS=()

# ---- argument parsing -------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)
      CHECK=1
      ANSIBLE_ARGS+=(--check --diff)
      ;;
    --skip-iterm2)
      ANSIBLE_ARGS+=(--extra-vars "skip_iterm2=true")
      ;;
    --restore)
      # Everything after --restore goes to the restore tool.
      shift
      RESTORE_ARGS=("$@")
      cd "$REPO_DIR"
      exec python3 -m tooling.terminal_setup.restore_cli "${RESTORE_ARGS[@]}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      err "Unknown option: $1"
      usage
      exit 2
      ;;
  esac
  shift
done

# ---- platform detection -----------------------------------------------------
os_family() {
  case "$(uname -s)" in
    Darwin) echo macos ;;
    Linux)  echo linux ;;
    *)      echo unsupported ;;
  esac
}

# Native package manager for Linux prerequisites (not the terminal stack).
linux_pm() {
  if   command -v apt-get >/dev/null 2>&1; then echo apt
  elif command -v dnf     >/dev/null 2>&1; then echo dnf
  elif command -v pacman  >/dev/null 2>&1; then echo pacman
  else echo none
  fi
}

# ---- prerequisite detection (read-only) ------------------------------------
# Order matters: brew is needed to install the others on macOS.
PREREQS=(brew git curl python3 ansible-playbook)

# Map a prerequisite name to the command we probe for it.
MISSING=()

report_prereqs() {
  MISSING=()
  local tool
  for tool in "${PREREQS[@]}"; do
    if command -v "$tool" >/dev/null 2>&1; then
      log "${tool}: present"
    else
      log "${tool}: missing"
      MISSING+=("$tool")
    fi
  done
}

planned_command() {
  if [[ ${#ANSIBLE_ARGS[@]} -gt 0 ]]; then
    log "ansible-playbook -i inventory/localhost.yml site.yml ${ANSIBLE_ARGS[*]}"
  else
    log "ansible-playbook -i inventory/localhost.yml site.yml"
  fi
}

# ---- dry run: report and exit, mutating nothing -----------------------------
if [[ "$DRY_RUN" == "1" ]]; then
  log "== Terminal Setup bootstrap (dry run) =="
  report_prereqs
  if [[ ${#MISSING[@]} -gt 0 ]]; then
    log "Would install: ${MISSING[*]}"
  else
    log "All prerequisites present."
  fi
  log "Planned:"
  planned_command
  exit 0
fi

# ---- prerequisite installation (real run) ----------------------------------
install_homebrew() {
  log "Installing Homebrew..."
  NONINTERACTIVE=1 /bin/bash -c \
    "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Make brew available for the rest of this run.
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  elif [[ -x /home/linuxbrew/.linuxbrew/bin/brew ]]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  fi
}

# Install one prerequisite by name, choosing the right manager for the OS.
install_prereq() {
  local tool="$1" family; family="$(os_family)"
  local formula="$tool"
  [[ "$tool" == "ansible-playbook" ]] && formula="ansible"

  log "Installing ${tool}..."
  if [[ "$family" == "macos" ]]; then
    brew install "$formula"
  else
    case "$(linux_pm)" in
      apt)    sudo apt-get update -y && sudo apt-get install -y "$formula" ;;
      dnf)    sudo dnf install -y "$formula" ;;
      pacman) sudo pacman -Sy --noconfirm "$formula" ;;
      *)      err "No supported Linux package manager found to install ${tool}."; return 1 ;;
    esac
  fi
}

ensure_prerequisites() {
  report_prereqs
  local tool
  for tool in "${MISSING[@]}"; do
    if [[ "$tool" == "brew" ]]; then
      install_homebrew
    else
      install_prereq "$tool"
    fi
  done
}

# ---- real run ---------------------------------------------------------------
main() {
  log "== Terminal Setup bootstrap =="

  if [[ "$(os_family)" == "unsupported" ]]; then
    err "Unsupported operating system: $(uname -s). This tool supports macOS and Linux only."
    exit 1
  fi

  ensure_prerequisites

  if ! command -v ansible-playbook >/dev/null 2>&1; then
    err "ansible-playbook is still unavailable after installation. Aborting."
    exit 1
  fi

  cd "$REPO_DIR"
  if [[ ${#ANSIBLE_ARGS[@]} -gt 0 ]]; then
    exec ansible-playbook -i inventory/localhost.yml site.yml "${ANSIBLE_ARGS[@]}"
  else
    exec ansible-playbook -i inventory/localhost.yml site.yml
  fi
}

main
