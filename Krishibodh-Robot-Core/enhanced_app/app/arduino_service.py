import serial
from serial.tools import list_ports
import time
import threading
from .utils import log_message, get_timestamp

PLANT_LOCATIONS = {
    "PLANT_1": "2000,800,10000",
    "PLANT_2": "3000,1500,10000"
}

class ArduinoService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ArduinoService, cls).__new__(cls)
                    cls._instance.ser = None
                    cls._instance.stop_thread = False
                    cls._instance.is_listening = False
                    cls._instance.current_action = "IDLE"
        return cls._instance

    def get_available_ports(self):
        return [p.device for p in list_ports.comports()]

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def get_connected_port(self):
        if self.is_connected():
            return self.ser.port
        return "None"

    def connect(self, port, baud_rate=9600):
        if self.ser and self.ser.is_open:
            self.disconnect()
        
        try:
            # Attempt connection
            self.ser = serial.Serial(port, baud_rate, timeout=1, write_timeout=1)
            time.sleep(2.5) # Wait for reset
            self.ser.flushInput()
            self.ser.flushOutput()
            
            log_message(f"✅ Connected to {port}", "success")
            
            # Start listener
            self.start_listener()
            return True
        except Exception as e:
            log_message(f"❌ Connection failed: {str(e)}", "error")
            self.ser = None
            return False

    def disconnect(self):
        self.stop_thread = True
        if self.ser:
            try:
                port = self.ser.port
                self.ser.close()
                log_message(f"🔌 Disconnected from {port}", "info")
            except:
                pass
            self.ser = None

    def send_command(self, command):
        if not self.is_connected():
            log_message("⚠️ Not connected to Arduino.", "error")
            return False
            
        try:
            cmd_with_newline = command.strip() + '\n'
            self.ser.write(cmd_with_newline.encode('utf-8'))
            self.ser.flushOutput()
            log_message(f"📤 Sent: {command}", "info")
            return True
        except Exception as e:
            log_message(f"❌ Send failed: {e}", "error")
            return False

    def start_listener(self):
        if self.is_listening: 
            return
        
        self.stop_thread = False
        self.is_listening = True
        t = threading.Thread(target=self._listener_loop, daemon=True)
        t.start()

    def _listener_loop(self):
        log_message("📡 Background Listener Started", "info")
        while not self.stop_thread:
            if self.ser and self.ser.is_open:
                try:
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                             # Check if it's a moisture reading (digits)
                            if line.isdigit():
                                log_message(f"💧 Moisture: {line}", "info")
                                from .utils import persist_reading
                                persist_reading(line, action=self.current_action)
                                self.current_action = "IDLE" # Reset after saving
                            else:
                                log_message(f"📥 Arduino: {line}", "info")
                    else:
                        time.sleep(0.1)
                except Exception:
                    break
            else:
                time.sleep(1)
        self.is_listening = False
        log_message("📡 Background Listener Stopped", "info")

# Global instance
arduino = ArduinoService()
