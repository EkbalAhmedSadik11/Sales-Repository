"""Backup and restore for the SQLite database file.

Backups are plain copies of the .db file (SQLite's own on-disk format), which
is the most portable and lowest-risk approach: restoring is just swapping a
file back, with no schema/version translation to get wrong. Auto-backup runs
opportunistically on app startup rather than via an OS-level scheduler, since
Android background scheduling from a Kivy app is unreliable.
"""

import os
import shutil
from datetime import datetime, timedelta

from database.database import Database

MAX_AUTO_BACKUPS = 10


class BackupError(Exception):
    pass


class BackupService:
    def __init__(self, db: Database, backup_dir: str):
        self.db = db
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)

    def _checkpoint(self):
        """Flush the WAL file into the main .db file so the copy is complete."""
        self.db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

    def create_backup(self, label: str = "manual") -> str:
        try:
            self._checkpoint()
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            filename = f"inventory_backup_{timestamp}_{label}.db"
            dest_path = os.path.join(self.backup_dir, filename)
            shutil.copy2(self.db.db_path, dest_path)
            return dest_path
        except OSError as exc:
            raise BackupError(f"Backup failed: could not write file ({exc.strerror or exc}).")

    def list_backups(self) -> list:
        if not os.path.isdir(self.backup_dir):
            return []
        files = [
            f for f in os.listdir(self.backup_dir)
            if f.startswith("inventory_backup_") and f.endswith(".db")
        ]
        files.sort(reverse=True)
        return [os.path.join(self.backup_dir, f) for f in files]

    def prune_old_backups(self, keep: int = MAX_AUTO_BACKUPS):
        auto_backups = [f for f in self.list_backups() if f.endswith("_auto.db")]
        for path in auto_backups[keep:]:
            try:
                os.remove(path)
            except OSError:
                pass

    def restore_backup(self, backup_path: str):
        if not os.path.isfile(backup_path):
            raise BackupError("Backup file not found.")
        try:
            import sqlite3
            test_conn = sqlite3.connect(backup_path)
            test_conn.execute("SELECT COUNT(*) FROM products")
            test_conn.close()
        except sqlite3.DatabaseError:
            raise BackupError("This file is not a valid Sales Repository backup.")

        try:
            self.db.conn.close()
            shutil.copy2(backup_path, self.db.db_path)
        except OSError as exc:
            raise BackupError(f"Restore failed: {exc.strerror or exc}.")
        finally:
            import sqlite3
            self.db.conn = sqlite3.connect(self.db.db_path, check_same_thread=False)
            self.db.conn.row_factory = sqlite3.Row
            self.db.conn.execute("PRAGMA foreign_keys = ON;")
            self.db.conn.execute("PRAGMA journal_mode = WAL;")

    def maybe_run_auto_backup(self, enabled: bool, interval_days: int, last_backup_at: str) -> str:
        """Returns the new last_backup_at ISO string if a backup was taken, else None."""
        if not enabled:
            return None
        due = True
        if last_backup_at:
            try:
                last_dt = datetime.fromisoformat(last_backup_at)
                due = datetime.now() - last_dt >= timedelta(days=interval_days)
            except ValueError:
                due = True
        if not due:
            return None
        self.create_backup(label="auto")
        self.prune_old_backups()
        return datetime.now().isoformat(timespec="seconds")
