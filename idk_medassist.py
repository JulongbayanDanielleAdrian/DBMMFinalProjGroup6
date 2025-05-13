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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        name TEXT PRIMARY KEY,
        category TEXT,
        dosage_form TEXT,
        strength TEXT,
        manufacturer TEXT,
        indication TEXT,
        classification TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        name TEXT PRIMARY KEY
    )""")

    if os.path.exists("MEDICINE_UPDate.csv"):
        with open("MEDICINE_UPDate.csv", newline="", encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            for row in reader:
                if row:
                    row += [None] * (7 - len(row))
                    try:
                        cursor.execute("""
                        INSERT OR IGNORE INTO medicines (name, category, dosage_form, strength, manufacturer, indication, classification)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, row[:7])
                    except sqlite3.Error as e:
                        print("Insert error:", e)

    if os.path.exists("patients.csv"):
        with open("patients.csv", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            for row in reader:
                if row:
                    cursor.execute("INSERT OR IGNORE INTO patients (name) VALUES (?)", (row[0],))

    conn.commit()
    conn.close()

def clear_all_data():
    conn = sqlite3.connect("medassist.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM medicines")
    cursor.execute("DELETE FROM patients")
    conn.commit()
    conn.close()

def add_item(table, name):
    conn = sqlite3.connect("medassist.db")
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def get_items(table):
    conn = sqlite3.connect("medassist.db")
    cursor = conn.cursor()
    if table == "medicines":
        cursor.execute("SELECT name, category, dosage_form, strength, manufacturer FROM medicines LIMIT 100")
    else:
        cursor.execute(f"SELECT name FROM {table} LIMIT 100")
    items = cursor.fetchall()
    conn.close()
    return items

def get_item_by_name(table, name):
    conn = sqlite3.connect("medassist.db")
    cursor = conn.cursor()
    if table == "medicines":
        cursor.execute("SELECT name, category, dosage_form, strength, manufacturer FROM medicines WHERE name=?", (name,))
    else:
        cursor.execute(f"SELECT name FROM {table} WHERE name=?", (name,))
    item = cursor.fetchone()
    conn.close()
    return item

def update_item(table, old_name, new_name):
    conn = sqlite3.connect("medassist.db")
    cursor = conn.cursor()
    cursor.execute(f"UPDATE {table} SET name=? WHERE name=?", (new_name, old_name))
    conn.commit()
    conn.close()

def delete_item(table, name):
    conn = sqlite3.connect("medassist.db")
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table} WHERE name=?", (name,))
    conn.commit()
    conn.close()

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
        layout = BoxLayout(orientation="horizontal", padding=10, spacing=10)

        self.data_layout = BoxLayout(orientation="vertical", size_hint=(0.7, 1))
        self.scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, do_scroll_x=True, do_scroll_y=True)
        self.display = Label(size_hint_y=None, text=f"{table.capitalize()} List:", markup=True)
        self.display.bind(texture_size=lambda instance, size: setattr(self.display, 'height', size[1]))
        self.scroll_view.add_widget(self.display)
        self.data_layout.add_widget(self.scroll_view)

        controls_layout = BoxLayout(orientation="vertical", size_hint=(0.3, 1), spacing=10)
        self.input_name = TextInput(hint_text=f"{table[:-1].capitalize()} Name", multiline=False)

        refresh_btn = Button(text="Refresh")
        refresh_btn.bind(on_press=self.load_items)

        display_btn = Button(text="Display Selected Name")
        display_btn.bind(on_press=self.display_selected_name)

        add_btn = Button(text=f"Add {table[:-1].capitalize()}")
        add_btn.bind(on_press=self.add_item)

        update_btn = Button(text=f"Update {table[:-1].capitalize()}")
        update_btn.bind(on_press=self.update_item)

        delete_btn = Button(text=f"Delete {table[:-1].capitalize()}")
        delete_btn.bind(on_press=self.delete_item)

        back_btn = Button(text="Back to Dashboard")
        back_btn.bind(on_press=lambda x: setattr(self.manager, "current", "dashboard"))

        controls_layout.add_widget(refresh_btn)
        controls_layout.add_widget(display_btn)
        controls_layout.add_widget(self.input_name)
        controls_layout.add_widget(add_btn)
        controls_layout.add_widget(update_btn)
        controls_layout.add_widget(delete_btn)
        controls_layout.add_widget(back_btn)

        layout.add_widget(self.data_layout)
        layout.add_widget(controls_layout)
        self.add_widget(layout)

    def load_items(self, instance):
        items = get_items(self.table)
        self.display.text = f"{self.table.capitalize()} List:\n" + "\n".join(f"{i[0]}" for i in items)

    def display_selected_name(self, instance):
        name = self.input_name.text.strip()
        item = get_item_by_name(self.table, name)
        if item:
            self.display.text = f"Selected {self.table[:-1].capitalize()}:\n{item[0]}"
        else:
            self.display.text = "Item not found."

    def add_item(self, instance):
        name = self.input_name.text.strip()
        if name:
            add_item(self.table, name)
            self.load_items(instance)

    def update_item(self, instance):
        name = self.input_name.text.strip()
        new_name = self.input_name.text.strip()
        if name and new_name:
            update_item(self.table, name, new_name)
            self.load_items(instance)

    def delete_item(self, instance):
        name = self.input_name.text.strip()
        if name:
            delete_item(self.table, name)
            self.load_items(instance)

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

    def on_stop(self):
        self.conn.close()

if __name__ == "__main__":
    MedAssistApp().run()
