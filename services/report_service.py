"""Read-only aggregate reports built on top of InventoryService's data.

Kept separate from InventoryService because reports combine/reshape data for
display rather than mutating state - a different responsibility, and one that
export_service.py also depends on independently.
"""

from database.database import Database
from database.models import Product


class ReportService:
    def __init__(self, db: Database):
        self.db = db

    def today_report(self, inventory_service) -> dict:
        from datetime import datetime
        return inventory_service.get_daily_summary(datetime.now().strftime("%Y-%m-%d"))

    def product_report(self, product_id: int) -> dict:
        product_row = self.db.query_one(
            """
            SELECT p.*, c.name AS category_name FROM products p
            JOIN categories c ON c.id = p.category_id WHERE p.id = ?
            """,
            (product_id,),
        )
        if not product_row:
            return None
        product = Product.from_row(product_row)

        total_received = self.db.query_one(
            """
            SELECT COALESCE(SUM(quantity), 0) AS s FROM transactions
            WHERE product_id = ? AND transaction_type IN ('STOCK_IN', 'PRODUCT_CREATED')
            """,
            (product_id,),
        )["s"]
        total_sold = self.db.query_one(
            """
            SELECT COALESCE(SUM(-quantity), 0) AS s FROM transactions
            WHERE product_id = ? AND transaction_type = 'SALE'
            """,
            (product_id,),
        )["s"]

        return {
            "product": product,
            "total_received": total_received,
            "total_sold": total_sold,
            "current_stock": product.quantity,
        }

    def category_report(self) -> list:
        rows = self.db.query_all(
            """
            SELECT c.id, c.name,
                   COUNT(p.id) AS product_count,
                   COALESCE(SUM(p.quantity), 0) AS total_stock
            FROM categories c
            LEFT JOIN products p ON p.category_id = c.id AND p.status = 'ACTIVE'
            GROUP BY c.id
            ORDER BY c.name COLLATE NOCASE
            """
        )
        return [dict(r) for r in rows]

    def low_stock_report(self) -> list:
        rows = self.db.query_all(
            """
            SELECT p.*, c.name AS category_name
            FROM products p JOIN categories c ON c.id = p.category_id
            WHERE p.status = 'ACTIVE' AND p.quantity <= p.minimum_stock
            ORDER BY p.quantity ASC
            """
        )
        return [Product.from_row(r) for r in rows]
