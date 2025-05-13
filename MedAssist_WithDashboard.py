import sqlite3
import csv
import os
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView

# ---------- Database setup ----------
def init_db():
    conn = sqlite3.connect("medassist.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS medicines (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS patients (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()

    # Load data from CSVs if available
    if os.path.exists("medicines.csv"):
        with open("medicines.csv", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    cursor.execute("INSERT OR IGNORE INTO medicines (id, name) VALUES (?, ?)", (int(row[0]), row[1]))

    if os.path.exists("patients.csv"):
        with open("patients.csv", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    cursor.execute("INSERT OR IGNORE INTO patients (id, name) VALUES (?, ?)", (int(row[0]), row[1]))

    conn.commit()
    conn.close()

# ---------- CRUD Functions ----------
def add_item(table, name):
    conn = sqlite3.connect("medassist.db")
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def get_items(table):
    conn = sqlite3.connect("medassist.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT id, name FROM {table}")
    items = cursor.fetchall()
    conn.close()
    return items

def update_item(table, item_id, name):
    conn = sqlite3.connect("medassist.db")
    cursor = conn.cursor()
    cursor.execute(f"UPDATE {table} SET name=? WHERE id=?", (name, item_id))
    conn.commit()
    conn.close()

def delete_item(table, item_id):
    conn = sqlite3.connect("medassist.db")
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

# ---------- Screens ----------
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = GridLayout(cols=1, size_hint=(0.4, 0.6), pos_hint={"center_x": 0.5, "center_y": 0.5})
        layout.add_widget(Image(source="MedAssist.png"))

        self.greeting = Label(text="Welcome to MedAssist!!", font_size="25", color="#00a8f3")
        layout.add_widget(self.greeting)

        self.username = TextInput(hint_text="Username", multiline=False)
        self.password = TextInput(hint_text="Password", multiline=False, password=True)
        layout.add_widget(self.username)
        layout.add_widget(self.password)

        btn_layout = GridLayout(cols=2, size_hint_y=None, height=50)
        login_btn = Button(text="Login", background_color="#00a8f3")
        login_btn.bind(on_press=self.login)
        register_btn = Button(text="Register", background_color="#00cc66")
        register_btn.bind(on_press=self.register)
        btn_layout.add_widget(login_btn)
        btn_layout.add_widget(register_btn)

        layout.add_widget(btn_layout)
        self.add_widget(layout)

    def login(self, instance):
        app = App.get_running_app()
        username = self.username.text.strip()
        password = self.password.text.strip()
        app.cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        if app.cursor.fetchone():
            app.username = username
            app.screen_manager.get_screen("dashboard").update_welcome(username)
            app.screen_manager.current = "dashboard"
        else:
            self.greeting.text = "Invalid credentials"

    def register(self, instance):
        app = App.get_running_app()
        username = self.username.text.strip()
        password = self.password.text.strip()
        try:
            app.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            app.conn.commit()
            self.greeting.text = f"Account created! Welcome, {username}!"
        except sqlite3.IntegrityError:
            self.greeting.text = "Username already exists."

class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", spacing=10, padding=20)
        self.label = Label(text="Welcome!", font_size=24)
        self.layout.add_widget(self.label)
        self.layout.add_widget(Button(text="Medicine", on_press=lambda x: setattr(self.manager, "current", "medicine")))
        self.layout.add_widget(Button(text="Patients", on_press=lambda x: setattr(self.manager, "current", "patients")))
        self.add_widget(self.layout)

    def update_welcome(self, username):
        self.label.text = f"Welcome, {username}!"

class CrudScreen(Screen):
    def __init__(self, name, table, **kwargs):
        super().__init__(name=name, **kwargs)
        self.table = table
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        scroll_view = ScrollView(size_hint=(1, 0.5))
        self.display = Label(size_hint_y=None, text=f"{table.capitalize()} List:", markup=True)
        self.display.bind(texture_size=lambda instance, size: setattr(self.display, 'height', size[1]))
        scroll_view.add_widget(self.display)

        self.input_id = TextInput(hint_text="ID (for update/delete)", multiline=False)
        self.input_name = TextInput(hint_text=f"{table[:-1].capitalize()} Name", multiline=False)

        layout.add_widget(scroll_view)
        layout.add_widget(Button(text="Refresh", on_press=self.load_items))
        layout.add_widget(self.input_id)
        layout.add_widget(self.input_name)
        layout.add_widget(Button(text=f"Add {table[:-1].capitalize()}", on_press=self.add_item))
        layout.add_widget(Button(text=f"Update {table[:-1].capitalize()}", on_press=self.update_item))
        layout.add_widget(Button(text=f"Delete {table[:-1].capitalize()}", on_press=self.delete_item))
        layout.add_widget(Button(text="Back to Dashboard", on_press=lambda x: setattr(self.manager, "current", "dashboard")))

        self.add_widget(layout)

    def load_items(self, instance):
        items = get_items(self.table)
        self.display.text = f"{self.table.capitalize()} List:\n" + "\n".join(f"{i[0]}: {i[1]}" for i in items)

    def add_item(self, instance):
        name = self.input_name.text.strip()
        if name:
            add_item(self.table, name)
            self.load_items(instance)

    def update_item(self, instance):
        try:
            item_id = int(self.input_id.text)
            name = self.input_name.text.strip()
            update_item(self.table, item_id, name)
            self.load_items(instance)
        except:
            pass

    def delete_item(self, instance):
        try:
            item_id = int(self.input_id.text)
            delete_item(self.table, item_id)
            self.load_items(instance)
        except:
            pass

class MedAssistApp(App):
    def build(self):
        init_db()
        self.conn = sqlite3.connect("medassist.db")
        self.cursor = self.conn.cursor()
        self.username = ""

        self.screen_manager = ScreenManager()
        self.screen_manager.add_widget(LoginScreen(name="login"))
        self.screen_manager.add_widget(DashboardScreen(name="dashboard"))
        self.screen_manager.add_widget(CrudScreen(name="medicine", table="medicines"))
        self.screen_manager.add_widget(CrudScreen(name="patients", table="patients"))

        return self.screen_manager

if __name__ == "__main__":
    MedAssistApp().run()
