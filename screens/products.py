"""Product list: search, filter, sort, quick stock actions, add product FAB."""

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivymd.uix.screen import MDScreen
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout

from widgets.product_card import ProductCard
from services.inventory_service import InsufficientStockError
from utils.validation import ValidationError

KV = """
<ProductsScreen>:
    name: "products"

    MDFloatLayout:

        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: 1

            MDBoxLayout:
                size_hint_y: None
                height: "56dp"
                padding: "12dp", "6dp"
                spacing: "8dp"

                MDTextField:
                    id: search_field
                    hint_text: "Search by name or product ID"
                    icon_right: "magnify"
                    on_text: root.on_search(self.text)

                MDIconButton:
                    icon: "filter-variant"
                    on_release: root.open_filter_menu(self)

                MDIconButton:
                    icon: "sort"
                    on_release: root.open_sort_menu(self)

            MDLabel:
                id: active_filter_label
                text: ""
                theme_text_color: "Secondary"
                font_style: "Caption"
                size_hint_y: None
                height: self.texture_size[1] if self.text else 0
                padding: "12dp", 0

            MDLabel:
                id: empty_label
                text: "No products found."
                halign: "center"
                theme_text_color: "Secondary"
                size_hint_y: None
                height: "40dp" if self.text else 0

            RecycleView:
                id: product_rv
                viewclass: "ProductCard"
                bar_width: "4dp"

                RecycleBoxLayout:
                    id: rv_layout
                    default_size: None, dp(128)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: "vertical"
                    spacing: "8dp"
                    padding: "8dp"

        MDFloatingActionButton:
            icon: "plus"
            pos_hint: {"right": 0.96, "y": 0.04}
            md_bg_color: app.theme_cls.primary_color
            on_release: app.goto("add_product")
"""
Builder.load_string(KV)


class ProductsScreen(MDScreen):
    pending_stock_filter = StringProperty(None, allownone=True)
    pending_category_id = None

    def on_pre_enter(self, *args):
        if self.pending_stock_filter is not None:
            self.stock_filter = self.pending_stock_filter
            self.pending_stock_filter = None
        else:
            if not hasattr(self, "stock_filter"):
                self.stock_filter = None
        if not hasattr(self, "sort_by"):
            self.sort_by = "name"
            self.sort_dir = "asc"
        if not hasattr(self, "category_id"):
            self.category_id = None
        if not hasattr(self, "status"):
            self.status = "ACTIVE"
        self.refresh()

    def on_navigate(self, **kwargs):
        self.pending_stock_filter = kwargs.get("stock_filter")
        self.category_id = kwargs.get("category_id")
        self.status = kwargs.get("status") or "ACTIVE"

    # ---- data loading ----------------------------------------------

    def on_search(self, text):
        self.refresh()

    def refresh(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        search = self.ids.search_field.text
        products = app.inventory.list_products(
            search=search,
            category_id=self.category_id,
            status=self.status,
            stock_filter=self.stock_filter,
            sort_by=self.sort_by,
            sort_dir=self.sort_dir,
        )
        symbol = app.settings.currency_symbol()
        is_archived_view = self.status == "ARCHIVED"
        data = []
        for p in products:
            status_badge = p.stock_label if p.stock_label != "OK" else ""
            color = (0.8, 0.15, 0.15, 1) if p.is_out_of_stock else (
                (0.85, 0.55, 0.05, 1) if p.is_low_stock else (0.2, 0.2, 0.2, 1)
            )
            data.append({
                "product_id": p.id,
                "name": p.name,
                "category_name": p.category_name or "",
                "quantity": p.quantity,
                "price_text": f"{symbol}{p.price:.2f}" if p.price else "",
                "status_badge": "ARCHIVED" if is_archived_view else status_badge,
                "status_color": (0.4, 0.4, 0.4, 1) if is_archived_view else color,
                "show_quick_actions": not is_archived_view,
                "on_stock_in_cb": None if is_archived_view else self.quick_stock_in,
                "on_sell_cb": None if is_archived_view else self.quick_sell,
                "on_details_cb": self.open_details,
            })
        self.ids.product_rv.data = data
        self.ids.empty_label.text = "No products found." if not data else ""

        labels = []
        if is_archived_view:
            labels.append("Archived products")
        if self.stock_filter == "low":
            labels.append("Low stock")
        elif self.stock_filter == "out":
            labels.append("Out of stock")
        if self.category_id:
            cat = app.inventory.get_category(self.category_id)
            if cat:
                labels.append(cat.name)
        self.ids.active_filter_label.text = ("Filter: " + ", ".join(labels)) if labels else ""

    def open_details(self, product_id):
        from kivymd.app import MDApp
        MDApp.get_running_app().goto("product_details", product_id=product_id)

    # ---- filter / sort menus ----------------------------------------

    def open_filter_menu(self, caller):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        categories = app.inventory.list_categories()

        items = [
            {"text": "All Active Products", "on_release": lambda: self._apply_filter(None, None, "ACTIVE")},
            {"text": "Low Stock", "on_release": lambda: self._apply_filter("low", self.category_id, "ACTIVE")},
            {"text": "Out of Stock", "on_release": lambda: self._apply_filter("out", self.category_id, "ACTIVE")},
            {"text": "Archived Products", "on_release": lambda: self._apply_filter(None, None, "ARCHIVED")},
        ]
        for cat in categories:
            items.append({
                "text": f"Category: {cat['name']}",
                "on_release": (lambda cid=cat["id"]: self._apply_filter(self.stock_filter, cid, "ACTIVE")),
            })
        menu_items = [
            {"text": it["text"], "viewclass": "OneLineListItem", "on_release": it["on_release"]}
            for it in items
        ]
        self._menu = MDDropdownMenu(caller=caller, items=menu_items, width_mult=4)
        self._menu.open()

    def _apply_filter(self, stock_filter, category_id, status="ACTIVE"):
        self.stock_filter = stock_filter
        self.category_id = category_id
        self.status = status
        if hasattr(self, "_menu"):
            self._menu.dismiss()
        self.refresh()

    def open_sort_menu(self, caller):
        options = [
            ("Name (A-Z)", "name", "asc"),
            ("Quantity (High-Low)", "quantity", "desc"),
            ("Quantity (Low-High)", "quantity", "asc"),
            ("Price (High-Low)", "price", "desc"),
            ("Recently Updated", "updated_at", "desc"),
        ]
        menu_items = [
            {
                "text": label,
                "viewclass": "OneLineListItem",
                "on_release": (lambda by=by, d=d: self._apply_sort(by, d)),
            }
            for label, by, d in options
        ]
        self._menu = MDDropdownMenu(caller=caller, items=menu_items, width_mult=4)
        self._menu.open()

    def _apply_sort(self, sort_by, sort_dir):
        self.sort_by = sort_by
        self.sort_dir = sort_dir
        if hasattr(self, "_menu"):
            self._menu.dismiss()
        self.refresh()

    # ---- quick actions -------------------------------------------------

    def quick_stock_in(self, product_id):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        product = app.inventory.get_product(product_id)
        qty_field = MDTextField(hint_text="Quantity to add", input_filter="int")

        def confirm(*a):
            try:
                app.inventory.increase_stock(product_id, qty_field.text)
                dialog.dismiss()
                app.snackbar(f"Stock updated: {product.name}")
                self.refresh()
            except (ValidationError,) as exc:
                qty_field.error = True
                qty_field.helper_text = str(exc)
                qty_field.helper_text_mode = "on_error"

        dialog = MDDialog(
            title=f"Add Stock: {product.name}",
            type="custom",
            content_cls=self._wrap(qty_field, f"Current stock: {product.quantity}"),
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="CONFIRM", on_release=confirm),
            ],
        )
        dialog.open()

    def quick_sell(self, product_id):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        product = app.inventory.get_product(product_id)
        qty_field = MDTextField(hint_text="Quantity sold", input_filter="int")

        def confirm(*a):
            try:
                app.inventory.sell_stock(product_id, qty_field.text)
                dialog.dismiss()
                app.snackbar(f"Sale recorded: {product.name}")
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
            content_cls=self._wrap(qty_field, f"Current stock: {product.quantity}"),
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="CONFIRM SALE", on_release=confirm),
            ],
        )
        dialog.open()

    def _wrap(self, field, helper):
        box = MDBoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="120dp",
                           padding=("12dp", "8dp"))
        from kivymd.uix.label import MDLabel
        box.add_widget(MDLabel(text=helper, theme_text_color="Secondary", size_hint_y=None, height="24dp"))
        box.add_widget(field)
        return box
