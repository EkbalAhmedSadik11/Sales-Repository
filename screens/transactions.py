"""Transaction History: searchable, filterable by type, exportable to CSV."""

from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.menu import MDDropdownMenu

from widgets.transaction_item import TransactionItem
from utils.formatting import format_datetime

TYPE_LABELS = {
    None: "All Types",
    "STOCK_IN": "Stock In",
    "SALE": "Sale",
    "STOCK_ADJUSTMENT": "Adjustment",
    "PRODUCT_CREATED": "Product Created",
    "PRODUCT_ARCHIVED": "Archived",
    "PRODUCT_RESTORED": "Restored",
}

KV = """
<TransactionsScreen>:
    name: "transactions"

    MDBoxLayout:
        orientation: "vertical"

        MDBoxLayout:
            size_hint_y: None
            height: "56dp"
            padding: "12dp", "6dp"
            spacing: "8dp"

            MDTextField:
                id: search_field
                hint_text: "Search by product name"
                icon_right: "magnify"
                on_text: root.refresh()

            MDIconButton:
                icon: "filter-variant"
                on_release: root.open_type_menu(self)

            MDIconButton:
                icon: "export"
                on_release: root.export()

        MDLabel:
            id: filter_label
            text: "All Types"
            theme_text_color: "Secondary"
            font_style: "Caption"
            padding: "12dp", 0
            size_hint_y: None
            height: self.texture_size[1]

        ScrollView:
            do_scroll_x: False
            MDBoxLayout:
                id: history_box
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: "2dp"
"""
Builder.load_string(KV)


class TransactionsScreen(MDScreen):
    transaction_type = None

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        search = self.ids.search_field.text
        txs = app.inventory.search_transactions(
            transaction_type=self.transaction_type, search=search, limit=300
        )
        box = self.ids.history_box
        box.clear_widgets()
        if not txs:
            from kivymd.uix.label import MDLabel
            box.add_widget(MDLabel(text="No transactions found.", theme_text_color="Secondary",
                                    size_hint_y=None, height="40dp", halign="center"))
        for t in txs:
            color = (0.13, 0.55, 0.13, 1) if t.quantity > 0 else (
                (0.75, 0.2, 0.2, 1) if t.quantity < 0 else (0.4, 0.4, 0.4, 1)
            )
            box.add_widget(TransactionItem(
                date_text=format_datetime(t.created_at, "%d %b %Y, %I:%M %p"),
                product_name=t.product_name,
                type_label=TYPE_LABELS.get(t.transaction_type, t.transaction_type),
                reason=t.reason or "",
                quantity_text=(f"+{t.quantity}" if t.quantity > 0 else str(t.quantity)) if t.quantity else "-",
                quantity_color=color,
            ))

    def open_type_menu(self, caller):
        menu_items = [
            {"text": label, "viewclass": "OneLineListItem",
             "on_release": (lambda tt=tt: self._apply_type(tt))}
            for tt, label in TYPE_LABELS.items()
        ]
        self._menu = MDDropdownMenu(caller=caller, items=menu_items, width_mult=4)
        self._menu.open()

    def _apply_type(self, transaction_type):
        self.transaction_type = transaction_type
        self.ids.filter_label.text = TYPE_LABELS.get(transaction_type, "All Types")
        if hasattr(self, "_menu"):
            self._menu.dismiss()
        self.refresh()

    def export(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        txs = app.inventory.search_transactions(
            transaction_type=self.transaction_type, search=self.ids.search_field.text, limit=100000
        )
        path = app.export_service.export_transactions(txs)
        app.snackbar(f"Exported to {path}")
