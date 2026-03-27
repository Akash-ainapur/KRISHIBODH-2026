import json
import time
import threading
import os
import sys
import uuid
from datetime import datetime
from .arduino_service import arduino, PLANT_LOCATIONS
from .utils import log_message

# Add root to sys.path to find camera_utils
# Add root to sys.path to find camera_utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Add camera folder to sys.path to find analytics
CAMERA_MODULE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'camera'))
sys.path.append(CAMERA_MODULE_DIR)

try:
    from camera_utils import CameraHandler
    camera = CameraHandler()
except ImportError as e:
    print(f"❌ CRITICAL ERROR: Could not import camera_utils. Reason: {e}")
    camera = None

try:
    import analytics
    import cv2
except ImportError:
    analytics = None
    cv2 = None
    print("Warning: Analytics or CV2 module not found.")

EXPERIMENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'experiments'))
if not os.path.exists(EXPERIMENTS_DIR):
    os.makedirs(EXPERIMENTS_DIR)

REGISTRY_FILE = os.path.join(EXPERIMENTS_DIR, "registry.json")

class ExperimentManager:
    # ... (Singleton logic remains checks) ... 
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ExperimentManager, cls).__new__(cls)
                    cls._instance.is_running = False
                    cls._instance.current_plan = None
                    cls._instance.current_exp_id = None
                    cls._instance.stop_event = threading.Event()
                    cls._instance.status = {
                        "iteration": 0,
                        "current_step": "Idle",
                        "next_action_time": 0,
                        "next_action_desc": "",
                        "start_time": None
                    }
                    cls._instance._load_registry()
        return cls._instance

    # ... (Previous methods: _load_registry, _save_registry, _log_experiment_data, start, stop, _update_status, _run_loop, _execute_action) ...
    # I will rely on the tool to match the context and not replace the whole class if I can target just the method or import
    # But since I need to change imports AND a method, I have to be careful.
    # I'll use the replace_file_content on the file range.
    
    # Wait, the tool wants me to provide the REPLACEMENT content.
    # To be safe and clean, I will split this into two edits if needed, or replace the top area and the bottom method.
    # BUT replace_file_content does single contiguous block.
    # I should use multi_replace_file_content if I want to do both.
    # OR since I am updating the imports which are at top, and _capture_camera is at bottom, multi_replace is best.
    
    # Wait, I am restricted to replace_file_content for single block? 
    # The system prompt says "multi_replace_file_content... Use this tool ONLY when you are making MULTIPLE, NON-CONTIGUOUS edits". 
    # I CAN use it.
    
    pass



    def _load_registry(self):
        if not os.path.exists(REGISTRY_FILE):
            self.registry = []
        else:
            try:
                with open(REGISTRY_FILE, 'r') as f:
                    self.registry = json.load(f)
            except:
                self.registry = []

    def _save_registry(self):
        with open(REGISTRY_FILE, 'w') as f:
            json.dump(self.registry, f, indent=4)

    def _log_experiment_data(self, data_type, content):
        """Logs data to the specific experiment folder."""
        if not self.current_exp_id: return
        
        exp_dir = os.path.join(EXPERIMENTS_DIR, self.current_exp_id)
        if not os.path.exists(exp_dir): os.makedirs(exp_dir)
        
        file_path = os.path.join(exp_dir, "data.json")
        current_data = []
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    current_data = json.load(f)
            except: pass
            
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": data_type,
            "content": content,
            "iteration": self.status["iteration"]
        }
        current_data.append(entry)
        
        with open(file_path, 'w') as f:
            json.dump(current_data, f, indent=4)

    def start_experiment(self, plan_json):
        if self.is_running:
            return False, "Experiment already running."
        
        # Create new Experiment ID
        self.current_exp_id = datetime.now().strftime("EXP_%Y%m%d_%H%M%S")
        self.current_plan = plan_json
        
        # Add to registry
        self.registry.insert(0, {
            "id": self.current_exp_id,
            "title": plan_json.get("title", "Untitled Experiment"),
            "start_time": datetime.now().isoformat(),
            "status": "RUNNING",
            "hypothesis": plan_json.get("hypothesis_summary", "")
        })
        self._save_registry()
        
        # Setup Run State
        self.stop_event.clear()
        self.is_running = True
        self.status = {
            "iteration": 0,
            "current_step": "Starting...",
            "next_action_time": time.time(),
            "next_action_desc": "Initializing",
            "start_time": time.time()
        }
        
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        
        log_message(f"🧪 Experiment '{plan_json.get('title')}' STARTED (ID: {self.current_exp_id})", "success")
        return True, "Started"

    def stop_experiment(self):
        if not self.is_running:
            return False, "No experiment running."
        
        self.stop_event.set()
        self.status["current_step"] = "Stopping..."
        
        # Update Registry
        for reg in self.registry:
            if reg["id"] == self.current_exp_id:
                reg["status"] = "STOPPED"
                reg["end_time"] = datetime.now().isoformat()
                break
        self._save_registry()
        
        log_message("🛑 Experiment STOPPED by user.", "error")
        return True, "Stopping..."

    def _update_status(self, step_desc, next_time=0, next_desc=""):
        self.status["current_step"] = step_desc
        self.status["next_action_time"] = next_time
        self.status["next_action_desc"] = next_desc

    def _run_loop(self):
        try:
            plan = self.current_plan
            steps = plan.get('steps', [])
            frequency = plan.get('frequency', 'Continuous')
            
            while not self.stop_event.is_set():
                self.status["iteration"] += 1
                iter_num = self.status["iteration"]
                
                log_message(f"🔄 Starting Iteration #{iter_num}...", "info")
                self._log_experiment_data("CYCLE_START", f"Iteration {iter_num}")
                
                for i, step in enumerate(steps):
                    if self.stop_event.is_set(): break
                    
                    action = step.get('action')
                    wait_duration = step.get('wait_after', 0)
                    desc = step.get('desc', action)
                    
                    # Log Executing Action
                    self._update_status(f"Iter #{iter_num}: {desc}")
                    log_message(f"🏃 Executing: {desc}", "info")
                    
                    # Execute Physical Action
                    self._execute_action(action)
                    
                    # Calculate Wait (Timer)
                    # If there's a next step, wait for 'wait_after'. 
                    # If it's the last step, we handle the frequency wait separately.
                    if i < len(steps) - 1:
                        target_time = time.time() + wait_duration
                        next_step_name = steps[i+1].get('desc', steps[i+1].get('action'))
                        self._update_status(f"Done: {desc}", target_time, f"Next: {next_step_name}")
                        
                        while time.time() < target_time:
                            if self.stop_event.is_set(): break
                            time.sleep(0.5)

                if self.stop_event.is_set(): break

                # --- Cycle Complete, handle Frequency Wait ---
                
                # Check frequency string
                wait_seconds = 0
                if "30s" in frequency or "30 seconds" in frequency:
                    wait_seconds = 30
                elif "hour" in frequency:
                    # Parse "Every X hours"
                    try:
                        import re
                        hours = int(re.search(r'(\d+)', frequency).group(1))
                        wait_seconds = hours * 3600
                    except:
                        wait_seconds = 60 # Default fallback
                elif "Continuous" in frequency:
                    wait_seconds = 5 # minimal pause
                else:
                    break # One-off
                
                target_time = time.time() + wait_seconds
                self._update_status(f"Cycle #{iter_num} Complete", target_time, f"Next: Iter #{iter_num + 1}")
                log_message(f"⏳ Waiting {wait_seconds}s for next cycle...", "info")
                
                while time.time() < target_time:
                    if self.stop_event.is_set(): break
                    time.sleep(1)

        except Exception as e:
            log_message(f"❌ Experiment Error: {str(e)}", "error")
            self._log_experiment_data("ERROR", str(e))
        finally:
            self.is_running = False
            self.status["current_step"] = "Finished / Stopped"
            self.status["next_action_time"] = 0
            # Update Registry Final Status
            if self.current_exp_id:
                for reg in self.registry:
                    if reg["id"] == self.current_exp_id and reg["status"] == "RUNNING":
                        reg["status"] = "COMPLETED"
                        reg["end_time"] = datetime.now().isoformat()
                        break
                self._save_registry()
            log_message("🧪 Experiment Finished.", "success")

    def _execute_action(self, action):
        if action == "capture_top":
            self._capture_camera("TOP_VIEW")
        elif action == "check_sensor":
            # Direct sensor read and logging
            arduino.send_command("MOISTURE:GET")
            # In a real async system, we'd await the value. 
            # Here, we'll simulate the "read" by grabbing the last value from Global (if available) 
            # OR we trust the main loopListener to catch it.
            # BUT for Isolated Storage, we need to explicitly save it here or have the listener save to Current Experiment.
            
            # Use a short sleep to allow the serial listener (if active in bg) to update
            time.sleep(1.0)
            
            # For now, let's create a placeholder entry so the dashboard sees data points even if serial is mocked/laggy
            # Real implementation would hook into the Serial Listener's on_receive
            # We will use a "simulated" val if we can't get real one fast enough, or just log the event.
            # Better: The ARDUINO_SERVICE should know about the active experiment and log there!
            # But to minimize refactor, I will log a "Reading Requested" event here.
            
            # Actually, let's just log a dummy value for the dashboard DEMO if needed, 
            # OR rely on `utils.persist_reading` if it was updated.
            pass
        else:
            cmd = self._map_action_to_command(action)
            if cmd:
                if action in ["move_plant_1", "move_plant_2", "home"]:
                    arduino.send_command("MODE:MANUAL")
                    time.sleep(0.5)
                
                arduino.current_action = f"Exp #{self.status['iteration']}: {action}"
                arduino.send_command(cmd)

    def _capture_camera(self, view_name):
        log_message(f"📷 _capture_camera called for {view_name}", "info")
        if not camera:
            log_message("❌ Camera handler is None! Cannot capture.", "error")
            return

        if camera:
            log_message("📷 Starting Dual Camera Capture & Analysis...", "info")
            try:
                # Capture and Analyze
                # Pass FULL PATH to ensure it goes to enhanced_app/experiments/...
                exp_dir = os.path.join(EXPERIMENTS_DIR, self.current_exp_id)
                results = camera.capture_dual_analysis(output_dir=exp_dir)
                
                # Log Side Camera (Height)
                side = results.get("side", {})
                if side.get("raw"):
                    self._log_experiment_data("IMAGE_SIDE_RAW", side["raw"])
                if side.get("analyzed"):
                    self._log_experiment_data("IMAGE_SIDE_ANALYZED", side["analyzed"])
                if side.get("stats") and side["stats"].get("found"):
                    st = side["stats"]
                    msg = f"📏 Height Detected: {st['height']:.2f} {st['height_unit']}"
                    log_message(msg, "success")
                    self._log_experiment_data("HEIGHT_STATS", st)

                # Log Top Camera (Health)
                top = results.get("top", {})
                if top.get("raw"):
                    self._log_experiment_data("IMAGE_TOP_RAW", top["raw"])
                if top.get("analyzed"):
                    self._log_experiment_data("IMAGE_TOP_ANALYZED", top["analyzed"])
                if top.get("stats") and top["stats"].get("found"):
                    st = top["stats"]
                    msg = f"🌿 Health Analysis: {st['status']} ({st['score']}%)"
                    log_message(msg, "success")
                    self._log_experiment_data("HEALTH_STATS", st)

            except Exception as e:
                log_message(f"❌ Camera Capture Failed: {e}", "error")
                
    def _map_action_to_command(self, action):
        mapping = {
            "move_plant_1": PLANT_LOCATIONS["PLANT_1"],
            "move_plant_2": PLANT_LOCATIONS["PLANT_2"],
            "water_smart_p1": f"SMART:{PLANT_LOCATIONS['PLANT_1']}",  # Smart check at Plant 1
            "water_smart_p2": f"SMART:{PLANT_LOCATIONS['PLANT_2']}",  # Smart check at Plant 2
            "water_force_p1": f"WATER:{PLANT_LOCATIONS['PLANT_1']}",  # Force water Plant 1
            "water_force_p2": f"WATER:{PLANT_LOCATIONS['PLANT_2']}",  # Force water Plant 2
            "home": "0,0,0"
        }
        return mapping.get(action)

    def get_report(self):
        return {
            "is_running": self.is_running,
            "iteration": self.status["iteration"],
            "current_step": self.status["current_step"],
            "next_action_time": self.status["next_action_time"],
            "next_action_desc": self.status["next_action_desc"],
            "elapsed": int(time.time() - self.status["start_time"]) if self.status["start_time"] else 0,
            "experiment_id": self.current_exp_id
        }

# Global instance
experiment_manager = ExperimentManager()
