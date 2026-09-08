import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import Database
from services.inventory_service import InventoryService
from services.backup_service import BackupService, BackupError


class BackupServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.backup_dir = os.path.join(self.tmpdir, "backups")
        self.db = Database(self.db_path)
        self.svc = InventoryService(self.db)
        self.backup_svc = BackupService(self.db, self.backup_dir)
        self.drinks_id = self.db.query_one("SELECT id FROM categories WHERE name = 'Drinks'")["id"]

    def tearDown(self):
        try:
            self.db.close()
        except Exception:
            pass

    def test_create_backup_file_exists(self):
        self.svc.add_product("Item", self.drinks_id, 10, 1, 1)
        path = self.backup_svc.create_backup("manual")
        self.assertTrue(os.path.isfile(path))

    def test_restore_brings_back_data(self):
        pid = self.svc.add_product("BeforeBackup", self.drinks_id, 10, 1, 1)
        backup_path = self.backup_svc.create_backup("manual")

        self.svc.add_product("AfterBackup", self.drinks_id, 5, 1, 1)
        self.assertIsNotNone(
            self.db.query_one("SELECT id FROM products WHERE name = 'AfterBackup'")
        )

        self.backup_svc.restore_backup(backup_path)

        self.assertIsNotNone(self.svc.get_product(pid))
        self.assertIsNone(
            self.db.query_one("SELECT id FROM products WHERE name = 'AfterBackup'")
        )

    def test_restore_rejects_invalid_file(self):
        bad_file = os.path.join(self.tmpdir, "not_a_db.txt")
        with open(bad_file, "w") as f:
            f.write("this is not a database")
        with self.assertRaises(BackupError):
            self.backup_svc.restore_backup(bad_file)

    def test_auto_backup_skipped_when_not_due(self):
        from datetime import datetime
        result = self.backup_svc.maybe_run_auto_backup(
            enabled=True, interval_days=1, last_backup_at=datetime.now().isoformat()
        )
        self.assertIsNone(result)

    def test_auto_backup_runs_when_due(self):
        result = self.backup_svc.maybe_run_auto_backup(
            enabled=True, interval_days=1, last_backup_at=""
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(self.backup_svc.list_backups()), 1)


if __name__ == "__main__":
    unittest.main()
