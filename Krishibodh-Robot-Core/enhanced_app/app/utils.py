import json
import os
from datetime import datetime

# Global log store
message_log_history = []

def get_timestamp():
    """Returns a formatted timestamp string."""
    return datetime.now().strftime("%H:%M:%S")

def log_message(message, category="info"):
    """Adds a new message to our persistent log."""
    print(f"[{category.upper()}] {message}") # Print to console as well
    message_log_history.insert(0, {"message": message, "category": category})

def get_logs():
    return message_log_history

def persist_reading(value, action="CHECKED"):
    """Saves moisture reading to JSON for the dashboard."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": timestamp,
        "moisture_value": int(value),
        "action_taken": action
    }
    
    # Use absolute path to ensure it's always in the enhanced_app folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "readings.json")
    data = []
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except:
            data = []
            
    data.append(entry)
    
    # Keep only last 100 readings
    if len(data) > 100:
        data = data[-100:]
        
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
        print(f"💾 Persisted moisture reading: {value} (Action: {action})")
        
        # BRIDGE TO ISOLATED EXPERIMENT STORAGE
        try:
            from .experiment_manager import experiment_manager
            if experiment_manager.is_running:
                experiment_manager._log_experiment_data("MOISTURE_READING", {
                    "value": int(value),
                    "action": action
                })
        except Exception as e:
            print(f"Warning: Could not log to isolated storage: {e}")

    except Exception as e:
        print(f"❌ Error persisting reading: {e}")
def get_readings():
    """Reads moisture readings from JSON."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "readings.json")
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except:
        return []
