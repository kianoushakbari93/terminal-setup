"""Deep bash health probe.

Pure parsing (``parse_bash_health``) plus a thin real runner (``run_bash_health``)
that launches an interactive bash (under a PTY) against a given HOME and feeds its
output to the parser.
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

# Powerline triangles the rendered starship config must contain.
REQUIRED_GLYPHS = (0xE0B0, 0xE0B2)

# Printed by the in-bash probe; parsed back into named checks.
PROBE_SNIPPET = (
    'echo "ble=${BLE_VERSION:+1}"; '
    'echo "starship=${STARSHIP_SHELL:+1}"; '
    'echo "completion=${BASH_COMPLETION_VERSINFO:+1}"'
)


@dataclass(frozen=True)
class ProbeOutcome:
    name: str
    ok: bool
    detail: str = ""


def _flag(stdout: str, key: str) -> bool:
    m = re.search(rf"^{re.escape(key)}=(\d+)\s*$", stdout, re.MULTILINE)
    return bool(m) and m.group(1) == "1"


def parse_bash_health(
    stdout: str,
    stderr: str,
    elapsed_s: float,
    starship_toml: str,
    bashrc_text: str = "",
    threshold_s: float = 2.0,
) -> List[ProbeOutcome]:
    cps = {ord(c) for c in starship_toml}
    glyphs_ok = all(g in cps for g in REQUIRED_GLYPHS)
    clean = stderr.strip() == ""
    sourced_ok = (".aliases" in bashrc_text) and ("bashrc.local" in bashrc_text)
    return [
        ProbeOutcome("bash clean login", clean, "" if clean else stderr.strip()),
        ProbeOutcome("ble.sh loaded", _flag(stdout, "ble")),
        ProbeOutcome("starship active", _flag(stdout, "starship")),
        ProbeOutcome("bash-completion loaded", _flag(stdout, "completion")),
        ProbeOutcome("aliases and .local sourced", sourced_ok,
                     "" if sourced_ok else ".bashrc does not source ~/.aliases and .bashrc.local"),
        ProbeOutcome("prompt glyphs present", glyphs_ok,
                     "" if glyphs_ok else "powerline triangles missing from starship.toml"),
        ProbeOutcome("startup under threshold", elapsed_s < threshold_s,
                     "" if elapsed_s < threshold_s else f"{elapsed_s:.2f}s >= {threshold_s}s"),
    ]


def run_bash_health(
    home: str,
    bash_bin: str = "bash",
    threshold_s: float = 2.0,
    warmup: bool = True,
) -> List[ProbeOutcome]:
    """Launch an interactive bash (under a PTY) with HOME=``home`` and probe it.
    tmux auto-start is suppressed by posing as VS Code's integrated terminal.

    A warm-up run is performed first so the measured startup reflects steady
    state, not one-time cold init."""
    env = dict(os.environ)
    env["HOME"] = home
    env["TERM_PROGRAM"] = "vscode"
    env["TERM"] = env.get("TERM", "xterm-256color")
    env.pop("TMUX", None)
    # Point starship at the rendered config in this HOME.
    env["STARSHIP_CONFIG"] = os.path.join(home, ".config", "starship.toml")

    # ble.sh declines to load under `bash -c`, so run a real interactive bash and
    # feed the probe (then exit) over stdin.
    probe_input = PROBE_SNIPPET + "\nexit\n"
    if warmup:
        ts_pty.run_in_pty([bash_bin, "-i"], env, stdin_data=probe_input)

    start = time.monotonic()
    output = ts_pty.run_in_pty([bash_bin, "-i"], env, stdin_data=probe_input)
    elapsed = time.monotonic() - start

    def _read(path):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        return ""

    toml_text = _read(os.path.join(home, ".config", "starship.toml"))
    bashrc_text = _read(os.path.join(home, ".bashrc"))

    return parse_bash_health(
        output, ts_pty.detect_errors(output), elapsed, toml_text, bashrc_text, threshold_s
    )
