"""CSV export for products, transactions, and reports.

Uses only the stdlib csv module - no pandas/openpyxl - to keep the APK small.
"""

import csv
import os
from datetime import datetime

from utils.formatting import format_date


class ExportService:
    def __init__(self, export_dir: str):
        self.export_dir = export_dir
        os.makedirs(self.export_dir, exist_ok=True)

    def _path_for(self, name: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        return os.path.join(self.export_dir, f"{name}_{timestamp}.csv")

    def export_products(self, products) -> str:
        path = self._path_for("products")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Product ID", "Code", "Name", "Category", "Stock",
                "Minimum Stock", "Price", "Status", "Created", "Updated",
            ])
            for p in products:
                writer.writerow([
                    p.id, p.product_code, p.name, p.category_name or "",
                    p.quantity, p.minimum_stock, p.price, p.status,
                    format_date(p.created_at), format_date(p.updated_at),
                ])
        return path

    def export_transactions(self, transactions) -> str:
        path = self._path_for("transactions")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Transaction ID", "Product", "Type", "Quantity",
                "Previous Stock", "New Stock", "Reason", "Date/Time",
            ])
            for t in transactions:
                writer.writerow([
                    t.id, t.product_name, t.transaction_type, t.quantity,
                    t.previous_quantity, t.new_quantity, t.reason or "", t.created_at,
                ])
        return path

    def export_daily_summary(self, summary: dict) -> str:
        path = self._path_for(f"daily_summary_{summary['date']}")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Received", "Sold", "Adjustments", "Total Stock"])
            writer.writerow([
                summary["date"], summary["received"], summary["sold"],
                summary["adjustments"], summary["total_stock"],
            ])
            writer.writerow([])
            writer.writerow(["Transaction ID", "Product", "Type", "Quantity", "Reason", "Time"])
            for t in summary["transactions"]:
                writer.writerow([t.id, t.product_name, t.transaction_type, t.quantity, t.reason or "", t.created_at])
        return path

    def export_category_report(self, rows: list) -> str:
        path = self._path_for("category_report")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Category", "Product Count", "Total Stock"])
            for r in rows:
                writer.writerow([r["name"], r["product_count"], r["total_stock"]])
        return path

    def export_low_stock_report(self, products) -> str:
        path = self._path_for("low_stock_report")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Code", "Name", "Category", "Stock", "Minimum Stock", "Status"])
            for p in products:
                writer.writerow([
                    p.product_code, p.name, p.category_name or "",
                    p.quantity, p.minimum_stock, p.stock_label,
                ])
        return path
