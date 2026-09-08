"""Settings: backup/restore, auto-backup preferences, admin PIN, advanced reset."""

import os

from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem

from services.backup_service import BackupError
from utils.validation import ValidationError

KV = """
<SettingsScreen>:
    name: "settings"

    ScrollView:
        do_scroll_x: False

        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
            padding: "16dp"
            spacing: "14dp"

            MDLabel:
                text: "Settings"
                font_style: "H6"
                bold: True
                size_hint_y: None
                height: self.texture_size[1]

            MDCard:
                orientation: "vertical"
                padding: "16dp"
                spacing: "10dp"
                size_hint_y: None
                height: self.minimum_height
                radius: [12]
                elevation: 1

                MDLabel:
                    text: "Backup & Restore"
                    font_style: "Subtitle1"
                    bold: True
                    size_hint_y: None
                    height: self.texture_size[1]

                MDLabel:
                    id: last_backup_label
                    text: ""
                    theme_text_color: "Secondary"
                    font_style: "Caption"
                    size_hint_y: None
                    height: self.texture_size[1]

                MDBoxLayout:
                    size_hint_y: None
                    height: "44dp"
                    spacing: "8dp"
                    adaptive_width: True

                    MDRaisedButton:
                        text: "BACKUP NOW"
                        on_release: root.backup_now()

                    MDFlatButton:
                        text: "RESTORE FROM BACKUP"
                        on_release: root.show_restore_list()

                MDBoxLayout:
                    size_hint_y: None
                    height: "44dp"

                    MDLabel:
                        text: "Automatic backups"
                        valign: "middle"

                    MDSwitch:
                        id: auto_backup_switch
                        pos_hint: {"center_y": 0.5}
                        on_active: root.toggle_auto_backup(self.active)

            MDCard:
                orientation: "vertical"
                padding: "16dp"
                spacing: "10dp"
                size_hint_y: None
                height: self.minimum_height
                radius: [12]
                elevation: 1

                MDLabel:
                    text: "Export Data"
                    font_style: "Subtitle1"
                    bold: True
                    size_hint_y: None
                    height: self.texture_size[1]

                MDFlatButton:
                    text: "OPEN EXPORTS FOLDER PATH"
                    on_release: root.show_export_path()

            MDCard:
                orientation: "vertical"
                padding: "16dp"
                spacing: "10dp"
                size_hint_y: None
                height: self.minimum_height
                radius: [12]
                elevation: 1

                MDLabel:
                    text: "Admin PIN"
                    font_style: "Subtitle1"
                    bold: True
                    size_hint_y: None
                    height: self.texture_size[1]

                MDFlatButton:
                    text: "CHANGE PIN"
                    on_release: root.change_pin_dialog()

            MDCard:
                orientation: "vertical"
                padding: "16dp"
                spacing: "6dp"
                size_hint_y: None
                height: self.minimum_height
                radius: [12]
                elevation: 1
                md_bg_color: 1, 0.96, 0.93, 1

                MDLabel:
                    text: "Advanced"
                    font_style: "Subtitle1"
                    bold: True
                    size_hint_y: None
                    height: self.texture_size[1]

                MDLabel:
                    text: "For development/testing only. Not part of normal use."
                    theme_text_color: "Secondary"
                    font_style: "Caption"
                    size_hint_y: None
                    height: self.texture_size[1]

                MDFlatButton:
                    text: "RESET DATABASE"
                    theme_text_color: "Custom"
                    text_color: 0.75, 0.2, 0.2, 1
                    on_release: root.confirm_reset_database()
"""
Builder.load_string(KV)


class SettingsScreen(MDScreen):
    def on_pre_enter(self, *args):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        self.ids.auto_backup_switch.active = app.settings.auto_backup_enabled()
        self._refresh_last_backup_label()

    def _refresh_last_backup_label(self):
        from kivymd.app import MDApp
        from utils.formatting import format_datetime
        app = MDApp.get_running_app()
        last = app.settings.last_auto_backup_at()
        self.ids.last_backup_label.text = (
            f"Last automatic backup: {format_datetime(last)}" if last else "No automatic backup yet."
        )

    def toggle_auto_backup(self, active):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        app.settings.set("auto_backup_enabled", "1" if active else "0")

    def backup_now(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        try:
            path = app.backup_service.create_backup("manual")
            app.snackbar(f"Backup saved: {os.path.basename(path)}")
        except BackupError as exc:
            app.snackbar(str(exc))

    def show_restore_list(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        backups = app.backup_service.list_backups()
        if not backups:
            app.snackbar("No backups found yet.")
            return

        box = MDBoxLayout(orientation="vertical", size_hint_y=None, spacing="4dp")
        box.bind(minimum_height=box.setter("height"))
        for path in backups[:20]:
            box.add_widget(OneLineListItem(
                text=os.path.basename(path),
                on_release=lambda inst, p=path: self.confirm_restore(p),
            ))

        from kivy.uix.scrollview import ScrollView
        scroller = ScrollView(size_hint_y=None, height="320dp")
        scroller.add_widget(box)

        self._list_dialog = MDDialog(
            title="Choose a Backup to Restore",
            type="custom",
            content_cls=scroller,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *a: self._list_dialog.dismiss())],
        )
        self._list_dialog.open()

    def confirm_restore(self, path):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        if hasattr(self, "_list_dialog"):
            self._list_dialog.dismiss()

        def confirm(*a):
            try:
                app.backup_service.restore_backup(path)
                dialog.dismiss()
                app.snackbar("Backup restored. Reloading data.")
                app.goto("dashboard")
            except BackupError as exc:
                dialog.dismiss()
                app.snackbar(str(exc))

        dialog = MDDialog(
            title="Restore this backup?",
            text=f"Restoring \"{os.path.basename(path)}\" may replace current data.\n\nAre you sure?",
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                     MDRaisedButton(text="RESTORE", md_bg_color=(0.75, 0.2, 0.2, 1), on_release=confirm)],
        )
        dialog.open()

    def show_export_path(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        app.snackbar(f"CSV exports are saved to: {app.export_service.export_dir}")

    def change_pin_dialog(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        current_field = MDTextField(hint_text="Current PIN", password=True, input_filter="int")
        new_field = MDTextField(hint_text="New PIN (4-8 digits)", password=True, input_filter="int")

        box = MDBoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="120dp",
                           padding=("12dp", "8dp"))
        box.add_widget(current_field)
        box.add_widget(new_field)

        def confirm(*a):
            try:
                app.settings.change_pin(current_field.text, new_field.text)
                dialog.dismiss()
                app.snackbar("PIN updated.")
            except ValidationError as exc:
                current_field.error = True
                new_field.error = True
                new_field.helper_text = str(exc)
                new_field.helper_text_mode = "on_error"

        dialog = MDDialog(
            title="Change Admin PIN",
            type="custom",
            content_cls=box,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                     MDRaisedButton(text="SAVE", on_release=confirm)],
        )
        dialog.open()

    def confirm_reset_database(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        field = MDTextField(hint_text='Type "RESET" to confirm')

        def confirm(*a):
            if field.text.strip().upper() != "RESET":
                field.error = True
                field.helper_text = 'Type "RESET" exactly to confirm.'
                field.helper_text_mode = "on_error"
                return
            app.backup_service.create_backup("pre_reset")
            app.reset_database()
            dialog.dismiss()
            app.snackbar("Database reset. A safety backup was saved first.")
            app.goto("dashboard")

        box = MDBoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="130dp",
                           padding=("12dp", "8dp"))
        box.add_widget(MDLabel(
            text="This permanently erases all products, categories, and history.\n"
                 "A safety backup is taken automatically first.",
            theme_text_color="Secondary", size_hint_y=None, height="60dp",
        ))
        box.add_widget(field)

        dialog = MDDialog(
            title="Reset Database?",
            type="custom",
            content_cls=box,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                     MDRaisedButton(text="RESET", md_bg_color=(0.75, 0.2, 0.2, 1), on_release=confirm)],
        )
        dialog.open()
