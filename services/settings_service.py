"""Key/value application settings (admin PIN hash, backup preferences, etc.)."""

from database.database import Database
from utils.security import hash_pin, verify_pin
from utils.validation import validate_pin_format, ValidationError


class SettingsService:
    def __init__(self, db: Database):
        self.db = db

    def get(self, key: str, default: str = "") -> str:
        row = self.db.query_one("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else default

    def set(self, key: str, value: str):
        with self.db.transaction() as cur:
            cur.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value)),
            )

    def get_all(self) -> dict:
        rows = self.db.query_all("SELECT key, value FROM settings")
        return {r["key"]: r["value"] for r in rows}

    # ---- Admin PIN -----------------------------------------------------

    def has_pin(self) -> bool:
        return bool(self.get("admin_pin_hash"))

    def set_pin(self, pin: str):
        pin = validate_pin_format(pin)
        hash_hex, salt_hex = hash_pin(pin)
        self.set("admin_pin_hash", hash_hex)
        self.set("admin_pin_salt", salt_hex)

    def check_pin(self, pin: str) -> bool:
        return verify_pin(pin, self.get("admin_pin_hash"), self.get("admin_pin_salt"))

    def change_pin(self, current_pin: str, new_pin: str):
        if self.has_pin() and not self.check_pin(current_pin):
            raise ValidationError("Current PIN is incorrect.")
        self.set_pin(new_pin)

    def clear_pin(self):
        self.set("admin_pin_hash", "")
        self.set("admin_pin_salt", "")

    # ---- Backup preferences --------------------------------------------

    def auto_backup_enabled(self) -> bool:
        return self.get("auto_backup_enabled", "1") == "1"

    def auto_backup_interval_days(self) -> int:
        try:
            return int(self.get("auto_backup_interval_days", "1"))
        except ValueError:
            return 1

    def last_auto_backup_at(self) -> str:
        return self.get("last_auto_backup_at", "")

    def currency_symbol(self) -> str:
        return self.get("currency_symbol", "৳")
