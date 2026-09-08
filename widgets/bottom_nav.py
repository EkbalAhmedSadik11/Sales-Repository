"""Custom bottom navigation bar for the three primary screens.

A plain custom widget (rather than KivyMD's MDBottomNavigation) so that the
screen bodies stay ordinary MDScreen subclasses managed by one MDScreenManager
shared with every other screen in the app (product details, categories,
admin, etc.) - simpler than juggling two separate screen-switching systems.
"""

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.boxlayout import MDBoxLayout

KV = """
<NavButton>:
    orientation: "vertical"
    padding: 0, "6dp"

    MDIcon:
        icon: root.icon
        halign: "center"
        theme_text_color: "Custom"
        text_color: (app.theme_cls.primary_color if root.active else (0.55, 0.55, 0.55, 1))
        pos_hint: {"center_x": 0.5}

    MDLabel:
        text: root.label_text
        halign: "center"
        font_style: "Caption"
        theme_text_color: "Custom"
        text_color: (app.theme_cls.primary_color if root.active else (0.55, 0.55, 0.55, 1))
        size_hint_y: None
        height: self.texture_size[1]

<BottomNavBar>:
    size_hint_y: None
    height: "60dp"
    md_bg_color: 1, 1, 1, 1
    elevation: 4

    NavButton:
        screen_name: "dashboard"
        icon: "view-dashboard-outline"
        label_text: "Dashboard"
        active: root.current == "dashboard"
        on_release: root.select("dashboard")

    NavButton:
        screen_name: "products"
        icon: "package-variant-closed"
        label_text: "Products"
        active: root.current == "products"
        on_release: root.select("products")

    NavButton:
        screen_name: "reports"
        icon: "chart-bar"
        label_text: "Reports"
        active: root.current == "reports"
        on_release: root.select("reports")
"""
Builder.load_string(KV)


class NavButton(ButtonBehavior, MDBoxLayout):
    screen_name = StringProperty("")
    icon = StringProperty("")
    label_text = StringProperty("")
    active = BooleanProperty(False)


class BottomNavBar(MDBoxLayout):
    current = StringProperty("dashboard")

    def select(self, screen_name):
        from kivymd.app import MDApp
        MDApp.get_running_app().goto(screen_name)


Factory.register("NavButton", cls=NavButton)
Factory.register("BottomNavBar", cls=BottomNavBar)
