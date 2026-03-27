import json
import time
import requests
import os
from datetime import datetime
from camera_utils import CameraHandler

CONFIG_FILE = "experiment_config.json"

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def send_command(base_url, command):
    """Sends a command to the Flask API."""
    url = f"{base_url}/ai_command"
    try:
        response = requests.post(url, json={"command": command})
        if response.status_code == 200:
            print(f"✅ Success: {command} -> {response.json().get('message')}")
            return True
        else:
            print(f"❌ Error: {command} -> {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return False

def run_experiment_cycle(config, camera, cycle_count):
    print(f"\n--- Starting Cycle {cycle_count} ---")
    base_url = config['api_url']
    
    for plant in config['plants']:
        plant_id = plant['id']
        print(f"\nProcessing {plant_id}...")
        
        # 1. Move to Camera Position (Z=0)
        # We use explicit MOVE: command to ensure no watering happens
        move_cmd = f"MOVE:{plant['coordinates_move']}"
        if send_command(base_url, move_cmd):
            # Wait for movement to complete (estimate)
            time.sleep(5) 
            
            # 2. Take Photo
            if config['camera_enabled']:
                print(f"📸 Capturing image for {plant_id}...")
                camera.capture_image(plant_id, f"cycle_{cycle_count}")
        
        # 3. Move to Irrigation Position (Z=Low)
        water_pos_cmd = f"MOVE:{plant['coordinates_water']}"
        send_command(base_url, water_pos_cmd)
        time.sleep(5) # Wait for movement
        
        # 4. Execute Irrigation Strategy
        if plant['mode'] == 'smart':
            # Smart Check - Arduino decides based on moisture
            send_command(base_url, plant['command_check'])
            
        elif plant['mode'] == 'fixed':
            # Fixed Interval - Check if this cycle matches the interval
            interval = plant.get('water_every_n_cycles', 1)
            if cycle_count % interval == 0:
                print(f"💧 Fixed Schedule: Watering {plant_id} now.")
                send_command(base_url, plant['command_water'])
            else:
                print(f"⏳ Fixed Schedule: Skipping water for {plant_id} (Cycle {cycle_count}/{interval})")

def main():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: Config file {CONFIG_FILE} not found.")
        return

    config = load_config()
    camera = CameraHandler(save_dir=f"data/{config['experiment_name']}")
    
    cycle_interval = config.get('interval_minutes', 60) * 60
    cycle_count = 0
    
    print(f"🧪 Experiment '{config['experiment_name']}' Initialized.")
    print(f"📡 API URL: {config['api_url']}")
    print(f"⏱️ Interval: {config['interval_minutes']} minutes.")
    
    try:
        while True:
            cycle_count += 1
            run_experiment_cycle(config, camera, cycle_count)
            
            print(f"\n💤 Sleeping for {config['interval_minutes']} minutes...")
            time.sleep(cycle_interval)
            
    except KeyboardInterrupt:
        print("\nExperiment stopped by user.")

if __name__ == "__main__":
    main()
