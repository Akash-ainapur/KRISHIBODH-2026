# 02. Experiment scheduler: many jobs, one gantry

**Files:** `include/krishi/scheduler.hpp`, `src/scheduler.cpp`, `tests/test_scheduler.cpp`
**DSA:** heaps / priority queues, lazy deletion, simulation with a virtual clock

## The problem
`ExperimentManager` in the Python app runs each experiment's steps with `time.sleep()`. Two experiments ("capture plant 1 every 30 min" and "water plant 2 at noon") can both want the gantry at 12:00. There is one gantry. Something must decide who goes first and who waits.

## The idea: a min-heap ordered by time
Every job sits in a **priority queue**. The one at the top is always the next job due. Popping it is O(log n), and peeking is O(1).

Ordering key: `(due time, priority, id)`.
- earliest due first
- if due at the same time, lower `priority` number first (watering beats photos)
- if still tied, the job added first goes first (`id`), so results are deterministic

`std::priority_queue` is a **max-heap** by default. The `Later` comparator flips it into a min-heap: it says "a comes after b if a is due later".

## Three behaviours worth explaining

### 1. The gantry is a single resource
```cpp
const Seconds start = std::max(job.due, gantry_free_at_);
```
A job starts when it is due **and** the previous job has finished. The wait is recorded, so you can see contention.

### 2. Recurring jobs do not drift
A job every 60 s, delayed once by 15 s: when is the next run?
- **Wrong:** `finished + 60`. Every delay pushes every future run later, forever ("drift").
- **Right (what we do):** `due + 60`. The schedule stays anchored to the clock.

If a job fell more than a whole period behind (the gantry was busy for 4 minutes), we **skip the missed slots** instead of firing a burst of 4 catch-up captures. That is a design decision; for photos, skipping is right.

### 3. Cancel with lazy deletion
`std::priority_queue` cannot remove an element from the middle. Instead, `cancel(id)` puts the id in an `unordered_set`. When a cancelled job reaches the top, it is popped and ignored. Cancel is O(1); the cost is paid later, when it would be popped anyway.

## Why a simulated clock?
`run_until(t)` uses plain integers for time, not the wall clock. A full 24-hour day runs in microseconds, and tests are deterministic (no flaky timing). The real driver calls `run_until(now())` in its loop. The design separates **what to run** from **how time passes**.

## Results (`krishi day`)
Four realistic jobs over 24 h: 83 jobs ran, 4 had to wait (1320 s total), and **none collided**. Today's `sleep()`-based runner has no concept of a collision at all.

## Interview questions
1. **Heap vs sorted list?** Heap insert and pop are O(log n). A sorted list makes insert O(n). A heap only promises the minimum is on top, and that is all a scheduler needs.
2. **Why is `std::priority_queue` a max-heap, and how do you get a min-heap?** Its comparator defaults to `std::less`, which puts the largest on top. Pass `std::greater` or your own comparator.
3. **How would you support "change a job's time"?** Lazy deletion again: cancel the old entry, add a new one. Or use an indexed heap that tracks each job's position (more code, true O(log n) update).
4. **What is starvation, and can it happen here?** A low-priority job never running because higher ones keep arriving. Here priority only breaks ties at the same due time, so an earlier-due job always goes first, and no job starves.
5. **How does an OS scheduler differ?** It preempts (interrupts a running task). Our gantry cannot stop halfway through watering, so jobs are non-preemptive.

## Ideas for your team
- Replace `time.sleep()` in `experiment_manager.py` by calling this scheduler (or porting the same idea to Python with `heapq`).
- Add a "deadline" field and report jobs that missed it.
