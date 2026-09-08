"""Lightweight dataclasses mapping sqlite3.Row objects to typed Python objects.

These are pure data holders - no database access happens here. Keeping them
separate from database.py and services/*.py means the UI layer can type-hint
against Product/Category/Transaction without importing sqlite3 anywhere else.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Category:
    id: int
    name: str
    created_at: str

    @staticmethod
    def from_row(row) -> "Category":
        return Category(id=row["id"], name=row["name"], created_at=row["created_at"])


@dataclass
class Product:
    id: int
    product_code: str
    name: str
    category_id: int
    quantity: int
    minimum_stock: int
    price: float
    status: str
    created_at: str
    updated_at: str
    category_name: Optional[str] = None

    @staticmethod
    def from_row(row) -> "Product":
        keys = row.keys()
        return Product(
            id=row["id"],
            product_code=row["product_code"],
            name=row["name"],
            category_id=row["category_id"],
            quantity=row["quantity"],
            minimum_stock=row["minimum_stock"],
            price=row["price"] or 0,
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            category_name=row["category_name"] if "category_name" in keys else None,
        )

    @property
    def is_out_of_stock(self) -> bool:
        return self.quantity <= 0

    @property
    def is_low_stock(self) -> bool:
        return 0 < self.quantity <= self.minimum_stock

    @property
    def stock_label(self) -> str:
        if self.is_out_of_stock:
            return "OUT OF STOCK"
        if self.is_low_stock:
            return "LOW STOCK"
        return "OK"


@dataclass
class Transaction:
    id: int
    product_id: int
    product_name: str
    transaction_type: str
    quantity: int
    previous_quantity: int
    new_quantity: int
    reason: Optional[str]
    created_at: str

    @staticmethod
    def from_row(row) -> "Transaction":
        return Transaction(
            id=row["id"],
            product_id=row["product_id"],
            product_name=row["product_name"],
            transaction_type=row["transaction_type"],
            quantity=row["quantity"],
            previous_quantity=row["previous_quantity"],
            new_quantity=row["new_quantity"],
            reason=row["reason"],
            created_at=row["created_at"],
        )
