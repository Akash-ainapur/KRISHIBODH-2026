// Benchmarks: each compares the new approach with the obvious baseline.
// All inputs are synthetic and seeded, so runs are repeatable. Numbers depend
// on the machine; quote them as "on <machine>, synthetic data".

#include <chrono>
#include <cstdio>
#include <random>

#include "krishi/leaf_spots.hpp"
#include "krishi/protocol.hpp"
#include "krishi/route_planner.hpp"
#include "krishi/sensor_history.hpp"
#include "sensor_filter.h"

using namespace krishi;
using Clock = std::chrono::steady_clock;

template <class F>
double ms(F&& f, int reps = 1) {
    const auto t0 = Clock::now();
    for (int i = 0; i < reps; ++i) f();
    return std::chrono::duration<double, std::milli>(Clock::now() - t0).count() / reps;
}

static volatile double sink;  // stops the optimizer deleting "unused" work

std::vector<Plant> random_bed(std::size_t n, std::mt19937& rng) {
    std::uniform_int_distribution<int> x(0, 6000), y(0, 3000);
    std::vector<Plant> v;
    for (std::size_t i = 0; i < n; ++i) v.push_back({"P", {x(rng), y(rng), 10000}});
    return v;
}

void bench_routes() {
    std::puts("== 1. Route planner: gantry time to visit every plant (avg of 50 random beds) ==");
    std::printf("%7s %12s %12s %12s %12s %14s\n", "plants", "fixed s", "NN+2opt s", "optimal s", "saved", "held-karp ms");
    std::mt19937 rng(2026);
    for (std::size_t n : {5, 10, 14}) {
        double fixed = 0, heur = 0, opt = 0, hk_ms = 0;
        for (int trial = 0; trial < 50; ++trial) {
            RoutePlanner rp({0, 0, 0}, random_bed(n, rng));
            fixed += rp.fixed_order().seconds;
            heur += rp.two_opt(rp.nearest_neighbour()).seconds;
            Route best;
            hk_ms += ms([&] { best = rp.held_karp(); });
            opt += best.seconds;
        }
        std::printf("%7zu %12.1f %12.1f %12.1f %11.1f%% %14.2f\n", n, fixed / 50, heur / 50, opt / 50,
                    100.0 * (fixed - opt) / fixed, hk_ms / 50);
    }
    std::printf("%7s %12s %12s %12s %12s %14s\n", "", "", "", "", "", "2-opt ms");
    for (std::size_t n : {50, 200}) {
        RoutePlanner rp({0, 0, 0}, random_bed(n, rng));
        Route r;
        const double t = ms([&] { r = rp.two_opt(rp.nearest_neighbour()); });
        const double f = rp.fixed_order().seconds;
        std::printf("%7zu %12.1f %12.1f %12s %11.1f%% %14.2f\n", n, f, r.seconds, "(too big)", 100.0 * (f - r.seconds) / f, t);
    }
}

void bench_history() {
    std::puts("\n== 2. Sensor history: 1 year of readings every 5 min, 10,000 random range queries ==");
    SensorHistory h;
    std::mt19937 rng(1);
    std::normal_distribution<double> v(600, 60);
    const std::int64_t start = 1'700'000'000;
    const int n = 365 * 24 * 12;
    const double build = ms([&] { for (int i = 0; i < n; ++i) h.append({start + 300LL * i, v(rng)}); });
    std::uniform_int_distribution<std::int64_t> t(start, start + 300LL * n);
    std::vector<std::pair<std::int64_t, std::int64_t>> qs;
    for (int i = 0; i < 10000; ++i) { auto a = t(rng), b = t(rng); qs.push_back({std::min(a, b), std::max(a, b)}); }
    double acc = 0;
    const double fast = ms([&] { for (auto& q : qs) acc += h.query(q.first, q.second).mean(); });
    const double slow = ms([&] { for (auto& q : qs) acc += h.query_naive(q.first, q.second).mean(); });
    sink = acc;
    std::printf("%d readings appended in %.1f ms\n", n, build);
    std::printf("segment tree: %8.2f ms total  (%.2f us/query)\n", fast, 1000 * fast / static_cast<double>(qs.size()));
    std::printf("naive scan:   %8.2f ms total  (%.2f us/query)   -> %.0fx faster\n", slow, 1000 * slow / static_cast<double>(qs.size()), slow / fast);
}

void bench_filter() {
    std::puts("\n== 3. Moisture decision: 10,000 readings of a WET plant with 2% electrical spikes ==");
    std::mt19937 rng(9);
    std::normal_distribution<double> noise(0, 8);
    std::bernoulli_distribution spike(0.02);
    MedianFilter<5> median;
    int raw_false = 0, filtered_false = 0;
    for (int i = 0; i < 10000; ++i) {
        double val = 540 + noise(rng);                 // truly wet: well under the 599 threshold
        if (spike(rng)) val = 1023;                    // loose wire / EMI from the pump relay
        const auto reading = static_cast<uint16_t>(val);
        if (reading > 599) ++raw_false;                // old firmware: one reading decides
        if (median.update(reading) > 599 && median.warmed_up()) ++filtered_false;
    }
    std::printf("false 'dry' decisions: single reading %d, median-of-5 %d\n", raw_false, filtered_false);
}

void bench_crc() {
    std::puts("\n== 4. CRC-16: bitwise (Arduino) vs table (PC), 1 MB ==");
    std::vector<std::uint8_t> data(1 << 20);
    std::mt19937 rng(4);
    for (auto& b : data) b = static_cast<std::uint8_t>(rng());
    std::uint16_t a = 0, b = 0;
    const double bit = ms([&] { a = proto::crc16(data.data(), data.size()); }, 5);
    const double tab = ms([&] { b = crc16_table(data.data(), data.size()); }, 5);
    std::printf("bitwise %.2f ms, table %.2f ms (%.1fx), results %s\n", bit, tab, bit / tab, a == b ? "match" : "DIFFER");
}

void bench_spots() {
    std::puts("\n== 5. Leaf-spot counting on a 1280x720 lesion mask ==");
    std::mt19937 rng(8);
    std::bernoulli_distribution lesion(0.3);
    const int w = 1280, h = 720;
    std::vector<PixelClass> cls(static_cast<std::size_t>(w) * h);
    for (auto& c : cls) c = lesion(rng) ? PixelClass::Lesion : PixelClass::Healthy;
    SpotReport a, b;
    const double uf = ms([&] { a = find_spots_union_find(cls, w, h, 1); }, 3);
    const double bfs = ms([&] { b = find_spots_bfs(cls, w, h, 1); }, 3);
    std::printf("union-find %.1f ms, BFS %.1f ms, spots %zu vs %zu\n", uf, bfs, a.spots.size(), b.spots.size());
}

int main() {
    bench_routes();
    bench_history();
    bench_filter();
    bench_crc();
    bench_spots();
}
