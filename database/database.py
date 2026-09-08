"""
Core SQLite database layer for Sales Repository.

Design notes:
- One long-lived connection per app process (Kivy runs single-threaded on the
  main/UI thread for our purposes), opened with WAL journaling so reads and
  writes don't corrupt each other if the app is killed mid-write.
- Foreign keys are enforced (SQLite disables them by default).
- All schema creation is idempotent (CREATE TABLE IF NOT EXISTS) so opening
  an existing database from a prior app run never destroys data.
- Historical tables (transactions) are append-only from the application's
  point of view - nothing in this module issues a DELETE against them.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

SCHEMA_VERSION = 1

DEFAULT_CATEGORIES = [
    "Food", "Drinks", "Electronics", "Clothing", "Stationery", "Medicine", "Other",
]

DEFAULT_SETTINGS = {
    "schema_version": str(SCHEMA_VERSION),
    "admin_pin_hash": "",
    "admin_pin_salt": "",
    "auto_backup_enabled": "1",
    "auto_backup_interval_days": "1",
    "last_auto_backup_at": "",
    "currency_symbol": "৳",
    "low_stock_notify": "1",
}

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code    TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    category_id     INTEGER NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    minimum_stock   INTEGER NOT NULL DEFAULT 0 CHECK (minimum_stock >= 0),
    price           REAL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ARCHIVED')),
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS transactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id          INTEGER NOT NULL,
    product_name        TEXT NOT NULL,
    transaction_type    TEXT NOT NULL CHECK (transaction_type IN (
                            'STOCK_IN', 'SALE', 'STOCK_ADJUSTMENT',
                            'PRODUCT_CREATED', 'PRODUCT_ARCHIVED', 'PRODUCT_RESTORED'
                        )),
    quantity            INTEGER NOT NULL,
    previous_quantity   INTEGER NOT NULL,
    new_quantity        INTEGER NOT NULL,
    reason              TEXT,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS settings (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    key     TEXT NOT NULL UNIQUE,
    value   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_products_name ON products (name);
CREATE INDEX IF NOT EXISTS idx_products_category ON products (category_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products (status);
CREATE INDEX IF NOT EXISTS idx_products_code ON products (product_code);
CREATE INDEX IF NOT EXISTS idx_transactions_product ON transactions (product_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions (created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions (transaction_type);
"""


def default_db_path(app_data_dir: str = None) -> str:
    """Resolve the on-disk path for the SQLite file.

    On Android, App.user_data_dir gives a persistent, app-private directory
    that survives app restarts and phone reboots. On desktop (dev/testing)
    we default to a local ./data folder next to the project.
    """
    if app_data_dir:
        os.makedirs(app_data_dir, exist_ok=True)
        return os.path.join(app_data_dir, "sales_repository.db")

    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "sales_repository.db")


class Database:
    """Thin wrapper around a single sqlite3 connection for the app's lifetime."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA synchronous = NORMAL;")
        self._init_schema()
        self._seed_defaults()

    def _init_schema(self):
        with self.transaction() as cur:
            cur.executescript(_SCHEMA_SQL)

    def _seed_defaults(self):
        with self.transaction() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM categories")
            if cur.fetchone()["c"] == 0:
                now = datetime.now().isoformat(timespec="seconds")
                cur.executemany(
                    "INSERT INTO categories (name, created_at) VALUES (?, ?)",
                    [(name, now) for name in DEFAULT_CATEGORIES],
                )
            cur.execute("SELECT key FROM settings")
            existing = {row["key"] for row in cur.fetchall()}
            for key, value in DEFAULT_SETTINGS.items():
                if key not in existing:
                    cur.execute(
                        "INSERT INTO settings (key, value) VALUES (?, ?)", (key, value)
                    )

    @contextmanager
    def transaction(self):
        """Context manager giving a cursor; commits on success, rolls back on error.

        Every write in the app goes through this so a crash or exception never
        leaves the database half-updated (e.g. stock changed but transaction
        row missing).
        """
        cur = self.conn.cursor()
        try:
            yield cur
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def query_all(self, sql: str, params: tuple = ()):
        return self.conn.execute(sql, params).fetchall()

    def query_one(self, sql: str, params: tuple = ()):
        return self.conn.execute(sql, params).fetchone()

    def close(self):
        self.conn.close()

    def reset_inventory_data(self):
        """Advanced/dev-only: wipes products, categories, and transaction
        history and reseeds the default category list. Admin PIN and app
        settings are left untouched. Callers are expected to take a backup
        immediately before calling this - it is the one place in the app
        that intentionally destroys historical data."""
        with self.transaction() as cur:
            cur.execute("DELETE FROM transactions")
            cur.execute("DELETE FROM products")
            cur.execute("DELETE FROM categories")
            now = datetime.now().isoformat(timespec="seconds")
            cur.executemany(
                "INSERT INTO categories (name, created_at) VALUES (?, ?)",
                [(name, now) for name in DEFAULT_CATEGORIES],
            )


_instance: Database = None


def get_db(app_data_dir: str = None) -> Database:
    """Return the process-wide Database singleton, creating it on first call."""
    global _instance
    if _instance is None:
        _instance = Database(default_db_path(app_data_dir))
    return _instance


def reset_singleton_for_tests():
    """Used only by unit tests to force a fresh Database on the next get_db()."""
    global _instance
    if _instance is not None:
        _instance.close()
    _instance = None
