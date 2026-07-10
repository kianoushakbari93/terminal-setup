"""Config-merge engine: own a marker-delimited managed block inside a config
file while losslessly preserving the user's foreign content in a sibling
``.local`` file, idempotently.

Pure logic (no Ansible imports) so it is unit-testable directly and reusable by
the ``config_merge`` Ansible module via ``ansible.module_utils``.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Sequence

MANIFEST_NAME = "manifest.jsonl"

DEFAULT_BEGIN = "# >>> terminal-setup >>>"
DEFAULT_END = "# <<< terminal-setup <<<"

# Lines matching these (substring, case-insensitive) are tool-owned prompt/plugin
# setup. During first migration they are dropped rather than copied to .local, so
# the managed block never duplicates prompt configuration the tool re-installs.
DEFAULT_SIGNATURES: Sequence[str] = (
    "powerlevel10k",
    ".p10k.zsh",
    "starship init",
    # Competing prompt frameworks: the tool owns the prompt, and the frameworks
    # role uninstalls these, so their config must not migrate into .local
    # (sourcing a removed path would error on every launch).
    "oh-my-posh",
    "oh-my-zsh",
    "zsh_theme",
    "ble.sh",
    "blesh/ble",
    "zsh-autosuggestions",
    "zsh-syntax-highlighting",
    "tmux/plugins/tpm",
    "@plugin '",
    "@plugin \"",
    "catppuccin/tmux",
    "tmux-battery",
    # tmux status-bar theming: the tool owns the bar end-to-end (window tabs,
    # right-side modules, styles). Leftover theme lines in .local would source
    # after the managed block and silently override the rendered bar.
    "status-left",
    "status-right",
    "status-style",
    "status-position",
    "status-justify",
    "status-interval",
    "status-bg",
    "status-fg",
    "window-status",
)


@dataclass
class MergeResult:
    target_path: str
    local_path: str
    changed: bool
    backup_path: Optional[str] = None
    actions: List[str] = field(default_factory=list)
    before_content: str = ""   # target content before the merge (for diff)
    after_content: str = ""    # target content after the merge (for diff)


@dataclass(frozen=True)
class ManifestEntry:
    original: str
    backup: str
    timestamp: str


def read_manifest(backup_root: str) -> List[ManifestEntry]:
    """Read all backup manifest entries recorded under ``backup_root``."""
    path = os.path.join(os.path.expanduser(backup_root), MANIFEST_NAME)
    if not os.path.exists(path):
        return []
    entries: List[ManifestEntry] = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                d = json.loads(line)
                entries.append(ManifestEntry(d["original"], d["backup"], d["timestamp"]))
    return entries


def _record_manifest(backup_root: str, original: str, backup: str, now: datetime) -> None:
    backup_root = os.path.expanduser(backup_root)
    os.makedirs(backup_root, exist_ok=True)
    entry = {"original": original, "backup": backup, "timestamp": now.isoformat() + "Z"}
    with open(os.path.join(backup_root, MANIFEST_NAME), "a") as fh:
        fh.write(json.dumps(entry) + "\n")


def _render_block(begin, end, managed_content, source_line):
    return "\n".join([begin, managed_content.rstrip("\n"), source_line, end]) + "\n"


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    problems: List[str] = field(default_factory=list)


def verify(
    target_path: str,
    managed_content: str,
    *,
    begin_marker: str = DEFAULT_BEGIN,
    end_marker: str = DEFAULT_END,
    local_suffix: str = ".local",
) -> VerifyResult:
    """Confirm a target's post-merge invariants: the managed block is present
    and current, and the file sources its .local sibling."""
    target_path = os.path.expanduser(target_path)
    local_path = target_path + local_suffix
    problems: List[str] = []

    if not os.path.exists(target_path):
        return VerifyResult(False, [f"{target_path} does not exist"])

    with open(target_path) as fh:
        body = fh.read()

    if begin_marker not in body or end_marker not in body:
        problems.append("managed block markers are missing")
    else:
        block = body.split(begin_marker, 1)[1].split(end_marker, 1)[0]
        for line in managed_content.strip().splitlines():
            if line.strip() and line not in block:
                problems.append("managed block is stale (expected content not found)")
                break
        if os.path.basename(local_path) not in block:
            problems.append("managed block does not source the .local file")

    return VerifyResult(ok=not problems, problems=problems)


_IF_OPEN = re.compile(r"^\s*if\b")
_FI_CLOSE = re.compile(r"^\s*fi\b")
_FI_INLINE = re.compile(r"[;\s]fi\s*(#.*)?$")


def _scrub_signatures(text: str, signatures: Sequence[str]) -> str:
    lowered = [s.lower() for s in signatures]

    def is_signature(line: str) -> bool:
        return any(sig in line.lower() for sig in lowered)

    lines = text.splitlines()
    kept: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not is_signature(line):
            kept.append(line)
            i += 1
            continue
        # A tool-owned line that opens a multi-line `if` guard (the common
        # `if [ -f plugin ]; then source plugin; fi` pattern) takes the whole
        # block with it up to the matching `fi`; dropping only the matching
        # lines would strand the `fi` and break the shell.
        if _IF_OPEN.match(line) and not _FI_INLINE.search(line):
            depth = 1
            i += 1
            while i < len(lines) and depth:
                if _IF_OPEN.match(lines[i]) and not _FI_INLINE.search(lines[i]):
                    depth += 1
                elif _FI_CLOSE.match(lines[i]):
                    depth -= 1
                i += 1
            continue
        i += 1
    return "\n".join(kept)


def _backup(target_path: str, backup_root: str, now: datetime) -> str:
    backup_root = os.path.expanduser(backup_root)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    snapshot = os.path.join(backup_root, stamp)
    os.makedirs(snapshot, exist_ok=True)
    dest = os.path.join(snapshot, os.path.basename(target_path))
    shutil.copy2(target_path, dest)
    _record_manifest(backup_root, target_path, dest, now)
    return dest


def merge_config(
    target_path: str,
    managed_content: str,
    *,
    begin_marker: str = DEFAULT_BEGIN,
    end_marker: str = DEFAULT_END,
    local_suffix: str = ".local",
    source_line: Optional[str] = None,
    backup_root: str = "~/.terminal-setup/backups",
    signature_patterns: Sequence[str] = DEFAULT_SIGNATURES,
    now: Optional[datetime] = None,
    check_mode: bool = False,
) -> MergeResult:
    # Naive UTC keeps the manifest/snapshot stamp format stable (a trailing
    # `Z` is appended manually) without the deprecated ``utcnow``.
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    target_path = os.path.expanduser(target_path)
    local_path = target_path + local_suffix
    # Default to the POSIX-shell guarded source; callers (tmux/TOML) override.
    if source_line is None:
        source_line = f'[[ -f "{local_path}" ]] && source "{local_path}"'

    block = _render_block(begin_marker, end_marker, managed_content, source_line)

    exists = os.path.exists(target_path)
    original = ""
    if exists:
        with open(target_path) as fh:
            original = fh.read()

    # ---- compute the would-be result (no writes yet) ------------------------
    local_content = None  # None => leave .local untouched
    if not exists:
        new_content = block
        actions = ["created target with managed block"]
    elif begin_marker not in original:  # first migration
        foreign = _scrub_signatures(original, signature_patterns).rstrip("\n")
        local_content = foreign + "\n" if foreign else ""
        new_content = block
        actions = ["backed up original", "moved foreign content to .local", "wrote managed block"]
    else:  # update: replace only the marker region, preserve outside content
        pattern = re.compile(
            re.escape(begin_marker) + r".*?" + re.escape(end_marker) + r"\n?",
            re.DOTALL,
        )
        new_content = pattern.sub(lambda _m: block, original, count=1)
        actions = ["backed up original", "rewrote managed block"]

    changed = new_content != original or not exists and new_content != ""

    if not changed:
        return MergeResult(
            target_path=target_path, local_path=local_path, changed=False,
            backup_path=None, actions=["managed block already current"],
            before_content=original, after_content=original,
        )

    # ---- apply (unless previewing) ------------------------------------------
    backup_path = None
    if not check_mode:
        if exists:
            backup_path = _backup(target_path, backup_root, now)
        os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
        with open(target_path, "w") as fh:
            fh.write(new_content)
        if local_content is not None:
            with open(local_path, "w") as fh:
                fh.write(local_content)

    return MergeResult(
        target_path=target_path, local_path=local_path, changed=True,
        backup_path=backup_path, actions=actions,
        before_content=original, after_content=new_content,
    )
