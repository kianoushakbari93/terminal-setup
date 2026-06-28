"""Restore managed files from a backup snapshot.

Reverts files using the JSONL manifest the merge engine writes
(``<backup_root>/manifest.jsonl``, entries ``{original, backup, timestamp}``).
Pure logic so it is testable and reusable by the restore CLI.
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from typing import List, Optional

# Must match module_utils/ts_merge.py MANIFEST_NAME (the manifest contract).
MANIFEST_NAME = "manifest.jsonl"


class RestoreError(Exception):
    """Raised when a restore cannot proceed (missing snapshot/manifest/backup)."""


@dataclass(frozen=True)
class RestoreEntry:
    original: str
    backup: str
    changed: bool


@dataclass(frozen=True)
class RestoreResult:
    snapshot: str
    entries: List[RestoreEntry] = field(default_factory=list)


def _manifest_path(backup_root: str) -> str:
    return os.path.join(os.path.expanduser(backup_root), MANIFEST_NAME)


def _read_manifest(backup_root: str) -> List[dict]:
    path = _manifest_path(backup_root)
    if not os.path.exists(path):
        raise RestoreError(f"no backup manifest found at {path}")
    entries = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def list_snapshots(backup_root: str) -> List[str]:
    """Return the timestamped snapshot directory names, oldest first."""
    backup_root = os.path.expanduser(backup_root)
    if not os.path.isdir(backup_root):
        return []
    snaps = [
        name for name in os.listdir(backup_root)
        if os.path.isdir(os.path.join(backup_root, name))
    ]
    return sorted(snaps)


def restore(backup_root: str, snapshot: Optional[str] = None) -> RestoreResult:
    backup_root = os.path.expanduser(backup_root)
    if not os.path.isdir(backup_root):
        raise RestoreError(f"backup root does not exist: {backup_root}")

    snapshots = list_snapshots(backup_root)
    if not snapshots:
        raise RestoreError(f"no backup snapshots found under {backup_root}")
    if snapshot is None:
        snapshot = snapshots[-1]  # latest
    elif snapshot not in snapshots:
        raise RestoreError(
            f"snapshot {snapshot!r} not found. Available: {', '.join(snapshots)}"
        )

    snapshot_dir = os.path.join(backup_root, snapshot)
    entries: List[RestoreEntry] = []
    for rec in _read_manifest(backup_root):
        backup = rec["backup"]
        if os.path.dirname(backup) != snapshot_dir:
            continue  # belongs to a different snapshot
        if not os.path.exists(backup):
            raise RestoreError(f"backup file missing: {backup}")
        original = rec["original"]
        changed = _restore_one(backup, original)
        entries.append(RestoreEntry(original=original, backup=backup, changed=changed))
    return RestoreResult(snapshot=snapshot, entries=entries)


def _restore_one(backup: str, original: str) -> bool:
    with open(backup, "rb") as fh:
        backup_bytes = fh.read()
    if os.path.exists(original):
        with open(original, "rb") as fh:
            if fh.read() == backup_bytes:
                return False  # already matches; nothing to do
    os.makedirs(os.path.dirname(original) or ".", exist_ok=True)
    shutil.copy2(backup, original)
    return True
