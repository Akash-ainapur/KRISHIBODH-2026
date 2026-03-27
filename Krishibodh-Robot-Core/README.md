# Krishibodh: Autonomous Precision Agriculture Robot

**Krishibodh** ("Agriculture Knowledge") is a Cartesian Gantry Robot designed to conduct scientific experiments comparing "Smart" vs. "Fixed Schedule" irrigation strategies. It combines a Python-based AI brain with an Arduino-controlled hardware motion system.

## 🤖 Hardware Architecture

The system is built on a custom CNC-style gantry frame.

### 1. Motion System (Cartesian Gantry)
*   **Controller**: Arduino Uno with **CNC Shield V3**.
*   **X-Axis (Gantry movement)**: Powered by **Two Stepper Motors** (Dual Drive) on pins `StepX/DirX` and `StepA/DirA` (A-axis is a slave to X).
*   **Y-Axis (Carriage)**: Single motor on `StepY/DirY`.
*   **Z-Axis (Tool Head)**: Vertical actuator on `StepZ/DirZ`.

### 2. Tool Head (End Effector)
*   **Moisture Sensor**: Analog Capacitive Sensor (Pin `A1`). Lowers into the soil to read moisture capabilities.
*   **Irrigation**: Relay Module (Pin `10`) controlling a Water Pump.
*   **Vision**: USB Webcam mounted on the carriage for plant growth analysis.

---

## 🧠 Software Architecture

### 1. Frontend & Control Server (`/frontend`)
*   **Tech**: Python (Flask).
*   **Role**: Acts as the "Ground Station". Hosting the web UI and handling Serial communication with the Arduino.
*   **Key Features**:
    *   Manual Control Interface.
    *   Real-time Serial Logging.
    *   **AI Command Endpoint** (`/ai_command`) for receiving instructions from the experiment runner.

### 2. Firmware (`/sketch`)
*   **Tech**: C++ (Arduino).
*   **Role**: Handles real-time motor control and safety checks.
*   **Modes**:
    *   **Move Only (`MOVE:x,y,z`)**: Moves to coordinates. **Safety**: Does NOT trigger water pump. Used for camera positioning.
    *   **Smart Check (`SMART:x,y,z`)**: Moves -> Lowers Z -> Checks Sensor -> Waters IF dry.
    *   **Force Water (`WATER:x,y,z`)**: Moves -> Lowers Z -> Waters immediately (Fixed schedule).

### 3. Experiment Runner (`/`)
*   **Tech**: Python (`experiment_runner.py`).
*   **Role**: The "Brain" of the experiment.
    *   Reads `experiment_config.json`.
    *   Orchestrates the robot to move to plants, take photos (Z=0), and then water (Z=Low).
    *   Uses `camera_utils.py` for image capture.

---

## 🧪 Scientific Experiment Logic

The robot autonomously manages two plants to test the hypothesis: **"Smart watering leads to better growth than fixed intervals."**

| Factor | Plant A (Smart) | Plant B (Fixed) |
| :--- | :--- | :--- |
| **Location** | `(2000, 800)` | `(3000, 1500)` |
| **Logic** | Checks moisture sensor. Waters **ONLY if dry** (<600). | Waters on a **fixed timer** (e.g., every 24h) regardless of moisture. |
| **Data** | Visual Growth (Camera) + Water Usage. | Visual Growth (Camera) + Water Usage. |

---

## 🚀 How to Run

### Prerequisite: Setup Support
1.  Connect Hardware (Arduino via USB, Camera via USB).
2.  Upload `sketch/sketch_nov8a.ino` to Arduino.

### Step 1: Start the Server (Terminal 1)
```powershell
cd frontend
python app.py
```
*Access UI at `http://localhost:5000`*

### Step 2: Run Experiment (Terminal 2)
```powershell
# Install dependencies
pip install requests opencv-python

# Run Automation
python experiment_runner.py
```
