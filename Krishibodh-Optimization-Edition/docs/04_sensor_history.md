# 04. Sensor history: fast range queries with a segment tree

**Files:** `include/krishi/sensor_history.hpp`, `src/sensor_history.cpp`, `tests/test_sensor_history.cpp`
**DSA:** binary search, segment trees, amortised analysis

## The problem
The dashboard should answer questions like "what was plant 2's driest moment last week?" or "average moisture between 9 am and 5 pm?". With a year of readings every 5 minutes (105,120 of them), scanning the whole list for every question is slow, and it gets slower every day.

## Two ideas, combined

### 1. Binary search turns times into positions
Readings are appended in time order, so the timestamps are **sorted**. `std::lower_bound` finds the first reading at or after `t0`; `std::upper_bound` finds the first after `t1`. Both are O(log n). The question becomes "stats over positions `[l, r)`".

### 2. A segment tree answers any range in O(log n)
A segment tree is a binary tree where:
- each **leaf** holds one reading
- each **inner node** holds the min, max, sum and count of its two children

```
                 [min 3, max 9, sum 24]          <- whole range
               /                        \
       [3..7: sum 10]               [5..9: sum 14]
        /        \                    /       \
      [7]        [3]               [9]        [5]   <- readings
```
Any range is covered by at most about 2·log(n) nodes, so a query combines O(log n) precomputed summaries instead of touching every reading.

### The iterative version used here
The tree is stored in an array: leaves at `tree[cap + i]`, the parent of node `i` is `i / 2`, children are `2i` and `2i + 1`. No pointers, no recursion.

The query walks both ends of the range upward. If the left end is a **right child**, its parent also covers things outside the range, so take that node and step right. The same applies, mirrored, on the right end. Each level does O(1) work.

### Appending is amortised O(log n)
Each append updates its leaf and walks up to the root: O(log n). When the array is full, capacity **doubles** and the tree is rebuilt in O(n). Doubling means a rebuild happens after 1, 2, 4, 8... appends, so the total rebuild cost over n appends is under 2n, i.e. O(1) extra per append. This is the same argument as `std::vector::push_back`.

## Results (`krishi_bench`, synthetic)
1 year of 5-minute readings (105,120), then 10,000 random range queries:

| Method | Time per query |
|---|---|
| Naive scan | 75.47 µs |
| Binary search + segment tree | **0.32 µs** (**238× faster**) |

Building the whole year took 9.9 ms.

## How the tests prove it works
`history_matches_naive_scan_on_random_queries`: 500 random queries, each compared with the slow, obviously-correct scan. Readings include several at the same second, to test the `lower_bound`/`upper_bound` edges. Another test crosses every power-of-two capacity up to 1024 to exercise the rebuilds.

## Interview questions
1. **Segment tree vs prefix sums?** Prefix sums give range *sums* in O(1) but cannot do min/max, and an update costs O(n). A segment tree does any associative combine (min, max, sum, gcd) with O(log n) updates.
2. **Segment tree vs Fenwick (binary indexed) tree?** A Fenwick tree is smaller and simpler for sums, but min/max over arbitrary ranges does not work well with it.
3. **`lower_bound` vs `upper_bound`?** `lower_bound(x)` is the first element ≥ x; `upper_bound(x)` is the first element > x. Together they bracket every element equal to x.
4. **Why is the empty `RangeStats` the "identity"?** count 0, min +∞, max −∞, sum 0. Combining it with anything leaves that thing unchanged, which makes the query loop simple with no special cases.
5. **What is amortised complexity?** The average cost per operation over a worst-case sequence of operations. One append may cost O(n), but n appends cost O(n log n) in total.

## Ideas for your team
- Store one `SensorHistory` per plant and expose `query()` to the Flask dashboard (via pybind11, or a small HTTP service).
- Add downsampling for charts: one min/max/avg point per hour, straight from the tree.
