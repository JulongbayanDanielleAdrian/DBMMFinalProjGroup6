import sqlite3
import os
import csv
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from datetime import datetime


# ---------- Database setup ----------
def init_db():
    conn = sqlite3.connect("medassist.db")
    cursor = conn.cursor()

    # User table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL
    )""")

    # Medicine info table with additional fields
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS med_info (
        med_id INTEGER PRIMARY KEY AUTOINCREMENT,
        med_name TEXT NOT NULL,
        med_type TEXT,
        dosage_form TEXT,
        strength TEXT,
        manufacturer TEXT,
        indication TEXT,
        classification TEXT
    )""")

    # Create a table to track CSV import status
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS csv_import_status (
        filename TEXT PRIMARY KEY,
        last_modified INTEGER
    )""")

    # Schedule table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedule (
        med_id INTEGER,
        consumption_start TEXT,
        consumption_end TEXT,
        frequency TEXT,
        FOREIGN KEY (med_id) REFERENCES med_info(med_id) ON DELETE CASCADE
    )""")

    # Inventory table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        med_id INTEGER,
        quantity INTEGER,
        expiration TEXT,
        FOREIGN KEY (med_id) REFERENCES med_info(med_id) ON DELETE CASCADE
    )""")

    # Import data from CSV if it exists and has been modified
    csv_path = "MEDICINE_UPDate.csv"
    if os.path.exists(csv_path):
        current_mtime = int(os.path.getmtime(csv_path))
        
        # Check if CSV has been modified since last import
        cursor.execute("SELECT last_modified FROM csv_import_status WHERE filename=?", (csv_path,))
        last_import = cursor.fetchone()
        
        if not last_import or last_import[0] < current_mtime:
            print(f"Importing updated CSV file: {csv_path}")
            try:
                # Clear existing medicine data before import
                cursor.execute("DELETE FROM med_info")
                
                with open(csv_path, newline="", encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)  # Skip header row
                    print(f"CSV Headers: {headers}")
                    
                    for row in reader:
                        if row:
                            # Pad row with None values if it's shorter than expected
                            row += [None] * (7 - len(row))
                            try:
                                cursor.execute("""
                                INSERT INTO med_info 
                                (med_name, med_type, dosage_form, strength, manufacturer, indication, classification)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
                            except sqlite3.Error as e:
                                print(f"Error importing medicine row {row}: {e}")
                
                # Update the import status
                cursor.execute("""
                    INSERT OR REPLACE INTO csv_import_status (filename, last_modified)
                    VALUES (?, ?)
                """, (csv_path, current_mtime))
                
                print("CSV import completed successfully")
            except Exception as e:
                print(f"Error during CSV import: {e}")
        else:
            print("CSV file unchanged since last import, skipping...")

    conn.commit()
    conn.close()


def check_csv_file():
    csv_path = "MEDICINE_UPDate.csv"
    if os.path.exists(csv_path):
        print("\nChecking CSV file contents:")
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                print("First few lines of the CSV file:")
                for i, line in enumerate(f):
                    if i < 5:  # Print first 5 lines
                        print(f"Line {i+1}: {line.strip()}")
                    else:
                        break
        except Exception as e:
            print(f"Error reading CSV file: {e}")
    else:
        print(f"\nCSV file not found at: {csv_path}")
        print("Current working directory:", os.getcwd())
        print("Files in current directory:", os.listdir())


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = GridLayout(cols=1, size_hint=(0.4, 0.6), pos_hint={"center_x": 0.5, "center_y": 0.5})

        self.greeting = Label(text="Medicine Management System", font_size="25", color="#00a8f3")
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
        conn = sqlite3.connect("medicine_db.db")
        cursor = conn.cursor()
        username = self.username.text.strip()
        password = self.password.text.strip()
        cursor.execute("SELECT * FROM user WHERE username=? AND password=?", (username, password))
        if cursor.fetchone():
            self.manager.current = "dashboard"
        else:
            self.greeting.text = "Invalid credentials"
        conn.close()

    def register(self, instance):
        conn = sqlite3.connect("medicine_db.db")
        cursor = conn.cursor()
        username = self.username.text.strip()
        password = self.password.text.strip()
        try:
            cursor.execute("INSERT INTO user (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            self.greeting.text = f"Account created! Welcome, {username}!"
        except sqlite3.IntegrityError:
            self.greeting.text = "Username already exists."
        conn.close()


class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", spacing=10, padding=20)
        self.label = Label(text="Welcome!", font_size=24)
        self.layout.add_widget(self.label)
        self.layout.add_widget(
            Button(text="Medicine Management", on_press=lambda x: setattr(self.manager, "current", "medicine")))
        self.layout.add_widget(Button(text="Schedule", on_press=lambda x: setattr(self.manager, "current", "schedule")))
        self.layout.add_widget(
            Button(text="Inventory", on_press=lambda x: setattr(self.manager, "current", "inventory")))
        self.layout.add_widget(Button(text="Logout", on_press=self.logout))
        self.add_widget(self.layout)

    def logout(self, instance):
        self.manager.current = "login"


class BaseCrudScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", spacing=10, padding=20)

        # Header with back button
        header_layout = BoxLayout(orientation="horizontal", size_hint_y=0.1)
        back_btn = Button(text="Back to Dashboard",
                          size_hint_x=0.3,
                          background_color="#666666",
                          on_press=lambda x: setattr(self.manager, "current", "dashboard"))
        self.title_label = Label(text="", font_size=20)
        header_layout.add_widget(back_btn)
        header_layout.add_widget(self.title_label)
        self.layout.add_widget(header_layout)

        # Main content area
        content_layout = BoxLayout(orientation="horizontal", spacing=10)

        # Left side - List view
        self.list_layout = BoxLayout(orientation="vertical", size_hint_x=0.7)
        self.scroll_view = ScrollView()
        self.list_content = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.list_content.bind(minimum_height=self.list_content.setter('height'))
        self.scroll_view.add_widget(self.list_content)
        self.list_layout.add_widget(self.scroll_view)

        # Right side - Controls
        self.controls_layout = BoxLayout(orientation="vertical", size_hint_x=0.3, spacing=10)

        content_layout.add_widget(self.list_layout)
        content_layout.add_widget(self.controls_layout)
        self.layout.add_widget(content_layout)

        self.add_widget(self.layout)

    def refresh_list(self):
        self.list_content.clear_widgets()
        # To be implemented by child classes


class MedicineInfoScreen(BaseCrudScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title_label.text = "Medicine Information"

        # Add input fields
        self.med_id = TextInput(hint_text="Medicine ID (for update/delete)", multiline=False)
        self.med_name = TextInput(hint_text="Medicine Name", multiline=False)
        self.med_type = TextInput(hint_text="Medicine Type", multiline=False)

        # Add buttons
        add_btn = Button(text="Add Medicine", background_color="#00a8f3")
        add_btn.bind(on_press=self.add_medicine)

        update_btn = Button(text="Update Medicine", background_color="#00cc66")
        update_btn.bind(on_press=self.update_medicine)

        delete_btn = Button(text="Delete Medicine", background_color="#ff3333")
        delete_btn.bind(on_press=self.delete_medicine)

        refresh_btn = Button(text="Refresh List", background_color="#666666")
        refresh_btn.bind(on_press=lambda x: self.refresh_list())

        self.controls_layout.add_widget(self.med_id)
        self.controls_layout.add_widget(self.med_name)
        self.controls_layout.add_widget(self.med_type)
        self.controls_layout.add_widget(add_btn)
        self.controls_layout.add_widget(update_btn)
        self.controls_layout.add_widget(delete_btn)
        self.controls_layout.add_widget(refresh_btn)

        self.refresh_list()

    def refresh_list(self):
        self.list_content.clear_widgets()
        conn = sqlite3.connect("medicine_db.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT med_id, med_name, med_type 
            FROM med_info 
            ORDER BY med_name
        """)
        medicines = cursor.fetchall()
        conn.close()

        for med in medicines:
            item = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)
            item.add_widget(Label(
                text=f"ID: {med[0]} | {med[1]} ({med[2]})",
                size_hint_x=1,
                halign='left'
            ))
            self.list_content.add_widget(item)

    def add_medicine(self, instance):
        name = self.med_name.text.strip()
        med_type = self.med_type.text.strip()

        if name and med_type:
            conn = sqlite3.connect("medicine_db.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO med_info (med_name, med_type) VALUES (?, ?)",
                           (name, med_type))
            conn.commit()
            conn.close()
            self.med_id.text = ""
            self.med_name.text = ""
            self.med_type.text = ""
            self.refresh_list()

    def update_medicine(self, instance):
        try:
            med_id = int(self.med_id.text.strip())
            name = self.med_name.text.strip()
            med_type = self.med_type.text.strip()

            if all([med_id, name, med_type]):
                conn = sqlite3.connect("medicine_db.db")
                cursor = conn.cursor()

                # Check if medicine exists
                cursor.execute("SELECT med_id FROM med_info WHERE med_id = ?", (med_id,))
                if cursor.fetchone():
                    cursor.execute("""
                        UPDATE med_info 
                        SET med_name = ?, med_type = ? 
                        WHERE med_id = ?
                    """, (name, med_type, med_id))
                    conn.commit()
                    self.med_id.text = ""
                    self.med_name.text = ""
                    self.med_type.text = ""
                    self.refresh_list()
                else:
                    print(f"Medicine with ID {med_id} not found")
                conn.close()
        except (ValueError, sqlite3.Error) as e:
            print(f"Error updating medicine: {e}")

    def delete_medicine(self, instance):
        try:
            med_id = int(self.med_id.text.strip())

            conn = sqlite3.connect("medicine_db.db")
            cursor = conn.cursor()

            # Check if medicine exists
            cursor.execute("SELECT med_id FROM med_info WHERE med_id = ?", (med_id,))
            if cursor.fetchone():
                # Delete related records in schedule and inventory tables
                cursor.execute("DELETE FROM schedule WHERE med_id = ?", (med_id,))
                cursor.execute("DELETE FROM inventory WHERE med_id = ?", (med_id,))
                # Delete the medicine
                cursor.execute("DELETE FROM med_info WHERE med_id = ?", (med_id,))
                conn.commit()
                self.med_id.text = ""
                self.med_name.text = ""
                self.med_type.text = ""
                self.refresh_list()
            else:
                print(f"Medicine with ID {med_id} not found")
            conn.close()
        except (ValueError, sqlite3.Error) as e:
            print(f"Error deleting medicine: {e}")


class ScheduleScreen(BaseCrudScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title_label.text = "Medicine Schedule"

        # Add input fields
        self.med_id = TextInput(hint_text="Medicine ID", multiline=False)
        self.start_date = TextInput(hint_text="Start Date (YYYY-MM-DD)", multiline=False)
        self.end_date = TextInput(hint_text="End Date (YYYY-MM-DD)", multiline=False)
        self.frequency = TextInput(hint_text="Frequency (e.g., 'Once daily')", multiline=False)

        # Add buttons
        add_btn = Button(text="Add Schedule", background_color="#00a8f3")
        add_btn.bind(on_press=self.add_schedule)

        refresh_btn = Button(text="Refresh List", background_color="#666666")
        refresh_btn.bind(on_press=lambda x: self.refresh_list())

        self.controls_layout.add_widget(self.med_id)
        self.controls_layout.add_widget(self.start_date)
        self.controls_layout.add_widget(self.end_date)
        self.controls_layout.add_widget(self.frequency)
        self.controls_layout.add_widget(add_btn)
        self.controls_layout.add_widget(refresh_btn)

        self.refresh_list()

    def refresh_list(self):
        self.list_content.clear_widgets()
        conn = sqlite3.connect("medicine_db.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.schedule_id, m.med_name, s.consumption_start, s.consumption_end, s.frequency 
            FROM schedule s 
            JOIN med_info m ON s.med_id = m.med_id
            ORDER BY s.consumption_start
        """)
        schedules = cursor.fetchall()
        conn.close()

        for schedule in schedules:
            item = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)
            item.add_widget(Label(
                text=f"Schedule #{schedule[0]} | {schedule[1]}\nFrom {schedule[2]} to {schedule[3]} ({schedule[4]})",
                size_hint_x=1,
                halign='left'
            ))
            self.list_content.add_widget(item)

    def add_schedule(self, instance):
        try:
            med_id = int(self.med_id.text.strip())
            start_date = datetime.strptime(self.start_date.text.strip(), "%Y-%m-%d").date()
            end_date = datetime.strptime(self.end_date.text.strip(), "%Y-%m-%d").date()
            frequency = self.frequency.text.strip()

            if all([med_id, start_date, end_date, frequency]):
                conn = sqlite3.connect("medicine_db.db")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO schedule (med_id, consumption_start, consumption_end, frequency) 
                    VALUES (?, ?, ?, ?)
                """, (med_id, start_date, end_date, frequency))
                conn.commit()
                conn.close()

                self.med_id.text = ""
                self.start_date.text = ""
                self.end_date.text = ""
                self.frequency.text = ""
                self.refresh_list()
        except (ValueError, sqlite3.Error) as e:
            print(f"Error adding schedule: {e}")


class InventoryScreen(BaseCrudScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title_label.text = "Inventory Management"

        # Add input fields
        self.med_id = TextInput(hint_text="Medicine ID", multiline=False)
        self.quantity = TextInput(hint_text="Quantity", multiline=False)
        self.expiration = TextInput(hint_text="Expiration Date (YYYY-MM-DD)", multiline=False)

        # Add buttons
        add_btn = Button(text="Add Inventory", background_color="#00a8f3")
        add_btn.bind(on_press=self.add_inventory)

        refresh_btn = Button(text="Refresh List", background_color="#666666")
        refresh_btn.bind(on_press=lambda x: self.refresh_list())

        self.controls_layout.add_widget(self.med_id)
        self.controls_layout.add_widget(self.quantity)
        self.controls_layout.add_widget(self.expiration)
        self.controls_layout.add_widget(add_btn)
        self.controls_layout.add_widget(refresh_btn)

        self.refresh_list()

    def refresh_list(self):
        self.list_content.clear_widgets()
        conn = sqlite3.connect("medicine_db.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.inventory_id, m.med_name, i.quantity, i.expiration 
            FROM inventory i 
            JOIN med_info m ON i.med_id = m.med_id
            ORDER BY i.expiration
        """)
        inventory_items = cursor.fetchall()
        conn.close()

        for item in inventory_items:
            list_item = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)
            list_item.add_widget(Label(
                text=f"Inventory #{item[0]} | {item[1]} | Quantity: {item[2]} | Expires: {item[3]}",
                size_hint_x=1,
                halign='left'
            ))
            self.list_content.add_widget(list_item)

    def add_inventory(self, instance):
        try:
            med_id = int(self.med_id.text.strip())
            quantity = int(self.quantity.text.strip())
            expiration = datetime.strptime(self.expiration.text.strip(), "%Y-%m-%d").date()

            if all([med_id, quantity, expiration]):
                conn = sqlite3.connect("medicine_db.db")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO inventory (med_id, quantity, expiration) 
                    VALUES (?, ?, ?)
                """, (med_id, quantity, expiration))
                conn.commit()
                conn.close()

                self.med_id.text = ""
                self.quantity.text = ""
                self.expiration.text = ""
                self.refresh_list()
        except (ValueError, sqlite3.Error) as e:
            print(f"Error adding inventory: {e}")


class MedicineScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.page = 1
        self.items_per_page = 10
        self.total_items = 0
        
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        # Main layout for the list and controls
        main_layout = BoxLayout(orientation="horizontal", padding=10, spacing=10)

        # Data layout (list area)
        self.data_layout = BoxLayout(orientation="vertical", size_hint=(0.7, 1))
        
        # Add pagination controls at the top
        pagination_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=5)
        self.prev_btn = Button(text="Previous", size_hint_x=None, width=100)
        self.prev_btn.bind(on_press=lambda x: self.change_page(-1))
        self.next_btn = Button(text="Next", size_hint_x=None, width=100)
        self.next_btn.bind(on_press=lambda x: self.change_page(1))
        self.page_label = Label(text="Page 1")
        
        pagination_layout.add_widget(self.prev_btn)
        pagination_layout.add_widget(self.page_label)
        pagination_layout.add_widget(self.next_btn)
        self.data_layout.add_widget(pagination_layout)
        
        # Create table header
        header_layout = GridLayout(cols=5, size_hint_y=None, height=40)
        headers = ['ID/Name', 'Type/Form', 'Strength', 'Manufacturer', 'Indication/Class']
        for header in headers:
            header_layout.add_widget(
                Label(text=header, bold=True, size_hint_y=None, height=40)
            )
        self.data_layout.add_widget(header_layout)

        # Scroll view for medicine list
        self.scroll_view = ScrollView(size_hint=(1, 1))
        self.list_layout = GridLayout(cols=5, spacing=(10, 5), size_hint_y=None, padding=(5, 5))
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll_view.add_widget(self.list_layout)
        self.data_layout.add_widget(self.scroll_view)

        # Controls layout
        controls_layout = BoxLayout(orientation="vertical", size_hint=(0.3, 1), spacing=10)

        # Input fields
        self.name_input = TextInput(hint_text="Medicine Name", multiline=False)
        self.type_input = TextInput(hint_text="Medicine Type", multiline=False)
        self.dosage_form_input = TextInput(hint_text="Dosage Form", multiline=False)
        self.strength_input = TextInput(hint_text="Strength", multiline=False)
        self.manufacturer_input = TextInput(hint_text="Manufacturer", multiline=False)
        self.indication_input = TextInput(hint_text="Indication", multiline=False)
        self.classification_input = TextInput(hint_text="Classification", multiline=False)

        # Buttons
        refresh_btn = Button(text="Refresh")
        refresh_btn.bind(on_press=self.refresh_medicines)

        add_btn = Button(text="Add Medicine")
        add_btn.bind(on_press=self.add_medicine)

        delete_btn = Button(text="Delete Medicine")
        delete_btn.bind(on_press=self.delete_medicine)

        back_btn = Button(text="Back to Dashboard")
        back_btn.bind(on_press=lambda x: setattr(self.manager, "current", "dashboard"))

        # Add widgets to controls
        for widget in [
            self.name_input, 
            self.type_input,
            self.dosage_form_input,
            self.strength_input,
            self.manufacturer_input,
            self.indication_input,
            self.classification_input,
            refresh_btn,
            add_btn,
            delete_btn,
            back_btn
        ]:
            controls_layout.add_widget(widget)

        # Add layouts to main layout
        main_layout.add_widget(self.data_layout)
        main_layout.add_widget(controls_layout)
        layout.add_widget(main_layout)

        self.add_widget(layout)

    def change_page(self, direction):
        new_page = self.page + direction
        if new_page >= 1 and new_page <= (self.total_items + self.items_per_page - 1) // self.items_per_page:
            self.page = new_page
            self.refresh_medicines()

    def update_pagination_controls(self):
        total_pages = (self.total_items + self.items_per_page - 1) // self.items_per_page
        self.page_label.text = f"Page {self.page} of {total_pages}"
        self.prev_btn.disabled = self.page <= 1
        self.next_btn.disabled = self.page >= total_pages

    def get_total_items(self):
        app = App.get_running_app()
        try:
            app.cursor.execute("SELECT COUNT(*) FROM med_info")
            return app.cursor.fetchone()[0]
        except sqlite3.Error:
            return 0

    def refresh_medicines(self, *args):
        app = App.get_running_app()
        try:
            # Get total count for pagination
            self.total_items = self.get_total_items()
            
            # Calculate offset for current page
            offset = (self.page - 1) * self.items_per_page
            
            app.cursor.execute("""
                SELECT med_id, med_name, med_type, dosage_form, strength, 
                       manufacturer, indication, classification 
                FROM med_info
                ORDER BY med_name
                LIMIT ? OFFSET ?
            """, (self.items_per_page, offset))

            medicines = app.cursor.fetchall()
            
            # Clear previous content
            self.list_layout.clear_widgets()
            
            if not medicines:
                # Add a "No medicines found" message spanning all columns
                self.list_layout.add_widget(
                    Label(text="No medicines found", size_hint_y=None, height=40)
                )
                return

            # Add medicines to the grid
            for med in medicines:
                # Column 1: ID and Name
                self.list_layout.add_widget(
                    Label(
                        text=f"ID: {med[0]}\n{med[1]}", 
                        size_hint_y=None, 
                        height=60,
                        text_size=(None, None),
                        halign='left'
                    )
                )
                
                # Column 2: Type and Form
                type_form = f"Type: {med[2] or 'N/A'}"
                if med[3]:  # dosage_form
                    type_form += f"\nForm: {med[3]}"
                self.list_layout.add_widget(
                    Label(
                        text=type_form,
                        size_hint_y=None,
                        height=60,
                        text_size=(None, None),
                        halign='left'
                    )
                )
                
                # Column 3: Strength
                self.list_layout.add_widget(
                    Label(
                        text=med[4] or "N/A",
                        size_hint_y=None,
                        height=60,
                        text_size=(None, None),
                        halign='left'
                    )
                )
                
                # Column 4: Manufacturer
                self.list_layout.add_widget(
                    Label(
                        text=med[5] or "N/A",
                        size_hint_y=None,
                        height=60,
                        text_size=(None, None),
                        halign='left'
                    )
                )
                
                # Column 5: Indication and Classification
                ind_class = f"Ind: {med[6] or 'N/A'}"
                if med[7]:  # classification
                    ind_class += f"\nClass: {med[7]}"
                self.list_layout.add_widget(
                    Label(
                        text=ind_class,
                        size_hint_y=None,
                        height=60,
                        text_size=(None, None),
                        halign='left'
                    )
                )
            
            # Update pagination controls
            self.update_pagination_controls()
                
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            self.list_layout.clear_widgets()
            self.list_layout.add_widget(
                Label(
                    text=f"Error loading medicines: {str(e)}", 
                    size_hint_y=None, 
                    height=40
                )
            )
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.list_layout.clear_widgets()
            self.list_layout.add_widget(
                Label(
                    text=f"Unexpected error: {str(e)}", 
                    size_hint_y=None, 
                    height=40
                )
            )

    def on_enter(self):
        self.page = 1  # Reset to first page when entering the screen
        self.refresh_medicines()

    def add_medicine(self, instance):
        app = App.get_running_app()
        name = self.name_input.text.strip()
        med_type = self.type_input.text.strip()
        dosage_form = self.dosage_form_input.text.strip() or None
        strength = self.strength_input.text.strip() or None
        manufacturer = self.manufacturer_input.text.strip() or None
        indication = self.indication_input.text.strip() or None
        classification = self.classification_input.text.strip() or None

        if not name:
            self.list_layout.clear_widgets()
            self.list_layout.add_widget(
                Label(
                    text="Medicine name is required!", 
                    size_hint_y=None, 
                    height=40
                )
            )
            return

        try:
            app.cursor.execute("""
                INSERT INTO med_info (med_name, med_type, dosage_form, strength, 
                                    manufacturer, indication, classification)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, med_type, dosage_form, strength, manufacturer,
                  indication, classification))
            app.conn.commit()
            self.refresh_medicines()

            # Clear inputs
            for input_field in [
                self.name_input, self.type_input, self.dosage_form_input,
                self.strength_input, self.manufacturer_input,
                self.indication_input, self.classification_input
            ]:
                input_field.text = ""

        except sqlite3.Error as e:
            self.list_layout.clear_widgets()
            self.list_layout.add_widget(
                Label(
                    text=f"Error adding medicine: {str(e)}", 
                    size_hint_y=None, 
                    height=40
                )
            )

    def delete_medicine(self, instance):
        app = App.get_running_app()
        try:
            med_id = int(self.name_input.text.strip())

            app.cursor.execute("SELECT med_id FROM med_info WHERE med_id = ?", (med_id,))
            if app.cursor.fetchone():
                # Delete related records in schedule and inventory tables
                app.cursor.execute("DELETE FROM schedule WHERE med_id = ?", (med_id,))
                app.cursor.execute("DELETE FROM inventory WHERE med_id = ?", (med_id,))
                # Delete the medicine
                app.cursor.execute("DELETE FROM med_info WHERE med_id = ?", (med_id,))
                app.conn.commit()
                self.name_input.text = ""
                self.type_input.text = ""
                self.dosage_form_input.text = ""
                self.strength_input.text = ""
                self.manufacturer_input.text = ""
                self.indication_input.text = ""
                self.classification_input.text = ""
                self.refresh_medicines()
            else:
                print(f"Medicine with ID {med_id} not found")
        except (ValueError, sqlite3.Error) as e:
            print(f"Error deleting medicine: {e}")


class MedicineApp(App):
    def build(self):
        init_db()
        # clear_all_data() # DEV ONLY FEATURE

        self.conn = sqlite3.connect("medassist.db")
        self.cursor = self.conn.cursor()
        self.username = None

        self.screen_manager = ScreenManager()
        self.screen_manager.add_widget(LoginScreen(name="login"))
        self.screen_manager.add_widget(DashboardScreen(name="dashboard"))
        self.screen_manager.add_widget(MedicineScreen(name="medicine"))
        self.screen_manager.add_widget(ScheduleScreen(name="schedule"))
        self.screen_manager.add_widget(InventoryScreen(name="inventory"))

        return self.screen_manager

    def on_stop(self):
        self.conn.close()


if __name__ == "__main__":
    MedicineApp().run()
