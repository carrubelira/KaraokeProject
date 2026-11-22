"""Backups: the database, and every blob the destination does not have yet.

Blobs never change, so a backup after the first one copies only what is new.
"""

import shutil
from pathlib import Path

from karaoke_contracts.cas import BlobStore
from karaoke_server.services import Services


def backup(found: Services, dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    found.db.backup(dest / found.settings.db_path.name)
    target = BlobStore(dest / "blobs")
    copied = 0
    for sha in found.store.all():
        if not target.has(sha):
            target.path(sha).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(found.store.path(sha), target.path(sha))
            copied += 1
    return copied
