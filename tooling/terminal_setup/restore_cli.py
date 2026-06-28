"""CLI to restore managed files from a backup snapshot.

Usage:
    python3 -m tooling.terminal_setup.restore_cli [--list] [--snapshot STAMP]
                                                  [--backup-root DIR]
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from . import restore

DEFAULT_BACKUP_ROOT = "~/.terminal-setup/backups"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="terminal-setup-restore",
        description="Restore managed config files from a backup snapshot.",
    )
    parser.add_argument("--backup-root", default=DEFAULT_BACKUP_ROOT,
                        help="directory holding snapshots + manifest")
    parser.add_argument("--snapshot", default=None,
                        help="snapshot to restore (default: the latest)")
    parser.add_argument("--list", action="store_true",
                        help="list available snapshots and exit")
    args = parser.parse_args(argv)
    backup_root = os.path.expanduser(args.backup_root)

    if args.list:
        snaps = restore.list_snapshots(backup_root)
        if not snaps:
            print(f"No snapshots found under {backup_root}")
        else:
            print("Available snapshots (oldest first):")
            for s in snaps:
                print(f"  {s}")
        return 0

    try:
        result = restore.restore(backup_root, snapshot=args.snapshot)
    except restore.RestoreError as exc:
        print(f"restore failed: {exc}", file=sys.stderr)
        return 1

    changed = [e for e in result.entries if e.changed]
    print(f"Restored from snapshot {result.snapshot}:")
    if not result.entries:
        print("  (snapshot recorded no managed files)")
    for e in result.entries:
        mark = "restored" if e.changed else "unchanged"
        print(f"  [{mark}] {e.original}")
    print(f"{len(changed)}/{len(result.entries)} file(s) restored")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
