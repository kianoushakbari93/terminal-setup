"""Deep zsh health probe.

Splits into pure parsing (``parse_zsh_health`` - fully unit-testable) and a thin
real runner (``run_zsh_health``) that launches an interactive zsh against a given
ZDOTDIR and feeds its output to the parser.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import List

try:  # works as an Ansible module_util and as a direct import in tests
    from ansible.module_utils import ts_pty
except ImportError:
    import ts_pty

# Powerline caps the rendered p10k prompt must contain (proof glyphs survived).
REQUIRED_GLYPHS = (0xE0B4, 0xE0B6)

# Emitted by the in-zsh probe; parsed back into named checks.
PROBE_SNIPPET = (
    'print -r -- "p10k=$(( $+functions[p10k] ))"; '
    'print -r -- "autosuggest=$(( $+ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE ))"; '
    'print -r -- "highlight=$(( $+ZSH_HIGHLIGHT_STYLES ))"'
)


@dataclass(frozen=True)
class ProbeOutcome:
    name: str
    ok: bool
    detail: str = ""


def _flag(stdout: str, key: str) -> bool:
    m = re.search(rf"^{re.escape(key)}=(\d+)\s*$", stdout, re.MULTILINE)
    return bool(m) and m.group(1) == "1"


def parse_zsh_health(
    stdout: str,
    stderr: str,
    elapsed_s: float,
    p10k_text: str,
    threshold_s: float = 2.0,
) -> List[ProbeOutcome]:
    cps = {ord(c) for c in p10k_text}
    glyphs_ok = all(g in cps for g in REQUIRED_GLYPHS)
    clean = stderr.strip() == ""
    return [
        ProbeOutcome("zsh clean login", clean, "" if clean else stderr.strip()),
        ProbeOutcome("p10k loaded", _flag(stdout, "p10k")),
        ProbeOutcome("autosuggestions active", _flag(stdout, "autosuggest")),
        ProbeOutcome("syntax-highlighting active", _flag(stdout, "highlight")),
        ProbeOutcome("prompt glyphs present", glyphs_ok,
                     "" if glyphs_ok else "powerline caps missing from p10k config"),
        ProbeOutcome("startup under threshold", elapsed_s < threshold_s,
                     "" if elapsed_s < threshold_s else f"{elapsed_s:.2f}s >= {threshold_s}s"),
    ]


def run_zsh_health(
    zdotdir: str,
    zsh_bin: str = "zsh",
    threshold_s: float = 2.0,
    warmup: bool = True,
) -> List[ProbeOutcome]:
    """Launch an interactive zsh (under a PTY) against ``zdotdir`` and probe it.
    tmux auto-start is suppressed by posing as VS Code's integrated terminal
    and as an already-nested tmux client.

    A warm-up run is performed first so the measured startup reflects steady
    state, not one-time cold init (compinit cache build, gitstatusd download)."""
    env = dict(os.environ)
    env["ZDOTDIR"] = zdotdir
    env["TERM_PROGRAM"] = "vscode"   # skips the .zshrc tmux auto-start branch
    env["TERM"] = env.get("TERM", "xterm-256color")
    # Pose as an already-nested tmux client: user rc files commonly guard tmux
    # auto-start with `[ -z "$TMUX" ]`, and a launched tmux would swallow the
    # probe until its timeout.
    env["TMUX"] = "terminal-setup-health-probe,0,0"

    if warmup:
        ts_pty.run_in_pty([zsh_bin, "-i", "-c", PROBE_SNIPPET], env)

    start = time.monotonic()
    output = ts_pty.run_in_pty([zsh_bin, "-i", "-c", PROBE_SNIPPET], env)
    elapsed = time.monotonic() - start

    p10k_path = os.path.join(zdotdir, ".p10k.zsh")
    p10k_text = ""
    if os.path.exists(p10k_path):
        with open(p10k_path, encoding="utf-8") as fh:
            p10k_text = fh.read()

    return parse_zsh_health(output, ts_pty.detect_errors(output), elapsed, p10k_text, threshold_s)
