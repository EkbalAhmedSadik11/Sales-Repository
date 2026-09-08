"""Core business logic: products, categories, and stock transactions.

Every function that changes a product's quantity writes exactly one matching
row to `transactions` in the *same* SQLite transaction (see Database.transaction),
so stock level and audit history can never drift apart - a crash mid-operation
rolls back both or neither (see section 22 of the spec: "never simply change
the stock number without recording why it changed").
"""

from datetime import datetime

from database.database import Database
from database.models import Product, Category, Transaction
from utils.formatting import next_product_code
from utils.validation import ValidationError, require_non_empty, parse_positive_int, parse_price


class InsufficientStockError(Exception):
    def __init__(self, current: int, requested: int):
        self.current = current
        self.requested = requested
        super().__init__(
            f"Not enough stock available.\nCurrent stock: {current}\nRequested: {requested}"
        )


class DuplicateProductCodeError(ValidationError):
    pass


class CategoryInUseError(ValidationError):
    pass


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class InventoryService:
    def __init__(self, db: Database):
        self.db = db

    # ---------------------------------------------------------------- #
    # Categories
    # ---------------------------------------------------------------- #

    def list_categories(self):
        rows = self.db.query_all(
            """
            SELECT c.*, COUNT(p.id) AS product_count
            FROM categories c
            LEFT JOIN products p ON p.category_id = c.id AND p.status = 'ACTIVE'
            GROUP BY c.id
            ORDER BY c.name COLLATE NOCASE
            """
        )
        return rows

    def get_category(self, category_id: int) -> Category:
        row = self.db.query_one("SELECT * FROM categories WHERE id = ?", (category_id,))
        return Category.from_row(row) if row else None

    def add_category(self, name: str) -> int:
        name = require_non_empty(name, "Category name")
        existing = self.db.query_one(
            "SELECT id FROM categories WHERE name = ? COLLATE NOCASE", (name,)
        )
        if existing:
            raise ValidationError(f'Category "{name}" already exists.')
        with self.db.transaction() as cur:
            cur.execute(
                "INSERT INTO categories (name, created_at) VALUES (?, ?)", (name, _now())
            )
            return cur.lastrowid

    def rename_category(self, category_id: int, new_name: str):
        new_name = require_non_empty(new_name, "Category name")
        existing = self.db.query_one(
            "SELECT id FROM categories WHERE name = ? COLLATE NOCASE AND id != ?",
            (new_name, category_id),
        )
        if existing:
            raise ValidationError(f'Category "{new_name}" already exists.')
        with self.db.transaction() as cur:
            cur.execute(
                "UPDATE categories SET name = ? WHERE id = ?", (new_name, category_id)
            )

    def delete_category(self, category_id: int):
        count_row = self.db.query_one(
            "SELECT COUNT(*) AS c FROM products WHERE category_id = ?", (category_id,)
        )
        if count_row["c"] > 0:
            raise CategoryInUseError(
                "This category still has products assigned to it. "
                "Reassign or archive them before deleting the category."
            )
        with self.db.transaction() as cur:
            cur.execute("DELETE FROM categories WHERE id = ?", (category_id,))

    # ---------------------------------------------------------------- #
    # Products
    # ---------------------------------------------------------------- #

    def _generate_product_code(self) -> str:
        row = self.db.query_one(
            "SELECT product_code FROM products ORDER BY id DESC LIMIT 1"
        )
        last_code = row["product_code"] if row else None
        candidate = next_product_code(last_code)
        # guard against gaps from manual codes / archived+recreated rows
        while self.db.query_one(
            "SELECT id FROM products WHERE product_code = ?", (candidate,)
        ):
            candidate = next_product_code(candidate)
        return candidate

    def list_products(
        self,
        search: str = None,
        category_id: int = None,
        status: str = "ACTIVE",
        stock_filter: str = None,  # 'low', 'out', None
        sort_by: str = "name",  # name, quantity, price, updated_at
        sort_dir: str = "asc",
        limit: int = None,
        offset: int = 0,
    ):
        clauses = []
        params = []

        if status:
            clauses.append("p.status = ?")
            params.append(status)
        if category_id:
            clauses.append("p.category_id = ?")
            params.append(category_id)
        if search:
            clauses.append("(p.name LIKE ? OR p.product_code LIKE ?)")
            like = f"%{search.strip()}%"
            params.extend([like, like])
        if stock_filter == "low":
            clauses.append("p.quantity > 0 AND p.quantity <= p.minimum_stock")
        elif stock_filter == "out":
            clauses.append("p.quantity <= 0")

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        sort_column = {
            "name": "p.name COLLATE NOCASE",
            "quantity": "p.quantity",
            "price": "p.price",
            "updated_at": "p.updated_at",
        }.get(sort_by, "p.name COLLATE NOCASE")
        direction = "DESC" if sort_dir == "desc" else "ASC"

        sql = f"""
            SELECT p.*, c.name AS category_name
            FROM products p
            JOIN categories c ON c.id = p.category_id
            {where_sql}
            ORDER BY {sort_column} {direction}
        """
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        rows = self.db.query_all(sql, tuple(params))
        return [Product.from_row(r) for r in rows]

    def count_products(self, search: str = None, category_id: int = None,
                        status: str = "ACTIVE", stock_filter: str = None) -> int:
        clauses = []
        params = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if category_id:
            clauses.append("category_id = ?")
            params.append(category_id)
        if search:
            clauses.append("(name LIKE ? OR product_code LIKE ?)")
            like = f"%{search.strip()}%"
            params.extend([like, like])
        if stock_filter == "low":
            clauses.append("quantity > 0 AND quantity <= minimum_stock")
        elif stock_filter == "out":
            clauses.append("quantity <= 0")
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        row = self.db.query_one(f"SELECT COUNT(*) AS c FROM products {where_sql}", tuple(params))
        return row["c"]

    def get_product(self, product_id: int) -> Product:
        row = self.db.query_one(
            """
            SELECT p.*, c.name AS category_name
            FROM products p JOIN categories c ON c.id = p.category_id
            WHERE p.id = ?
            """,
            (product_id,),
        )
        return Product.from_row(row) if row else None

    def add_product(self, name: str, category_id: int, initial_quantity,
                     minimum_stock, price=None, product_code: str = None) -> int:
        name = require_non_empty(name, "Product name")
        if not category_id:
            raise ValidationError("Category is required.")
        qty = parse_positive_int(initial_quantity, "Initial quantity")
        min_stock = parse_positive_int(minimum_stock, "Minimum stock level")
        price_val = parse_price(price)

        if product_code:
            product_code = product_code.strip()
            if self.db.query_one("SELECT id FROM products WHERE product_code = ?", (product_code,)):
                raise DuplicateProductCodeError(f'Product code "{product_code}" is already in use.')
        else:
            product_code = self._generate_product_code()

        now = _now()
        with self.db.transaction() as cur:
            cur.execute(
                """
                INSERT INTO products
                    (product_code, name, category_id, quantity, minimum_stock,
                     price, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """,
                (product_code, name, category_id, qty, min_stock, price_val, now, now),
            )
            product_id = cur.lastrowid
            cur.execute(
                """
                INSERT INTO transactions
                    (product_id, product_name, transaction_type, quantity,
                     previous_quantity, new_quantity, reason, created_at)
                VALUES (?, ?, 'PRODUCT_CREATED', ?, 0, ?, ?, ?)
                """,
                (product_id, name, qty, qty, "Initial stock on product creation", now),
            )
            return product_id

    def update_product_details(self, product_id: int, name: str = None,
                                category_id: int = None, minimum_stock=None, price=None):
        """Edit non-quantity fields. Quantity changes must go through the
        stock-in / sell / adjust methods so they're always audited."""
        product = self.get_product(product_id)
        if not product:
            raise ValidationError("Product not found.")

        new_name = require_non_empty(name, "Product name") if name is not None else product.name
        new_category = category_id or product.category_id
        new_min = parse_positive_int(minimum_stock, "Minimum stock level") if minimum_stock is not None else product.minimum_stock
        new_price = parse_price(price) if price is not None else product.price

        with self.db.transaction() as cur:
            cur.execute(
                """
                UPDATE products
                SET name = ?, category_id = ?, minimum_stock = ?, price = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_name, new_category, new_min, new_price, _now(), product_id),
            )

    def archive_product(self, product_id: int):
        product = self.get_product(product_id)
        if not product:
            raise ValidationError("Product not found.")
        if product.status == "ARCHIVED":
            return
        now = _now()
        with self.db.transaction() as cur:
            cur.execute(
                "UPDATE products SET status = 'ARCHIVED', updated_at = ? WHERE id = ?",
                (now, product_id),
            )
            cur.execute(
                """
                INSERT INTO transactions
                    (product_id, product_name, transaction_type, quantity,
                     previous_quantity, new_quantity, reason, created_at)
                VALUES (?, ?, 'PRODUCT_ARCHIVED', 0, ?, ?, 'Archived by admin', ?)
                """,
                (product_id, product.name, product.quantity, product.quantity, now),
            )

    def restore_product(self, product_id: int):
        product = self.get_product(product_id)
        if not product:
            raise ValidationError("Product not found.")
        if product.status == "ACTIVE":
            return
        now = _now()
        with self.db.transaction() as cur:
            cur.execute(
                "UPDATE products SET status = 'ACTIVE', updated_at = ? WHERE id = ?",
                (now, product_id),
            )
            cur.execute(
                """
                INSERT INTO transactions
                    (product_id, product_name, transaction_type, quantity,
                     previous_quantity, new_quantity, reason, created_at)
                VALUES (?, ?, 'PRODUCT_RESTORED', 0, ?, ?, 'Restored from archive', ?)
                """,
                (product_id, product.name, product.quantity, product.quantity, now),
            )

    # ---------------------------------------------------------------- #
    # Stock movements
    # ---------------------------------------------------------------- #

    def increase_stock(self, product_id: int, quantity, reason: str = "Stock received") -> Transaction:
        qty = parse_positive_int(quantity, "Quantity", allow_zero=False)
        product = self.get_product(product_id)
        if not product:
            raise ValidationError("Product not found.")
        new_qty = product.quantity + qty
        now = _now()
        with self.db.transaction() as cur:
            cur.execute(
                "UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?",
                (new_qty, now, product_id),
            )
            cur.execute(
                """
                INSERT INTO transactions
                    (product_id, product_name, transaction_type, quantity,
                     previous_quantity, new_quantity, reason, created_at)
                VALUES (?, ?, 'STOCK_IN', ?, ?, ?, ?, ?)
                """,
                (product_id, product.name, qty, product.quantity, new_qty, reason, now),
            )
            row = self.db.query_one("SELECT * FROM transactions WHERE id = last_insert_rowid()")
            return Transaction.from_row(row)

    def sell_stock(self, product_id: int, quantity, reason: str = "Sale") -> Transaction:
        qty = parse_positive_int(quantity, "Quantity sold", allow_zero=False)
        product = self.get_product(product_id)
        if not product:
            raise ValidationError("Product not found.")
        if qty > product.quantity:
            raise InsufficientStockError(current=product.quantity, requested=qty)
        new_qty = product.quantity - qty
        now = _now()
        with self.db.transaction() as cur:
            cur.execute(
                "UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?",
                (new_qty, now, product_id),
            )
            cur.execute(
                """
                INSERT INTO transactions
                    (product_id, product_name, transaction_type, quantity,
                     previous_quantity, new_quantity, reason, created_at)
                VALUES (?, ?, 'SALE', ?, ?, ?, ?, ?)
                """,
                (product_id, product.name, -qty, product.quantity, new_qty, reason, now),
            )
            row = self.db.query_one("SELECT * FROM transactions WHERE id = last_insert_rowid()")
            return Transaction.from_row(row)

    def adjust_stock(self, product_id: int, delta, reason: str) -> Transaction:
        """Manual correction. `delta` may be positive or negative."""
        reason = require_non_empty(reason, "Reason")
        try:
            delta = int(delta)
        except (TypeError, ValueError):
            raise ValidationError("Adjustment must be a whole number.")
        if delta == 0:
            raise ValidationError("Adjustment quantity cannot be zero.")

        product = self.get_product(product_id)
        if not product:
            raise ValidationError("Product not found.")
        new_qty = product.quantity + delta
        if new_qty < 0:
            raise InsufficientStockError(current=product.quantity, requested=-delta)

        now = _now()
        with self.db.transaction() as cur:
            cur.execute(
                "UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?",
                (new_qty, now, product_id),
            )
            cur.execute(
                """
                INSERT INTO transactions
                    (product_id, product_name, transaction_type, quantity,
                     previous_quantity, new_quantity, reason, created_at)
                VALUES (?, ?, 'STOCK_ADJUSTMENT', ?, ?, ?, ?, ?)
                """,
                (product_id, product.name, delta, product.quantity, new_qty, reason, now),
            )
            row = self.db.query_one("SELECT * FROM transactions WHERE id = last_insert_rowid()")
            return Transaction.from_row(row)

    # ---------------------------------------------------------------- #
    # Transactions / history
    # ---------------------------------------------------------------- #

    def get_product_transactions(self, product_id: int, limit: int = 100, offset: int = 0):
        rows = self.db.query_all(
            """
            SELECT * FROM transactions
            WHERE product_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (product_id, limit, offset),
        )
        return [Transaction.from_row(r) for r in rows]

    def search_transactions(self, transaction_type: str = None, search: str = None,
                             date_from: str = None, date_to: str = None,
                             limit: int = 200, offset: int = 0):
        clauses = []
        params = []
        if transaction_type:
            clauses.append("transaction_type = ?")
            params.append(transaction_type)
        if search:
            clauses.append("product_name LIKE ?")
            params.append(f"%{search.strip()}%")
        if date_from:
            clauses.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("created_at <= ?")
            params.append(date_to + "T23:59:59")
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT * FROM transactions
            {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = self.db.query_all(sql, tuple(params))
        return [Transaction.from_row(r) for r in rows]

    # ---------------------------------------------------------------- #
    # Dashboard / aggregate stats
    # ---------------------------------------------------------------- #

    def get_dashboard_stats(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")

        total_products = self.db.query_one(
            "SELECT COUNT(*) AS c FROM products WHERE status = 'ACTIVE'"
        )["c"]
        total_categories = self.db.query_one("SELECT COUNT(*) AS c FROM categories")["c"]
        stock_available = self.db.query_one(
            "SELECT COALESCE(SUM(quantity), 0) AS s FROM products WHERE status = 'ACTIVE'"
        )["s"]
        low_stock = self.db.query_one(
            """
            SELECT COUNT(*) AS c FROM products
            WHERE status = 'ACTIVE' AND quantity > 0 AND quantity <= minimum_stock
            """
        )["c"]
        out_of_stock = self.db.query_one(
            "SELECT COUNT(*) AS c FROM products WHERE status = 'ACTIVE' AND quantity <= 0"
        )["c"]

        received_today = self.db.query_one(
            """
            SELECT COALESCE(SUM(quantity), 0) AS s FROM transactions
            WHERE transaction_type IN ('STOCK_IN', 'PRODUCT_CREATED')
              AND created_at LIKE ?
            """,
            (f"{today}%",),
        )["s"]
        sold_today = self.db.query_one(
            """
            SELECT COALESCE(SUM(-quantity), 0) AS s FROM transactions
            WHERE transaction_type = 'SALE' AND created_at LIKE ?
            """,
            (f"{today}%",),
        )["s"]

        return {
            "total_products": total_products,
            "total_categories": total_categories,
            "stock_available": stock_available,
            "received_today": received_today,
            "sold_today": sold_today,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
        }

    def get_daily_summary(self, date_str: str) -> dict:
        """date_str format: YYYY-MM-DD"""
        received = self.db.query_one(
            """
            SELECT COALESCE(SUM(quantity), 0) AS s FROM transactions
            WHERE transaction_type IN ('STOCK_IN', 'PRODUCT_CREATED') AND created_at LIKE ?
            """,
            (f"{date_str}%",),
        )["s"]
        sold = self.db.query_one(
            """
            SELECT COALESCE(SUM(-quantity), 0) AS s FROM transactions
            WHERE transaction_type = 'SALE' AND created_at LIKE ?
            """,
            (f"{date_str}%",),
        )["s"]
        adjustments = self.db.query_one(
            """
            SELECT COALESCE(SUM(quantity), 0) AS s FROM transactions
            WHERE transaction_type = 'STOCK_ADJUSTMENT' AND created_at LIKE ?
            """,
            (f"{date_str}%",),
        )["s"]
        total_stock = self.db.query_one(
            "SELECT COALESCE(SUM(quantity), 0) AS s FROM products WHERE status = 'ACTIVE'"
        )["s"]
        transactions = self.search_transactions(date_from=date_str, date_to=date_str, limit=500)

        return {
            "date": date_str,
            "received": received,
            "sold": sold,
            "adjustments": adjustments,
            "total_stock": total_stock,
            "transactions": transactions,
        }
