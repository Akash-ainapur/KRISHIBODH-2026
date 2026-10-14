#include "krishi/sensor_history.hpp"

#include <algorithm>
#include <stdexcept>
#include <utility>

namespace krishi {

RangeStats SensorHistory::combine(const RangeStats& a, const RangeStats& b) {
    return {a.count + b.count, std::min(a.min, b.min), std::max(a.max, b.max), a.sum + b.sum};
}

void SensorHistory::rebuild(std::size_t new_cap) {
    cap_ = new_cap;
    tree_.assign(2 * cap_, RangeStats{});  // empty RangeStats is the identity for combine()
    for (std::size_t i = 0; i < readings_.size(); ++i) tree_[cap_ + i] = leaf(readings_[i].value);
    for (std::size_t i = cap_ - 1; i >= 1; --i) tree_[i] = combine(tree_[2 * i], tree_[2 * i + 1]);
}

void SensorHistory::append(Reading r) {
    if (!readings_.empty() && r.t < readings_.back().t)
        throw std::invalid_argument("readings must be appended in time order");
    readings_.push_back(r);
    if (readings_.size() > cap_) {
        rebuild(std::max<std::size_t>(1, cap_ * 2));  // amortised O(1) rebuilds per append
        return;
    }
    // Point update: set the leaf, then walk up recomputing each parent. O(log n).
    std::size_t i = cap_ + readings_.size() - 1;
    tree_[i] = leaf(r.value);
    for (i /= 2; i >= 1; i /= 2) tree_[i] = combine(tree_[2 * i], tree_[2 * i + 1]);
}

std::optional<std::pair<std::size_t, std::size_t>> SensorHistory::index_range(std::int64_t t0, std::int64_t t1) const {
    if (t0 > t1) return std::nullopt;
    auto by_time = [](const Reading& r, std::int64_t t) { return r.t < t; };
    auto lo = std::lower_bound(readings_.begin(), readings_.end(), t0, by_time);
    auto hi = std::upper_bound(readings_.begin(), readings_.end(), t1,
                               [](std::int64_t t, const Reading& r) { return t < r.t; });
    if (lo >= hi) return std::nullopt;
    return std::make_pair(static_cast<std::size_t>(lo - readings_.begin()),
                          static_cast<std::size_t>(hi - readings_.begin()));
}

RangeStats SensorHistory::query(std::int64_t t0, std::int64_t t1) const {
    const auto range = index_range(t0, t1);
    if (!range) return {};
    // Half-open [l, r) on leaves. Climb both ends: when l is a right child it
    // cannot share a parent with anything inside the range, so take it and step
    // right; same for r on the left. Each level does O(1) work: O(log n) total.
    RangeStats left, right;
    for (std::size_t l = range->first + cap_, r = range->second + cap_; l < r; l /= 2, r /= 2) {
        if (l & 1U) left = combine(left, tree_[l++]);
        if (r & 1U) right = combine(tree_[--r], right);
    }
    return combine(left, right);
}

RangeStats SensorHistory::query_naive(std::int64_t t0, std::int64_t t1) const {
    RangeStats s;
    for (const Reading& r : readings_)
        if (r.t >= t0 && r.t <= t1) s = combine(s, leaf(r.value));
    return s;
}

}  // namespace krishi
