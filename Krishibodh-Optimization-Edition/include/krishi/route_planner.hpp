#pragma once
// Route planner: in which order should the gantry visit the plants?
//
// This is the Travelling Salesman Problem (start at home, visit every plant
// once, return home). Three strategies, from fast-and-rough to slow-and-exact:
//   nearest_neighbour  O(n^2)        greedy construction
//   two_opt            O(n^2)/pass   local search that removes crossings
//   held_karp          O(n^2 * 2^n)  exact dynamic programming, n <= 16

#include <cstddef>
#include <vector>

#include "krishi/geometry.hpp"

namespace krishi {

struct Route {
    std::vector<std::size_t> order;  // indices into the plant list, home excluded
    double seconds = 0.0;            // total time home -> plants -> home
};

class RoutePlanner {
public:
    RoutePlanner(Point home, std::vector<Plant> plants, GantryModel model = {});

    // Baseline: visit plants in the order they were listed (what the robot does today).
    Route fixed_order() const;
    Route nearest_neighbour() const;
    // Improves any starting route by reversing segments while that saves time.
    Route two_opt(Route start) const;
    // Exact optimum. Throws std::invalid_argument when there are more than kMaxExact plants.
    Route held_karp() const;

    double route_time(const std::vector<std::size_t>& order) const;
    const std::vector<Plant>& plants() const { return plants_; }

    static constexpr std::size_t kMaxExact = 16;

private:
    // Node 0 is home, node i + 1 is plant i. cost_[a][b] is precomputed once.
    double cost(std::size_t a, std::size_t b) const { return cost_[a * nodes_ + b]; }

    Point home_;
    std::vector<Plant> plants_;
    std::size_t nodes_;
    std::vector<double> cost_;  // flat n x n matrix: one allocation, cache friendly
};

}  // namespace krishi
