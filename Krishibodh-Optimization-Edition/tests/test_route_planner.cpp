#include <algorithm>
#include <random>
#include <set>

#include "check.hpp"
#include "krishi/route_planner.hpp"

using namespace krishi;

namespace {
std::vector<Plant> random_plants(std::size_t n, unsigned seed) {
    std::mt19937 rng(seed);
    std::uniform_int_distribution<int> x(0, 6000), y(0, 3000);
    std::vector<Plant> v;
    for (std::size_t i = 0; i < n; ++i) v.push_back({"P" + std::to_string(i), {x(rng), y(rng), 10000}});
    return v;
}
bool is_permutation_of_n(const std::vector<std::size_t>& order, std::size_t n) {
    std::set<std::size_t> s(order.begin(), order.end());
    return order.size() == n && s.size() == n && *s.rbegin() == n - 1;
}
}  // namespace

TEST(axis_time_triangle_and_trapezoid) {
    const AxisLimits lim{800.0, 200.0};          // ramp distance = 800^2/200 = 3200 steps
    CHECK_NEAR(axis_time(0, lim), 0.0, 1e-12);
    CHECK_NEAR(axis_time(800, lim), 2.0 * std::sqrt(800.0 / 200.0), 1e-9);  // never reaches top speed
    CHECK_NEAR(axis_time(3200, lim), 8.0, 1e-9);  // both formulas agree at the boundary
    CHECK_NEAR(axis_time(6400, lim), 6400.0 / 800.0 + 4.0, 1e-9);
    CHECK_NEAR(axis_time(-6400, lim), axis_time(6400, lim), 1e-12);  // direction does not matter
}

TEST(travel_time_is_set_by_the_slower_axis) {
    GantryModel m;
    m.include_z = false;
    const Point a{0, 0, 0};
    // X is fast (800/s) but accelerates slowly; Y is slow (400/s). The move takes the max of both.
    const Point b{4000, 100, 0};
    CHECK_NEAR(travel_time(a, b, m), std::max(axis_time(4000, m.x), axis_time(100, m.y)), 1e-12);
}

TEST(all_strategies_return_valid_routes) {
    RoutePlanner rp({0, 0, 0}, random_plants(9, 7));
    for (const Route& r : {rp.fixed_order(), rp.nearest_neighbour(), rp.two_opt(rp.nearest_neighbour()), rp.held_karp()}) {
        CHECK(is_permutation_of_n(r.order, 9));
        CHECK_NEAR(r.seconds, rp.route_time(r.order), 1e-9);
    }
}

TEST(held_karp_is_optimal_vs_brute_force) {
    // 7 plants = 5040 permutations: small enough to check every one.
    for (unsigned seed = 1; seed <= 5; ++seed) {
        RoutePlanner rp({0, 0, 0}, random_plants(7, seed));
        std::vector<std::size_t> perm{0, 1, 2, 3, 4, 5, 6};
        double best = 1e18;
        do best = std::min(best, rp.route_time(perm));
        while (std::next_permutation(perm.begin(), perm.end()));
        CHECK_NEAR(rp.held_karp().seconds, best, 1e-6);
    }
}

TEST(two_opt_never_makes_a_route_worse) {
    for (unsigned seed = 1; seed <= 20; ++seed) {
        RoutePlanner rp({0, 0, 0}, random_plants(14, seed));
        const Route start = rp.fixed_order();
        const Route improved = rp.two_opt(start);
        CHECK(improved.seconds <= start.seconds + 1e-9);
        CHECK(improved.seconds >= rp.held_karp().seconds - 1e-6);  // nothing beats the optimum
    }
}

TEST(held_karp_rejects_too_many_plants) {
    RoutePlanner rp({0, 0, 0}, random_plants(RoutePlanner::kMaxExact + 1, 3));
    CHECK_THROWS(rp.held_karp());
}

TEST(empty_and_single_plant) {
    RoutePlanner none({0, 0, 0}, {});
    CHECK_EQ(none.held_karp().order.size(), std::size_t{0});
    RoutePlanner one({0, 0, 0}, {{"P0", {1000, 500, 10000}}});
    CHECK_EQ(one.two_opt(one.nearest_neighbour()).order.size(), std::size_t{1});
    CHECK_NEAR(one.held_karp().seconds, one.fixed_order().seconds, 1e-12);
}
