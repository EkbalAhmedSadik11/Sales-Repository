"""Tappable row used on the Admin hub screen."""

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.card import MDCard

KV = """
<AdminActionTile>:
    orientation: "horizontal"
    size_hint_y: None
    height: "68dp"
    padding: "14dp", "8dp"
    spacing: "14dp"
    radius: [10]
    elevation: 1

    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: app.theme_cls.primary_color
        size_hint_x: None
        width: "32dp"

    MDBoxLayout:
        orientation: "vertical"

        MDLabel:
            text: root.title
            bold: True
            font_style: "Subtitle2"

        MDLabel:
            text: root.subtitle
            theme_text_color: "Secondary"
            font_style: "Caption"

    MDIcon:
        icon: "chevron-right"
        size_hint_x: None
        width: "24dp"
"""
Builder.load_string(KV)


class AdminActionTile(ButtonBehavior, MDCard):
    icon = StringProperty("cog-outline")
    title = StringProperty("")
    subtitle = StringProperty("")


Factory.register("AdminActionTile", cls=AdminActionTile)
