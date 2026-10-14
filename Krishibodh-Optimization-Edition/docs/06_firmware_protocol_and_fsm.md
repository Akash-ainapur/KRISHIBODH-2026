# 06. Firmware: binary protocol and a non-blocking state machine

**Files:** `firmware/krishi_motion/krishi_protocol.h`, `motion_fsm.h`, `krishi_motion.ino`; PC side `include/krishi/protocol.hpp`, `src/protocol.cpp`; tests `tests/test_protocol.cpp`, `tests/test_motion_fsm.cpp`
**Concepts:** CRC (bit manipulation), byte stuffing (COBS), finite-state machines, queues, dependency injection via templates

> **Status:** the protocol and state machine are unit-tested on the PC. `krishi_motion.ino` has **not** been compiled with the Arduino toolchain or flashed yet. Bench-test it with the gantry lifted first.

## Part A: what is wrong with the current firmware

| Today (`sketch_nov8a.ino`) | Problem |
|---|---|
| `while (stepper.distanceToGo() != 0) stepper.run();` | **Blocks.** Nothing else happens while the gantry moves. |
| `delay(5000)` for the probe and the pump | **Blocks** for 5 s. It cannot answer "what's the moisture?" or "stop!" |
| Text commands, `"SMART:2000,800,10000"` | A flipped bit silently becomes a different coordinate. |
| `"Ready for next command."` parsed from text | Fragile. Change the wording and the Python side breaks. |
| One `analogRead()` decides watering | A spike waters a wet plant (see doc 03). |

## Part B: the wire protocol (`krishi_protocol.h`)

```
COBS( seq | cmd | len | payload[len] | crc_hi | crc_lo )  0x00
```
- **seq:** increments per command. The robot's ACK/DONE echo it, so the PC knows which command a reply belongs to.
- **CRC-16/CCITT-FALSE:** a checksum computed from the bytes. Any single flipped bit changes it. The test flips **every single bit** of a frame and confirms every corrupted frame is rejected.
- **COBS (Consistent Overhead Byte Stuffing):** rewrites the frame so it contains no `0x00` bytes. That makes `0x00` a safe end-of-frame marker. If bytes are lost, the receiver throws away the broken frame and starts fresh at the next `0x00`. Overhead: at most 1 byte per 254.
- **Little-endian helpers** (`put_i32` / `get_i32`): byte order is written out explicitly. Never `memcpy` a struct between two different machines.

The same header compiles on the Arduino and the PC: no STL, no heap, fixed buffers. One source of truth, so the two sides can never disagree about the format.

`krishi frame 2000 800 10000` shows the two side by side:
- text, 21 bytes, no error check: `SMART:2000,800,10000`
- binary, 19 bytes, CRC + framing: `06 01 02 0C D0 07 01 03 20 03 01 03 10 27 01 03 CA 1D 00`

### How CRC works, in one paragraph
Treat the message as one giant binary number and divide it by a fixed polynomial (0x1021), using XOR instead of subtraction. The remainder is the CRC. The receiver repeats the division; a different remainder means the data changed. The bitwise version does 8 shift/XOR steps per byte, which needs tiny code and no table, right for the Arduino. The table version precomputes all 256 one-byte results (built at compile time with `constexpr`), so it does one lookup per byte. It is 2.5× faster on the PC in our benchmark, but its 512-byte table is a quarter of an Uno's RAM.

## Part C: the non-blocking state machine (`motion_fsm.h`)

```
IDLE → RETRACT_Z → TRAVEL_XY → LOWER_Z → SETTLE → SENSE → WATER → IDLE
                                   └─ MOVE / HOME / FORCE_WATER skip what they don't need
```
`loop()` calls `tick()` thousands of times per second. Each call steps the motors a little, checks **one** condition, maybe changes state, and **returns immediately**. Waiting is done by comparing timestamps, never by `delay()`:
```cpp
case SETTLE:
    if (now - timer_ >= cfg_.settle_ms) { ... state_ = SENSE; }
```
While it waits, `loop()` keeps reading the serial port, so STOP and MOISTURE_GET are answered **instantly**, even halfway through a 5-second settle. The test `stays_responsive_during_long_settle` proves that.

### Details that matter
- **Command queue (4 deep):** commands are ACKed and queued while the robot is busy. `StaticQueue` **refuses** a push when full and sends NACK `QUEUE_FULL`. A command must never be silently dropped. (The ring buffer from doc 03 overwrites instead, which suits sensor readings but not commands.)
- **Median-of-5 sensing:** one spike can no longer water a wet plant (`spike_does_not_trigger_watering`).
- **`millis()` wraparound:** `millis()` overflows back to 0 after about 49.7 days. `now - timer_` with **unsigned** integers still gives the right interval across the overflow, while `now >= timer_ + 5000` would not. A test starts the clock 2 seconds before overflow.
- **Retract before travel:** a test checks that X and Y never move while the probe is lowered.

### Testing firmware without hardware: templates as dependency injection
`MotionController<Hal>` takes the hardware as a template parameter:
- on the Arduino, `Hal` = `ArduinoHal` (AccelStepper, `analogRead`, the relay)
- in the tests, `Hal` = `FakeHal`, a pretend robot that moves 500 steps per tick and lets the test control time and moisture

The logic is identical; only the hardware is swapped. That is how embedded teams test firmware on a laptop in CI.

## Interview questions
1. **Why is `delay()` bad in firmware?** The CPU does nothing else: no serial reading, no sensor checks, no emergency stop. A state machine with timestamps keeps the loop running.
2. **What does a CRC detect?** All single-bit errors, all 2-bit errors within its range, all odd numbers of bit errors (with this polynomial), and all burst errors up to 16 bits long. It does **not** protect against deliberate tampering; that needs a cryptographic MAC.
3. **Why COBS instead of "escape" bytes like SLIP?** COBS has a fixed worst-case overhead (1 byte per 254). Escaping can double the size in the worst case.
4. **Interrupts vs polling?** We poll `Serial.available()` in `loop()`. The Arduino's UART already receives bytes in an interrupt into a 64-byte buffer, so polling every loop is enough as long as the loop never blocks, which is exactly why non-blocking matters.
5. **What does `volatile` mean in embedded C++?** "This value can change outside the program's control (an interrupt or a hardware register), so always re-read it." It is not a thread-synchronisation tool.
6. **What surprises a PC programmer on an 8-bit AVR?** `int` is **16 bits**. `byte << 8` promotes the byte to a signed 16-bit int, so for bytes ≥ 128 it overflows: undefined behaviour. The CRC code widens to `uint16_t` before shifting for exactly this reason. Tests on a PC (32-bit `int`) cannot catch it, so reason about the target's types, or use fixed-width types (`uint16_t`, `int32_t`) everywhere, as this code does.
7. **Template vs virtual-function interface for the HAL?** A template has no run-time cost and is fully inlined, but each `Hal` produces its own compiled copy. Virtual functions share one copy and allow swapping at run time, at the cost of an indirect call. On an 8-bit MCU, the template is the usual choice.

## What your team still needs to do
1. Compile `krishi_motion.ino` in the Arduino IDE (it needs the AccelStepper library), and fix anything avr-gcc rejects.
2. Bench-test with the gantry lifted: MOVE, then STOP mid-move, then SMART_WATER with the probe in dry and in wet soil.
3. Update the Python `arduino_service.py` to send frames (it can import the same format via `struct.pack` plus a small COBS function) and to wait for ACK/DONE by `seq`, retrying when no ACK arrives.
