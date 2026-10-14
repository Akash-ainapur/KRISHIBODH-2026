// KRISHIBODH motion firmware, optimization edition.
//
// STATUS: the logic in motion_fsm.h is unit-tested on the PC with a fake robot,
// but THIS FILE has not been compiled or flashed yet. Test on the bench with
// the gantry lifted before trusting it near plants.
//
// Same pins and motion limits as sketch_nov8a.ino. What changed:
//   - non-blocking state machine (no delay(), no busy-wait loops)
//   - binary frames with CRC instead of text commands
//   - median-of-5 moisture reading instead of a single analogRead
//   - commands queue up (4 deep) and are ACKed / NACKed

#include <AccelStepper.h>

#include "krishi_protocol.h"
#include "sensor_filter.h"
#include "motion_fsm.h"

using namespace krishi;

// --- Pins (CNC Shield V3), unchanged ---------------------------------------
const int StepX = 2, DirX = 5;
const int StepY = 3, DirY = 6;
const int StepZ = 4, DirZ = 7;
const int StepA = 12, DirA = 13;  // second X motor, mirrored
const int relayPin = 10;
const int moistPin = A0;

AccelStepper stepperX(AccelStepper::DRIVER, StepX, DirX);
AccelStepper stepperY(AccelStepper::DRIVER, StepY, DirY);
AccelStepper stepperZ(AccelStepper::DRIVER, StepZ, DirZ);
AccelStepper stepperA(AccelStepper::DRIVER, StepA, DirA);

// The hardware adapter MotionController expects (see motion_fsm.h).
struct ArduinoHal {
    void run() { stepperX.run(); stepperA.run(); stepperY.run(); stepperZ.run(); }
    void move_xy_to(int32_t x, int32_t y) { stepperX.moveTo(x); stepperA.moveTo(x); stepperY.moveTo(y); }
    void move_z_to(int32_t z) { stepperZ.moveTo(z); }
    bool xy_done() { return stepperX.distanceToGo() == 0 && stepperA.distanceToGo() == 0 && stepperY.distanceToGo() == 0; }
    bool z_done() { return stepperZ.distanceToGo() == 0; }
    void stop_all() { stepperX.stop(); stepperA.stop(); stepperY.stop(); stepperZ.stop(); }
    uint16_t read_moisture() { return static_cast<uint16_t>(analogRead(moistPin)); }
    void pump(bool on) { digitalWrite(relayPin, on ? HIGH : LOW); }
    uint32_t millis() { return ::millis(); }
    void send(const proto::Frame& f) {
        uint8_t out[proto::kMaxEncoded];
        const size_t n = proto::encode_frame(f, out);
        Serial.write(out, n);
    }
};

ArduinoHal hal;
MotionController<ArduinoHal> controller(hal);
proto::FrameDecoder decoder;

void setup() {
    Serial.begin(115200);  // binary frames are short; a faster link cuts latency

    stepperX.setMaxSpeed(800.0); stepperX.setAcceleration(200.0);
    stepperA.setMaxSpeed(800.0); stepperA.setAcceleration(200.0);
    stepperA.setPinsInverted(true, false, false);
    stepperY.setMaxSpeed(400.0); stepperY.setAcceleration(400.0);
    stepperZ.setMaxSpeed(800.0); stepperZ.setAcceleration(600.0);
    stepperX.setCurrentPosition(0); stepperA.setCurrentPosition(0);
    stepperY.setCurrentPosition(0); stepperZ.setCurrentPosition(0);

    pinMode(relayPin, OUTPUT);
    digitalWrite(relayPin, LOW);
}

void loop() {
    // Read whatever bytes have arrived; never wait for more.
    proto::Frame f;
    while (Serial.available() > 0) {
        if (decoder.feed(static_cast<uint8_t>(Serial.read()), f) == proto::FrameDecoder::GOT_FRAME) {
            controller.on_frame(f);
        }
        // BAD_FRAME: dropped silently; the PC retries when no ACK arrives.
    }
    controller.tick();
}
