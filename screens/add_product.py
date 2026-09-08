"""Add Product form."""

from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.menu import MDDropdownMenu

from utils.validation import ValidationError
from services.inventory_service import DuplicateProductCodeError

KV = """
<AddProductScreen>:
    name: "add_product"

    ScrollView:
        do_scroll_x: False

        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
            padding: "20dp"
            spacing: "16dp"

            MDLabel:
                text: "Add New Product"
                font_style: "H6"
                bold: True
                size_hint_y: None
                height: self.texture_size[1]

            MDTextField:
                id: name_field
                hint_text: "Product name *"

            MDTextField:
                id: category_field
                hint_text: "Category * (tap to choose)"
                readonly: True
                on_focus: if self.focus: root.open_category_menu()

            MDTextField:
                id: quantity_field
                hint_text: "Initial quantity *"
                input_filter: "int"
                helper_text: "Whole number, 0 or more"
                helper_text_mode: "persistent"

            MDTextField:
                id: min_stock_field
                hint_text: "Minimum stock level *"
                input_filter: "int"
                helper_text: "Triggers a Low Stock warning at/below this level"
                helper_text_mode: "persistent"

            MDTextField:
                id: price_field
                hint_text: "Unit price (optional)"
                input_filter: "float"

            MDLabel:
                id: error_label
                text: ""
                theme_text_color: "Error"
                size_hint_y: None
                height: self.texture_size[1] if self.text else 0

            MDBoxLayout:
                size_hint_y: None
                height: "48dp"
                spacing: "12dp"

                MDFlatButton:
                    text: "CANCEL"
                    on_release: app.goto("products")

                MDRaisedButton:
                    text: "SAVE PRODUCT"
                    on_release: root.save()
"""
Builder.load_string(KV)


class AddProductScreen(MDScreen):
    _selected_category_id = None

    def on_pre_enter(self, *args):
        for fid in ("name_field", "category_field", "quantity_field", "min_stock_field", "price_field"):
            self.ids[fid].text = ""
            self.ids[fid].error = False
        self.ids.error_label.text = ""
        self._selected_category_id = None

    def open_category_menu(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        categories = app.inventory.list_categories()
        menu_items = [
            {
                "text": cat["name"],
                "viewclass": "OneLineListItem",
                "on_release": (lambda cid=cat["id"], name=cat["name"]: self._select_category(cid, name)),
            }
            for cat in categories
        ]
        self._menu = MDDropdownMenu(caller=self.ids.category_field, items=menu_items, width_mult=4)
        self._menu.open()

    def _select_category(self, category_id, name):
        self._selected_category_id = category_id
        self.ids.category_field.text = name
        self.ids.category_field.focus = False
        if hasattr(self, "_menu"):
            self._menu.dismiss()

    def save(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        try:
            product_id = app.inventory.add_product(
                name=self.ids.name_field.text,
                category_id=self._selected_category_id,
                initial_quantity=self.ids.quantity_field.text or "0",
                minimum_stock=self.ids.min_stock_field.text or "0",
                price=self.ids.price_field.text,
            )
            app.snackbar("Product added successfully.")
            app.goto("product_details", product_id=product_id)
        except (ValidationError, DuplicateProductCodeError) as exc:
            self.ids.error_label.text = str(exc)
