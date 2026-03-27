import sqlite3
import datetime
import os

DB_NAME = "experiments.db"

def get_db_path():
    # Force DB to be in the same folder as this script (frontend/)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "experiments.db")

def init_db():
    """Initializes the database table structure."""
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    
    # 1. Experiments Table
    c.execute('''CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'ACTIVE'
                )''')

    # 2. Readings Table (Moisture & Actions)
    c.execute('''CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id INTEGER,
                    plant_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    moisture_value INTEGER,
                    action_taken TEXT,
                    img_path TEXT
                )''')
                
    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {get_db_path()}")

def log_reading(experiment_id, plant_id, moisture, action, img_path=None):
    """Logs a single sensor reading or action."""
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("INSERT INTO readings (experiment_id, plant_id, moisture_value, action_taken, img_path) VALUES (?, ?, ?, ?, ?)",
              (experiment_id, plant_id, moisture, action, img_path))
    conn.commit()
    conn.close()

def get_latest_readings(limit=10):
    """Fetches recent readings for the dashboard."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM readings ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    # Test Log
    log_reading(1, "TEST_PLANT", 500, "WATERED")
    print("Test reading logged.")
