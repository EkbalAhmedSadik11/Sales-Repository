"""PIN gate in front of the Admin section. Also handles first-time PIN setup."""

from kivy.lang import Builder
from kivymd.uix.screen import MDScreen

from utils.validation import ValidationError

KV = """
<AdminLoginScreen>:
    name: "admin_login"

    MDBoxLayout:
        orientation: "vertical"
        padding: "32dp"
        spacing: "16dp"

        Widget:
            size_hint_y: 0.2

        MDIcon:
            icon: "shield-lock-outline"
            font_size: "48sp"
            halign: "center"
            pos_hint: {"center_x": 0.5}

        MDLabel:
            id: title_label
            text: "Enter Admin PIN"
            halign: "center"
            font_style: "H6"
            bold: True
            size_hint_y: None
            height: self.texture_size[1]

        MDLabel:
            id: subtitle_label
            text: ""
            halign: "center"
            theme_text_color: "Secondary"
            size_hint_y: None
            height: self.texture_size[1]

        MDTextField:
            id: pin_field
            hint_text: "PIN"
            password: True
            input_filter: "int"
            halign: "center"
            size_hint_x: None
            width: "200dp"
            pos_hint: {"center_x": 0.5}

        MDLabel:
            id: error_label
            text: ""
            halign: "center"
            theme_text_color: "Error"
            size_hint_y: None
            height: self.texture_size[1] if self.text else 0

        MDRaisedButton:
            id: submit_button
            text: "UNLOCK"
            pos_hint: {"center_x": 0.5}
            on_release: root.submit()

        MDFlatButton:
            text: "CANCEL"
            pos_hint: {"center_x": 0.5}
            on_release: app.goto("dashboard")

        Widget:
"""
Builder.load_string(KV)


class AdminLoginScreen(MDScreen):
    def on_pre_enter(self, *args):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        self.ids.pin_field.text = ""
        self.ids.error_label.text = ""
        self._first_time = not app.settings.has_pin()
        if self._first_time:
            self.ids.title_label.text = "Set Admin PIN"
            self.ids.subtitle_label.text = "Choose a 4-8 digit PIN to protect the Admin section."
            self.ids.submit_button.text = "SET PIN"
        else:
            self.ids.title_label.text = "Enter Admin PIN"
            self.ids.subtitle_label.text = ""
            self.ids.submit_button.text = "UNLOCK"

    def submit(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        pin = self.ids.pin_field.text

        if self._first_time:
            try:
                app.settings.set_pin(pin)
                app.goto("admin")
            except ValidationError as exc:
                self.ids.error_label.text = str(exc)
            return

        if app.settings.check_pin(pin):
            self.ids.error_label.text = ""
            app.goto("admin")
        else:
            self.ids.error_label.text = "Incorrect PIN. Try again."
            self.ids.pin_field.text = ""
