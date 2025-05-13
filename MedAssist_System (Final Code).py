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
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.uix.widget import Widget

# Set default window size
Window.size = (1600, 900)

# ---------- Database setup ----------
def init_db():
    try:
        # Create database file if it doesn't exist
        conn = sqlite3.connect("medassist.db")
        cursor = conn.cursor()

        # Enable foreign key support
        cursor.execute("PRAGMA foreign_keys = ON")

        print("Creating database tables if they don't exist...")

        # User table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )""")
        print("User table checked/created")

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
        print("Medicine info table checked/created")

        # Create a table to track CSV import status
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS csv_import_status (
            filename TEXT PRIMARY KEY,
            last_modified INTEGER
        )""")
        print("CSV import status table checked/created")

        # Schedule table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            med_id INTEGER,
            consumption_start TEXT,
            consumption_end TEXT,
            frequency TEXT,
            FOREIGN KEY (med_id) REFERENCES med_info(med_id) ON DELETE CASCADE
        )""")
        print("Schedule table checked/created")

        # Inventory table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            med_id INTEGER,
            quantity INTEGER,
            expiration TEXT,
            FOREIGN KEY (med_id) REFERENCES med_info(med_id) ON DELETE CASCADE
        )""")
        print("Inventory table checked/created")

        # Verify tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Existing tables:", [table[0] for table in tables])

        # Import data from CSV if it exists and has been modified
        csv_path = "medicine.csv"
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
        else:
            print(f"CSV file not found at: {csv_path}")

        conn.commit()
        print("Database initialization completed successfully")

    except sqlite3.Error as e:
        print(f"SQLite error during database initialization: {e}")
        # Attempt to create tables individually if there was an error
        try:
            for table_name in ["user", "med_info", "schedule", "inventory"]:
                cursor.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
                print(f"Table {table_name} exists and is accessible")
        except sqlite3.Error as table_error:
            print(f"Error checking table {table_name}: {table_error}")
    except Exception as e:
        print(f"Unexpected error during database initialization: {e}")
    finally:
        try:
            conn.close()
            print("Database connection closed")
        except Exception as e:
            print(f"Error closing database connection: {e}")

# Function to check database integrity
def check_database():
    try:
        conn = sqlite3.connect("medassist.db")
        cursor = conn.cursor()

        # Check all tables
        tables = ["user", "med_info", "schedule", "inventory", "csv_import_status"]
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"Table {table} exists and contains {count} records")
            except sqlite3.Error as e:
                print(f"Error checking table {table}: {e}")

        conn.close()
    except Exception as e:
        print(f"Error checking database: {e}")

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
        conn = sqlite3.connect("medassist.db")
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
        conn = sqlite3.connect("medassist.db")
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
        layout = BoxLayout(orientation="vertical", spacing=20, padding=30)

        # Header
        header = Label(
            text="Medicine Management Dashboard",
            font_size=32,
            color=(0, 0.6, 1, 1),  # Light blue
            size_hint_y=0.2
        )
        layout.add_widget(header)

        # Welcome message
        self.welcome_label = Label(
            text="Welcome!",
            font_size=24,
            color=(0.2, 0.8, 0.2, 1),  # Green
            size_hint_y=0.1
        )
        layout.add_widget(self.welcome_label)

        # Buttons grid
        buttons_layout = GridLayout(
            cols=2,
            spacing=20,
            size_hint_y=0.6,
            padding=[20, 20]
        )

        # Create styled buttons
        med_btn = Button(
            text="Medicine\nManagement",
            background_color=(0, 0.6, 1, 1),  # Light blue
            font_size=20,
            halign='center',
            valign='middle'
        )
        med_btn.bind(on_press=lambda x: setattr(self.manager, "current", "medicine"))

        schedule_btn = Button(
            text="Schedule\nManagement",
            background_color=(0, 0.8, 0, 1),  # Green
            font_size=20,
            halign='center',
            valign='middle'
        )
        schedule_btn.bind(on_press=lambda x: setattr(self.manager, "current", "schedule"))

        inventory_btn = Button(
            text="Inventory\nManagement",
            background_color=(1, 0.6, 0, 1),  # Orange
            font_size=20,
            halign='center',
            valign='middle'
        )
        inventory_btn.bind(on_press=lambda x: setattr(self.manager, "current", "inventory"))

        logout_btn = Button(
            text="Logout",
            background_color=(0.8, 0.2, 0.2, 1),  # Red
            font_size=20,
            halign='center',
            valign='middle'
        )
        logout_btn.bind(on_press=self.logout)

        # Add buttons to grid
        for btn in [med_btn, schedule_btn, inventory_btn, logout_btn]:
            buttons_layout.add_widget(btn)

        layout.add_widget(buttons_layout)
        self.add_widget(layout)

    def update_welcome(self, username):
        self.welcome_label.text = f"Welcome, {username}!"

    def logout(self, instance):
        app = App.get_running_app()
        app.username = None
        app.screen_manager.current = "login"
        app.screen_manager.get_screen("login").username.text = ""
        app.screen_manager.get_screen("login").password.text = ""
        app.screen_manager.get_screen("login").greeting.text = "Welcome to MedAssist!!"


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
        conn = sqlite3.connect("medassist.db")
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
            conn = sqlite3.connect("medassist.db")
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
                conn = sqlite3.connect("medassist.db")
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

            conn = sqlite3.connect("medassist.db")
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
        self.med_id = TextInput(hint_text="Medicine ID (required)", multiline=False)
        self.start_date = TextInput(hint_text="Start Date (YYYY-MM-DD)", multiline=False)
        self.end_date = TextInput(hint_text="End Date (YYYY-MM-DD)", multiline=False)
        self.frequency = TextInput(hint_text="Frequency (e.g., 'Once daily')", multiline=False)
        
        # Add field for schedule ID (for update/delete)
        self.schedule_id = TextInput(
            hint_text="Schedule ID (for update/delete)",
            multiline=False,
            size_hint_y=None,
            height=40
        )
        
        # Add status label for messages
        self.status_label = Label(
            text="",
            color=(1, 0, 0, 1),  # Red for errors
            size_hint_y=None,
            height=30
        )

        # Add buttons
        add_btn = Button(
            text="Add Schedule",
            background_color=(0, 0.7, 0, 1),  # Green
            size_hint_y=None,
            height=40
        )
        add_btn.bind(on_press=self.add_schedule)
        
        load_btn = Button(
            text="Load Schedule",
            background_color=(0.3, 0.5, 0.9, 1),  # Light blue
            size_hint_y=None,
            height=40
        )
        load_btn.bind(on_press=self.load_schedule)
        
        update_btn = Button(
            text="Update Schedule",
            background_color=(0, 0.6, 1, 1),  # Blue
            size_hint_y=None,
            height=40
        )
        update_btn.bind(on_press=self.update_schedule)
        
        delete_btn = Button(
            text="Delete Schedule",
            background_color=(0.8, 0.2, 0.2, 1),  # Red
            size_hint_y=None,
            height=40
        )
        delete_btn.bind(on_press=self.delete_schedule)
        
        refresh_btn = Button(
            text="Refresh List",
            background_color=(0.5, 0.5, 0.5, 1),  # Gray
            size_hint_y=None,
            height=40
        )
        refresh_btn.bind(on_press=lambda x: self.refresh_list())
        
        # Add fields and buttons to controls layout
        self.controls_layout.add_widget(Label(
            text="Add/Update Schedule",
            bold=True,
            size_hint_y=None,
            height=30
        ))
        self.controls_layout.add_widget(self.med_id)
        self.controls_layout.add_widget(self.start_date)
        self.controls_layout.add_widget(self.end_date)
        self.controls_layout.add_widget(self.frequency)
        self.controls_layout.add_widget(Widget(size_hint_y=None, height=20))  # Spacer
        
        self.controls_layout.add_widget(Label(
            text="Schedule ID for Update/Delete",
            bold=True,
            size_hint_y=None,
            height=30
        ))
        self.controls_layout.add_widget(self.schedule_id)
        self.controls_layout.add_widget(Widget(size_hint_y=None, height=10))  # Spacer
        
        self.controls_layout.add_widget(add_btn)
        self.controls_layout.add_widget(load_btn)
        self.controls_layout.add_widget(update_btn)
        self.controls_layout.add_widget(delete_btn)
        self.controls_layout.add_widget(refresh_btn)
        self.controls_layout.add_widget(self.status_label)

    def show_error(self, message):
        """Display error message"""
        self.status_label.text = message
        self.status_label.color = (1, 0, 0, 1)  # Red

    def show_success(self, message):
        """Display success message"""
        self.status_label.text = message
        self.status_label.color = (0, 0.8, 0, 1)  # Green

    def validate_schedule(self):
        """Validate schedule input fields"""
        errors = []
        
        # Validate Medicine ID
        if not self.med_id.text.strip():
            errors.append("Medicine ID is required")
        elif not self.med_id.text.strip().isdigit():
            errors.append("Medicine ID must be a number")
            
        # Validate dates
        try:
            if self.start_date.text.strip():
                datetime.strptime(self.start_date.text.strip(), "%Y-%m-%d")
            else:
                errors.append("Start date is required")
        except ValueError:
            errors.append("Invalid start date format (use YYYY-MM-DD)")
            
        try:
            if self.end_date.text.strip():
                datetime.strptime(self.end_date.text.strip(), "%Y-%m-%d")
            else:
                errors.append("End date is required")
        except ValueError:
            errors.append("Invalid end date format (use YYYY-MM-DD)")
            
        # Validate frequency
        if not self.frequency.text.strip():
            errors.append("Frequency is required")
            
        return errors

    def load_schedule(self, instance):
        """Load schedule data for updating"""
        try:
            schedule_id = self.schedule_id.text.strip()
            
            if not schedule_id:
                self.show_error("Please enter a Schedule ID to load")
                return
                
            if not schedule_id.isdigit():
                self.show_error("Schedule ID must be a number")
                return
                
            app = App.get_running_app()
            app.cursor.execute("""
                SELECT med_id, consumption_start, consumption_end, frequency
                FROM schedule WHERE schedule_id = ?
            """, (schedule_id,))
            
            result = app.cursor.fetchone()
            if not result:
                self.show_error(f"No schedule found with ID {schedule_id}")
                return
                
            # Populate input fields
            self.med_id.text = str(result[0])
            self.start_date.text = result[1]
            self.end_date.text = result[2]
            self.frequency.text = result[3]
            
            self.show_success(f"Loaded schedule data for ID {schedule_id}")
            
        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except Exception as e:
            self.show_error(f"Error loading schedule: {str(e)}")

    def update_schedule(self, instance):
        """Update existing schedule"""
        try:
            schedule_id = self.schedule_id.text.strip()
            
            if not schedule_id:
                self.show_error("Please enter a Schedule ID to update")
                return
                
            if not schedule_id.isdigit():
                self.show_error("Schedule ID must be a number")
                return
                
            # Validate inputs
            errors = self.validate_schedule()
            if errors:
                self.show_error("\n".join(errors))
                return
                
            med_id = self.med_id.text.strip()
            start_date = self.start_date.text.strip()
            end_date = self.end_date.text.strip()
            frequency = self.frequency.text.strip()
            
            app = App.get_running_app()
            
            # Check if schedule exists
            app.cursor.execute("SELECT schedule_id FROM schedule WHERE schedule_id = ?", (schedule_id,))
            if not app.cursor.fetchone():
                self.show_error(f"No schedule found with ID {schedule_id}")
                return
                
            # Check if medicine exists
            app.cursor.execute("SELECT med_id FROM med_info WHERE med_id = ?", (med_id,))
            if not app.cursor.fetchone():
                self.show_error(f"Medicine with ID {med_id} does not exist")
                return
            
            # Update the schedule
            app.cursor.execute("""
                UPDATE schedule SET
                    med_id = ?,
                    consumption_start = ?,
                    consumption_end = ?,
                    frequency = ?
                WHERE schedule_id = ?
            """, (med_id, start_date, end_date, frequency, schedule_id))
            app.conn.commit()
            
            # Clear inputs
            self.schedule_id.text = ""
            self.med_id.text = ""
            self.start_date.text = ""
            self.end_date.text = ""
            self.frequency.text = ""
            
            self.show_success(f"Successfully updated schedule {schedule_id}")
            self.refresh_list()
            
        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except Exception as e:
            self.show_error(f"Error updating schedule: {str(e)}")

    def delete_schedule(self, instance):
        """Delete existing schedule"""
        try:
            schedule_id = self.schedule_id.text.strip()
            
            if not schedule_id:
                self.show_error("Please enter a Schedule ID to delete")
                return
                
            if not schedule_id.isdigit():
                self.show_error("Schedule ID must be a number")
                return
                
            app = App.get_running_app()
            
            # Check if schedule exists
            app.cursor.execute("SELECT schedule_id FROM schedule WHERE schedule_id = ?", (schedule_id,))
            if not app.cursor.fetchone():
                self.show_error(f"No schedule found with ID {schedule_id}")
                return
            
            # Delete the schedule
            app.cursor.execute("DELETE FROM schedule WHERE schedule_id = ?", (schedule_id,))
            app.conn.commit()
            
            # Clear inputs
            self.schedule_id.text = ""
            self.med_id.text = ""
            self.start_date.text = ""
            self.end_date.text = ""
            self.frequency.text = ""
            
            self.show_success(f"Successfully deleted schedule {schedule_id}")
            self.refresh_list()
            
        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except Exception as e:
            self.show_error(f"Error deleting schedule: {str(e)}")

    def refresh_list(self):
        """Refresh the schedule list"""
        self.list_content.clear_widgets()
        try:
            conn = sqlite3.connect("medassist.db")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.schedule_id, m.med_name, s.consumption_start, s.consumption_end, s.frequency 
                FROM schedule s 
                JOIN med_info m ON s.med_id = m.med_id
                ORDER BY s.consumption_start
            """)
            schedules = cursor.fetchall()
            conn.close()

            if not schedules:
                self.list_content.add_widget(Label(
                    text="No schedules found",
                    size_hint_y=None,
                    height=40
                ))
                return

            for schedule in schedules:
                item = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)
                item.add_widget(Label(
                    text=f"ID: {schedule[0]} | Medicine: {schedule[1]}\nFrom {schedule[2]} to {schedule[3]} ({schedule[4]})",
                    size_hint_x=1,
                    halign='left'
                ))
                self.list_content.add_widget(item)

        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
            
    def add_schedule(self, instance):
        """Add new schedule"""
        try:
            # Validate inputs
            errors = self.validate_schedule()
            if errors:
                self.show_error("\n".join(errors))
                return
                
            med_id = self.med_id.text.strip()
            start_date = self.start_date.text.strip()
            end_date = self.end_date.text.strip()
            frequency = self.frequency.text.strip()
            
            app = App.get_running_app()
            
            # Check if medicine exists
            app.cursor.execute("SELECT med_id FROM med_info WHERE med_id = ?", (med_id,))
            if not app.cursor.fetchone():
                self.show_error(f"Medicine with ID {med_id} does not exist")
                return
            
            # Add the schedule
            app.cursor.execute("""
                INSERT INTO schedule (med_id, consumption_start, consumption_end, frequency)
                VALUES (?, ?, ?, ?)
            """, (med_id, start_date, end_date, frequency))
            app.conn.commit()
            
            # Clear inputs
            self.med_id.text = ""
            self.start_date.text = ""
            self.end_date.text = ""
            self.frequency.text = ""
            
            self.show_success("Successfully added new schedule")
            self.refresh_list()
            
        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except Exception as e:
            self.show_error(f"Error adding schedule: {str(e)}")


class InventoryScreen(BaseCrudScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title_label.text = "Inventory Management"
        
        # Add input fields
        self.med_id = TextInput(hint_text="Medicine ID (required)", multiline=False)
        self.quantity = TextInput(hint_text="Quantity (required)", multiline=False)
        self.expiration = TextInput(hint_text="Expiration Date (YYYY-MM-DD)", multiline=False)
        
        # Add field for inventory ID (for update/delete)
        self.inventory_id = TextInput(
            hint_text="Inventory ID (for update/delete)",
            multiline=False,
            size_hint_y=None,
            height=40
        )
        
        # Add status label for messages
        self.status_label = Label(
            text="",
            color=(1, 0, 0, 1),  # Red for errors
            size_hint_y=None,
            height=30
        )

        # Add buttons
        add_btn = Button(
            text="Add Inventory",
            background_color=(0, 0.7, 0, 1),  # Green
            size_hint_y=None,
            height=40
        )
        add_btn.bind(on_press=self.add_inventory)
        
        load_btn = Button(
            text="Load Inventory",
            background_color=(0.3, 0.5, 0.9, 1),  # Light blue
            size_hint_y=None,
            height=40
        )
        load_btn.bind(on_press=self.load_inventory)
        
        update_btn = Button(
            text="Update Inventory",
            background_color=(0, 0.6, 1, 1),  # Blue
            size_hint_y=None,
            height=40
        )
        update_btn.bind(on_press=self.update_inventory)
        
        delete_btn = Button(
            text="Delete Inventory",
            background_color=(0.8, 0.2, 0.2, 1),  # Red
            size_hint_y=None,
            height=40
        )
        delete_btn.bind(on_press=self.delete_inventory)
        
        refresh_btn = Button(
            text="Refresh List",
            background_color=(0.5, 0.5, 0.5, 1),  # Gray
            size_hint_y=None,
            height=40
        )
        refresh_btn.bind(on_press=lambda x: self.refresh_list())
        
        # Add fields and buttons to controls layout
        self.controls_layout.add_widget(Label(
            text="Add/Update Inventory",
            bold=True,
            size_hint_y=None,
            height=30
        ))
        self.controls_layout.add_widget(self.med_id)
        self.controls_layout.add_widget(self.quantity)
        self.controls_layout.add_widget(self.expiration)
        self.controls_layout.add_widget(Widget(size_hint_y=None, height=20))  # Spacer
        
        self.controls_layout.add_widget(Label(
            text="Inventory ID for Update/Delete",
            bold=True,
            size_hint_y=None,
            height=30
        ))
        self.controls_layout.add_widget(self.inventory_id)
        self.controls_layout.add_widget(Widget(size_hint_y=None, height=10))  # Spacer
        
        self.controls_layout.add_widget(add_btn)
        self.controls_layout.add_widget(load_btn)
        self.controls_layout.add_widget(update_btn)
        self.controls_layout.add_widget(delete_btn)
        self.controls_layout.add_widget(refresh_btn)
        self.controls_layout.add_widget(self.status_label)

    def show_error(self, message):
        """Display error message"""
        self.status_label.text = message
        self.status_label.color = (1, 0, 0, 1)  # Red

    def show_success(self, message):
        """Display success message"""
        self.status_label.text = message
        self.status_label.color = (0, 0.8, 0, 1)  # Green

    def validate_inventory(self):
        """Validate inventory input fields"""
        errors = []
        
        # Validate Medicine ID
        if not self.med_id.text.strip():
            errors.append("Medicine ID is required")
        elif not self.med_id.text.strip().isdigit():
            errors.append("Medicine ID must be a number")
            
        # Validate quantity
        if not self.quantity.text.strip():
            errors.append("Quantity is required")
        elif not self.quantity.text.strip().isdigit():
            errors.append("Quantity must be a number")
        elif int(self.quantity.text.strip()) < 0:
            errors.append("Quantity cannot be negative")
            
        # Validate expiration date
        try:
            if self.expiration.text.strip():
                expiration_date = datetime.strptime(self.expiration.text.strip(), "%Y-%m-%d").date()
                if expiration_date < datetime.now().date():
                    errors.append("Expiration date cannot be in the past")
            else:
                errors.append("Expiration date is required")
        except ValueError:
            errors.append("Invalid expiration date format (use YYYY-MM-DD)")
            
        return errors

    def load_inventory(self, instance):
        """Load inventory data for updating"""
        try:
            inventory_id = self.inventory_id.text.strip()
            
            if not inventory_id:
                self.show_error("Please enter an Inventory ID to load")
                return
                
            if not inventory_id.isdigit():
                self.show_error("Inventory ID must be a number")
                return
                
            app = App.get_running_app()
            app.cursor.execute("""
                SELECT med_id, quantity, expiration
                FROM inventory WHERE inventory_id = ?
            """, (inventory_id,))
            
            result = app.cursor.fetchone()
            if not result:
                self.show_error(f"No inventory found with ID {inventory_id}")
                return
                
            # Populate input fields
            self.med_id.text = str(result[0])
            self.quantity.text = str(result[1])
            self.expiration.text = result[2]
            
            self.show_success(f"Loaded inventory data for ID {inventory_id}")
            
        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except Exception as e:
            self.show_error(f"Error loading inventory: {str(e)}")

    def update_inventory(self, instance):
        """Update existing inventory"""
        try:
            inventory_id = self.inventory_id.text.strip()
            
            if not inventory_id:
                self.show_error("Please enter an Inventory ID to update")
                return
                
            if not inventory_id.isdigit():
                self.show_error("Inventory ID must be a number")
                return
                
            # Validate inputs
            errors = self.validate_inventory()
            if errors:
                self.show_error("\n".join(errors))
                return
                
            med_id = self.med_id.text.strip()
            quantity = self.quantity.text.strip()
            expiration = self.expiration.text.strip()
            
            app = App.get_running_app()
            
            # Check if inventory exists
            app.cursor.execute("SELECT inventory_id FROM inventory WHERE inventory_id = ?", (inventory_id,))
            if not app.cursor.fetchone():
                self.show_error(f"No inventory found with ID {inventory_id}")
                return
                
            # Check if medicine exists
            app.cursor.execute("SELECT med_id FROM med_info WHERE med_id = ?", (med_id,))
            if not app.cursor.fetchone():
                self.show_error(f"Medicine with ID {med_id} does not exist")
                return
            
            # Update the inventory
            app.cursor.execute("""
                UPDATE inventory SET
                    med_id = ?,
                    quantity = ?,
                    expiration = ?
                WHERE inventory_id = ?
            """, (med_id, quantity, expiration, inventory_id))
            app.conn.commit()
            
            # Clear inputs
            self.inventory_id.text = ""
            self.med_id.text = ""
            self.quantity.text = ""
            self.expiration.text = ""
            
            self.show_success(f"Successfully updated inventory {inventory_id}")
            self.refresh_list()
            
        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except Exception as e:
            self.show_error(f"Error updating inventory: {str(e)}")

    def delete_inventory(self, instance):
        """Delete existing inventory"""
        try:
            inventory_id = self.inventory_id.text.strip()
            
            if not inventory_id:
                self.show_error("Please enter an Inventory ID to delete")
                return
                
            if not inventory_id.isdigit():
                self.show_error("Inventory ID must be a number")
                return
                
            app = App.get_running_app()
            
            # Check if inventory exists
            app.cursor.execute("SELECT inventory_id FROM inventory WHERE inventory_id = ?", (inventory_id,))
            if not app.cursor.fetchone():
                self.show_error(f"No inventory found with ID {inventory_id}")
                return
            
            # Delete the inventory
            app.cursor.execute("DELETE FROM inventory WHERE inventory_id = ?", (inventory_id,))
            app.conn.commit()
            
            # Clear inputs
            self.inventory_id.text = ""
            self.med_id.text = ""
            self.quantity.text = ""
            self.expiration.text = ""
            
            self.show_success(f"Successfully deleted inventory {inventory_id}")
            self.refresh_list()
            
        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except Exception as e:
            self.show_error(f"Error deleting inventory: {str(e)}")

    def refresh_list(self):
        """Refresh the inventory list"""
        self.list_content.clear_widgets()
        try:
            conn = sqlite3.connect("medassist.db")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.inventory_id, m.med_name, i.quantity, i.expiration 
                FROM inventory i 
                JOIN med_info m ON i.med_id = m.med_id
                ORDER BY i.expiration
            """)
            inventory_items = cursor.fetchall()
            conn.close()

            if not inventory_items:
                self.list_content.add_widget(Label(
                    text="No inventory items found",
                    size_hint_y=None,
                    height=40
                ))
                return

            for item in inventory_items:
                list_item = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)
                list_item.add_widget(Label(
                    text=f"ID: {item[0]} | Medicine: {item[1]} | Quantity: {item[2]} | Expires: {item[3]}",
                    size_hint_x=1,
                    halign='left'
                ))
                self.list_content.add_widget(list_item)

        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
            
    def add_inventory(self, instance):
        """Add new inventory"""
        try:
            # Validate inputs
            errors = self.validate_inventory()
            if errors:
                self.show_error("\n".join(errors))
                return
                
            med_id = self.med_id.text.strip()
            quantity = self.quantity.text.strip()
            expiration = self.expiration.text.strip()
            
            app = App.get_running_app()
            
            # Check if medicine exists
            app.cursor.execute("SELECT med_id FROM med_info WHERE med_id = ?", (med_id,))
            if not app.cursor.fetchone():
                self.show_error(f"Medicine with ID {med_id} does not exist")
                return
            
            # Add the inventory
            app.cursor.execute("""
                INSERT INTO inventory (med_id, quantity, expiration)
                VALUES (?, ?, ?)
            """, (med_id, quantity, expiration))
            app.conn.commit()
            
            # Clear inputs
            self.med_id.text = ""
            self.quantity.text = ""
            self.expiration.text = ""
            
            self.show_success("Successfully added new inventory")
            self.refresh_list()
            
        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except Exception as e:
            self.show_error(f"Error adding inventory: {str(e)}")


class MedicineScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.page = 1
        self.items_per_page = 10
        self.total_items = 0
        self.search_query = ""
        
        # Create input fields for adding medicine
        self.name_input = TextInput(hint_text="Enter name (required)", multiline=False)
        self.type_input = TextInput(hint_text="Enter type (required)", multiline=False)
        self.dosage_form_input = TextInput(hint_text="Enter form (optional)", multiline=False)
        self.strength_input = TextInput(hint_text="Enter strength (optional)", multiline=False)
        self.manufacturer_input = TextInput(hint_text="Enter manufacturer (optional)", multiline=False)
        self.indication_input = TextInput(hint_text="Enter indication (optional)", multiline=False)
        self.classification_input = TextInput(hint_text="Enter classification (optional)", multiline=False)
        
        # Create field for deleting medicine
        self.med_id_input = TextInput(
            hint_text="Enter Medicine ID to delete",
            multiline=False,
            size_hint_y=None,
            height=40
        )
        
        # Add status label for error messages
        self.status_label = Label(
            text="",
            color=(1, 0, 0, 1),  # Red for errors
            size_hint_y=None,
            height=30
        )

        layout = BoxLayout(orientation="vertical", padding=15, spacing=10)

        # Header
        header = Label(
            text="Medicine Information Management",
            font_size=28,
            color=(0, 0.6, 1, 1),  # Light blue
            size_hint_y=None,
            height=50
        )
        layout.add_widget(header)

        # Main layout for the list and controls
        main_layout = BoxLayout(orientation="horizontal", padding=10, spacing=15)

        # Data layout (list area)
        self.data_layout = BoxLayout(
            orientation="vertical",
            size_hint=(0.7, 1),
            padding=10
        )
        with self.data_layout.canvas.before:
            Color(0.95, 0.95, 0.95, 1)  # Light gray background
            self.data_layout.rect = Rectangle(pos=self.data_layout.pos, size=self.data_layout.size)
        self.data_layout.bind(pos=self._update_rect, size=self._update_rect)

        # Add search box and button at the top
        search_layout = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=40,
            spacing=10,
            padding=[0, 5]
        )
        
        self.search_input = TextInput(
            hint_text="Search medicines...",
            multiline=False,
            size_hint=(0.7, None),
            height=40
        )
        self.search_input.bind(text=self.on_search_text)
        
        search_btn = Button(
            text="Search",
            size_hint=(0.15, None),
            height=40,
            background_color=(0.3, 0.5, 0.9, 1)  # Blue
        )
        search_btn.bind(on_press=self.on_search)
        
        clear_btn = Button(
            text="Clear",
            size_hint=(0.15, None),
            height=40,
            background_color=(0.7, 0.7, 0.7, 1)  # Gray
        )
        clear_btn.bind(on_press=self.clear_search)
        
        search_layout.add_widget(self.search_input)
        search_layout.add_widget(search_btn)
        search_layout.add_widget(clear_btn)
        self.data_layout.add_widget(search_layout)

        # Add pagination controls at the top
        pagination_layout = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=40,
            spacing=10,
            padding=[0, 5]
        )
        
        self.prev_btn = Button(
            text="Previous",
            size_hint_x=None,
            width=100,
            background_color=(0.3, 0.5, 0.9, 1)  # Blue
        )
        self.prev_btn.bind(on_press=lambda x: self.change_page(-1))
        
        self.next_btn = Button(
            text="Next",
            size_hint_x=None,
            width=100,
            background_color=(0.3, 0.5, 0.9, 1)  # Blue
        )
        self.next_btn.bind(on_press=lambda x: self.change_page(1))
        
        self.page_label = Label(
            text="Page 1",
            color=(0.2, 0.2, 0.2, 1)  # Dark gray
        )
        
        pagination_layout.add_widget(self.prev_btn)
        pagination_layout.add_widget(self.page_label)
        pagination_layout.add_widget(self.next_btn)
        self.data_layout.add_widget(pagination_layout)

        # Create table header
        header_layout = GridLayout(
            cols=5,
            size_hint_y=None,
            height=40,
            spacing=(2, 0)
        )
        headers = ['ID/Name', 'Type/Form', 'Strength', 'Manufacturer', 'Indication/Class']
        for header_text in headers:
            header_label = Label(
                text=header_text,
                bold=True,
                size_hint_y=None,
                height=40,
                color=(0.2, 0.2, 0.2, 1)  # Dark gray
            )
            with header_label.canvas.before:
                Color(0.85, 0.85, 0.85, 1)  # Header background
                header_label.rect = Rectangle(pos=header_label.pos, size=header_label.size)
            header_label.bind(pos=self._update_rect, size=self._update_rect)
            header_layout.add_widget(header_label)
        self.data_layout.add_widget(header_layout)

        # Scroll view for medicine list
        self.scroll_view = ScrollView(size_hint=(1, 1))
        self.list_layout = GridLayout(
            cols=5,
            spacing=(2, 2),
            size_hint_y=None,
            padding=(5, 5)
        )
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll_view.add_widget(self.list_layout)
        self.data_layout.add_widget(self.scroll_view)

        # Controls layout with sections
        controls_layout = BoxLayout(
            orientation="vertical",
            size_hint=(0.3, 1),
            spacing=10,
            padding=10
        )
        with controls_layout.canvas.before:
            Color(0.9, 0.9, 0.9, 1)  # Light gray background
            controls_layout.rect = Rectangle(pos=controls_layout.pos, size=controls_layout.size)
        controls_layout.bind(pos=self._update_rect, size=self._update_rect)

        # Add Medicine Section
        add_section = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        add_section.add_widget(Label(
            text="Add New Medicine",
            bold=True,
            size_hint_y=None,
            height=30,
            color=(0, 0.6, 0, 1)  # Green
        ))

        # Input fields with labels
        input_fields = [
            ("Medicine Name", self.name_input),
            ("Medicine Type", self.type_input),
            ("Dosage Form", self.dosage_form_input),
            ("Strength", self.strength_input),
            ("Manufacturer", self.manufacturer_input),
            ("Indication", self.indication_input),
            ("Classification", self.classification_input)
        ]

        for label_text, input_widget in input_fields:
            field_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=60)
            field_layout.add_widget(Label(
                text=label_text,
                size_hint_y=None,
                height=20,
                color=(0.2, 0.2, 0.2, 1)  # Dark gray
            ))
            field_layout.add_widget(input_widget)
            add_section.add_widget(field_layout)

        add_btn = Button(
            text="Add Medicine",
            background_color=(0, 0.7, 0, 1),  # Green
            size_hint_y=None,
            height=40
        )
        add_btn.bind(on_press=self.add_medicine)
        add_section.add_widget(add_btn)
        
        # Update Medicine Section
        update_section = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None, height=120)
        update_section.add_widget(Label(
            text="Update Medicine",
            bold=True,
            size_hint_y=None,
            height=30,
            color=(0, 0.6, 1, 1)  # Blue
        ))
        
        # Add ID field for update
        self.update_id_input = TextInput(
            hint_text="Enter Medicine ID to update",
            multiline=False,
            size_hint_y=None,
            height=40
        )
        update_section.add_widget(self.update_id_input)
        
        update_btn_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=40,
            spacing=5
        )
        
        load_btn = Button(
            text="Load Data",
            background_color=(0.3, 0.5, 0.9, 1),  # Light blue
            size_hint_x=0.5
        )
        load_btn.bind(on_press=self.load_medicine_data)
        
        update_btn = Button(
            text="Update",
            background_color=(0, 0.6, 1, 1),  # Blue
            size_hint_x=0.5
        )
        update_btn.bind(on_press=self.update_medicine)
        
        update_btn_layout.add_widget(load_btn)
        update_btn_layout.add_widget(update_btn)
        update_section.add_widget(update_btn_layout)
        
        # Delete Medicine Section
        delete_section = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None, height=120)
        delete_section.add_widget(Label(
            text="Delete Medicine",
            bold=True,
            size_hint_y=None,
            height=30,
            color=(0.8, 0, 0, 1)  # Red
        ))
        delete_section.add_widget(self.med_id_input)
        delete_btn = Button(
            text="Delete Medicine",
            background_color=(0.8, 0.2, 0.2, 1),  # Red
            size_hint_y=None,
            height=40
        )
        delete_btn.bind(on_press=self.delete_medicine)
        delete_section.add_widget(delete_btn)

        # Add sections to controls layout
        controls_layout.add_widget(add_section)
        controls_layout.add_widget(Widget(size_hint_y=None, height=20))  # Spacer
        controls_layout.add_widget(update_section)
        controls_layout.add_widget(Widget(size_hint_y=None, height=20))  # Spacer
        controls_layout.add_widget(delete_section)
        controls_layout.add_widget(self.status_label)
        
        # Back to Dashboard button at the bottom
        back_btn = Button(
            text="Back to Dashboard",
            background_color=(0.5, 0.5, 0.5, 1),  # Gray
            size_hint_y=None,
            height=40
        )
        back_btn.bind(on_press=lambda x: setattr(self.manager, "current", "dashboard"))
        controls_layout.add_widget(back_btn)

        # Add layouts to main layout
        main_layout.add_widget(self.data_layout)
        main_layout.add_widget(controls_layout)
        layout.add_widget(main_layout)

        self.add_widget(layout)

    def _update_rect(self, instance, value):
        """Update the Rectangle position and size when the widget changes."""
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size

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

    def on_search_text(self, instance, value):
        """Handle search input changes"""
        self.search_query = value.strip()
        self.page = 1  # Reset to first page when search changes
        self.refresh_medicines()

    def on_search(self, instance):
        """Handle search button press"""
        self.page = 1  # Reset to first page when searching
        self.refresh_medicines()

    def clear_search(self, instance):
        """Clear search and reset display"""
        self.search_input.text = ""
        self.search_query = ""
        self.page = 1
        self.refresh_medicines()

    def get_total_items(self):
        app = App.get_running_app()
        try:
            query = "SELECT COUNT(*) FROM med_info"
            params = []
            
            if self.search_query:
                query = """
                    SELECT COUNT(*) FROM med_info 
                    WHERE med_name LIKE ? OR med_type LIKE ? OR 
                          dosage_form LIKE ? OR strength LIKE ? OR 
                          manufacturer LIKE ? OR indication LIKE ? OR 
                          classification LIKE ?
                """
                search_param = f"%{self.search_query}%"
                params = [search_param] * 7
            
            app.cursor.execute(query, params)
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
            
            # Base query
            query = """
                SELECT med_id, med_name, med_type, dosage_form, strength, 
                       manufacturer, indication, classification 
                FROM med_info
            """
            params = []
            
            # Add search condition if there's a search query
            if self.search_query:
                query += """
                    WHERE med_name LIKE ? OR med_type LIKE ? OR 
                          dosage_form LIKE ? OR strength LIKE ? OR 
                          manufacturer LIKE ? OR indication LIKE ? OR 
                          classification LIKE ?
                """
                search_param = f"%{self.search_query}%"
                params = [search_param] * 7
            
            # Add ordering and pagination
            query += " ORDER BY med_name LIMIT ? OFFSET ?"
            params.extend([self.items_per_page, offset])
            
            app.cursor.execute(query, params)
            medicines = app.cursor.fetchall()
            
            # Clear previous content
            self.list_layout.clear_widgets()
            
            if not medicines:
                # Add a "No medicines found" message spanning all columns
                self.list_layout.add_widget(
                    Label(
                        text="No medicines found" if self.search_query else "No medicines in database",
                        size_hint_y=None,
                        height=40,
                        color=(0, 0, 0, 1)  # Black text
                    )
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
                        halign='left',
                        color=(0, 0, 0, 1)  # Black text
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
                        halign='left',
                        color=(0, 0, 0, 1)  # Black text
                    )
                )

                # Column 3: Strength
                self.list_layout.add_widget(
                    Label(
                        text=med[4] or "N/A",
                        size_hint_y=None,
                        height=60,
                        text_size=(None, None),
                        halign='left',
                        color=(0, 0, 0, 1)  # Black text
                    )
                )

                # Column 4: Manufacturer
                self.list_layout.add_widget(
                    Label(
                        text=med[5] or "N/A",
                        size_hint_y=None,
                        height=60,
                        text_size=(None, None),
                        halign='left',
                        color=(0, 0, 0, 1)  # Black text
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
                        halign='left',
                        color=(0, 0, 0, 1)  # Black text
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
                    height=40,
                    color=(0, 0, 0, 1)  # Black text
                )
            )
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.list_layout.clear_widgets()
            self.list_layout.add_widget(
                Label(
                    text=f"Unexpected error: {str(e)}",
                    size_hint_y=None,
                    height=40,
                    color=(0, 0, 0, 1)  # Black text
                )
            )

    def on_enter(self):
        self.page = 1  # Reset to first page when entering the screen
        self.refresh_medicines()

    def show_error(self, message):
        """Display error message to user"""
        self.status_label.text = message
        self.status_label.color = (1, 0, 0, 1)  # Red for errors
        
    def show_success(self, message):
        """Display success message to user"""
        self.status_label.text = message
        self.status_label.color = (0, 0.8, 0, 1)  # Green for success

    def validate_inputs(self, operation="add"):
        """Validate input fields based on operation type"""
        errors = []
        
        if operation == "add":
            # Required fields
            if not self.name_input.text.strip():
                errors.append("Medicine name is required")
            if not self.type_input.text.strip():
                errors.append("Medicine type is required")
                
            # Length validations
            if len(self.name_input.text) > 100:
                errors.append("Medicine name must be less than 100 characters")
            if len(self.type_input.text) > 50:
                errors.append("Medicine type must be less than 50 characters")
                
            # Optional field validations
            if self.strength_input.text.strip():
                # Check if strength contains valid numeric characters and units
                strength = self.strength_input.text.strip()
                if not any(char.isdigit() for char in strength):
                    errors.append("Strength must contain at least one number")
                    
            if self.dosage_form_input.text.strip() and len(self.dosage_form_input.text) > 50:
                errors.append("Dosage form must be less than 50 characters")
                
        elif operation == "delete":
            # Validate medicine ID
            try:
                med_id = self.med_id_input.text.strip()  # Use med_id_input instead of name_input
                if not med_id:
                    errors.append("Medicine ID is required for deletion")
                elif not med_id.isdigit():
                    errors.append("Medicine ID must be a number")
            except ValueError:
                errors.append("Invalid Medicine ID format")
                
        return errors

    def add_medicine(self, instance):
        try:
            # Clear previous status
            self.show_error("")
            
            # Validate inputs
            errors = self.validate_inputs("add")
            if errors:
                self.show_error("\n".join(errors))
                return
                
            name = self.name_input.text.strip()
            med_type = self.type_input.text.strip()
            dosage_form = self.dosage_form_input.text.strip() or None
            strength = self.strength_input.text.strip() or None
            manufacturer = self.manufacturer_input.text.strip() or None
            indication = self.indication_input.text.strip() or None
            classification = self.classification_input.text.strip() or None

            app = App.get_running_app()
            
            # Check if medicine with same name already exists
            app.cursor.execute("SELECT med_id FROM med_info WHERE med_name = ?", (name,))
            if app.cursor.fetchone():
                self.show_error(f"Medicine with name '{name}' already exists")
                return

            # Insert new medicine
            app.cursor.execute("""
                INSERT INTO med_info (
                    med_name, med_type, dosage_form, strength,
                    manufacturer, indication, classification
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, med_type, dosage_form, strength,
                  manufacturer, indication, classification))
            app.conn.commit()

            # Clear inputs on success
            for input_field in [
                self.name_input, self.type_input, self.dosage_form_input,
                self.strength_input, self.manufacturer_input,
                self.indication_input, self.classification_input
            ]:
                input_field.text = ""

            self.show_success(f"Successfully added medicine: {name}")
            self.refresh_medicines()

        except sqlite3.IntegrityError as e:
            self.show_error(f"Database error: Medicine could not be added (duplicate entry)")
        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except Exception as e:
            self.show_error(f"Unexpected error: {str(e)}")

    def delete_medicine(self, instance):
        try:
            # Clear previous status
            self.show_error("")
            
            # Validate inputs
            errors = self.validate_inputs("delete")
            if errors:
                self.show_error("\n".join(errors))
                return

            med_id = self.med_id_input.text.strip()  # Use med_id_input instead of name_input

            app = App.get_running_app()
            
            # Check if medicine exists and get its name
            app.cursor.execute("SELECT med_name FROM med_info WHERE med_id = ?", (med_id,))
            result = app.cursor.fetchone()
            if not result:
                self.show_error(f"Medicine with ID {med_id} not found")
                return
                
            med_name = result[0]

            # Check if medicine is referenced in schedules or inventory
            app.cursor.execute("SELECT COUNT(*) FROM schedule WHERE med_id = ?", (med_id,))
            schedule_count = app.cursor.fetchone()[0]
            
            app.cursor.execute("SELECT COUNT(*) FROM inventory WHERE med_id = ?", (med_id,))
            inventory_count = app.cursor.fetchone()[0]
            
            if schedule_count > 0 or inventory_count > 0:
                warning = f"Warning: This medicine has {schedule_count} schedule(s) and {inventory_count} inventory record(s).\n"
                warning += "These related records will also be deleted.\nProceeding with deletion..."
                self.show_error(warning)
                
            # Delete the medicine and related records
            app.cursor.execute("DELETE FROM schedule WHERE med_id = ?", (med_id,))
            app.cursor.execute("DELETE FROM inventory WHERE med_id = ?", (med_id,))
            app.cursor.execute("DELETE FROM med_info WHERE med_id = ?", (med_id,))
            app.conn.commit()

            # Clear inputs
            self.med_id_input.text = ""  # Clear only the med_id_input
            
            self.show_success(f"Successfully deleted medicine: {med_name}")
            self.refresh_medicines()

        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except ValueError as e:
            self.show_error(f"Invalid input: {str(e)}")
        except Exception as e:
            self.show_error(f"Unexpected error: {str(e)}")

    def load_medicine_data(self, instance):
        """Load medicine data into input fields for updating"""
        try:
            med_id = self.update_id_input.text.strip()
            
            if not med_id:
                self.show_error("Please enter a Medicine ID to load")
                return
                
            if not med_id.isdigit():
                self.show_error("Medicine ID must be a number")
                return
                
            app = App.get_running_app()
            app.cursor.execute("""
                SELECT med_name, med_type, dosage_form, strength,
                       manufacturer, indication, classification
                FROM med_info WHERE med_id = ?
            """, (med_id,))
            
            result = app.cursor.fetchone()
            if not result:
                self.show_error(f"No medicine found with ID {med_id}")
                return
                
            # Populate input fields with existing data
            self.name_input.text = result[0] or ""
            self.type_input.text = result[1] or ""
            self.dosage_form_input.text = result[2] or ""
            self.strength_input.text = result[3] or ""
            self.manufacturer_input.text = result[4] or ""
            self.indication_input.text = result[5] or ""
            self.classification_input.text = result[6] or ""
            
            self.show_success(f"Loaded data for medicine ID {med_id}")
            
        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except Exception as e:
            self.show_error(f"Error loading medicine data: {str(e)}")

    def update_medicine(self, instance):
        """Update existing medicine record"""
        try:
            # Clear previous status
            self.show_error("")
            
            # Get the medicine ID
            med_id = self.update_id_input.text.strip()
            if not med_id:
                self.show_error("Please enter a Medicine ID to update")
                return
                
            if not med_id.isdigit():
                self.show_error("Medicine ID must be a number")
                return
            
            # Validate inputs
            errors = self.validate_inputs("add")  # Reuse add validation
            if errors:
                self.show_error("\n".join(errors))
                return
                
            name = self.name_input.text.strip()
            med_type = self.type_input.text.strip()
            dosage_form = self.dosage_form_input.text.strip() or None
            strength = self.strength_input.text.strip() or None
            manufacturer = self.manufacturer_input.text.strip() or None
            indication = self.indication_input.text.strip() or None
            classification = self.classification_input.text.strip() or None

            app = App.get_running_app()
            
            # Check if medicine exists
            app.cursor.execute("SELECT med_id FROM med_info WHERE med_id = ?", (med_id,))
            if not app.cursor.fetchone():
                self.show_error(f"No medicine found with ID {med_id}")
                return
            
            # Check if new name conflicts with existing medicine (excluding current record)
            app.cursor.execute("SELECT med_id FROM med_info WHERE med_name = ? AND med_id != ?", (name, med_id))
            if app.cursor.fetchone():
                self.show_error(f"Another medicine with name '{name}' already exists")
                return

            # Update the medicine
            app.cursor.execute("""
                UPDATE med_info SET
                    med_name = ?, med_type = ?, dosage_form = ?,
                    strength = ?, manufacturer = ?, indication = ?,
                    classification = ?
                WHERE med_id = ?
            """, (name, med_type, dosage_form, strength,
                  manufacturer, indication, classification, med_id))
            app.conn.commit()

            # Clear inputs
            self.update_id_input.text = ""
            self.name_input.text = ""
            self.type_input.text = ""
            self.dosage_form_input.text = ""
            self.strength_input.text = ""
            self.manufacturer_input.text = ""
            self.indication_input.text = ""
            self.classification_input.text = ""

            self.show_success(f"Successfully updated medicine: {name}")
            self.refresh_medicines()

        except sqlite3.Error as e:
            self.show_error(f"Database error: {str(e)}")
        except Exception as e:
            self.show_error(f"Error updating medicine: {str(e)}")


class MedicineApp(App):
    def build(self):
        # Initialize and check database
        init_db()
        check_database()

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
    # haha 2003'rd line my birth year
