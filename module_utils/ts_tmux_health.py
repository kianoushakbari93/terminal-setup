"""Deep tmux health probe.

Pure parsing (``parse_tmux_health``) plus a thin real runner
(``run_tmux_health``) that boots an isolated tmux server (custom socket) from a
rendered config and inspects its status bar and plugins. Non-destructive: the
custom socket means the user's own tmux server is never touched.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, List

# Rounded window-cap glyphs the tab format must contain.
REQUIRED_CAPS = (0xE0B6, 0xE0B4)


def battery_required(conf_text: str) -> bool:
    """tmux-battery is declared only on hosts with a battery, so the plugin is
    required exactly when the rendered config loads it."""
    return "tmux-battery" in conf_text


@dataclass(frozen=True)
class ProbeOutcome:
    name: str
    ok: bool
    detail: str = ""


def parse_tmux_health(
    config_ok: bool,
    config_err: str,
    status_right: str,
    window_format: str,
    plugins_present: Dict[str, bool],
) -> List[ProbeOutcome]:
    parse_ok = config_ok and not config_err.strip()
    # Non-empty status with at least one digit => date/battery/session rendered.
    status_ok = bool(status_right.strip()) and bool(re.search(r"\d", status_right))
    caps = {ord(c) for c in window_format}
    caps_ok = all(c in caps for c in REQUIRED_CAPS)
    missing = [name for name, ok in plugins_present.items() if not ok]
    return [
        ProbeOutcome("tmux config parses", parse_ok, "" if parse_ok else config_err.strip()),
        ProbeOutcome("status-right modules non-empty", status_ok,
                     "" if status_ok else "status-right expanded empty"),
        ProbeOutcome("window tabs rounded caps", caps_ok,
                     "" if caps_ok else "rounded caps missing from window format"),
        ProbeOutcome("required plugins present", not missing,
                     "" if not missing else "missing plugins: " + ", ".join(missing)),
    ]


def run_tmux_health(
    conf_path: str,
    home: str,
    plugins_root: str = None,
    tmux_bin: str = "tmux",
    socket: str = "ts_health",
) -> List[ProbeOutcome]:
    env = dict(os.environ)
    env["HOME"] = home
    env["TERM"] = env.get("TERM", "xterm-256color")
    # tpm and the plugins it sources call plain `tmux` from run-shell hooks, so
    # the server environment must resolve it - guarantee that regardless of the
    # caller's PATH by prepending the probed binary's own directory.
    bin_dir = os.path.dirname(tmux_bin)
    if bin_dir:
        env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
    plugins_root = plugins_root or os.path.join(home, ".tmux", "plugins")

    def tmux(*args):
        return subprocess.run(
            [tmux_bin, "-L", socket, *args], env=env, capture_output=True, text=True
        )

    start = tmux("-f", conf_path, "new-session", "-d", "-s", "probe")
    config_ok = start.returncode == 0
    config_err = (start.stderr or start.stdout).strip()

    status_right = window_format = ""
    if config_ok:
        # The config's `run tpm` loads plugins asynchronously; the catppuccin
        # status modules appear only once that finishes. Poll briefly instead
        # of failing on a not-yet-populated status line.
        deadline = time.monotonic() + 5.0
        while True:
            status_right = tmux("display-message", "-p", "#{E:status-right}").stdout
            if re.search(r"\d", status_right) or time.monotonic() >= deadline:
                break
            time.sleep(0.2)
        window_format = tmux("display-message", "-p", "#{window-status-current-format}").stdout
    tmux("kill-server")

    plugins_present = {
        "tpm": os.path.isdir(os.path.join(plugins_root, "tpm")),
        "catppuccin": os.path.exists(os.path.join(plugins_root, "tmux", "catppuccin.tmux")),
    }
    try:
        with open(conf_path, encoding="utf-8") as f:
            conf_text = f.read()
    except OSError:
        conf_text = ""
    if battery_required(conf_text):
        plugins_present["battery"] = os.path.isdir(os.path.join(plugins_root, "tmux-battery"))
    return parse_tmux_health(config_ok, config_err, status_right, window_format, plugins_present)
