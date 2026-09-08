"""Unit tests for InventoryService, run against a temp SQLite file (no Kivy).

Run with:  python -m unittest discover -s tests
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import Database
from services.inventory_service import (
    InventoryService, InsufficientStockError, DuplicateProductCodeError, CategoryInUseError,
)
from utils.validation import ValidationError


class InventoryServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.db = Database(self.db_path)
        self.svc = InventoryService(self.db)
        self.drinks_id = self.db.query_one("SELECT id FROM categories WHERE name = 'Drinks'")["id"]

    def tearDown(self):
        self.db.close()

    def test_add_product_creates_row_and_transaction(self):
        pid = self.svc.add_product("Coca Cola 500ml", self.drinks_id, 50, 20, 40)
        product = self.svc.get_product(pid)
        self.assertEqual(product.quantity, 50)
        self.assertEqual(product.product_code, "P001")
        txs = self.svc.get_product_transactions(pid)
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0].transaction_type, "PRODUCT_CREATED")

    def test_duplicate_product_code_rejected(self):
        self.svc.add_product("A", self.drinks_id, 1, 1, 1, product_code="X1")
        with self.assertRaises(DuplicateProductCodeError):
            self.svc.add_product("B", self.drinks_id, 1, 1, 1, product_code="X1")

    def test_sequential_product_codes(self):
        p1 = self.svc.add_product("A", self.drinks_id, 1, 1, 1)
        p2 = self.svc.add_product("B", self.drinks_id, 1, 1, 1)
        self.assertEqual(self.svc.get_product(p1).product_code, "P001")
        self.assertEqual(self.svc.get_product(p2).product_code, "P002")

    def test_increase_stock(self):
        pid = self.svc.add_product("Coca Cola", self.drinks_id, 50, 20, 40)
        tx = self.svc.increase_stock(pid, 20)
        product = self.svc.get_product(pid)
        self.assertEqual(product.quantity, 70)
        self.assertEqual(tx.previous_quantity, 50)
        self.assertEqual(tx.new_quantity, 70)
        self.assertEqual(tx.quantity, 20)

    def test_sell_stock_reduces_quantity(self):
        pid = self.svc.add_product("Coca Cola", self.drinks_id, 50, 20, 40)
        self.svc.sell_stock(pid, 5)
        self.assertEqual(self.svc.get_product(pid).quantity, 45)

    def test_sell_more_than_stock_raises(self):
        pid = self.svc.add_product("Coca Cola", self.drinks_id, 5, 20, 40)
        with self.assertRaises(InsufficientStockError) as ctx:
            self.svc.sell_stock(pid, 10)
        self.assertEqual(ctx.exception.current, 5)
        self.assertEqual(ctx.exception.requested, 10)
        # stock must be unchanged after the failed sale
        self.assertEqual(self.svc.get_product(pid).quantity, 5)

    def test_stock_never_goes_negative_via_adjustment(self):
        pid = self.svc.add_product("Rice", self.drinks_id, 5, 1, 10)
        with self.assertRaises(InsufficientStockError):
            self.svc.adjust_stock(pid, -10, "Damaged")
        self.assertEqual(self.svc.get_product(pid).quantity, 5)

    def test_adjustment_requires_reason(self):
        pid = self.svc.add_product("Rice", self.drinks_id, 100, 1, 10)
        with self.assertRaises(ValidationError):
            self.svc.adjust_stock(pid, -3, "")

    def test_adjustment_records_transaction(self):
        pid = self.svc.add_product("Rice", self.drinks_id, 100, 1, 10)
        tx = self.svc.adjust_stock(pid, -3, "Damaged products")
        self.assertEqual(tx.transaction_type, "STOCK_ADJUSTMENT")
        self.assertEqual(tx.new_quantity, 97)
        self.assertEqual(tx.reason, "Damaged products")

    def test_archive_hides_from_active_list_but_keeps_history(self):
        pid = self.svc.add_product("Old Item", self.drinks_id, 10, 1, 5)
        self.svc.increase_stock(pid, 5)
        self.svc.archive_product(pid)

        active = self.svc.list_products(status="ACTIVE")
        self.assertFalse(any(p.id == pid for p in active))

        archived = self.svc.list_products(status="ARCHIVED")
        self.assertTrue(any(p.id == pid for p in archived))

        txs = self.svc.get_product_transactions(pid)
        self.assertEqual(len(txs), 3)  # created, stock_in, archived

    def test_restore_brings_product_back(self):
        pid = self.svc.add_product("Old Item", self.drinks_id, 10, 1, 5)
        self.svc.archive_product(pid)
        self.svc.restore_product(pid)
        active = self.svc.list_products(status="ACTIVE")
        self.assertTrue(any(p.id == pid for p in active))

    def test_low_stock_and_out_of_stock_detection(self):
        low_id = self.svc.add_product("Low", self.drinks_id, 5, 10, 1)
        out_id = self.svc.add_product("Out", self.drinks_id, 0, 5, 1)
        ok_id = self.svc.add_product("Ok", self.drinks_id, 100, 10, 1)

        low = self.svc.get_product(low_id)
        out = self.svc.get_product(out_id)
        ok = self.svc.get_product(ok_id)

        self.assertTrue(low.is_low_stock)
        self.assertTrue(out.is_out_of_stock)
        self.assertFalse(ok.is_low_stock)

        low_list = self.svc.list_products(stock_filter="low")
        self.assertTrue(any(p.id == low_id for p in low_list))
        self.assertFalse(any(p.id == out_id for p in low_list))

        out_list = self.svc.list_products(stock_filter="out")
        self.assertTrue(any(p.id == out_id for p in out_list))

    def test_search_by_name_and_code(self):
        pid = self.svc.add_product("Pepsi 500ml", self.drinks_id, 10, 1, 1, product_code="PEP1")
        results = self.svc.list_products(search="pepsi")
        self.assertTrue(any(p.id == pid for p in results))
        results2 = self.svc.list_products(search="PEP1")
        self.assertTrue(any(p.id == pid for p in results2))

    def test_category_delete_blocked_when_in_use(self):
        self.svc.add_product("Item", self.drinks_id, 1, 1, 1)
        with self.assertRaises(CategoryInUseError):
            self.svc.delete_category(self.drinks_id)

    def test_category_rename_and_duplicate_rejection(self):
        cat_id = self.svc.add_category("Snacks")
        self.svc.rename_category(cat_id, "Snacks & Chips")
        self.assertEqual(self.svc.get_category(cat_id).name, "Snacks & Chips")
        with self.assertRaises(ValidationError):
            self.svc.add_category("Snacks & Chips")

    def test_dashboard_stats_reflect_todays_activity(self):
        pid = self.svc.add_product("Coca Cola", self.drinks_id, 50, 20, 40)
        self.svc.increase_stock(pid, 20)
        self.svc.sell_stock(pid, 5)
        stats = self.svc.get_dashboard_stats()
        self.assertEqual(stats["received_today"], 70)  # 50 initial + 20 stock-in
        self.assertEqual(stats["sold_today"], 5)
        self.assertEqual(stats["stock_available"], 65)

    def test_data_persists_across_reopen(self):
        pid = self.svc.add_product("Persistent Item", self.drinks_id, 42, 5, 9.5)
        self.db.close()

        reopened = Database(self.db_path)
        svc2 = InventoryService(reopened)
        product = svc2.get_product(pid)
        self.assertIsNotNone(product)
        self.assertEqual(product.quantity, 42)
        self.assertEqual(product.name, "Persistent Item")
        reopened.close()


if __name__ == "__main__":
    unittest.main()
