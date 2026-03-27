import sqlite3
import os

# Always look in frontend/experiments.db
DB_PATH = os.path.join("frontend", "experiments.db")

if not os.path.exists(DB_PATH):
    print(f"❌ {DB_PATH} not found! Did you run app.py?")
    # Try absolute path just in case
    if os.path.exists(r"d:\hackathon\frontend\experiments.db"):
        DB_PATH = r"d:\hackathon\frontend\experiments.db"
    else:
        exit()

print(f"📂 Opening database: {DB_PATH}")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("\n--- 📊 DATA IN MEMORY (readings table) ---")
try:
    c.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    if not rows:
        print("Empty table. No readings logged yet.")
    for row in rows:
        # id, exp_id, plant, time, value, action, img
        print(f"✅ ID: {row[0]} | Time: {row[3]} | Moisture: {row[4]} | Action: {row[5]}")
except Exception as e:
    print(f"Error reading DB: {e}")

conn.close()
print("\n------------------------------------------")
