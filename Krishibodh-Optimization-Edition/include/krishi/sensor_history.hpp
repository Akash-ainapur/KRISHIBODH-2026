#pragma once
// Sensor history: store every moisture reading and answer
// "min / max / average between time t0 and t1" in O(log n).
//
// Two ideas combined:
//   1. Readings arrive in time order, so timestamps are sorted: binary search
//      (std::lower_bound) turns [t0, t1] into an index range [l, r) in O(log n).
//   2. A segment tree over the values answers min/max/sum on any index range
//      in O(log n), instead of scanning every reading in the range (O(n)).
//
// The tree is iterative ("bottom-up"): leaves live at tree_[cap_ + i], and the
// parent of node i is i / 2. Capacity doubles when full and the tree is
// rebuilt, so append is amortised O(log n), the same trick std::vector uses.

#include <cstddef>
#include <cstdint>
#include <limits>
#include <optional>
#include <vector>

namespace krishi {

struct Reading {
    std::int64_t t;   // unix seconds
    double value;
};

struct RangeStats {
    std::size_t count = 0;
    double min = std::numeric_limits<double>::infinity();
    double max = -std::numeric_limits<double>::infinity();
    double sum = 0.0;
    double mean() const { return count ? sum / static_cast<double>(count) : 0.0; }
};

class SensorHistory {
public:
    // Readings must arrive in non-decreasing time order (throws otherwise).
    void append(Reading r);
    // Stats over readings with t0 <= t <= t1. count == 0 if none.
    RangeStats query(std::int64_t t0, std::int64_t t1) const;
    // Same answer by scanning every reading: the O(n) baseline for tests and benchmarks.
    RangeStats query_naive(std::int64_t t0, std::int64_t t1) const;

    std::size_t size() const { return readings_.size(); }

private:
    static RangeStats combine(const RangeStats& a, const RangeStats& b);
    static RangeStats leaf(double v) { return {1, v, v, v}; }
    void rebuild(std::size_t new_cap);
    std::optional<std::pair<std::size_t, std::size_t>> index_range(std::int64_t t0, std::int64_t t1) const;

    std::vector<Reading> readings_;
    std::vector<RangeStats> tree_;  // size 2 * cap_; tree_[1] is the root
    std::size_t cap_ = 0;
};

}  // namespace krishi
