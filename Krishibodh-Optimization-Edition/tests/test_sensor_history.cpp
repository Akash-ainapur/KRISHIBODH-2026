#include <random>

#include "check.hpp"
#include "krishi/sensor_history.hpp"

using namespace krishi;

TEST(history_matches_naive_scan_on_random_queries) {
    std::mt19937 rng(11);
    std::uniform_real_distribution<double> val(300, 900);
    std::uniform_int_distribution<int> gap(0, 120);  // gap 0 = several readings at the same second
    SensorHistory h;
    std::int64_t t = 1'700'000'000;
    for (int i = 0; i < 2000; ++i) { t += gap(rng); h.append({t, val(rng)}); }

    std::uniform_int_distribution<std::int64_t> pick(1'700'000'000 - 100, t + 100);
    for (int q = 0; q < 500; ++q) {
        std::int64_t a = pick(rng), b = pick(rng);
        if (a > b) std::swap(a, b);
        const RangeStats fast = h.query(a, b), slow = h.query_naive(a, b);
        CHECK_EQ(fast.count, slow.count);
        if (slow.count) {
            CHECK_NEAR(fast.min, slow.min, 1e-9);
            CHECK_NEAR(fast.max, slow.max, 1e-9);
            CHECK_NEAR(fast.sum, slow.sum, 1e-6);
        }
    }
}

TEST(history_empty_and_out_of_range) {
    SensorHistory h;
    CHECK_EQ(h.query(0, 100).count, std::size_t{0});
    h.append({50, 1.0});
    CHECK_EQ(h.query(0, 49).count, std::size_t{0});
    CHECK_EQ(h.query(50, 50).count, std::size_t{1});
    CHECK_EQ(h.query(60, 40).count, std::size_t{0});  // inverted range
}

TEST(history_rejects_out_of_order_append) {
    SensorHistory h;
    h.append({100, 1.0});
    CHECK_THROWS(h.append({99, 2.0}));
}

TEST(history_grows_across_capacity_boundaries) {
    SensorHistory h;
    for (int i = 0; i < 1025; ++i) h.append({i, static_cast<double>(i)});  // crosses 1, 2, 4 ... 1024
    const RangeStats all = h.query(0, 1024);
    CHECK_EQ(all.count, std::size_t{1025});
    CHECK_NEAR(all.min, 0.0, 0);
    CHECK_NEAR(all.max, 1024.0, 0);
    CHECK_NEAR(all.mean(), 512.0, 1e-9);
}
