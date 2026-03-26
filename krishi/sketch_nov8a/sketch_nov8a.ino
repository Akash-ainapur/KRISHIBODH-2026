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
const float z_max = 1800.0;
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
  Serial.println(moistvalue);
  return moistvalue;
}


void waterme(){

  Serial.println("Activating watering relay...");
  digitalWrite(relayPin, HIGH);    // Turn ON relay (use LOW if your module is active low)
  delay(2000);                     // Keep ON for 2 seconds
  digitalWrite(relayPin, LOW);     // Turn OFF relay
  Serial.println("Watering complete.");

}




// --- Simplified Movement Sequence ---
void runMovementSequence(long targetX, long targetY, long targetZ, bool interruptible, bool checkMoisture) {
  Serial.println("--- Starting New Movement ---");
  Serial.print("Target -> X: "); Serial.print(targetX); //[cite: 18]
  Serial.print(", Y: "); Serial.print(targetY);
  Serial.print(", Z: "); Serial.println(targetZ);
  
  // --- PHASE 0: Retract Z-Axis ---
  stepperZ.moveTo(0); //[cite: 19]
  while (stepperZ.distanceToGo() != 0) {
    stepperZ.run();
    if (interruptible && checkForInterrupt(stepperZ)) return; //[cite: 20]
  }

  // --- PHASE 1: Move X, Y, and A axes ---
  stepperX.moveTo(targetX);
  stepperA.moveTo(targetX); //[cite: 21]
  stepperY.moveTo(targetY);
  while (stepperX.distanceToGo() != 0 || stepperY.distanceToGo() != 0 || stepperA.distanceToGo() != 0) {
    stepperX.run();
    stepperY.run();
    stepperA.run(); //[cite: 22]
    if (interruptible && checkForInterruptMultiple(stepperX, stepperY, stepperA)) return;
  }

  // --- PHASE 2: Move Z axis down ---
  stepperZ.moveTo(targetZ);
  while (stepperZ.distanceToGo() != 0) { //[cite: 23]
    stepperZ.run();
    if (interruptible && checkForInterrupt(stepperZ)) return;
  }

  Serial.println("Phase 2 Complete. All movements done."); //[cite: 24]
  Serial.println("------------------------------------");

  // --- NEW LOGIC: Smart Check vs. Force Water ---
  if(targetX != 0 || targetY != 0 || targetZ != 0) { // Only check/water if not at Home (0,0,0)

    if (checkMoisture) {
      // SMART MODE: Check moisture sensor first
      Serial.println("SMART CHECK: Reading moisture sensor...");
      delay(5000); // Wait for sensor to stabilize
      int pankajkumar = divineMoisture(); //[cite: 25]
      Serial.print("Moisture value read: ");  
      Serial.println(pankajkumar);
      
      if(pankajkumar > 599) {
        waterme();
      } else {
        Serial.println("Soil is moist. Watering skipped.");
      }
      
    } else {
      // FORCE MODE: Bypass sensor and water immediately
      Serial.println("FORCE WATER: Bypassing moisture sensor.");
      waterme(); // Water regardless of moisture
    }
  }
}

void setup() {
  Serial.begin(9600);
  Serial.println("--- KRISHIBODH Controller v3.0 (Simplified) ---");

  

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
    // The default sequence should use the smart check
    runMovementSequence(3000, 1000, 10000, true, true); // true = check moisture
    if (!useDefaultCoords) return; //[cite: 29]

    for(int i=0; i<100; i++){
      delay(10);
      if (checkForInterrupt(stepperZ)) break; //[cite: 30]
    }
    if (!useDefaultCoords) return;

    // Going home. The 'true' here doesn't matter as it won't water at 0,0,0
    runMovementSequence(0, 0, 0, true, true); //[cite: 31]
    if (!useDefaultCoords) return;

    for(int i=0; i<100; i++){
      delay(10);
      if (checkForInterrupt(stepperZ)) break; //[cite: 32]
    }
  } else {
    // --- Serial Input Mode ---
    if (Serial.available() > 0) {
      String command = Serial.readStringUntil('\n');
      command.trim(); //[cite: 33]

      if (command.equalsIgnoreCase("MODE:DEFAULT")) {
        Serial.println("Switching to Default Coordinate Mode.");
        useDefaultCoords = true; //[cite: 34]
        
      } else if (command.equalsIgnoreCase("MODE:MANUAL")) {
        Serial.println("Already in Manual Input Mode.");
        useDefaultCoords = false; //[cite: 35]
        
      // --- NEW LOGIC BLOCK ---
      } else if (command.startsWith("FORCE_WATER:")) {
        Serial.println("FORCE_WATER command received.");
        
        // Extract coordinates after "FORCE_WATER:" (12 characters)
        String coords = command.substring(12);
        
        long inputX, inputY, inputZ;
        int parsed = sscanf(coords.c_str(), "%ld,%ld,%ld", &inputX, &inputY, &inputZ);
        
        if (parsed == 3) {
          // Call sequence, 'false' means DO NOT check moisture
          runMovementSequence(inputX, inputY, inputZ, false, false); 
          Serial.println("Ready for next command.");
        } else {
          Serial.println("Error: Invalid FORCE_WATER coordinate format.");
        }
        
      // --- END NEW LOGIC BLOCK ---
        
      } else {
        // This is the original "smart" coordinate command
        long inputX, inputY, inputZ;
        int parsed = sscanf(command.c_str(), "%ld,%ld,%ld", &inputX, &inputY, &inputZ); //[cite: 36]
        
        if (parsed == 3) {
          // Call sequence, 'true' means DO check moisture
          runMovementSequence(inputX, inputY, inputZ, false, true); 
          Serial.println("Ready for next command."); //[cite: 37]
        } else {
          Serial.println("Error: Invalid coordinate format."); //[cite: 38]
        }
      }
    }
  }
}