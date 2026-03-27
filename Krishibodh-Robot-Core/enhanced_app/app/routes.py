from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from .arduino_service import arduino, PLANT_LOCATIONS
from .experiment_manager import experiment_manager
from .utils import log_message, get_timestamp, get_logs
import time
import os
import json

main_bp = Blueprint('main', __name__)

# --- PAGES ---

@main_bp.route('/')
def home():
    return render_template('home.html')

@main_bp.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@main_bp.route('/ai_command', methods=['POST'])
def ai_command():
    data = request.json
    user_msg = data.get('message', '').lower()
    
    from .arduino_service import arduino
    
    # Simple Logic for porting (Later we can integrate real LLM)
    command = None
    response = "I'm not sure how to do that yet."
    
    if "water plant 1" in user_msg:
        command = "WATER1"
        arduino.current_action = "AI: Water P1"
        response = "Initiating watering sequence for Plant 1."
    elif "water plant 2" in user_msg:
        command = "WATER2"
        arduino.current_action = "AI: Water P2"
        response = "Initiating watering sequence for Plant 2."
    elif "home" in user_msg:
        command = "0,0,0"
        arduino.current_action = "AI: Home"
        response = "Returning to home position."
    elif "plant 1" in user_msg and ("move" in user_msg or "go to" in user_msg):
        command = PLANT_LOCATIONS["PLANT_1"]
        arduino.current_action = "AI: Move P1"
        response = "Moving to Plant 1 coordinates."
    elif "plant 2" in user_msg and ("move" in user_msg or "go to" in user_msg):
        command = PLANT_LOCATIONS["PLANT_2"]
        arduino.current_action = "AI: Move P2"
        response = "Moving to Plant 2 coordinates."
    elif "hello" in user_msg or "hi" in user_msg:
        response = "Hello! I am ABHIMANYU. How can I help you with your KRISHIBODH system today?"

    if command:
        if arduino.is_connected():
            arduino.send_command("MODE:MANUAL")
            import time
            time.sleep(0.2)
            arduino.send_command(command)
            return jsonify({"status": "success", "command_executed": command, "response": response})
        else:
            return jsonify({"status": "error", "response": "Robot not connected. Please connect via C.C. first."})
    
    return jsonify({"status": "success", "response": response})

@main_bp.route('/controller')
def controller():
    return render_template('controller.html', 
                           available_ports=arduino.get_available_ports(),
                           is_connected=arduino.is_connected(),
                           connected_port=arduino.get_connected_port(),
                           log_history=get_logs())

@main_bp.route('/experiments')
def experiments():
    return render_template('experiments.html', 
                           is_running=experiment_manager.is_running,
                           is_connected=arduino.is_connected(),
                           connected_port=arduino.get_connected_port(),
                           available_ports=arduino.get_available_ports())

@main_bp.route('/dashboard')
def dashboard():
    from .utils import get_readings
    return render_template('dashboard.html', db_readings=get_readings())

@main_bp.route('/dashboard_data')
def dashboard_data():
    """Provides structured data for the 4-chart dashboard."""
    from .utils import get_readings
    import os
    
    exp_id = request.args.get('experiment_id')
    readings = []
    
    if exp_id:
        # Load from isolated storage
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(base_dir, "experiments", exp_id, "data.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Filter for 'MOISTURE_READING' or similar if we strictly logged types
                    # But our utils.persist_reading currently saves to global readings.json
                    # We need to bridge this. 
                    # If we use the new system, we log everything to data.json.
                    # Let's assume data.json contains mixed types.
                    readings = [d['content'] for d in data if d['type'] == 'MOISTURE_READING'] 
                    # Wait, my ExperimentManager._log_experiment_data logs dict content? 
                    # No, it logs 'content'. If 'content' is the reading dict, good.
                    # But I haven't updated persist_reading to use ExperimentManager.
                    # I need to fix that connection.
                    # For now, let's look at how ExperimentManager logs.
                    pass 
        except:
            readings = []
    else:
        readings = get_readings()
    
    # ... (Rest of logic needs access to 'readings' list of dicts)
    # This part is tricky because I haven't fully migrated the reading persistence yet.
    # Let's revert to standard behavior for now and fix persistence in next step if needed.
    # Actually, the user wants history. 
    # Let's just allow reading from the new 'data.json' structure.
    
    # ADAPTER: If reading from data.json, transform to match get_readings() format
    # data.json entries: {timestamp, type, content, iteration}
    # readings.json entries: {timestamp, moisture_value, action_taken}
    
    if exp_id:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(base_dir, "experiments", exp_id, "data.json")
            readings = []
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    raw_data = json.load(f)
                    for item in raw_data:
                        # We need to extract moisture readings. 
                        # I'll need to ensure ExperimentManager logs them as specific type.
                        if item.get('type') == 'SENSOR_READING':
                             # Content might be "Moisture: 500" string or dict?
                             # I will ensure it logs dict.
                             content = item.get('content')
                             if isinstance(content, dict):
                                 readings.append(content)
        except:
            readings = []
    
    # 1. Moisture Trends (Control vs Treatment)
    control_data = [] # P1
    treatment_data = [] # P2
    labels = []
    
    for r in readings:
        labels.append(r['timestamp'])
        val = r['moisture_value']
        action = r.get('action_taken', '')
        
        # Categorize by action/location
        if "Plant 1" in action or "2000,800" in action:
            control_data.append(val)
            treatment_data.append(None) # Gap for treatment
        elif "Plant 2" in action or "3000,1500" in action or "move_plant_2" in action:
            treatment_data.append(val)
            control_data.append(None) # Gap for control
        else:
            control_data.append(val)
            treatment_data.append(val)

    # 2. Watering Efficiency (Counts)
    p1_waters = sum(1 for r in readings if "Plant 1" in (r.get('action_taken','') or '') and "Water" in (r.get('action_taken','') or ''))
    p2_waters = sum(1 for r in readings if "Plant 2" in (r.get('action_taken','') or '') and "Water" in (r.get('action_taken','') or ''))
    
    # 3. Stability Distribution (Dry < 400, Optimal 400-600, Wet > 600)
    stability = {"Dry": 0, "Optimal": 0, "Wet": 0}
    for r in readings:
        v = r['moisture_value']
        if v < 400: stability["Wet"] += 1
        elif v <= 600: stability["Optimal"] += 1
        else: stability["Dry"] += 1

    # 4. KPI Score (Efficiency)
    total_samples = max(1, len(readings))
    waterings = p1_waters + p2_waters
    efficiency = int(((total_samples - waterings) / total_samples) * 100)

    # Limit to last 15 for trends
    limit = -15
    
    
    # 5. Images List
    images_list = []
    # If loading from Isolated Data
    if exp_id:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(base_dir, "experiments", exp_id, "data.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    raw_data = json.load(f)
                    for item in raw_data:
                        if "IMAGE" in item.get('type', ''):
                            images_list.append({
                                "filename": item.get('content'),
                                "type": item.get('type'),
                                "timestamp": item.get('timestamp'),
                                "exp_id": exp_id
                            })
        except: pass
    else:
        # No exp_id specified - load from most recent experiment
        try:
            from .experiment_manager import experiment_manager
            if experiment_manager.registry and len(experiment_manager.registry) > 0:
                latest_exp = experiment_manager.registry[0]  # Registry is sorted newest first
                latest_id = latest_exp.get('id')
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                file_path = os.path.join(base_dir, "experiments", latest_id, "data.json")
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        raw_data = json.load(f)
                        for item in raw_data:
                            if "IMAGE" in item.get('type', ''):
                                images_list.append({
                                    "filename": item.get('content'),
                                    "type": item.get('type'),
                                    "timestamp": item.get('timestamp'),
                                    "exp_id": latest_id
                                })
        except: pass
    
    
    return jsonify({
        "trends": {
            "labels": [l.split(' ')[1] for l in labels[limit:]] if labels else [], 
            "control": control_data[limit:],
            "treatment": treatment_data[limit:]
        },
        "efficiency": {
            "labels": ["Control (P1)", "Treatment (P2)"],
            "data": [p1_waters, p2_waters]
        },
        "stability": {
            "labels": list(stability.keys()),
            "data": list(stability.values())
        },
        "performance": efficiency,
        "images": images_list
    })

@main_bp.route('/experiment_images/<exp_id>/<filename>')
def serve_experiment_image(exp_id, filename):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, "experiments", exp_id)
    # If exp_id is empty/none, fallback to default captured_images for testing
    if not exp_id or exp_id == "null":
         target_dir = os.path.join(base_dir, "app", "captured_images")
         
    from flask import send_from_directory
    return send_from_directory(target_dir, filename)

# --- CONTROLLER API ---

@main_bp.route('/connect', methods=['POST'])
def connect():
    port = request.form.get('port')
    next_page = request.form.get('next', 'main.controller')
    if port:
        arduino.connect(port)
    return redirect(url_for(next_page))

@main_bp.route('/disconnect', methods=['POST'])
def disconnect():
    next_page = request.form.get('next', 'main.controller')
    arduino.disconnect()
    return redirect(url_for(next_page))

@main_bp.route('/move', methods=['POST'])
def move():
    action = request.form.get('action')
    
    # Ensure Arduino is in MANUAL mode for any movement command
    arduino.send_command("MODE:MANUAL")
    time.sleep(0.2)

    if action == 'move':
        try:
            x = int(request.form.get('x_coord', 0))
            y = int(request.form.get('y_coord', 0))
            z = int(request.form.get('z_coord', 0))
            arduino.current_action = f"Move ({x},{y},{z})"
            arduino.send_command(f"{x},{y},{z}")
        except (ValueError, TypeError):
            log_message("⚠️ Invalid coordinates entered.", "error")
        
    elif action == 'home':
        arduino.current_action = "Home"
        arduino.send_command("0,0,0")
        
    elif action == 'plant1':
        arduino.current_action = "Plant 1 Move"
        arduino.send_command(PLANT_LOCATIONS["PLANT_1"])
        
    elif action == 'plant2':
        arduino.current_action = "Plant 2 Move"
        arduino.send_command(PLANT_LOCATIONS["PLANT_2"])
        
    elif action == 'water1':
        arduino.current_action = "Plant 1 Water"
        arduino.send_command("WATER1")
        
    elif action == 'water2':
        arduino.current_action = "Plant 2 Water"
        arduino.send_command("WATER2")
        
    elif action == 'sensor':
        arduino.current_action = "Manual Sensor Read"
        arduino.send_command("MOISTURE:GET")
        
    return redirect(url_for('main.controller'))

@main_bp.route('/set_mode', methods=['POST'])
def set_mode():
    mode = request.form.get('mode')
    cmd = "MODE:MANUAL" if mode == 'manual' else "MODE:DEFAULT"
    arduino.send_command(cmd)
    return redirect(url_for('main.controller'))

# --- EXPERIMENT API ---

@main_bp.route('/generate_plans', methods=['POST'])
def generate_plans():
    data = request.get_json()
    hypothesis = data.get('hypothesis', '')
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    ai_generated = False
    plans = []

    if api_key and hypothesis:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Generate 2 scientific experiment plans to test this hypothesis on a plant robot: "{hypothesis}".
            The robot has functions: move_plant_1, move_plant_2, water_smart_p1, water_smart_p2, water_force_p1, water_force_p2, check_sensor, capture_top, home.
            Return a purely valid JSON object (no markdown) with this structure:
            {{
                "plans": [
                    {{
                        "title": "...", 
                        "hypothesis_summary": "...", 
                        "variables": {{"control": {{"label": "...", "details": "..."}}, "treatment": {{"label": "...", "details": "..."}}}},
                        "metrics": [{{"name": "...", "value": "...", "icon": "..."}}],
                        "timeline": {{"start": "...", "duration": "...", "next_capture": "..."}},
                        "steps": [{{"action": "...", "desc": "...", "wait_after": 5}}],
                        "frequency": "..."
                    }}
                ]
            }}
            """
            response = model.generate_content(prompt)
            print(f"AI Response: {response.text}")
            
            # Clean and parse JSON
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            plans = json.loads(clean_text).get('plans', [])
            ai_generated = True
        except Exception as e:
            print(f"AI Generation Failed: {e}")
            log_message(f"⚠️ AI Generation failed, falling back to templates. Error: {e}", "warning")

    if not plans:
        # Fallback Templates
        plans = [
            {
                "id": 1, 
                "title": "Smart Irrigation Growth Comparison", 
                "hypothesis_summary": f"Testing: {hypothesis[:50]}...",
                "status": "Scheduled",
                "status_color": "chocolate",
                "variables": {
                    "control": { "label": "Fixed Interval", "details": "Watering every 6 hours" },
                    "treatment": { "label": "Moisture Optimized", "details": "Sensor-based trigger" }
                },
                "metrics": [
                    {"name": "Leaf Area", "value": "Collecting...", "unit": "", "icon": "🍃"},
                    {"name": "Height", "value": "Collecting...", "unit": "", "icon": "📏"}
                ],
                "timeline": { "start": "Today", "duration": "7 days", "next_capture": "4:00 PM" },
                "progress": { "percent": 0, "collected": 0, "total": 40 },
                "description": "Compare fixed vs smart watering strategies.",
                "steps": [
                    {"action": "move_plant_1", "desc": "Move to Plant 1", "wait_after": 2},
                    {"action": "check_sensor", "desc": "Measure moisture", "wait_after": 2},
                    {"action": "water_smart_p1", "desc": "Smart watering (if dry)", "wait_after": 5},
                    {"action": "capture_top", "desc": "Phenotypic scan", "wait_after": 2},
                    {"action": "home", "desc": "Return home", "wait_after": 0}
                ],
                "frequency": "Every 30 seconds"
            }
        ]

    return jsonify({"success": True, "plans": plans, "ai_generated": ai_generated})

@main_bp.route('/start_experiment', methods=['POST'])
def start_experiment():
    if not arduino.is_connected():
        return jsonify({"success": False, "message": "Robot not connected! Please connect first."})
        
    data = request.get_json()
    plan = data.get('plan')
    success, msg = experiment_manager.start_experiment(plan)
    return jsonify({"success": success, "message": msg})

@main_bp.route('/stop_experiment', methods=['POST'])
def stop_experiment():
    success, msg = experiment_manager.stop_experiment()
    return jsonify({"success": success, "message": msg})

@main_bp.route('/experiment_status')
def experiment_status():
    return jsonify(experiment_manager.get_report())

@main_bp.route('/experiment_history')
def experiment_history():
    """Returns list of past experiments."""
    return jsonify(experiment_manager.registry)

@main_bp.route('/experiment_data/<exp_id>')
def experiment_data(exp_id):
    """Returns data for a specific experiment ID."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "experiments", exp_id, "data.json")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)})
    return jsonify([])
