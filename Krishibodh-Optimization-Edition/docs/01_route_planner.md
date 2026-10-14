# 01. Route planner: which order should the gantry visit plants in?

**Files:** `include/krishi/geometry.hpp`, `include/krishi/route_planner.hpp`, `src/route_planner.cpp`, `tests/test_route_planner.cpp`
**DSA:** graphs, greedy algorithms, local search, dynamic programming with bitmasks

## The problem
Today the robot visits plants in the order they are listed. With 2 plants that is fine. With a full bed, the gantry crosses back and forth and wastes time and wear. Start at home, visit every plant once, come home: this is the **Travelling Salesman Problem (TSP)**.

## Step 1: what does a move actually cost? (`geometry.hpp`)
Not straight-line distance. Two facts from `sketch_nov8a.ino`:

1. **X and Y move at the same time**, so a move takes as long as the **slower axis**: `max(time_x, time_y)`.
2. **Each axis accelerates** (AccelStepper). Short moves never reach top speed:
   - long move (trapezoid): `t = d / v + v / a`
   - short move (triangle): `t = 2 * sqrt(d / a)`
   - the switch-over distance is `v² / a` (3200 steps for X with v = 800, a = 200)

Every visit also retracts Z to 0 and lowers it again, so that time is added too.

**Interview point:** "I modelled cost as *time*, not distance, because the axes have different speeds and accelerate. Using Euclidean distance would optimise the wrong thing." This is the most important sentence in this module.

## Step 2: three algorithms
All of them use a **precomputed cost matrix**: `n+1` nodes (home + plants), cost computed once, stored in one flat `std::vector<double>` (one allocation, cache friendly).

| Algorithm | Idea | Complexity | When to use |
|---|---|---|---|
| **Nearest neighbour** | From where you stand, go to the closest unvisited plant | O(n²) | Instant first answer |
| **2-opt** | If two edges of the route cross, reverse the segment between them. Repeat until no reversal helps | O(n²) per pass | Polishing any route; scales to hundreds of plants |
| **Held-Karp** | DP: `dp[mask][last]` = cheapest way to visit exactly the plants in `mask`, ending at `last` | O(n² · 2ⁿ) time, O(n · 2ⁿ) memory | Exact optimum, up to 16 plants |

### 2-opt in one picture
```
before:  A ─ B        after reversing B..C:   A   B
              ╳                                │   │
         D ─ C                                 D   C
```
Reversing `tour[i..j]` swaps edges `(i-1, i)` and `(j, j+1)` for `(i-1, j)` and `(i, j+1)`. Because our cost is **symmetric**, only those two edges change, so each candidate is checked in O(1).

### Held-Karp in plain words
`mask` is a number whose bits say which plants are visited (bit 3 set = plant 3 visited). For every set of visited plants and every possible "current plant", keep only the cheapest way to get there. To extend, try every unvisited `next`. `parent[]` remembers the choice so the route can be rebuilt backwards.
- 16 plants: 2¹⁶ × 16 = about 1 million states. Fine.
- 30 plants: 2³⁰ × 30 = 32 billion. Impossible. That is why `held_karp()` refuses more than 16.

## Results (`krishi_bench`, 50 random beds per size, synthetic)
| Plants | Fixed order | NN + 2-opt | Optimal | Saved | Held-Karp time |
|---|---|---|---|---|---|
| 5 | 179.7 s | 173.0 s | 173.0 s | 3.7% | <0.01 ms |
| 10 | 348.4 s | 325.2 s | 325.1 s | 6.7% | 0.26 ms |
| 14 | 483.6 s | 445.8 s | 445.6 s | 7.9% | 7.06 ms |
| 200 | 6806.8 s | 5866.7 s | n/a | 13.8% | 2-opt: 0.18 ms |

**Read these honestly:**
- The gains are **modest for small beds**, because random plants on a small bed are already close together. They grow with bed size.
- **NN + 2-opt landed within 0.1% of the true optimum** at every size we could check. That is the more interesting result: the cheap heuristic is nearly perfect here.
- The 12-plant demo file (`data/plants_demo.csv`) is an illustrative layout (10.1% saved). Re-run with your real coordinates before quoting a number.

## How the tests prove it works
- `held_karp_is_optimal_vs_brute_force`: for 7 plants, try all 5,040 orders and confirm Held-Karp finds the best one. This is how you test an optimiser: compare with a slow, obviously-correct version.
- `two_opt_never_makes_a_route_worse` and never beats the optimum.
- `axis_time_triangle_and_trapezoid`: both formulas agree at the switch-over point.

## Interview questions
1. **Is TSP solvable in polynomial time?** No known algorithm. It is NP-hard. Held-Karp is exponential (but far better than the n! brute force). For large n we use heuristics.
2. **Why is 2-opt's move evaluation O(1)?** Reversing a segment of a symmetric tour only changes the two edges at its ends; the inside edges are the same edges walked backwards.
3. **Can 2-opt get stuck?** Yes, in a local optimum where no single reversal helps. Fixes: start from several random tours, or use 3-opt or Or-opt.
4. **Why `std::size_t{1} << n` and not `1 << n`?** `1` is an `int`; shifting it by 31 or more is undefined behaviour. Making it `size_t` first keeps it 64-bit.
5. **Why a flat vector for the matrix instead of `vector<vector<double>>`?** One allocation and contiguous memory, so the CPU cache works well. A vector of vectors is n separate allocations scattered in memory.
6. **What if the cost were not symmetric (say, the gantry is slower uphill)?** 2-opt's O(1) trick breaks, because a reversed segment costs differently. Held-Karp still works unchanged.

## Ideas for your team
- Use the robot's measured move times to calibrate `GantryModel`, then report the real saving.
- Add **A\* on a grid** so the nozzle avoids tall plants when Z cannot fully retract.
