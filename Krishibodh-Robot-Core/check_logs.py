import os

# Paths to check
paths = ["logs.txt", "frontend/logs.txt"]

found = False
print("\n--- 📄 CHECKING TEXT LOGS ---")
for p in paths:
    if os.path.exists(p):
        found = True
        print(f"Reading {p}...")
        print("------------------------------------------------")
        with open(p, "r") as f:
            print(f.read())
        print("------------------------------------------------")

if not found:
    print("❌ No 'logs.txt' found yet. Move the robot to generate data!")
