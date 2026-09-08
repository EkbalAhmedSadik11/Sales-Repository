"""Row card for the product list: name/category/stock + quick actions."""

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import StringProperty, NumberProperty, ObjectProperty, BooleanProperty
from kivymd.uix.card import MDCard

KV = """
<ProductCard>:
    orientation: "vertical"
    size_hint_y: None
    height: "128dp"
    padding: "12dp", "8dp"
    spacing: "2dp"
    radius: [12]
    elevation: 1

    MDBoxLayout:
        size_hint_y: None
        height: "24dp"
        MDLabel:
            text: root.name
            bold: True
            font_style: "Subtitle1"
            shorten: True
            shorten_from: "right"
        MDLabel:
            text: root.status_badge
            halign: "right"
            theme_text_color: "Custom"
            text_color: root.status_color
            font_style: "Caption"
            size_hint_x: None
            width: "90dp"

    MDLabel:
        text: "Category: " + root.category_name
        theme_text_color: "Secondary"
        font_style: "Caption"
        size_hint_y: None
        height: "18dp"

    MDLabel:
        text: "Stock: " + str(root.quantity) + ("   |   " + root.price_text if root.price_text else "")
        theme_text_color: "Secondary"
        font_style: "Body2"
        size_hint_y: None
        height: "20dp"

    MDBoxLayout:
        size_hint_y: None
        height: "36dp" if root.show_quick_actions else "0dp"
        opacity: 1 if root.show_quick_actions else 0
        spacing: "8dp"
        padding: 0, "4dp", 0, 0

        MDFlatButton:
            text: "+ Stock"
            theme_text_color: "Custom"
            text_color: 0.13, 0.55, 0.13, 1
            disabled: not root.show_quick_actions
            on_release: root.on_stock_in()

        MDFlatButton:
            text: "- Sell"
            theme_text_color: "Custom"
            text_color: 0.75, 0.2, 0.2, 1
            disabled: not root.show_quick_actions
            on_release: root.on_sell()

        Widget:

        MDFlatButton:
            text: "Details"
            on_release: root.on_details()
"""
Builder.load_string(KV)


class ProductCard(MDCard):
    product_id = NumberProperty(0)
    name = StringProperty("")
    category_name = StringProperty("")
    quantity = NumberProperty(0)
    price_text = StringProperty("")
    status_badge = StringProperty("")
    status_color = ObjectProperty([0.2, 0.6, 0.2, 1])
    is_archived = BooleanProperty(False)
    show_quick_actions = BooleanProperty(True)

    on_stock_in_cb = ObjectProperty(None, allownone=True)
    on_sell_cb = ObjectProperty(None, allownone=True)
    on_details_cb = ObjectProperty(None, allownone=True)

    def on_stock_in(self):
        if self.on_stock_in_cb:
            self.on_stock_in_cb(self.product_id)

    def on_sell(self):
        if self.on_sell_cb:
            self.on_sell_cb(self.product_id)

    def on_details(self):
        if self.on_details_cb:
            self.on_details_cb(self.product_id)


Factory.register("ProductCard", cls=ProductCard)
