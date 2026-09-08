"""Reports hub: today's report, category report, low stock report, daily summary."""

from kivy.lang import Builder
from kivymd.uix.screen import MDScreen

from utils.formatting import format_price

KV = """
<ReportsScreen>:
    name: "reports"

    ScrollView:
        do_scroll_x: False

        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
            padding: "16dp"
            spacing: "16dp"

            MDLabel:
                text: "Reports"
                font_style: "H6"
                bold: True
                size_hint_y: None
                height: self.texture_size[1]

            MDCard:
                orientation: "vertical"
                padding: "16dp"
                spacing: "6dp"
                size_hint_y: None
                height: self.minimum_height
                radius: [12]
                elevation: 1

                MDLabel:
                    text: "Today's Report"
                    font_style: "Subtitle1"
                    bold: True
                    size_hint_y: None
                    height: self.texture_size[1]

                MDLabel:
                    id: today_label
                    text: ""
                    theme_text_color: "Secondary"
                    size_hint_y: None
                    height: self.texture_size[1]

                MDRaisedButton:
                    text: "VIEW DAILY SUMMARY / PICK DATE"
                    pos_hint: {"center_x": 0.5}
                    on_release: root.open_date_picker()

            MDCard:
                orientation: "vertical"
                padding: "16dp"
                spacing: "6dp"
                size_hint_y: None
                height: self.minimum_height
                radius: [12]
                elevation: 1

                MDLabel:
                    text: "Category Report"
                    font_style: "Subtitle1"
                    bold: True
                    size_hint_y: None
                    height: self.texture_size[1]

                MDBoxLayout:
                    id: category_report_box
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height

                MDFlatButton:
                    text: "EXPORT CATEGORY REPORT (CSV)"
                    on_release: root.export_category_report()

            MDCard:
                orientation: "vertical"
                padding: "16dp"
                spacing: "6dp"
                size_hint_y: None
                height: self.minimum_height
                radius: [12]
                elevation: 1

                MDLabel:
                    text: "Low Stock Report"
                    font_style: "Subtitle1"
                    bold: True
                    size_hint_y: None
                    height: self.texture_size[1]

                MDLabel:
                    id: low_stock_label
                    text: ""
                    theme_text_color: "Secondary"
                    size_hint_y: None
                    height: self.texture_size[1]

                MDBoxLayout:
                    size_hint_y: None
                    height: "44dp"
                    spacing: "8dp"

                    MDRaisedButton:
                        text: "VIEW LOW STOCK"
                        on_release: app.goto("products", stock_filter="low")

                    MDFlatButton:
                        text: "EXPORT (CSV)"
                        on_release: root.export_low_stock_report()

            MDFlatButton:
                text: "EXPORT ALL PRODUCTS (CSV)"
                pos_hint: {"center_x": 0.5}
                on_release: root.export_products()
"""
Builder.load_string(KV)


class ReportsScreen(MDScreen):
    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        from kivymd.app import MDApp
        from kivymd.uix.label import MDLabel
        app = MDApp.get_running_app()

        today = app.reports.today_report(app.inventory)
        self.ids.today_label.text = (
            f"Products Received: {today['received']}\n"
            f"Products Sold: {today['sold']}\n"
            f"Stock Adjustments: {today['adjustments']}\n"
            f"Total Current Stock: {today['total_stock']}"
        )

        cat_rows = app.reports.category_report()
        box = self.ids.category_report_box
        box.clear_widgets()
        for row in cat_rows:
            box.add_widget(MDLabel(
                text=f"{row['name']}: {row['product_count']} products, {row['total_stock']} units",
                theme_text_color="Secondary", size_hint_y=None, height="24dp",
            ))

        low_stock = app.reports.low_stock_report()
        self.ids.low_stock_label.text = f"{len(low_stock)} product(s) at or below minimum stock."

    def open_date_picker(self):
        from kivymd.uix.pickers import MDDatePicker
        picker = MDDatePicker()
        picker.bind(on_save=self._on_date_selected)
        picker.open()

    def _on_date_selected(self, instance, value, date_range):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        app.goto("daily_summary", date_str=value.strftime("%Y-%m-%d"))

    def export_category_report(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        rows = app.reports.category_report()
        path = app.export_service.export_category_report(rows)
        app.snackbar(f"Exported to {path}")

    def export_low_stock_report(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        products = app.reports.low_stock_report()
        path = app.export_service.export_low_stock_report(products)
        app.snackbar(f"Exported to {path}")

    def export_products(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        products = app.inventory.list_products(status="ACTIVE", limit=100000)
        path = app.export_service.export_products(products)
        app.snackbar(f"Exported to {path}")
