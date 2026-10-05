"""Standalone entry point for resyncing a single file's org-roam index entries.

Meant to be invoked by an external process right after a file under the
org-roam directory changes outside of Emacs (e.g. a Claude Code PostToolUse
hook after Edit/Write), so org-roam's SQLite cache doesn't go stale until
the next full org-roam-db-sync. Opens its own short-lived connection; does
not require the org-roam-mcp server process or Emacs to be running.
"""

import sys

from .config import OrgRoamConfig
from .database import OrgRoamDatabase


def resync_main() -> None:
    if len(sys.argv) != 2:
        print("usage: org-roam-resync <file-path>", file=sys.stderr)
        sys.exit(2)

    config = OrgRoamConfig.from_environment()
    db = OrgRoamDatabase(config.db_path)
    try:
        db.resync_file_node(sys.argv[1])
    finally:
        db.close()


if __name__ == "__main__":
    resync_main()
