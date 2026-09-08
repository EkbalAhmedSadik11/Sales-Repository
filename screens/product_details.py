"""Product Details: full info, edit, stock actions, archive/restore, history."""

from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel

from widgets.transaction_item import TransactionItem
from utils.formatting import format_datetime, format_price
from services.inventory_service import InsufficientStockError
from utils.validation import ValidationError

KV = """
<ProductDetailsScreen>:
    name: "product_details"

    ScrollView:
        do_scroll_x: False

        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
            padding: "16dp"
            spacing: "12dp"

            MDLabel:
                id: name_label
                text: ""
                font_style: "H6"
                bold: True
                size_hint_y: None
                height: self.texture_size[1]

            MDLabel:
                id: code_label
                text: ""
                theme_text_color: "Secondary"
                font_style: "Caption"
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
                    id: stock_label
                    text: ""
                    font_style: "H4"
                    bold: True
                    size_hint_y: None
                    height: self.texture_size[1]

                MDLabel:
                    id: status_flag_label
                    text: ""
                    theme_text_color: "Custom"
                    text_color: 0.8, 0.15, 0.15, 1
                    bold: True
                    size_hint_y: None
                    height: self.texture_size[1] if self.text else 0

                MDLabel:
                    id: totals_label
                    text: ""
                    theme_text_color: "Secondary"
                    size_hint_y: None
                    height: self.texture_size[1]

                MDLabel:
                    id: meta_label
                    text: ""
                    theme_text_color: "Secondary"
                    font_style: "Caption"
                    size_hint_y: None
                    height: self.texture_size[1]

            MDBoxLayout:
                size_hint_y: None
                height: "44dp"
                spacing: "8dp"

                MDRaisedButton:
                    text: "+ STOCK"
                    on_release: root.action_stock_in()

                MDRaisedButton:
                    text: "- SELL"
                    md_bg_color: 0.75, 0.2, 0.2, 1
                    on_release: root.action_sell()

                MDFlatButton:
                    text: "ADJUST"
                    on_release: root.action_adjust()

            MDBoxLayout:
                size_hint_y: None
                height: "44dp"
                spacing: "8dp"

                MDFlatButton:
                    text: "EDIT DETAILS"
                    on_release: root.action_edit()

                Widget:

                MDFlatButton:
                    id: archive_button
                    text: "ARCHIVE PRODUCT"
                    theme_text_color: "Custom"
                    text_color: 0.75, 0.2, 0.2, 1
                    on_release: root.action_archive_toggle()

            MDLabel:
                text: "Transaction History"
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


class ProductDetailsScreen(MDScreen):
    product_id = None

    def on_navigate(self, **kwargs):
        self.product_id = kwargs.get("product_id")

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        product = app.inventory.get_product(self.product_id)
        if not product:
            app.goto("products")
            return
        symbol = app.settings.currency_symbol()

        self.ids.name_label.text = product.name
        self.ids.code_label.text = f"Product ID: {product.product_code}   |   Category: {product.category_name}"
        self.ids.stock_label.text = f"Current Stock: {product.quantity}"
        self.ids.status_flag_label.text = product.stock_label if product.stock_label != "OK" else ""

        report = app.reports.product_report(self.product_id)
        self.ids.totals_label.text = (
            f"Total Received: {report['total_received']}    Total Sold: {report['total_sold']}\n"
            f"Minimum Stock: {product.minimum_stock}    Price: {format_price(product.price, symbol)}"
        )
        self.ids.meta_label.text = (
            f"Created: {format_datetime(product.created_at)}    "
            f"Updated: {format_datetime(product.updated_at)}    Status: {product.status}"
        )
        self.ids.archive_button.text = "RESTORE PRODUCT" if product.status == "ARCHIVED" else "ARCHIVE PRODUCT"

        history_box = self.ids.history_box
        history_box.clear_widgets()
        txs = app.inventory.get_product_transactions(self.product_id, limit=100)
        if not txs:
            history_box.add_widget(MDLabel(text="No transactions yet.", theme_text_color="Secondary",
                                            size_hint_y=None, height="32dp"))
        type_labels = {
            "STOCK_IN": "Stock In", "SALE": "Sale", "STOCK_ADJUSTMENT": "Adjustment",
            "PRODUCT_CREATED": "Product Created", "PRODUCT_ARCHIVED": "Archived",
            "PRODUCT_RESTORED": "Restored",
        }
        for t in txs:
            color = (0.13, 0.55, 0.13, 1) if t.quantity > 0 else (
                (0.75, 0.2, 0.2, 1) if t.quantity < 0 else (0.4, 0.4, 0.4, 1)
            )
            history_box.add_widget(TransactionItem(
                date_text=format_datetime(t.created_at, "%d %b, %I:%M %p"),
                product_name=type_labels.get(t.transaction_type, t.transaction_type),
                type_label=f"{t.previous_quantity} -> {t.new_quantity}",
                reason=t.reason or "",
                quantity_text=(f"+{t.quantity}" if t.quantity > 0 else str(t.quantity)) if t.quantity else "-",
                quantity_color=color,
            ))

    # ---- actions --------------------------------------------------

    def action_stock_in(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        product = app.inventory.get_product(self.product_id)
        qty_field = MDTextField(hint_text="Quantity to add", input_filter="int")

        def confirm(*a):
            try:
                app.inventory.increase_stock(self.product_id, qty_field.text)
                dialog.dismiss()
                app.snackbar("Stock increased.")
                self.refresh()
            except ValidationError as exc:
                qty_field.error = True
                qty_field.helper_text = str(exc)
                qty_field.helper_text_mode = "on_error"

        dialog = MDDialog(
            title=f"Add Stock: {product.name}",
            type="custom",
            content_cls=_field_box(qty_field, f"Current stock: {product.quantity}"),
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                     MDRaisedButton(text="CONFIRM", on_release=confirm)],
        )
        dialog.open()

    def action_sell(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        product = app.inventory.get_product(self.product_id)
        qty_field = MDTextField(hint_text="Quantity sold", input_filter="int")

        def confirm(*a):
            try:
                app.inventory.sell_stock(self.product_id, qty_field.text)
                dialog.dismiss()
                app.snackbar("Sale recorded.")
                self.refresh()
            except InsufficientStockError as exc:
                qty_field.error = True
                qty_field.helper_text = str(exc).replace("\n", "  ")
                qty_field.helper_text_mode = "on_error"
            except ValidationError as exc:
                qty_field.error = True
                qty_field.helper_text = str(exc)
                qty_field.helper_text_mode = "on_error"

        dialog = MDDialog(
            title=f"Sell: {product.name}",
            type="custom",
            content_cls=_field_box(qty_field, f"Current stock: {product.quantity}"),
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                     MDRaisedButton(text="CONFIRM SALE", on_release=confirm)],
        )
        dialog.open()

    def action_adjust(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        product = app.inventory.get_product(self.product_id)
        delta_field = MDTextField(hint_text="Adjustment (e.g. -3 or +5)")
        reason_field = MDTextField(hint_text="Reason *")

        box = MDBoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="180dp",
                           padding=("12dp", "8dp"))
        box.add_widget(MDLabel(text=f"Current stock: {product.quantity}", theme_text_color="Secondary",
                                size_hint_y=None, height="24dp"))
        box.add_widget(delta_field)
        box.add_widget(reason_field)

        def confirm(*a):
            try:
                app.inventory.adjust_stock(self.product_id, delta_field.text or "0", reason_field.text)
                dialog.dismiss()
                app.snackbar("Stock adjusted.")
                self.refresh()
            except InsufficientStockError as exc:
                delta_field.error = True
                delta_field.helper_text = str(exc).replace("\n", "  ")
                delta_field.helper_text_mode = "on_error"
            except ValidationError as exc:
                reason_field.error = True
                reason_field.helper_text = str(exc)
                reason_field.helper_text_mode = "on_error"

        dialog = MDDialog(
            title=f"Adjust Stock: {product.name}",
            type="custom",
            content_cls=box,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                     MDRaisedButton(text="CONFIRM", on_release=confirm)],
        )
        dialog.open()

    def action_edit(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        product = app.inventory.get_product(self.product_id)

        name_field = MDTextField(hint_text="Product name", text=product.name)
        min_field = MDTextField(hint_text="Minimum stock", text=str(product.minimum_stock), input_filter="int")
        price_field = MDTextField(hint_text="Price", text=str(product.price), input_filter="float")

        box = MDBoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="220dp",
                           padding=("12dp", "8dp"))
        for w in (name_field, min_field, price_field):
            box.add_widget(w)

        def confirm(*a):
            try:
                app.inventory.update_product_details(
                    self.product_id, name=name_field.text,
                    minimum_stock=min_field.text, price=price_field.text,
                )
                dialog.dismiss()
                app.snackbar("Product updated.")
                self.refresh()
            except ValidationError as exc:
                name_field.error = True
                name_field.helper_text = str(exc)
                name_field.helper_text_mode = "on_error"

        dialog = MDDialog(
            title="Edit Product",
            type="custom",
            content_cls=box,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                     MDRaisedButton(text="SAVE", on_release=confirm)],
        )
        dialog.open()

    def action_archive_toggle(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        product = app.inventory.get_product(self.product_id)
        archiving = product.status == "ACTIVE"

        def confirm(*a):
            if archiving:
                app.inventory.archive_product(self.product_id)
                app.snackbar("Product archived.")
            else:
                app.inventory.restore_product(self.product_id)
                app.snackbar("Product restored.")
            dialog.dismiss()
            self.refresh()

        body = (
            f"{product.name} will be removed from the active product list.\n\n"
            "Its historical transactions will remain."
        ) if archiving else f"{product.name} will be restored to the active product list."

        dialog = MDDialog(
            title="Archive Product?" if archiving else "Restore Product?",
            text=body,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                     MDRaisedButton(text="ARCHIVE" if archiving else "RESTORE", on_release=confirm)],
        )
        dialog.open()


def _field_box(field, helper):
    box = MDBoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="120dp",
                       padding=("12dp", "8dp"))
    box.add_widget(MDLabel(text=helper, theme_text_color="Secondary", size_hint_y=None, height="24dp"))
    box.add_widget(field)
    return box
