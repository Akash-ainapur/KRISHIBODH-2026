// MINIMAL SENSOR TEST - Upload this to diagnose the sensor
// This sketch ONLY reads the sensor and prints values every second

const int moistpin = A0;  // Your sensor pin

void setup() {
  Serial.begin(9600);
  Serial.println("=== MINIMAL SENSOR TEST ===");
  Serial.println("Reading from pin A0 every second...");
  Serial.println("===========================");
  pinMode(moistpin, INPUT);
}

void loop() {
  // Read the sensor
  int value = analogRead(moistpin);
  
  // Print it
  Serial.print("Sensor Value: ");
  Serial.println(value);
  
  // Wait 1 second
  delay(1000);
}
