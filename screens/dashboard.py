"""Dashboard: at-a-glance stock and today's activity statistics."""

from kivy.lang import Builder
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen

from widgets.statistic_card import StatCard

KV = """
<DashboardScreen>:
    name: "dashboard"

    ScrollView:
        do_scroll_x: False

        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
            padding: "16dp"
            spacing: "16dp"

            MDLabel:
                text: "Inventory Dashboard"
                font_style: "H6"
                bold: True
                size_hint_y: None
                height: self.texture_size[1]

            MDLabel:
                id: subtitle_label
                text: ""
                theme_text_color: "Secondary"
                font_style: "Caption"
                size_hint_y: None
                height: self.texture_size[1]

            MDGridLayout:
                id: stats_grid
                cols: 2
                spacing: "12dp"
                size_hint_y: None
                height: self.minimum_height

            MDCard:
                id: alert_card
                orientation: "vertical"
                padding: "12dp"
                spacing: "6dp"
                size_hint_y: None
                height: self.minimum_height
                radius: [12]
                elevation: 1
                md_bg_color: 1, 0.96, 0.93, 1

                MDLabel:
                    id: alert_label
                    text: ""
                    theme_text_color: "Custom"
                    text_color: 0.7, 0.25, 0.05, 1
                    font_style: "Body2"
                    size_hint_y: None
                    height: self.texture_size[1] if self.text else 0

            MDRaisedButton:
                text: "VIEW LOW STOCK PRODUCTS"
                pos_hint: {"center_x": 0.5}
                on_release: app.goto("products", stock_filter="low")
"""
Builder.load_string(KV)


class DashboardScreen(MDScreen):
    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        stats = app.inventory.get_dashboard_stats()
        symbol = app.settings.currency_symbol()

        grid = self.ids.stats_grid
        grid.clear_widgets()

        cards = [
            ("Products", str(stats["total_products"]), "cube-outline", (0.15, 0.47, 0.87, 1)),
            ("Categories", str(stats["total_categories"]), "shape-outline", (0.35, 0.35, 0.75, 1)),
            ("Stock Available", str(stats["stock_available"]), "warehouse", (0.13, 0.55, 0.13, 1)),
            ("Sold Today", str(stats["sold_today"]), "cart-outline", (0.75, 0.35, 0.1, 1)),
            ("Received Today", str(stats["received_today"]), "truck-delivery-outline", (0.15, 0.6, 0.6, 1)),
            ("Low Stock", str(stats["low_stock"]), "alert-outline", (0.85, 0.55, 0.05, 1)),
            ("Out of Stock", str(stats["out_of_stock"]), "close-octagon-outline", (0.8, 0.15, 0.15, 1)),
        ]
        for title, value, icon, color in cards:
            grid.add_widget(StatCard(title=title, value=value, icon=icon, accent_color=color))

        import datetime
        self.ids.subtitle_label.text = datetime.datetime.now().strftime("%A, %d %B %Y")

        alerts = []
        if stats["out_of_stock"]:
            alerts.append(f'{stats["out_of_stock"]} product(s) are OUT OF STOCK.')
        if stats["low_stock"]:
            alerts.append(f'{stats["low_stock"]} product(s) are running LOW ON STOCK.')
        self.ids.alert_label.text = "  ".join(alerts)
