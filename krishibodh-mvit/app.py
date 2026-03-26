from flask import Flask, render_template, request, redirect, url_for, jsonify
import serial
from serial.tools import list_ports
import time
from datetime import datetime

# --- Initialize Flask App ---
app = Flask(__name__)
app.secret_key = 'krishibodh-is-a-super-secret-project-98765'

# --- Arduino Configuration ---
BAUD_RATE = 9600 # <--- THIS FIXES THE ERROR YOU SAW

# --- Global Connection & Log ---
ser = None
# This list is the persistent log. It will not clear until the server restarts.
message_log_history = []

def get_timestamp():
    """Returns a formatted timestamp string."""
    return datetime.now().strftime("%H:%M:%S")

def log_message(message, category="info"):
    """Adds a new message to our persistent log."""
    # We add to the front of the list so new messages appear at the top.
    message_log_history.insert(0, {"message": message, "category": category})

def check_port_available(port):
    """Check if a port is available by trying to open it briefly."""
    test_ser = None
    try:
        test_ser = serial.Serial(port, BAUD_RATE, timeout=0.1)
        test_ser.close()
        return True
    except serial.SerialException:
        return False
    except Exception:
        return False
    finally:
        if test_ser and test_ser.is_open:
            try:
                test_ser.close()
            except:
                pass

def force_close_port(port):
    """Try to force close any existing connection to the port."""
    # Try to open and immediately close to release any locks
    try:
        temp_ser = serial.Serial(port, BAUD_RATE, timeout=0.1)
        temp_ser.close()
        time.sleep(0.3)
        return True
    except:
        return False

def initialize_serial(port):
    """Tries to connect to the Arduino on a SPECIFIED port."""
    global ser
    max_retries = 2
    retry_delay = 1.0
    
    # Close existing connection if any
    if ser and ser.is_open:
        try:
            ser.close()
            time.sleep(0.5)  # Give port time to release
        except:
            pass
        ser = None
    
    # Check if port exists in system
    available_ports = [p.device for p in list_ports.comports()]
    if port not in available_ports:
        log_message(f"❌ ({get_timestamp()}) Port {port} is not found. Please check your Arduino connection.", "error")
        return False

    # Try to connect with retries
    for attempt in range(1, max_retries + 1):
        try:
            # Try to force release the port on first attempt
            if attempt == 1:
                force_close_port(port)
                time.sleep(0.5)
            
            # Open serial connection with better error handling
            try:
                ser = serial.Serial(port, BAUD_RATE, timeout=1, write_timeout=1)
            except (OSError, serial.SerialException) as e:
                error_str = str(e)
                if "995" in error_str or "i/o operation" in error_str.lower() or "aborted" in error_str.lower():
                    # Windows error 995 - port interrupted, likely due to power connection
                    if attempt < max_retries:
                        log_message(f"⚠️ ({get_timestamp()}) Port interrupted during connection (attempt {attempt}/{max_retries}).", "error")
                        log_message(f"💡 ({get_timestamp()}) If you just connected motor power, wait 5 seconds and try again.", "info")
                        time.sleep(5)  # Wait longer for power to stabilize
                        continue
                    else:
                        raise  # Re-raise to be caught by outer exception handler
                else:
                    raise  # Re-raise other errors
            
            time.sleep(2.5)  # Wait for the Arduino to reset and stabilize
            
            # IMPORTANT: Clear all buffers - do NOT send any commands on connection
            ser.flushInput()  # Clear input buffer
            ser.flushOutput()  # Clear output buffer
            time.sleep(0.2)
            
            # Read and discard any initial data Arduino might be sending
            bytes_read = 0
            start_time = time.time()
            while time.time() - start_time < 0.5:  # Read for max 0.5 seconds
                if ser.in_waiting > 0:
                    try:
                        data = ser.read(ser.in_waiting)
                        bytes_read += len(data)
                    except:
                        break
                else:
                    time.sleep(0.1)
            
            if bytes_read > 0:
                log_message(f"ℹ️ ({get_timestamp()}) Cleared {bytes_read} bytes from Arduino buffer.", "info")
            
            # Final flush
            ser.flushInput()
            
            log_message(f"✅ ({get_timestamp()}) System Online. Connected to {port} at {BAUD_RATE} baud.", "success")
            log_message(f"💡 ({get_timestamp()}) Ready to send commands. NO commands sent automatically.", "info")
            log_message(f"⚠️ ({get_timestamp()}) If Arduino shows 'p 0,0,0' loop, it's an Arduino code issue, not Python.", "info")
            return True
            
        except serial.SerialException as e:
            error_msg = str(e).lower()
            error_str = str(e)
            
            # More specific error messages
            if "access is denied" in error_msg or "permission denied" in error_msg:
                if attempt < max_retries:
                    log_message(f"⚠️ ({get_timestamp()}) Port {port} is locked (attempt {attempt}/{max_retries}). Retrying...", "error")
                    time.sleep(retry_delay)
                    continue
                else:
                    log_message(f"❌ ({get_timestamp()}) Port {port} is locked after {max_retries} attempts.", "error")
                    log_message(f"💡 ({get_timestamp()}) Troubleshooting steps:", "info")
                    log_message(f"   1. Close Arduino IDE Serial Monitor completely", "info")
                    log_message(f"   2. Close any other programs using {port}", "info")
                    log_message(f"   3. Unplug and replug your Arduino USB cable", "info")
                    log_message(f"   4. Restart this application", "info")
                    
            elif "could not open port" in error_msg or "cannot configure port" in error_msg:
                if "995" in error_str or "i/o operation" in error_msg or "aborted" in error_msg:
                    # Windows error 995: I/O operation aborted - usually happens during power connection
                    if attempt < max_retries:
                        log_message(f"⚠️ ({get_timestamp()}) Port interrupted (attempt {attempt}/{max_retries}). This may happen when connecting motor power.", "error")
                        log_message(f"💡 ({get_timestamp()}) Wait 3 seconds for Arduino to stabilize, then retrying...", "info")
                        time.sleep(3)  # Longer delay for power stabilization
                        continue
                    else:
                        log_message(f"❌ ({get_timestamp()}) Port {port} connection failed after {max_retries} attempts.", "error")
                        log_message(f"💡 ({get_timestamp()}) Troubleshooting steps:", "info")
                        log_message(f"   1. Connect motor power supply BEFORE connecting to Arduino", "info")
                        log_message(f"   2. Wait 5 seconds after connecting power before connecting", "info")
                        log_message(f"   3. Use a separate power supply for motors (don't power from USB)", "info")
                        log_message(f"   4. Check USB cable connection - try a different cable", "info")
                        log_message(f"   5. Unplug USB, wait 2 seconds, then reconnect", "info")
                else:
                    log_message(f"❌ ({get_timestamp()}) Cannot open port {port}. Port may be disconnected.", "error")
            else:
                log_message(f"❌ ({get_timestamp()}) Connection FAILED on {port}: {str(e)}", "error")
            
            ser = None
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return False
                
        except Exception as e:
            log_message(f"❌ ({get_timestamp()}) Unexpected error connecting to {port}: {str(e)}", "error")
            ser = None
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return False
    
    return False

def read_arduino_response(timeout=0.5):
    """Read response from Arduino if available."""
    global ser
    if ser is None or not ser.is_open:
        return None
    try:
        original_timeout = ser.timeout
        ser.timeout = timeout
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8', errors='ignore').strip()
            ser.timeout = original_timeout
            
            # Check if response is a moisture value (just a number)
            if response and response.isdigit():
                log_message(f"💧 ({get_timestamp()}) Moisture Value: {response}", "info")
                return None  # Don't return moisture-only responses as regular responses
            
            return response if response else None
        ser.timeout = original_timeout
    except Exception as e:
        pass
    return None

def send_command_to_arduino(command_string, log_command=True):
    """Generic function to send any command string to the Arduino. Sends ONCE only."""
    global ser
    if ser is None or not ser.is_open:
        log_message(f"⚠️ ({get_timestamp()}) Command ignored. Not connected to Arduino.", "error")
        return False
    try:
        # Remove any existing newlines/carriage returns
        command_string = command_string.strip()
        
        # Arduino uses Serial.readStringUntil('\n') so it needs just \n (not \r\n)
        command_to_send = command_string + '\n'
        
        # Log the command being sent (for debugging)
        if log_command:
            log_message(f"📤 ({get_timestamp()}) Sending ONCE: '{command_string}'", "info")
        
        # Clear input buffer before sending (to avoid reading old data)
        ser.flushInput()
        
        # Send command ONCE - no loops, no repeats
        bytes_written = ser.write(command_to_send.encode('utf-8'))
        ser.flushOutput()  # Ensure data is sent immediately
        
        # Small delay to allow Arduino to process
        time.sleep(0.1)
        
        # Try to read response from Arduino (non-blocking, quick check)
        response = read_arduino_response(timeout=0.2)
        if response:
            # Check if response contains moisture value
            if "moisture" in response.lower() or "moisture value" in response.lower():
                # Extract moisture value if present
                try:
                    # Arduino sends: "Moisture value read: 650" or similar
                    if ":" in response:
                        parts = response.split(":")
                        if len(parts) > 1:
                            moisture_val = parts[-1].strip()
                            log_message(f"💧 ({get_timestamp()}) Moisture Value: {moisture_val}", "info")
                        else:
                            log_message(f"📥 ({get_timestamp()}) Arduino: '{response}'", "info")
                    else:
                        log_message(f"📥 ({get_timestamp()}) Arduino: '{response}'", "info")
                except:
                    log_message(f"📥 ({get_timestamp()}) Arduino: '{response}'", "info")
            else:
                log_message(f"📥 ({get_timestamp()}) Arduino: '{response}'", "info")
        
        if bytes_written > 0:
            return True
        else:
            log_message(f"⚠️ ({get_timestamp()}) No bytes written to serial port.", "error")
            return False
            
    except serial.SerialException as e:
        log_message(f"❌ ({get_timestamp()}) Communication Error: {e}. Connection lost.", "error")
        try:
            if ser and ser.is_open:
                ser.close()
        except:
            pass
        ser = None
        return False
    except Exception as e:
        log_message(f"❌ ({get_timestamp()}) Unexpected error sending command: {str(e)}", "error")
        return False

@app.route('/')
def index():
    """Main page. Pass all port and log data to the template."""
    ports = list_ports.comports()
    available_ports = [p.device for p in ports]
    is_connected = ser is not None and ser.is_open
    
    # Safely get connected port
    if is_connected and ser is not None:
        try:
            connected_port = ser.port
        except:
            connected_port = "None"
    else:
        connected_port = "None"
    
    # Pass the entire log history to the webpage
    return render_template('index.html', 
                           available_ports=available_ports,
                           is_connected=is_connected,
                           connected_port=connected_port,
                           log_history=message_log_history) # Pass the persistent log

@app.route('/chatbot')
def chatbot():
    """Renders the new AI Chatbot page (ABHIMANYU)."""
    return render_template('chatbot.html')

# --- NEW ROUTE FOR AI COMMANDS (POST) ---
@app.route('/ai_command', methods=['POST'])
def ai_command():
    """Receives a clean command string from the AI chatbot and executes it."""
    # The JSON payload from the chatbot should contain the 'command' key.
    command_data = request.get_json()
    command_string = command_data.get('command', '').strip()
    
    if not command_string:
        log_message(f"⚠️ ({get_timestamp()}) AI Command Failed: No command string received.", "error")
        return jsonify({"success": False, "message": "No command string received."}), 400

    # 1. Determine action based on command prefix
    action_type = "Move"
    log_message(f"🧠 ({get_timestamp()}) AI Initiated Command: '{command_string}'", "info")

    if command_string.startswith("WATER1") or command_string.startswith("WATER2"):
        # For 'WATER1' or 'WATER2', move to plant coordinates and let Arduino decide watering via moisture sensor.
        coords = (2000, 800, 10000) if command_string == "WATER1" else (3000, 1500, 10000)
        final_command = f"{coords[0]},{coords[1]},{coords[2]}"
        action_type = "Moisture-Checked Water"
        
    elif command_string.startswith("HOME"):
        # Arduino expects "0,0,0" for home
        final_command = "0,0,0"
        action_type = "Home"

    elif command_string.startswith("MOVE:"):
        # Arduino expects coordinates "x,y,z"
        # We strip the "MOVE:" prefix to get the raw coordinates
        coord_part = command_string.replace("MOVE:", "", 1)
        final_command = coord_part
        action_type = f"Manual Move to ({coord_part})"

    else:
        log_message(f"⚠️ ({get_timestamp()}) AI Command Failed: Unknown command format '{command_string}'.", "error")
        return jsonify({"success": False, "message": "Unknown command format."}), 400

    # 2. Ensure system is in MANUAL mode for physical movements/actions
    # This prevents the AI from disrupting autonomous sequences unless necessary
    mode_command = "MODE:MANUAL"
    send_command_to_arduino(mode_command, log_command=False)
    time.sleep(0.2) # Small delay for mode change processing

    # 3. Send the command to the Arduino
    if send_command_to_arduino(final_command):
        log_message(f"✅ ({get_timestamp()}) AI Execution Successful: {action_type} command sent to device.", "success")
        return jsonify({"success": True, "message": f"{action_type} command executed successfully."}), 200
    else:
        return jsonify({"success": False, "message": "Failed to communicate with Arduino. Check connection."}), 500

# --- END NEW ROUTE ---


@app.route('/connect', methods=['POST'])
def connect():
    selected_port = request.form.get('port')
    if selected_port:
        initialize_serial(selected_port)
    else:
        log_message(f"⚠️ ({get_timestamp()}) Please select a port from the dropdown.", "error")
    return redirect(url_for('index'))

@app.route('/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from the current Arduino port."""
    global ser
    if ser and ser.is_open:
        try:
            port = ser.port
            ser.close()
            log_message(f"🔌 ({get_timestamp()}) Disconnected from {port}.", "info")
        except Exception as e:
            log_message(f"⚠️ ({get_timestamp()}) Error disconnecting: {str(e)}", "error")
        finally:
            ser = None
    else:
        log_message(f"⚠️ ({get_timestamp()}) No active connection to disconnect.", "error")
    return redirect(url_for('index'))

@app.route('/move', methods=['POST'])
def move():
    action = request.form.get('action')
    command_to_send = None
    
    # IMPORTANT: Arduino must be in MANUAL mode to accept coordinate commands
    # We now send this for ALL coordinate-based actions
    if action in ['move', 'home', 'plant1', 'plant2', 'water1', 'water2']:
        # Ensure Arduino is in manual mode before sending coordinates
        mode_command = "MODE:MANUAL"
        send_command_to_arduino(mode_command, log_command=False)
        time.sleep(0.2)  # Small delay to let Arduino process mode change
    
    if action == 'move':
        try:
            x, y, z = (int(request.form.get(c)) for c in ['x_coord', 'y_coord', 'z_coord'])
            # This is the "smart" move-and-check command
            command_to_send = f"{x},{y},{z}"
            if send_command_to_arduino(command_to_send):
                log_message(f"➡️ ({get_timestamp()}) Executing manual move to ({x}, {y}, {z}).", "success")
                log_message(f"💡 ({get_timestamp()}) Arduino will check moisture after movement and water if needed.", "info")
        except (ValueError, KeyError, TypeError):
            log_message(f"⚠️ ({get_timestamp()}) Invalid coordinates.", "error")
            
    elif action == 'home':
        # Arduino expects format: "x,y,z" (comma-separated, NO prefix)
        command_to_send = "0,0,0"
        if send_command_to_arduino(command_to_send):
            log_message(f"🏠 ({get_timestamp()}) Task: Return to Home Position.", "success")
            log_message(f"   - Phase 1: Retracting Z-Axis to safe height (0).", "info")
            log_message(f"   - Phase 2: Moving X/Y Axes to origin (0, 0).", "info")

    elif action == 'plant1' or action == 'plant2':
        coords = (2000, 800, 10000)
        plant_name = "Plant 1"
        if action == 'plant2':
            coords = (3000, 1500, 10000)
            plant_name = "Plant 2"
        
        # This is the "smart" move-and-check command
        command_to_send = f"{coords[0]},{coords[1]},{coords[2]}"
        
        if send_command_to_arduino(command_to_send):
            log_message(f"➡️ ({get_timestamp()}) Task: Move to {plant_name}.", "success")
            log_message(f"   - Phase 1: Retracting Z-Axis for safe travel.", "info")
            log_message(f"   - Phase 2: Moving to XY position ({coords[0]}, {coords[1]}).", "info")
            log_message(f"   - Phase 3: Lowering tool to Z position ({coords[2]}).", "info")
            log_message(f"💡 ({get_timestamp()}) Arduino will check moisture after movement and water if needed.", "info")
    
    # --- NEW UPDATED LOGIC ---
    elif action == 'water1':
        coords = (2000, 800, 10000)  # Plant 1 Coords
        command_to_send = f"{coords[0]},{coords[1]},{coords[2]}"
        
        if send_command_to_arduino(command_to_send):
            log_message(f"💧 ({get_timestamp()}) Task: Moisture-checked watering at Plant 1.", "success")
            log_message(f"   - Sending smart command: {command_to_send}", "info")
            log_message(f"💡 ({get_timestamp()}) Arduino will check moisture before watering.", "info")
            
    elif action == 'water2':
        coords = (3000, 1500, 10000)  # Plant 2 Coords
        command_to_send = f"{coords[0]},{coords[1]},{coords[2]}"
        
        if send_command_to_arduino(command_to_send):
            log_message(f"💧 ({get_timestamp()}) Task: Moisture-checked watering at Plant 2.", "success")
            log_message(f"   - Sending smart command: {command_to_send}", "info")
            log_message(f"💡 ({get_timestamp()}) Arduino will check moisture before watering.", "info")
    # --- END OF NEW LOGIC ---
            
    return redirect(url_for('index'))

@app.route('/set_mode', methods=['POST'])
def set_mode():
    mode = request.form.get('mode')
    command_to_send = "MODE:DEFAULT" if mode == 'default' else "MODE:MANUAL"
    human_message = "Engaging autonomous sequence." if mode == 'default' else "Switching to Manual Override."
    
    if send_command_to_arduino(command_to_send):
        log_message(f"⚙️ ({get_timestamp()}) {human_message}", "success")
        
    return redirect(url_for('index'))

@app.route('/test_connection', methods=['POST'])
def test_connection():
    """Send a test command to verify Arduino communication."""
    test_command = "TEST"
    if send_command_to_arduino(test_command):
        log_message(f"🧪 ({get_timestamp()}) Test command sent. Check Arduino Serial Monitor for response.", "info")
    return redirect(url_for('index'))

@app.route('/test_z_axis', methods=['POST'])
def test_z_axis():
    """Test Z-axis movement independently."""
    # Test moving Z-axis down then back up
    # Arduino expects format: "x,y,z" - so we send "0,0,5000" then "0,0,0"
    test_z_down = "0,0,5000"  # Move Z down to 5000 steps (X=0, Y=0, Z=5000)
    test_z_up = "0,0,0"       # Move Z back to 0
    
    log_message(f"🔧 ({get_timestamp()}) Testing Z-axis movement...", "info")
    
    if send_command_to_arduino(test_z_down):
        log_message(f"⬇️ ({get_timestamp()}) Z-axis moving DOWN to 5000 steps...", "info")
        time.sleep(3)  # Wait for movement
    
    if send_command_to_arduino(test_z_up):
        log_message(f"⬆️ ({get_timestamp()}) Z-axis moving UP to 0 steps...", "info")
    
    log_message(f"💡 ({get_timestamp()}) Check if Z-axis motor rotates. If not, check hardware connections.", "info")
    return redirect(url_for('index'))

@app.route('/clear_buffer', methods=['POST'])
def clear_buffer():
    """Clear Arduino serial buffer - useful if Arduino is stuck in a loop."""
    global ser
    if ser and ser.is_open:
        try:
            # Read and discard all data in buffer
            bytes_cleared = 0
            start_time = time.time()
            while time.time() - start_time < 0.5:  # Clear for 0.5 seconds
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    bytes_cleared += len(data)
                else:
                    break
                time.sleep(0.05)
            
            ser.flushInput()
            ser.flushOutput()
            
            if bytes_cleared > 0:
                log_message(f"🧹 ({get_timestamp()}) Cleared {bytes_cleared} bytes from buffer.", "info")
            else:
                log_message(f"🧹 ({get_timestamp()}) Buffer already clear.", "info")
        except Exception as e:
            log_message(f"⚠️ ({get_timestamp()}) Error clearing buffer: {str(e)}", "error")
    else:
        log_message(f"⚠️ ({get_timestamp()}) Not connected. Cannot clear buffer.", "error")
    return redirect(url_for('index'))


if __name__ == '__main__':
    log_message(f"Server started at {get_timestamp()}. Please connect to Arduino.", "info")
    log_message(f"💡 Tip: Make sure Arduino IDE Serial Monitor is closed before connecting.", "info")
    app.run(debug=True, host='0.0.0.0', use_reloader=False)