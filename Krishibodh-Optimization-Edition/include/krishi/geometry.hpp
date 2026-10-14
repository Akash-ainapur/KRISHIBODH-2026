#pragma once
// Gantry geometry and the motion-time model.
//
// The gantry moves X and Y at the same time (see runMovementSequence in the
// firmware), so a move takes as long as its SLOWER axis. Each axis follows a
// trapezoidal velocity profile from AccelStepper: accelerate, cruise, decelerate.

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>

namespace krishi {

// Position in stepper steps, matching the firmware's coordinate system.
struct Point {
    std::int64_t x = 0;
    std::int64_t y = 0;
    std::int64_t z = 0;
};

struct Plant {
    std::string name;
    Point pos;
};

// One axis: max speed (steps/s) and acceleration (steps/s^2).
struct AxisLimits {
    double max_speed;
    double accel;
};

// Values copied from sketch_nov8a.ino (x_max, x_a, y_max, y_a, z_max, z_a).
struct GantryModel {
    AxisLimits x{800.0, 200.0};
    AxisLimits y{400.0, 400.0};
    AxisLimits z{800.0, 600.0};
    // Every visit retracts Z to 0 and lowers it again (phases 0 and 2).
    bool include_z = true;
};

// Time (s) for one axis to travel `distance` steps from rest to rest.
// Trapezoid if the axis reaches max speed, triangle if it does not.
inline double axis_time(double distance, const AxisLimits& lim) {
    distance = std::fabs(distance);
    if (distance == 0.0) return 0.0;
    const double ramp = lim.max_speed * lim.max_speed / lim.accel;  // distance spent accelerating + braking
    if (distance >= ramp) {
        return distance / lim.max_speed + lim.max_speed / lim.accel;  // trapezoid
    }
    return 2.0 * std::sqrt(distance / lim.accel);                      // triangle
}

// Time (s) to move between two plant positions the way the firmware does it:
// retract Z, move X and Y together, lower Z.
inline double travel_time(const Point& a, const Point& b, const GantryModel& m) {
    const double xy = std::max(axis_time(static_cast<double>(b.x - a.x), m.x),
                               axis_time(static_cast<double>(b.y - a.y), m.y));
    if (!m.include_z) return xy;
    return axis_time(static_cast<double>(a.z), m.z) + xy + axis_time(static_cast<double>(b.z), m.z);
}

}  // namespace krishi
