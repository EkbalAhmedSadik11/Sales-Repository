"""Forward-only schema migration runner.

database.py already creates the current schema from scratch via
CREATE TABLE IF NOT EXISTS, so a fresh install never touches this file.
This module only matters when SCHEMA_VERSION is bumped in a future release
and an existing user's database (with real data) needs to be upgraded in
place without losing anything. Add new migrations by appending to
MIGRATIONS - never rewrite an already-shipped migration.
"""

from database.database import Database

# Each migration is (target_version, list_of_sql_statements).
# Migration N takes a database from version N-1 to version N.
MIGRATIONS = [
    # Example for the future:
    # (2, ["ALTER TABLE products ADD COLUMN barcode TEXT;"]),
]


def current_version(db: Database) -> int:
    row = db.query_one("SELECT value FROM settings WHERE key = 'schema_version'")
    return int(row["value"]) if row else 1


def run_migrations(db: Database):
    version = current_version(db)
    applied = False
    for target_version, statements in MIGRATIONS:
        if target_version <= version:
            continue
        with db.transaction() as cur:
            for sql in statements:
                cur.execute(sql)
            cur.execute(
                "UPDATE settings SET value = ? WHERE key = 'schema_version'",
                (str(target_version),),
            )
        version = target_version
        applied = True
    return applied
