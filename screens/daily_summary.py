"""Daily Inventory / Sales Summary for a single selected date."""

from kivy.lang import Builder
from kivymd.uix.screen import MDScreen

from widgets.transaction_item import TransactionItem
from utils.formatting import format_date, format_datetime

TYPE_LABELS = {
    "STOCK_IN": "Stock In", "SALE": "Sale", "STOCK_ADJUSTMENT": "Adjustment",
    "PRODUCT_CREATED": "Product Created", "PRODUCT_ARCHIVED": "Archived",
    "PRODUCT_RESTORED": "Restored",
}

KV = """
<DailySummaryScreen>:
    name: "daily_summary"

    ScrollView:
        do_scroll_x: False

        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
            padding: "16dp"
            spacing: "12dp"

            MDLabel:
                id: date_label
                text: ""
                font_style: "H6"
                bold: True
                size_hint_y: None
                height: self.texture_size[1]

            MDCard:
                orientation: "vertical"
                padding: "16dp"
                spacing: "4dp"
                size_hint_y: None
                height: self.minimum_height
                radius: [12]
                elevation: 1

                MDLabel:
                    id: summary_label
                    text: ""
                    size_hint_y: None
                    height: self.texture_size[1]

                MDFlatButton:
                    text: "EXPORT THIS DAY (CSV)"
                    on_release: root.export()

            MDLabel:
                text: "Transactions"
                font_style: "Subtitle1"
                bold: True
                size_hint_y: None
                height: self.texture_size[1]

            MDBoxLayout:
                id: history_box
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: "2dp"
"""
Builder.load_string(KV)


class DailySummaryScreen(MDScreen):
    date_str = None

    def on_navigate(self, **kwargs):
        self.date_str = kwargs.get("date_str")

    def on_pre_enter(self, *args):
        if not self.date_str:
            import datetime
            self.date_str = datetime.date.today().strftime("%Y-%m-%d")
        self.refresh()

    def refresh(self):
        from kivymd.app import MDApp
        from kivymd.uix.label import MDLabel
        app = MDApp.get_running_app()
        summary = app.inventory.get_daily_summary(self.date_str)
        self._summary = summary

        self.ids.date_label.text = format_date(self.date_str + "T00:00:00")
        self.ids.summary_label.text = (
            f"Products Received: {summary['received']}\n"
            f"Products Sold: {summary['sold']}\n"
            f"Stock Adjustments: {summary['adjustments']}\n"
            f"Total Current Stock: {summary['total_stock']}"
        )

        box = self.ids.history_box
        box.clear_widgets()
        if not summary["transactions"]:
            box.add_widget(MDLabel(text="No activity on this date.", theme_text_color="Secondary",
                                    size_hint_y=None, height="32dp"))
        for t in summary["transactions"]:
            color = (0.13, 0.55, 0.13, 1) if t.quantity > 0 else (
                (0.75, 0.2, 0.2, 1) if t.quantity < 0 else (0.4, 0.4, 0.4, 1)
            )
            box.add_widget(TransactionItem(
                date_text=format_datetime(t.created_at, "%I:%M %p"),
                product_name=t.product_name,
                type_label=TYPE_LABELS.get(t.transaction_type, t.transaction_type),
                reason=t.reason or "",
                quantity_text=(f"+{t.quantity}" if t.quantity > 0 else str(t.quantity)) if t.quantity else "-",
                quantity_color=color,
            ))

    def export(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        path = app.export_service.export_daily_summary(self._summary)
        app.snackbar(f"Exported to {path}")
