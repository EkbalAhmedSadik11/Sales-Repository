import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import Database
from services.settings_service import SettingsService
from utils.validation import ValidationError
from utils.formatting import next_product_code, format_price
from utils.security import hash_pin, verify_pin


class SettingsServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db = Database(os.path.join(self.tmpdir, "test.db"))
        self.svc = SettingsService(self.db)

    def tearDown(self):
        self.db.close()

    def test_pin_roundtrip(self):
        self.svc.set_pin("1234")
        self.assertTrue(self.svc.check_pin("1234"))
        self.assertFalse(self.svc.check_pin("9999"))

    def test_pin_never_stored_plaintext(self):
        self.svc.set_pin("1234")
        stored = self.svc.get("admin_pin_hash")
        self.assertNotIn("1234", stored)

    def test_change_pin_requires_current(self):
        self.svc.set_pin("1234")
        with self.assertRaises(ValidationError):
            self.svc.change_pin("0000", "5678")

    def test_invalid_pin_format_rejected(self):
        with self.assertRaises(ValidationError):
            self.svc.set_pin("12")  # too short
        with self.assertRaises(ValidationError):
            self.svc.set_pin("abcd")  # non-numeric


class SecurityUtilTestCase(unittest.TestCase):
    def test_hash_is_not_plaintext_and_verifies(self):
        h, salt = hash_pin("4321")
        self.assertNotEqual(h, "4321")
        self.assertTrue(verify_pin("4321", h, salt))
        self.assertFalse(verify_pin("1111", h, salt))


class FormattingUtilTestCase(unittest.TestCase):
    def test_next_product_code(self):
        self.assertEqual(next_product_code(None), "P001")
        self.assertEqual(next_product_code("P001"), "P002")
        self.assertEqual(next_product_code("P099"), "P100")

    def test_format_price(self):
        self.assertEqual(format_price(40, "৳"), "৳40.00")
        self.assertEqual(format_price(1234.5, "$"), "$1,234.50")


if __name__ == "__main__":
    unittest.main()
