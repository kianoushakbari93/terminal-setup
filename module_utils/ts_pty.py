"""Shared helpers for running an interactive shell under a real PTY and cleaning
its output. Used by the zsh and bash deep-health probes so a genuinely
interactive shell (job control, prompt frameworks) behaves correctly.
"""
from __future__ import annotations

import os
import pty
import re
import select
import subprocess
import time
from typing import List

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

# Shell/plugin output indicating a genuine problem (not benign chatter).
_ERROR_RE = re.compile(
    r"(?i)(\berror\b|can't |cannot |command not found|parse error|"
    r"insecure director|gitstatus.*fail|failed to|syntax error|"
    r"no such option|no such file|bad (option|pattern)|: unbound)"
)


def clean(raw: str) -> str:
    return _ANSI_RE.sub("", raw).replace("\r", "")


def detect_errors(output: str) -> str:
    """Return the error-looking lines of a (combined) shell session."""
    bad = [ln for ln in clean(output).splitlines() if _ERROR_RE.search(ln)]
    return "\n".join(bad)


def run_in_pty(argv: List[str], env: dict, timeout: int = 30, stdin_data: str = None) -> str:
    """Run a command attached to a real PTY and return its combined output.

    When ``stdin_data`` is given it is written to the PTY after launch - needed
    for shells like ble.sh-enabled bash that refuse to load under ``-c`` (they
    detect BASH_EXECUTION_STRING), so the probe must arrive on stdin instead.
    """
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        argv, stdin=slave, stdout=slave, stderr=slave,
        env=env, start_new_session=True, close_fds=True,
    )
    os.close(slave)
    if stdin_data:
        os.write(master, stdin_data.encode())
    chunks = []
    deadline = time.monotonic() + timeout
    while True:
        if time.monotonic() > deadline:
            proc.kill()
            break
        r, _, _ = select.select([master], [], [], 1.0)
        if r:
            try:
                data = os.read(master, 4096)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
        elif proc.poll() is not None:
            break
    try:
        os.close(master)
    except OSError:
        pass
    proc.wait()
    return clean(b"".join(chunks).decode("utf-8", errors="replace"))
