import json
import time
import requests
import os
import sys

# Configuration
PLAN_FILE = "experiment_plan.json"
API_URL = "http://localhost:5000/ai_command"
POLL_INTERVAL = 2  # Seconds to wait between checking checks or execution loops

def load_plan():
    """Reads the current plan from the JSON file."""
    if not os.path.exists(PLAN_FILE):
        return None
    try:
        with open(PLAN_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading plan: {e}")
        return None

def send_command(command):
    """Sends a command to the Flask API."""
    try:
        payload = {"command": command}
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ Command sent: {command}")
            return True
        else:
            print(f"❌ Failed to send command: {command}. Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection error sending {command}: {e}")
        return False

def execute_step(step):
    """Executes a single step from the plan sequence."""
    action = step.get('action')
    wait_time = step.get('wait_after', 2)
    
    command_map = {
        "move_plant_1": "MOVE:2000,800,10000", # Move only
        "move_plant_2": "MOVE:3000,1500,10000",
        "home": "HOME",
        "water_smart_1": "WATER1",  # Move & Check Water
        "water_smart_2": "WATER2",
        "check_sensor": "SMART:CHECK", # Just check
        "move_z_safe": "MOVE:0,0,0"
    }
    
    command = command_map.get(action)
    
    if command:
        print(f"➡️ Executing action: {action}...")
        send_command(command)
        
        # Determine wait time (dynamic based on action type could be better, but fixed for now)
        print(f"⏳ Waiting {wait_time}s for completion...")
        time.sleep(wait_time)
    else:
        print(f"⚠️ Unknown action: {action}")

def main():
    print("🤖 Experiment Bot Started.")
    print(f"📂 Monitoring {PLAN_FILE} for protocols...")
    
    last_plan_id = None
    current_plan = None
    
    while True:
        # 1. Reload Plan
        new_plan = load_plan()
        
        if new_plan:
            # Check if it's a new plan
            if new_plan.get('id') != last_plan_id:
                print(f"\n🆕 New Protocol Detected: {new_plan.get('title')}")
                print("------------------------------------------------")
                last_plan_id = new_plan.get('id')
                current_plan = new_plan
            
            # Check active status
            is_active = new_plan.get('active', False)
            
            if not is_active:
                print("⏸️ Experiment paused/inactive. Waiting for activation...", end='\r')
                time.sleep(POLL_INTERVAL)
                continue

            # 2. Execute Logic
            if current_plan:
                sequence = current_plan.get('execution_logic', {}).get('sequence', [])
                
                if not sequence:
                    print("⚠️ Plan has no execution sequence.")
                    time.sleep(5)
                    continue
                    
                print(f"\n🔄 Check cycle started at {time.strftime('%H:%M:%S')}")
                for step in sequence:
                    # Re-check active status mid-sequence to allow immediate stop
                    fresh_plan = load_plan()
                    if not fresh_plan or not fresh_plan.get('active', False):
                        print("\n🛑 Experiment stopped by user request.")
                        break
                        
                    execute_step(step)
                
                if not fresh_plan or not fresh_plan.get('active', False):
                    continue

                print("✅ Cycle complete.")
                
                # Parse frequency roughly
                freq = current_plan.get('frequency', 'Continuous')
                if "30 seconds" in freq:
                    time.sleep(30)
                elif "60 seconds" in freq or "minute" in freq:
                    time.sleep(60)
                else:
                    time.sleep(5) # Default fast loop
                    
        else:
            print("💤 No plan found. Waiting...", end='\r')
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user.")
        sys.exit(0)
