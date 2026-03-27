import serial
import time

# Simple script to test Arduino communication directly
PORT = "COM5"  # Change if needed
BAUD = 9600

print("=" * 50)
print("DIRECT SERIAL TEST")
print("=" * 50)

try:
    # Open connection
    print(f"\n1. Connecting to {PORT}...")
    ser = serial.Serial(PORT, BAUD, timeout=2)
    time.sleep(2.5)  # Wait for Arduino reset
    
    # Clear buffer
    print("2. Clearing buffer...")
    ser.flushInput()
    ser.flushOutput()
    time.sleep(0.5)
    
    # Read any startup messages
    print("3. Reading startup messages...")
    while ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print(f"   Arduino: {line}")
    
    # Send test command
    print("\n4. Sending 'SENSOR:CHECK' command...")
    ser.write(b"SENSOR:CHECK\n")
    ser.flush()
    
    # Read responses for 5 seconds
    print("5. Listening for responses (5 seconds)...\n")
    start = time.time()
    while time.time() - start < 5:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f"   >>> {line}")
                # Check if it's a number
                if line.isdigit():
                    print(f"   ✅ MOISTURE VALUE DETECTED: {line}")
        time.sleep(0.1)
    
    print("\n6. Closing connection...")
    ser.close()
    print("✅ Test complete!")
    
except serial.SerialException as e:
    print(f"❌ Serial Error: {e}")
    print("\nTroubleshooting:")
    print("  - Is the Arduino connected?")
    print("  - Is the Serial Monitor closed?")
    print("  - Is the correct COM port selected?")
except Exception as e:
    print(f"❌ Unexpected Error: {e}")

print("\n" + "=" * 50)
