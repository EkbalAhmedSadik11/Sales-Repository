"""Sales Repository - offline product inventory & sales management app.

Entry point. Wires together the SQLite database, services, and all screens,
and hosts the small amount of app-wide UI (top bar + bottom navigation) that
every screen shares.
"""

import os

from kivy.core.window import Window
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.snackbar import Snackbar

from database.database import get_db
from database.migrations import run_migrations
from services.inventory_service import InventoryService
from services.report_service import ReportService
from services.backup_service import BackupService
from services.export_service import ExportService
from services.settings_service import SettingsService

# Importing these registers their KV rules / Factory entries before any
# screen tries to instantiate them.
from widgets import bottom_nav, statistic_card, product_card, transaction_item, admin_action_tile  # noqa: F401

from screens.dashboard import DashboardScreen
from screens.products import ProductsScreen
from screens.add_product import AddProductScreen
from screens.product_details import ProductDetailsScreen
from screens.categories import CategoriesScreen
from screens.transactions import TransactionsScreen
from screens.reports import ReportsScreen
from screens.daily_summary import DailySummaryScreen
from screens.admin_login import AdminLoginScreen
from screens.admin import AdminScreen
from screens.settings import SettingsScreen

# Screens that show the bottom navigation bar (the three primary tabs).
TAB_SCREENS = {"dashboard", "products", "reports"}

TITLES = {
    "dashboard": "Sales Repository",
    "products": "Products",
    "add_product": "Add Product",
    "product_details": "Product Details",
    "categories": "Categories",
    "transactions": "Transaction History",
    "reports": "Reports",
    "daily_summary": "Daily Summary",
    "admin_login": "Admin",
    "admin": "Admin Panel",
    "settings": "Settings",
}

ROOT_KV = """
MDScreen:
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            id: top_bar
            title: "Sales Repository"
            elevation: 2
            left_action_items: [["arrow-left", lambda x: app.go_back()]] if root_manager.current not in ("dashboard", "products", "reports") else []
            right_action_items: [["shield-account-outline", lambda x: app.open_admin()]]

        MDScreenManager:
            id: root_manager

        BottomNavBar:
            id: bottom_nav
"""


class SalesRepositoryApp(MDApp):
    title = "Sales Repository"

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.accent_palette = "Teal"
        Window.softinput_mode = "below_target"

        base_dir = self.user_data_dir  # Android-safe persistent app directory
        self.db = get_db(base_dir)
        run_migrations(self.db)

        self.inventory = InventoryService(self.db)
        self.reports = ReportService(self.db)
        self.settings = SettingsService(self.db)
        self.backup_service = BackupService(self.db, os.path.join(base_dir, "backups"))
        self.export_service = ExportService(os.path.join(base_dir, "exports"))

        root = Builder.load_string(ROOT_KV)
        self.sm = root.ids.root_manager
        self.bottom_nav = root.ids.bottom_nav
        self.top_bar = root.ids.top_bar

        for screen_cls in (
            DashboardScreen, ProductsScreen, AddProductScreen, ProductDetailsScreen,
            CategoriesScreen, TransactionsScreen, ReportsScreen, DailySummaryScreen,
            AdminLoginScreen, AdminScreen, SettingsScreen,
        ):
            self.sm.add_widget(screen_cls())

        self.sm.current = "dashboard"
        self._history = ["dashboard"]
        self._apply_screen_chrome("dashboard")

        self._run_startup_auto_backup()

        Window.bind(on_keyboard=self._on_key_back)

        return root

    def _on_key_back(self, window, key, *args):
        """Route the Android back button / desktop Esc through in-app
        navigation instead of letting Kivy close the app immediately."""
        if key == 27:
            if self.sm.current == "dashboard" and len(self._history) <= 1:
                return False  # let the OS handle it (exit/minimize)
            self.go_back()
            return True
        return False

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #

    def goto(self, screen_name, _record_history=True, **kwargs):
        screen = self.sm.get_screen(screen_name)
        if hasattr(screen, "on_navigate"):
            screen.on_navigate(**kwargs)

        if self.sm.current != screen_name:
            self.sm.transition.direction = "left" if _record_history else "right"
            self.sm.current = screen_name
            if _record_history:
                self._history.append(screen_name)

        self._apply_screen_chrome(screen_name)

    def _apply_screen_chrome(self, screen_name):
        self.top_bar.title = TITLES.get(screen_name, "Sales Repository")
        self.bottom_nav.height = "60dp" if screen_name in TAB_SCREENS else 0
        self.bottom_nav.opacity = 1 if screen_name in TAB_SCREENS else 0
        if screen_name in TAB_SCREENS:
            self.bottom_nav.current = screen_name

    def go_back(self):
        if len(self._history) > 1:
            self._history.pop()  # drop current screen
            target = self._history[-1]
            self.goto(target, _record_history=False)
        else:
            self.goto("dashboard", _record_history=False)

    def open_admin(self):
        self.goto("admin_login")

    def open_settings(self):
        self.goto("settings")

    # ------------------------------------------------------------------ #
    # Shared helpers
    # ------------------------------------------------------------------ #

    def snackbar(self, text):
        Snackbar(text=text, duration=2.2).open()

    def reset_database(self):
        self.db.reset_inventory_data()

    def _run_startup_auto_backup(self):
        try:
            new_ts = self.backup_service.maybe_run_auto_backup(
                enabled=self.settings.auto_backup_enabled(),
                interval_days=self.settings.auto_backup_interval_days(),
                last_backup_at=self.settings.last_auto_backup_at(),
            )
            if new_ts:
                self.settings.set("last_auto_backup_at", new_ts)
        except Exception:
            # Auto-backup must never block app startup.
            pass

    def on_stop(self):
        try:
            self.db.close()
        except Exception:
            pass


if __name__ == "__main__":
    SalesRepositoryApp().run()
