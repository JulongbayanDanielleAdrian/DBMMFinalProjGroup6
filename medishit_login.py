import sqlite3
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget


# Screen for login/register
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = GridLayout(cols=1, size_hint=(0.4, 0.6), pos_hint={"center_x": 0.5, "center_y": 0.5})
        self.add_widget(layout)

        layout.add_widget(Image(source="MediShit.png"))

        self.greeting = Label(text="Welcome to MediSh*t!", font_size="25", color="#00a8f3")
        layout.add_widget(self.greeting)

        self.username = TextInput(hint_text="Username", multiline=False, padding_y=(10, 10), size_hint=(1, 0.5))
        layout.add_widget(self.username)

        self.password = TextInput(hint_text="Password", multiline=False, password=True,
                                  padding_y=(10, 10), size_hint=(1, 0.5))
        layout.add_widget(self.password)

        layout.add_widget(Widget(size_hint_y=None, height=20))

        # Register and Login Buttons
        btn_layout = GridLayout(cols=2, size_hint=(1, 0.5))
        self.login_btn = Button(text="Login", bold=True, background_color="#00a8f3")
        self.login_btn.bind(on_press=self.login)

        self.register_btn = Button(text="Register", bold=True, background_color="#00cc66")
        self.register_btn.bind(on_press=self.register)

        btn_layout.add_widget(self.login_btn)
        btn_layout.add_widget(self.register_btn)
        layout.add_widget(btn_layout)

    def login(self, instance):
        username = self.username.text.strip()
        password = self.password.text.strip()
        app = App.get_running_app()

        if not username or not password:
            self.greeting.text = "Please fill in all fields."
            return

        app.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = app.cursor.fetchone()

        if user and user[1] == password:
            self.greeting.text = f"Welcome, {username}!"
            app.screen_manager.current = 'success'
        else:
            self.greeting.text = "Invalid username or password."

    def register(self, instance):
        username = self.username.text.strip()
        password = self.password.text.strip()
        app = App.get_running_app()

        if not username or not password:
            self.greeting.text = "Please fill in all fields."
            return

        app.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if app.cursor.fetchone():
            self.greeting.text = "Username already exists."
        else:
            app.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            app.conn.commit()
            self.greeting.text = f"Account created! Welcome, {username}!"


# Success screen after login
class SuccessScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = GridLayout(cols=1, spacing=10, size_hint=(0.3, 0.3), pos_hint={"center_x": 0.5, "center_y": 0.5})
        self.add_widget(layout)

        self.message = Label(text="You have successfully logged in!", font_size=20)
        layout.add_widget(self.message)

        return_btn = Button(text="Return", size_hint=(1, 0.5), background_color="#f39c12")
        return_btn.bind(on_press=self.go_back)
        layout.add_widget(return_btn)

    def go_back(self, instance):
        App.get_running_app().screen_manager.transition.direction = 'right'
        App.get_running_app().screen_manager.current = 'login'


class MediShit(App):
    def build(self):
        self.create_db()

        self.screen_manager = ScreenManager()

        self.login_screen = LoginScreen(name='login')
        self.success_screen = SuccessScreen(name='success')

        self.screen_manager.add_widget(self.login_screen)
        self.screen_manager.add_widget(self.success_screen)

        return self.screen_manager

    def create_db(self):
        self.conn = sqlite3.connect("users.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        """)
        self.conn.commit()


if __name__ == "__main__":
    MediShit().run()