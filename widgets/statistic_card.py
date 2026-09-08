"""Dashboard statistic tile, e.g. "Products: 125"."""

from kivy.lang import Builder
from kivy.properties import StringProperty, ColorProperty
from kivymd.uix.card import MDCard

KV = """
<StatCard>:
    orientation: "vertical"
    padding: "12dp"
    spacing: "4dp"
    size_hint_y: None
    height: "92dp"
    radius: [14]
    elevation: 1
    md_bg_color: self.card_color

    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: root.accent_color
        font_size: "22sp"

    MDLabel:
        text: root.value
        font_style: "H5"
        bold: True
        theme_text_color: "Custom"
        text_color: root.accent_color
        size_hint_y: None
        height: self.texture_size[1]

    MDLabel:
        text: root.title
        font_style: "Caption"
        theme_text_color: "Secondary"
        size_hint_y: None
        height: self.texture_size[1]
"""
Builder.load_string(KV)


class StatCard(MDCard):
    title = StringProperty("")
    value = StringProperty("0")
    icon = StringProperty("cube-outline")
    accent_color = ColorProperty([0.15, 0.47, 0.87, 1])
    card_color = ColorProperty([1, 1, 1, 1])
