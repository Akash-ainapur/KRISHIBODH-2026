#pragma once
// Non-blocking motion controller for the KRISHIBODH gantry.
//
// The current firmware BLOCKS: runMovementSequence() sits in
// `while (distanceToGo() != 0)` loops and calls delay(5000), so while the robot
// moves or waits it cannot read a new command except through a special check
// squeezed into every loop. Here nothing ever waits. loop() calls tick() as
// fast as it can; each call does a little work and returns:
//
//   IDLE -> RETRACT_Z -> TRAVEL_XY -> LOWER_Z -> SETTLE -> SENSE -> WATER -> IDLE
//                                          (MOVE stops after LOWER_Z)
//
// Commands arrive as frames (krishi_protocol.h) at any time and wait in a
// fixed-size queue. STOP and MOISTURE_GET are answered immediately.
//
// The hardware is a template parameter (Hal). The Arduino passes a class that
// drives AccelStepper; the PC tests pass a fake robot. Same logic, testable
// without a board. The Hal must provide:
//   void     run();                         step motors a little (non-blocking)
//   void     move_xy_to(int32_t x, int32_t y);
//   void     move_z_to(int32_t z);
//   bool     xy_done();  bool z_done();
//   void     stop_all();
//   uint16_t read_moisture();
//   void     pump(bool on);
//   uint32_t millis();
//   void     send(const krishi::proto::Frame& f);

#include <stddef.h>
#include <stdint.h>

#include "krishi_protocol.h"
#include "sensor_filter.h"

namespace krishi {

// FIFO with a fixed capacity that REFUSES pushes when full (unlike RingBuffer,
// which overwrites). A dropped command must be reported, never silently lost.
template <typename T, size_t N>
class StaticQueue {
public:
    bool push(const T& v) {
        if (size_ == N) return false;
        data_[(head_ + size_) % N] = v;
        ++size_;
        return true;
    }
    bool pop(T& out) {
        if (size_ == 0) return false;
        out = data_[head_];
        head_ = (head_ + 1) % N;
        --size_;
        return true;
    }
    void clear() { head_ = size_ = 0; }
    size_t size() const { return size_; }

private:
    T data_[N];
    size_t head_ = 0;
    size_t size_ = 0;
};

struct MotionConfig {
    uint16_t dry_above = 599;     // same threshold as sketch_nov8a.ino
    uint32_t settle_ms = 5000;    // probe settle time (was delay(5000))
    uint32_t sample_gap_ms = 50;  // gap between the 5 moisture samples
    uint32_t water_ms = 5000;     // pump on-time (was delay(5000) in waterme())
};

template <class Hal>
class MotionController {
public:
    enum State : uint8_t { IDLE, RETRACT_Z, TRAVEL_XY, LOWER_Z, SETTLE, SENSE, WATER };

    explicit MotionController(Hal& hal, MotionConfig cfg = MotionConfig()) : hal_(hal), cfg_(cfg) {}

    // Call for every complete frame received from the PC.
    void on_frame(const proto::Frame& f) {
        switch (f.cmd) {
            case proto::STOP:
                hal_.stop_all();
                hal_.pump(false);
                queue_.clear();
                state_ = IDLE;
                reply(proto::ACK, f.seq);
                return;
            case proto::MOISTURE_GET: {
                reply(proto::ACK, f.seq);
                proto::Frame m = make(proto::MOISTURE, f.seq);
                const uint16_t v = hal_.read_moisture();
                m.len = 2;
                m.payload[0] = static_cast<uint8_t>(v & 0xFF);
                m.payload[1] = static_cast<uint8_t>(v >> 8);
                hal_.send(m);
                return;
            }
            case proto::MOVE:
            case proto::SMART_WATER:
            case proto::FORCE_WATER:
                if (f.len != 12) { nack(f.seq, proto::BAD_LENGTH); return; }
                break;
            case proto::HOME:
                if (f.len != 0) { nack(f.seq, proto::BAD_LENGTH); return; }
                break;
            default:
                nack(f.seq, proto::UNKNOWN_CMD);
                return;
        }
        if (queue_.push(f)) reply(proto::ACK, f.seq);
        else nack(f.seq, proto::QUEUE_FULL);
    }

    // Call from loop() as often as possible. Never blocks.
    void tick() {
        hal_.run();
        const uint32_t now = hal_.millis();
        switch (state_) {
            case IDLE:
                if (queue_.pop(current_)) start(current_);
                break;
            case RETRACT_Z:                      // phase 0: lift the probe clear of plants
                if (hal_.z_done()) { hal_.move_xy_to(tx_, ty_); state_ = TRAVEL_XY; }
                break;
            case TRAVEL_XY:                      // phase 1: X and Y together
                if (hal_.xy_done()) { hal_.move_z_to(tz_); state_ = LOWER_Z; }
                break;
            case LOWER_Z:                        // phase 2: lower the probe
                if (!hal_.z_done()) break;
                if (current_.cmd == proto::MOVE || current_.cmd == proto::HOME || at_home()) finish(false);
                else if (current_.cmd == proto::FORCE_WATER) start_water(now);
                else { timer_ = now; state_ = SETTLE; }
                break;
            case SETTLE:                         // wait for the probe to settle, without delay()
                if (now - timer_ >= cfg_.settle_ms) { samples_ = 0; timer_ = now; state_ = SENSE; }
                break;
            case SENSE:                          // 5 samples -> median, so one spike cannot water
                if (now - timer_ < cfg_.sample_gap_ms) break;
                timer_ = now;
                last_moisture_ = filter_.update(hal_.read_moisture());
                if (++samples_ < 5) break;
                if (last_moisture_ > cfg_.dry_above) start_water(now);
                else finish(false);
                break;
            case WATER:
                if (now - timer_ >= cfg_.water_ms) { hal_.pump(false); finish(true); }
                break;
        }
    }

    State state() const { return state_; }
    size_t queued() const { return queue_.size(); }
    uint16_t last_moisture() const { return last_moisture_; }

private:
    void start(const proto::Frame& f) {
        if (f.cmd == proto::HOME) { tx_ = ty_ = tz_ = 0; }
        else { tx_ = proto::get_i32(f.payload); ty_ = proto::get_i32(f.payload + 4); tz_ = proto::get_i32(f.payload + 8); }
        filter_ = MedianFilter<5>();     // fresh window per visit
        hal_.move_z_to(0);
        state_ = RETRACT_Z;
    }
    void start_water(uint32_t now) { hal_.pump(true); timer_ = now; state_ = WATER; }
    void finish(bool watered) {
        proto::Frame d = make(proto::DONE, current_.seq);
        d.len = 1;
        d.payload[0] = watered ? 1 : 0;
        hal_.send(d);
        state_ = IDLE;
    }
    bool at_home() const { return tx_ == 0 && ty_ == 0 && tz_ == 0; }  // never water at home (as before)
    static proto::Frame make(uint8_t cmd, uint8_t seq) { proto::Frame f; f.seq = seq; f.cmd = cmd; f.len = 0; return f; }
    void reply(uint8_t cmd, uint8_t seq) { hal_.send(make(cmd, seq)); }
    void nack(uint8_t seq, uint8_t reason) {
        proto::Frame f = make(proto::NACK, seq);
        f.len = 1;
        f.payload[0] = reason;
        hal_.send(f);
    }

    Hal& hal_;
    MotionConfig cfg_;
    StaticQueue<proto::Frame, 4> queue_;
    MedianFilter<5> filter_;
    proto::Frame current_ = {};
    State state_ = IDLE;
    int32_t tx_ = 0, ty_ = 0, tz_ = 0;
    uint32_t timer_ = 0;
    uint8_t samples_ = 0;
    uint16_t last_moisture_ = 0;
};

}  // namespace krishi
