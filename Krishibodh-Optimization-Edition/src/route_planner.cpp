#include "krishi/route_planner.hpp"

#include <algorithm>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <utility>

namespace krishi {

RoutePlanner::RoutePlanner(Point home, std::vector<Plant> plants, GantryModel model)
    : home_(home), plants_(std::move(plants)), nodes_(plants_.size() + 1), cost_(nodes_ * nodes_, 0.0) {
    auto pos = [&](std::size_t node) -> const Point& { return node == 0 ? home_ : plants_[node - 1].pos; };
    for (std::size_t a = 0; a < nodes_; ++a)
        for (std::size_t b = 0; b < nodes_; ++b)
            cost_[a * nodes_ + b] = (a == b) ? 0.0 : travel_time(pos(a), pos(b), model);
}

double RoutePlanner::route_time(const std::vector<std::size_t>& order) const {
    double total = 0.0;
    std::size_t prev = 0;  // start at home
    for (std::size_t plant : order) {
        total += cost(prev, plant + 1);
        prev = plant + 1;
    }
    return total + cost(prev, 0);  // return home
}

Route RoutePlanner::fixed_order() const {
    Route r;
    r.order.resize(plants_.size());
    std::iota(r.order.begin(), r.order.end(), std::size_t{0});
    r.seconds = route_time(r.order);
    return r;
}

Route RoutePlanner::nearest_neighbour() const {
    Route r;
    std::vector<bool> visited(plants_.size(), false);
    std::size_t current = 0;  // home
    for (std::size_t step = 0; step < plants_.size(); ++step) {
        std::size_t best = 0;
        double best_cost = std::numeric_limits<double>::infinity();
        for (std::size_t p = 0; p < plants_.size(); ++p) {
            if (!visited[p] && cost(current, p + 1) < best_cost) {
                best_cost = cost(current, p + 1);
                best = p;
            }
        }
        visited[best] = true;
        r.order.push_back(best);
        current = best + 1;
    }
    r.seconds = route_time(r.order);
    return r;
}

Route RoutePlanner::two_opt(Route start) const {
    // Work on the full tour with home at both ends: 0, p.., 0 (as node ids).
    std::vector<std::size_t> tour;
    tour.reserve(start.order.size() + 2);
    tour.push_back(0);
    for (std::size_t p : start.order) tour.push_back(p + 1);
    tour.push_back(0);

    // Reversing tour[i..j] replaces edges (i-1,i) and (j,j+1) with (i-1,j) and (i,j+1).
    // Our cost is symmetric, so only those two edges change: O(1) to evaluate a move.
    bool improved = true;
    while (improved) {
        improved = false;
        for (std::size_t i = 1; i + 1 < tour.size(); ++i) {
            for (std::size_t j = i + 1; j + 1 < tour.size(); ++j) {
                const double before = cost(tour[i - 1], tour[i]) + cost(tour[j], tour[j + 1]);
                const double after = cost(tour[i - 1], tour[j]) + cost(tour[i], tour[j + 1]);
                if (after + 1e-9 < before) {
                    std::reverse(tour.begin() + static_cast<std::ptrdiff_t>(i),
                                 tour.begin() + static_cast<std::ptrdiff_t>(j) + 1);
                    improved = true;
                }
            }
        }
    }

    Route r;
    for (std::size_t k = 1; k + 1 < tour.size(); ++k) r.order.push_back(tour[k] - 1);
    r.seconds = route_time(r.order);
    return r;
}

Route RoutePlanner::held_karp() const {
    const std::size_t n = plants_.size();
    if (n > kMaxExact) throw std::invalid_argument("held_karp: too many plants for exact search");
    if (n == 0) return Route{};

    // dp[mask][last] = cheapest time to start at home, visit exactly the plants
    // in `mask`, and stand at plant `last`. parent[] lets us rebuild the order.
    const std::size_t full = std::size_t{1} << n;
    const double inf = std::numeric_limits<double>::infinity();
    std::vector<double> dp(full * n, inf);
    std::vector<std::size_t> parent(full * n, n);
    auto at = [n](std::size_t mask, std::size_t last) { return mask * n + last; };

    for (std::size_t p = 0; p < n; ++p) dp[at(std::size_t{1} << p, p)] = cost(0, p + 1);

    for (std::size_t mask = 1; mask < full; ++mask) {
        for (std::size_t last = 0; last < n; ++last) {
            const double here = dp[at(mask, last)];
            if (!(mask >> last & 1U) || here == inf) continue;
            for (std::size_t next = 0; next < n; ++next) {
                if (mask >> next & 1U) continue;
                const std::size_t nmask = mask | (std::size_t{1} << next);
                const double cand = here + cost(last + 1, next + 1);
                if (cand < dp[at(nmask, next)]) {
                    dp[at(nmask, next)] = cand;
                    parent[at(nmask, next)] = last;
                }
            }
        }
    }

    // Close the tour back to home and pick the best last plant.
    std::size_t last = 0;
    double best = inf;
    for (std::size_t p = 0; p < n; ++p) {
        const double total = dp[at(full - 1, p)] + cost(p + 1, 0);
        if (total < best) { best = total; last = p; }
    }

    Route r;
    std::size_t mask = full - 1;
    while (last != n) {
        r.order.push_back(last);
        const std::size_t prev = parent[at(mask, last)];
        mask &= ~(std::size_t{1} << last);
        last = prev;
    }
    std::reverse(r.order.begin(), r.order.end());
    r.seconds = route_time(r.order);
    return r;
}

}  // namespace krishi
