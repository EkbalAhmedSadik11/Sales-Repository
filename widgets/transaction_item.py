"""Single row in a transaction history list."""

from kivy.lang import Builder
from kivy.properties import StringProperty, ColorProperty
from kivymd.uix.boxlayout import MDBoxLayout

KV = """
<TransactionItem>:
    size_hint_y: None
    height: "56dp"
    padding: "12dp", "4dp"
    spacing: "10dp"

    MDLabel:
        text: root.date_text
        theme_text_color: "Secondary"
        font_style: "Caption"
        size_hint_x: 0.28

    MDBoxLayout:
        orientation: "vertical"
        MDLabel:
            text: root.product_name
            font_style: "Body2"
            shorten: True
            shorten_from: "right"
        MDLabel:
            text: root.type_label + (("  -  " + root.reason) if root.reason else "")
            theme_text_color: "Secondary"
            font_style: "Caption"
            shorten: True
            shorten_from: "right"

    MDLabel:
        text: root.quantity_text
        halign: "right"
        bold: True
        theme_text_color: "Custom"
        text_color: root.quantity_color
        size_hint_x: 0.2
"""
Builder.load_string(KV)


class TransactionItem(MDBoxLayout):
    date_text = StringProperty("")
    product_name = StringProperty("")
    type_label = StringProperty("")
    reason = StringProperty("")
    quantity_text = StringProperty("")
    quantity_color = ColorProperty([0.2, 0.2, 0.2, 1])
