"""Category management: add, rename, delete (only when empty)."""

from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import TwoLineListItem

from services.inventory_service import CategoryInUseError
from utils.validation import ValidationError

KV = """
<CategoriesScreen>:
    name: "categories"

    MDFloatLayout:

        MDBoxLayout:
            orientation: "vertical"

            MDBoxLayout:
                size_hint_y: None
                height: "48dp"
                padding: "16dp", "8dp"

                MDLabel:
                    text: "Categories"
                    font_style: "H6"
                    bold: True

            ScrollView:
                MDList:
                    id: category_list

        MDFloatingActionButton:
            icon: "plus"
            pos_hint: {"right": 0.96, "y": 0.04}
            on_release: root.add_category_dialog()
"""
Builder.load_string(KV)


class CategoriesScreen(MDScreen):
    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        categories = app.inventory.list_categories()
        box = self.ids.category_list
        box.clear_widgets()
        for cat in categories:
            item = TwoLineListItem(
                text=cat["name"],
                secondary_text=f"{cat['product_count']} active product(s)",
                on_release=lambda inst, c=cat: self.category_options(c),
            )
            box.add_widget(item)

    def category_options(self, cat):
        dialog = MDDialog(
            title=cat["name"],
            buttons=[
                MDFlatButton(text="RENAME", on_release=lambda *a: (dialog.dismiss(), self.rename_dialog(cat))),
                MDFlatButton(text="DELETE", theme_text_color="Custom", text_color=(0.75, 0.2, 0.2, 1),
                             on_release=lambda *a: (dialog.dismiss(), self.delete_category(cat))),
                MDFlatButton(text="CLOSE", on_release=lambda *a: dialog.dismiss()),
            ],
        )
        dialog.open()

    def add_category_dialog(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        field = MDTextField(hint_text="Category name")

        def confirm(*a):
            try:
                app.inventory.add_category(field.text)
                dialog.dismiss()
                app.snackbar("Category added.")
                self.refresh()
            except ValidationError as exc:
                field.error = True
                field.helper_text = str(exc)
                field.helper_text_mode = "on_error"

        dialog = MDDialog(
            title="Add Category",
            type="custom",
            content_cls=field,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                     MDRaisedButton(text="ADD", on_release=confirm)],
        )
        dialog.open()

    def rename_dialog(self, cat):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        field = MDTextField(hint_text="New category name", text=cat["name"])

        def confirm(*a):
            try:
                app.inventory.rename_category(cat["id"], field.text)
                dialog.dismiss()
                app.snackbar("Category renamed.")
                self.refresh()
            except ValidationError as exc:
                field.error = True
                field.helper_text = str(exc)
                field.helper_text_mode = "on_error"

        dialog = MDDialog(
            title="Rename Category",
            type="custom",
            content_cls=field,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                     MDRaisedButton(text="SAVE", on_release=confirm)],
        )
        dialog.open()

    def delete_category(self, cat):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()

        def confirm(*a):
            try:
                app.inventory.delete_category(cat["id"])
                dialog.dismiss()
                app.snackbar("Category deleted.")
                self.refresh()
            except CategoryInUseError as exc:
                dialog.dismiss()
                app.snackbar(str(exc))

        dialog = MDDialog(
            title="Delete Category?",
            text=f'"{cat["name"]}" will be permanently removed. This only works if it has no products.',
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *a: dialog.dismiss()),
                     MDRaisedButton(text="DELETE", md_bg_color=(0.75, 0.2, 0.2, 1), on_release=confirm)],
        )
        dialog.open()
