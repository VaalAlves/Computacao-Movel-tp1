import flet as ft
import os
import json
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

ENCRYPTION_KEY = os.getenv("TASK_ENCRYPTION_KEY")

cipher = Fernet(ENCRYPTION_KEY.encode())

def encrypt_data(data):
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(data):
    return cipher.decrypt(data.encode()).decode()

class Task(ft.Column):
    def __init__(self, task_name, task_status_change, task_delete):
        super().__init__()
        self.completed = False
        self.task_name = task_name
        self.task_status_change = task_status_change
        self.task_delete = task_delete
        self.display_task = ft.Checkbox(
            value=False, label=self.task_name, on_change=self.status_changed
        )
        self.edit_name = ft.TextField(expand=1)

        self.display_view = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.display_task,
                ft.Row(
                    spacing=0,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.CREATE_OUTLINED,
                            tooltip="Edit To-Do",
                            on_click=self.edit_clicked,
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            tooltip="Delete To-Do",
                            on_click=self.delete_clicked,
                        ),
                    ],
                ),
            ],
        )

        self.edit_view = ft.Row(
            visible=False,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.edit_name,
                ft.IconButton(
                    icon=ft.Icons.DONE_OUTLINE_OUTLINED,
                    icon_color=ft.Colors.GREEN,
                    tooltip="Update To-Do",
                    on_click=self.save_clicked,
                ),
            ],
        )
        self.controls = [self.display_view, self.edit_view]

    def edit_clicked(self, e):
        self.edit_name.value = self.display_task.label
        self.display_view.visible = False
        self.edit_view.visible = True
        self.update()

    def save_clicked(self, e):
        self.task_name = self.edit_name.value
        self.display_task.label = self.task_name
        self.display_view.visible = True
        self.edit_view.visible = False
        self.task_status_change(self)
        self.update()

    def status_changed(self, e):
        self.completed = self.display_task.value
        self.task_status_change(self)

    def delete_clicked(self, e):
        self.task_delete(self)


class TodoApp(ft.Column):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.new_task = ft.TextField(
            hint_text="What needs to be done?", on_submit=self.add_clicked, expand=True
        )
        self.tasks = ft.Column()

        self.filter = ft.Tabs(
            scrollable=False,
            selected_index=0,
            on_change=self.tabs_changed,
            tabs=[ft.Tab(text="all"), ft.Tab(text="active"), ft.Tab(text="completed")],
        )

        self.items_left = ft.Text("0 items left")

        self.width = 600
        self.controls = [
            ft.Row(
                [ft.Text(value="Todos", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    self.new_task,
                    ft.FloatingActionButton(
                        icon=ft.Icons.ADD, on_click=self.add_clicked
                    ),
                ],
            ),
            ft.Column(
                spacing=25,
                controls=[
                    self.filter,
                    self.tasks,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self.items_left,
                            ft.OutlinedButton(
                                text="Clear completed", on_click=self.clear_clicked
                            ),
                        ],
                    )
                ],
            ),
        ]

    def add_clicked(self, e):
        if self.new_task.value:
            task = Task(self.new_task.value, self.task_status_change, self.task_delete)
            self.tasks.controls.append(task)
            self.new_task.value = ""
            self.new_task.focus()
            self.save_tasks(self)
            self.update()

    def task_status_change(self, task):
        self.save_tasks(self)
        self.update()

    def task_delete(self, task):
        self.tasks.controls.remove(task)
        self.save_tasks(self)
        self.update()

    def tabs_changed(self, e):
        self.update()

    def clear_clicked(self, e):
        for task in self.tasks.controls[:]:
            if task.completed:
                self.task_delete(task)

    def before_update(self):
        status = self.filter.tabs[self.filter.selected_index].text
        count = 0
        for task in self.tasks.controls:
            task.visible = (
                status == "all"
                or (status == "active" and task.completed == False)
                or (status == "completed" and task.completed)
            )
            if not task.completed:
                count += 1
        self.items_left.value = f"{count} active item(s) left"
        
    def save_tasks(self, e):
        existing_tasks = self.get_decrypted_tasks()
        
        task_dict = {}
        
        current_task_names = {task.task_name for task in self.tasks.controls}
        
        task_dict = {name: completed for name, completed in existing_tasks.items() if name in current_task_names}

        for task in self.tasks.controls:
            task_dict[task.task_name] = task.completed

        task_json = json.dumps(task_dict)
        encrypted_json = encrypt_data(task_json)

        self.page.client_storage.set("tasks", encrypted_json)

    def get_decrypted_tasks(self):
        existing_tasks = {}
        if self.page.client_storage.get("tasks"):
            encrypted_data = self.page.client_storage.get("tasks")
            decrypted_data = decrypt_data(encrypted_data)
            existing_tasks = json.loads(decrypted_data)
            return existing_tasks

    def load_tasks(self):
        existing_tasks = self.get_decrypted_tasks()
        if existing_tasks:
            for key, value in existing_tasks.items():
                print(f"{key}: {value}")
                task = Task(key, self.task_status_change, self.task_delete)
                task.completed = value
                task.display_task.value = value

                self.tasks.controls.append(task)

        self.update()


def main(page: ft.Page):
    page.title = "ToDo App"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE

    todo_app = TodoApp(page)
    page.add(todo_app)
    todo_app.load_tasks()

ft.app(main)