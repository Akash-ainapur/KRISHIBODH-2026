#include <algorithm>
#include <random>

#include "check.hpp"
#include "krishi/median.hpp"
#include "sensor_filter.h"

using namespace krishi;

TEST(ring_buffer_overwrites_oldest) {
    RingBuffer<int, 3> rb;
    for (int v : {1, 2, 3, 4, 5}) rb.push(v);
    CHECK_EQ(rb.size(), std::size_t{3});
    CHECK_EQ(rb[0], 3);
    CHECK_EQ(rb[2], 5);
}

TEST(median_filter_ignores_single_spike) {
    MedianFilter<5> f;
    uint16_t out = 0;
    for (int v : {500, 502, 1023, 499, 501}) out = f.update(static_cast<uint16_t>(v));  // 1023 = electrical spike
    CHECK_EQ(out, uint16_t{501});
}

TEST(hysteresis_does_not_flicker) {
    Hysteresis h(600, 560);
    int flips = 0;
    bool prev = h.dry();
    for (int v : {590, 605, 598, 603, 597, 601, 580, 570, 555, 565, 590}) {
        const bool now = h.update(static_cast<uint16_t>(v));
        if (now != prev) ++flips;
        prev = now;
    }
    CHECK_EQ(flips, 2);  // dry once at 605, wet once at 555. A single threshold would flip 6 times.
}

TEST(streaming_median_matches_sorting) {
    std::mt19937 rng(42);
    std::uniform_real_distribution<double> d(0, 1000);
    StreamingMedian sm;
    std::vector<double> all;
    for (int i = 0; i < 501; ++i) {
        const double v = d(rng);
        sm.add(v);
        all.push_back(v);
        std::vector<double> s = all;
        std::sort(s.begin(), s.end());
        const double expect = s.size() % 2 ? s[s.size() / 2] : (s[s.size() / 2 - 1] + s[s.size() / 2]) / 2;
        CHECK_NEAR(sm.median(), expect, 1e-9);
    }
}

TEST(sliding_median_matches_sorting_with_duplicates) {
    std::mt19937 rng(7);
    std::uniform_int_distribution<int> d(0, 5);  // many duplicates: tests erase-one-copy
    const std::size_t k = 7;
    SlidingMedian sw(k);
    std::vector<double> all;
    for (int i = 0; i < 300; ++i) {
        const double v = d(rng);
        sw.add(v);
        all.push_back(v);
        std::vector<double> w(all.end() - static_cast<std::ptrdiff_t>(std::min(k, all.size())), all.end());
        std::sort(w.begin(), w.end());
        const double expect = w.size() % 2 ? w[w.size() / 2] : (w[w.size() / 2 - 1] + w[w.size() / 2]) / 2;
        CHECK_NEAR(sw.median(), expect, 1e-9);
    }
}
