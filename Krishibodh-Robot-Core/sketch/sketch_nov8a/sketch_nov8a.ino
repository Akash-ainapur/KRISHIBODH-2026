#include <AccelStepper.h>

// --- Define Motor Pins (CNC Shield V3 Defaults) ---
const int StepX = 2;
const int DirX = 5;
const int StepY = 3;
const int DirY = 6;
const int StepZ = 4;
const int DirZ = 7;
const int StepA = 12;
const int DirA = 13;



const int relayPin = 10;
const int moistpin = A0;
int moistureDigitalPin = 9;

// --- CONTROL VARIABLE ---
bool useDefaultCoords = false;

// --- Unified Motion Settings ---
const float x_max = 800.0;
const float x_a = 200.0;
const float y_max = 400.0;
const float y_a = 400.0;
const float z_max = 800.0;
const float z_a = 600.0;

// --- Create Stepper Objects for Each Axis ---
AccelStepper stepperX(AccelStepper::DRIVER, StepX, DirX);
AccelStepper stepperY(AccelStepper::DRIVER, StepY, DirY);
AccelStepper stepperZ(AccelStepper::DRIVER, StepZ, DirZ);
AccelStepper stepperA(AccelStepper::DRIVER, StepA, DirA);

// --- Check for Interrupt and Stop Motors ---
bool checkForInterrupt(AccelStepper &stepper) {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    if (command.equalsIgnoreCase("MODE:MANUAL")) {
      Serial.println("INTERRUPT: Stop command received! Switching to Manual Mode.");
      useDefaultCoords = false;
      stepper.stop();
      return true; // Indicate interrupt occurred
    }
  }
  return false; // No interrupt
}

bool checkForInterruptMultiple(AccelStepper &stepperX, AccelStepper &stepperY, AccelStepper &stepperA) {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    if (command.equalsIgnoreCase("MODE:MANUAL")) {
      Serial.println("INTERRUPT: Stop command received! Switching to Manual Mode.");
      useDefaultCoords = false;
      stepperX.stop();
      stepperY.stop();
      stepperA.stop();
      return true; // Indicate interrupt occurred
    }
  }
  return false; // No interrupt
}

int divineMoisture(){
  int moistvalue;
  moistvalue = analogRead(moistpin);
  // Serial.println(moistvalue); // REMOVED: Python will handle printing/logging
  return moistvalue;
}


void waterme(){

  Serial.println("Activating watering relay...");
  digitalWrite(relayPin, HIGH);    // Turn ON relay (use LOW if your module is active low)
  delay(5000);                     // Keep ON for 2 seconds
  digitalWrite(relayPin, LOW);     // Turn OFF relay
  Serial.println("Watering complete.");

}




// --- Simplified Movement Sequence ---
// --- Simplified Movement Sequence ---
// actionMode: 0 = Move Only, 1 = Smart Check, 2 = Force Water
void runMovementSequence(long targetX, long targetY, long targetZ, int actionMode) {
  Serial.println("--- Starting New Movement ---");
  Serial.print("Target -> X: "); Serial.print(targetX);
  Serial.print(", Y: "); Serial.print(targetY);
  Serial.print(", Z: "); Serial.println(targetZ);
  Serial.print("Action Mode: "); Serial.println(actionMode);
  
  // --- PHASE 0: Retract Z-Axis ---
  stepperZ.moveTo(0);
  while (stepperZ.distanceToGo() != 0) {
    stepperZ.run();
    if (actionMode != 2 && checkForInterrupt(stepperZ)) return; // Allow interrupt unless forcing water
  }

  // --- PHASE 1: Move X, Y, and A axes ---
  stepperX.moveTo(targetX);
  stepperA.moveTo(targetX);
  stepperY.moveTo(targetY);
  while (stepperX.distanceToGo() != 0 || stepperY.distanceToGo() != 0 || stepperA.distanceToGo() != 0) {
    stepperX.run();
    stepperY.run();
    stepperA.run();
    if (checkForInterruptMultiple(stepperX, stepperY, stepperA)) return;
  }

  // --- PHASE 2: Move Z axis down ---
  stepperZ.moveTo(targetZ);
  while (stepperZ.distanceToGo() != 0) {
    stepperZ.run();
    if (checkForInterrupt(stepperZ)) return;
  }

  Serial.println("Phase 2 Complete. All movements done.");
  Serial.println("------------------------------------");

  // --- ACTION LOGIC ---
  if(targetX != 0 || targetY != 0 || targetZ != 0) { // Only check/water if not at Home (0,0,0)
    
    if (actionMode == 0) {
      Serial.println("MODE 0: Move Only. No checking, no watering.");
    
    } else if (actionMode == 1) {
      // SMART MODE: Check moisture sensor first
      Serial.println("MODE 1 (SMART): Reading moisture sensor...");
      delay(5000); // Wait for sensor to stabilize
      int moistVal = divineMoisture();
      
      // CRITICAL: Print raw value for Python persistence
      Serial.println(moistVal); 
      
      Serial.print("Moisture value read: ");  
      Serial.println(moistVal);
      
      if(moistVal > 599) {
        waterme();
      } else {
        Serial.println("Soil is moist. Watering skipped.");
      }
      
    } else if (actionMode == 2) {
      // FORCE MODE: Bypass sensor and water immediately
      Serial.println("MODE 2 (FORCE): Bypassing moisture sensor.");
      waterme(); 
    }
  }
}

void setup() {
  Serial.begin(9600);
  Serial.println("--- KRISHIBODH Controller v4.0 (Granular Control) ---");

  

  stepperX.setMaxSpeed(x_max);
  stepperX.setAcceleration(x_a);
  stepperX.setCurrentPosition(0);
  stepperY.setMaxSpeed(y_max);
  stepperY.setAcceleration(y_a);
  stepperY.setCurrentPosition(0);
  stepperZ.setMaxSpeed(z_max);
  stepperZ.setAcceleration(z_a);
  stepperZ.setCurrentPosition(0);
  stepperA.setMaxSpeed(x_max);
  stepperA.setAcceleration(x_a);
  stepperA.setCurrentPosition(0);
  stepperA.setPinsInverted(true, false, false);

  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, LOW);   // Make sure relay is OFF initially
  pinMode(moistureDigitalPin, INPUT);
}

void loop() {

  if (useDefaultCoords) {
    // --- Default Mode ---
    // The default sequence uses smart check (Mode 1)
    runMovementSequence(3000, 1000, 10000, 1); 
    if (!useDefaultCoords) return;

    for(int i=0; i<100; i++){
      delay(10);
      if (checkForInterrupt(stepperZ)) break;
    }
    if (!useDefaultCoords) return;

    // Going home. Mode 1 (Smart) is fine as it won't water at 0,0,0 anyway
    runMovementSequence(0, 0, 0, 1);
    if (!useDefaultCoords) return;

    for(int i=0; i<100; i++){
      delay(10);
      if (checkForInterrupt(stepperZ)) break;
    }
  } else {
    // --- Serial Input Mode ---
    if (Serial.available() > 0) {
      String command = Serial.readStringUntil('\n');
      command.trim();

      if (command.equalsIgnoreCase("MODE:DEFAULT")) {
        Serial.println("Switching to Default Coordinate Mode.");
        useDefaultCoords = true;
        
      } else if (command.equalsIgnoreCase("MODE:MANUAL")) {
        Serial.println("Already in Manual Input Mode.");
        useDefaultCoords = false;
        
      } else {
        // --- PARSE COMMAND PREFIXES ---
        int selectedMode = 1; // Default to Smart Check (Legacy behavior)
        String coords = command;

        if (command.startsWith("MOVE:")) {
          selectedMode = 0;
          coords = command.substring(5); // Remove "MOVE:"
        } 
        else if (command.startsWith("SMART:")) {
          selectedMode = 1;
          coords = command.substring(6); // Remove "SMART:"
        }
        else if (command.startsWith("WATER:")) {
          selectedMode = 2;
          coords = command.substring(6); // Remove "WATER:"
        }
        else if (command.equalsIgnoreCase("MOISTURE:GET")) {
          // NEW CLEAN COMMAND FOR ON-DEMAND READING
          int m = divineMoisture();
          Serial.println(m); // Print ONLY the value for easy parsing
          return;
        }
        else if (command.startsWith("SENSOR:")) {
          // NEW DIAGNOSTIC COMMAND
          Serial.println("--- SENSOR DIAGNOSTIC ---");
          int m = divineMoisture();
          Serial.print("Moisture value read: ");
          Serial.println(m);
          Serial.println("-------------------------");
          return; // Skip movement
        }
        else if (command.startsWith("FORCE_WATER:")) {
          selectedMode = 2;
          coords = command.substring(12); // Remove "FORCE_WATER:"
        }

        long inputX, inputY, inputZ;
        // Use sscanf to parse coordinates from the cleaned string
        int parsed = sscanf(coords.c_str(), "%ld,%ld,%ld", &inputX, &inputY, &inputZ);
        
        if (parsed == 3) {
          runMovementSequence(inputX, inputY, inputZ, selectedMode); 
          Serial.println("Ready for next command.");
        } else {
          Serial.println("Error: Invalid coordinate format.");
        }
      }
    }
  }
}