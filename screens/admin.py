"""Admin hub: shortcuts to management screens gated behind the PIN."""

from kivy.lang import Builder
from kivymd.uix.screen import MDScreen

KV = """
<AdminScreen>:
    name: "admin"

    ScrollView:
        do_scroll_x: False

        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
            padding: "16dp"
            spacing: "10dp"

            MDLabel:
                text: "Admin Panel"
                font_style: "H6"
                bold: True
                size_hint_y: None
                height: self.texture_size[1]

            AdminActionTile:
                icon: "shape-outline"
                title: "Manage Categories"
                subtitle: "Add, rename, or delete categories"
                on_release: app.goto("categories")

            AdminActionTile:
                icon: "history"
                title: "Transaction History"
                subtitle: "Search and export every stock movement"
                on_release: app.goto("transactions")

            AdminActionTile:
                icon: "chart-bar"
                title: "Reports"
                subtitle: "Daily, category, and low-stock reports"
                on_release: app.goto("reports")

            AdminActionTile:
                icon: "archive-outline"
                title: "Archived Products"
                subtitle: "View products removed from the active list"
                on_release: app.goto("products", status="ARCHIVED")

            AdminActionTile:
                icon: "cog-outline"
                title: "Settings"
                subtitle: "Backup, restore, PIN, and preferences"
                on_release: app.goto("settings")

            MDLabel:
                text: "Sales Repository keeps every sale, stock-in, and adjustment in its history. Removing a product only archives it - nothing is ever deleted automatically."
                theme_text_color: "Secondary"
                font_style: "Caption"
                size_hint_y: None
                height: self.texture_size[1]
                padding: "4dp", "12dp"
"""
Builder.load_string(KV)


class AdminScreen(MDScreen):
    pass
