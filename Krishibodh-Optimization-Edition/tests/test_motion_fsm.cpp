// Tests the firmware state machine on the PC with a fake robot.

#include "check.hpp"
#include "krishi/protocol.hpp"
#include "motion_fsm.h"

using namespace krishi;

namespace {

// A pretend gantry: each run() moves every axis up to `speed` steps toward its target.
struct FakeHal {
    long x = 0, y = 0, z = 0, tx = 0, ty = 0, tz = 0;
    long speed = 500;
    uint32_t now = 0;
    uint16_t moisture = 500;
    int reads = 0;
    int spike_on_read = -1;  // which read returns a 1023 electrical spike (-1 = never)
    bool pump_on = false;
    int pump_cycles = 0;
    std::vector<proto::Frame> sent;

    static long step(long pos, long target, long by) {
        if (pos < target) return std::min(pos + by, target);
        return std::max(pos - by, target);
    }
    void run() { x = step(x, tx, speed); y = step(y, ty, speed); z = step(z, tz, speed); }
    void move_xy_to(int32_t ax, int32_t ay) { tx = ax; ty = ay; }
    void move_z_to(int32_t az) { tz = az; }
    bool xy_done() { return x == tx && y == ty; }
    bool z_done() { return z == tz; }
    void stop_all() { tx = x; ty = y; tz = z; }
    uint16_t read_moisture() { return reads++ == spike_on_read ? uint16_t{1023} : moisture; }
    void pump(bool on) { if (on && !pump_on) ++pump_cycles; pump_on = on; }
    uint32_t millis() { return now; }
    void send(const proto::Frame& f) { sent.push_back(f); }

    int count(uint8_t cmd) const {
        int n = 0;
        for (const auto& f : sent) n += f.cmd == cmd;
        return n;
    }
};

// Advances simulated time 10 ms per tick until idle (or a safety limit).
void run_to_idle(MotionController<FakeHal>& c, FakeHal& hal, int max_ticks = 100000) {
    for (int i = 0; i < max_ticks; ++i) {
        hal.now += 10;
        c.tick();
        if (c.state() == MotionController<FakeHal>::IDLE && c.queued() == 0) return;
    }
}

}  // namespace

TEST(smart_water_waters_only_when_dry) {
    FakeHal hal;
    MotionController<FakeHal> c(hal);
    hal.moisture = 450;  // wet
    c.on_frame(make_move(1, proto::SMART_WATER, {2000, 800, 1000}));
    run_to_idle(c, hal);
    CHECK_EQ(hal.pump_cycles, 0);
    CHECK_EQ(hal.x, 2000L);

    hal.moisture = 700;  // dry
    c.on_frame(make_move(2, proto::SMART_WATER, {3000, 1500, 1000}));
    run_to_idle(c, hal);
    CHECK_EQ(hal.pump_cycles, 1);
    CHECK(!hal.pump_on);
    CHECK_EQ(hal.sent.back().cmd, std::uint8_t{proto::DONE});
    CHECK_EQ(hal.sent.back().payload[0], std::uint8_t{1});
}

TEST(retracts_z_before_moving_xy) {
    FakeHal hal;
    hal.z = 1000; hal.tz = 1000;  // probe starts lowered
    MotionController<FakeHal> c(hal);
    c.on_frame(make_move(1, proto::MOVE, {5000, 0, 1000}));
    bool xy_moved_while_lowered = false;
    for (int i = 0; i < 1000 && !(c.state() == MotionController<FakeHal>::IDLE && i > 0); ++i) {
        hal.now += 10;
        const long before = hal.x;
        c.tick();
        if (hal.x != before && hal.z != 0) xy_moved_while_lowered = true;
    }
    CHECK(!xy_moved_while_lowered);
}

TEST(stays_responsive_during_long_settle) {
    FakeHal hal;
    MotionController<FakeHal> c(hal);
    c.on_frame(make_move(1, proto::SMART_WATER, {100, 100, 100}));
    for (int i = 0; i < 20; ++i) { hal.now += 10; c.tick(); }  // now in SETTLE (5 s wait)
    CHECK_EQ(int{c.state()}, int{MotionController<FakeHal>::SETTLE});
    c.on_frame(proto::Frame{7, proto::MOISTURE_GET, 0, {}});  // old firmware could not answer here
    CHECK_EQ(hal.sent.back().cmd, std::uint8_t{proto::MOISTURE});
    CHECK_EQ(hal.sent.back().seq, std::uint8_t{7});
}

TEST(spike_does_not_trigger_watering) {
    FakeHal hal;
    MotionController<FakeHal> c(hal);
    hal.moisture = 450;      // wet
    hal.spike_on_read = 2;   // the 3rd of 5 samples is a spike
    c.on_frame(make_move(1, proto::SMART_WATER, {100, 0, 100}));
    run_to_idle(c, hal);
    CHECK_EQ(hal.reads, 5);
    CHECK_EQ(hal.pump_cycles, 0);  // the old single-read firmware would have watered on this spike
}

TEST(stop_aborts_and_clears_queue) {
    FakeHal hal;
    MotionController<FakeHal> c(hal);
    c.on_frame(make_move(1, proto::FORCE_WATER, {6000, 3000, 100}));
    c.on_frame(make_move(2, proto::MOVE, {100, 100, 0}));
    for (int i = 0; i < 3; ++i) { hal.now += 10; c.tick(); }
    c.on_frame(proto::Frame{3, proto::STOP, 0, {}});
    CHECK_EQ(int{c.state()}, int{MotionController<FakeHal>::IDLE});
    CHECK_EQ(c.queued(), std::size_t{0});
    CHECK(!hal.pump_on);
}

TEST(queue_full_and_bad_frames_are_nacked) {
    FakeHal hal;
    MotionController<FakeHal> c(hal);
    for (uint8_t s = 1; s <= 5; ++s) c.on_frame(make_move(s, proto::MOVE, {s, s, 0}));  // queue holds 4
    CHECK_EQ(hal.count(proto::ACK), 4);
    CHECK_EQ(hal.count(proto::NACK), 1);
    c.on_frame(proto::Frame{9, proto::MOVE, 3, {}});  // MOVE needs 12 bytes
    c.on_frame(proto::Frame{10, 0x7E, 0, {}});        // unknown command
    CHECK_EQ(hal.count(proto::NACK), 3);
}

TEST(millis_wraparound_is_safe) {
    FakeHal hal;
    hal.now = 0xFFFFFFFFu - 2000;  // millis() overflows after ~49.7 days of uptime
    MotionController<FakeHal> c(hal);
    hal.moisture = 700;
    c.on_frame(make_move(1, proto::SMART_WATER, {100, 0, 100}));
    run_to_idle(c, hal);
    CHECK_EQ(hal.pump_cycles, 1);  // unsigned subtraction (now - timer) still measures the interval
    CHECK(!hal.pump_on);
}
