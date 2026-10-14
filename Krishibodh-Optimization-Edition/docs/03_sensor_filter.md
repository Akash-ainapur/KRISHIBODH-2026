# 03. Sensor filtering: stop watering on a single bad reading

**Files:** `firmware/krishi_motion/sensor_filter.h` (Arduino + PC), `include/krishi/median.hpp` (PC), `tests/test_sensor_filter.cpp`
**DSA:** circular buffers, median, two heaps, balanced trees (multiset), hysteresis

## The problem
The firmware waters when **one** `analogRead()` is above 599. A loose wire, or a voltage spike from the pump relay switching, reads as 1023, which means "bone dry". So the robot waters a plant that is already wet.

## Fix 1: ring buffer + median (runs on the Arduino)
Keep the last 5 readings in a **ring buffer**: a fixed array where a write position wraps around with `% N`. When full, the oldest value is overwritten. No memory is ever allocated.

Then take the **median**, not the mean:
- readings `500, 502, 1023, 499, 501` → mean **605** (says DRY, wrong)
- sorted `499, 500, 501, 502, 1023` → median **501** (says WET, right)

A median of N ignores up to (N−1)/2 outliers. A mean is dragged by every one.

**Why insertion sort and not a heap?** N = 5. Sorting 5 numbers is about 10 comparisons, needs no extra memory, and beats any clever structure at this size. Big-O describes growth; for tiny fixed N, constants win. That is a good interview answer.

## Fix 2: hysteresis (two thresholds)
A reading sitting near 599 (598, 601, 597, 602...) flips "dry/wet" on every sample with one threshold. Two thresholds fix it:
- become **dry** when the value rises above 600
- become **wet** only when it falls below 560
- in between, keep the previous state

The same trick is used in thermostats and in the Schmitt trigger in electronics. The test sequence flips 6 times with one threshold and twice with hysteresis.

## Medians on the PC (the classic DSA versions)
| Class | Question it answers | Structure | add() | median() |
|---|---|---|---|---|
| `StreamingMedian` | Median of everything so far | **Two heaps**: max-heap of the smaller half, min-heap of the larger half, sizes within 1 | O(log n) | O(1) |
| `SlidingMedian` | Median of the last k values | **Two multisets** | O(log k) | O(1) |

Why can't `SlidingMedian` use heaps? A sliding window must **remove the oldest value**, which can be anywhere inside a heap. A `std::multiset` (a balanced binary search tree) can find and erase any value in O(log k).

Bug to know about: `multiset.erase(value)` erases **every** copy of that value. We use `erase(find(value))` to remove exactly one. The test uses many duplicate values on purpose to catch this.

## Results (`krishi_bench`, synthetic)
A wet plant (true reading around 540) with 2% random spikes to 1023, over 10,000 readings:

| Method | False "dry" decisions |
|---|---|
| Single reading (today) | **203** |
| Median of 5 | **1** |

The one remaining false trigger happens when two spikes land in the same window of 5. A window of 7 would tolerate 3 spikes.

## Interview questions
1. **Find the median of a stream** (LeetCode 295): two heaps, as above. Explain the rebalancing rule.
2. **Sliding window median** (LeetCode 480): two multisets, or two heaps with lazy deletion.
3. **Why `(head_ + N - size_ + i) % N` in the ring buffer?** It walks back from the write position to the oldest stored value. The `+ N` keeps the number non-negative before `%` (with unsigned types, going negative would wrap to a huge number).
4. **Mean vs median vs moving average?** A mean is optimal for random noise but fragile to outliers. A median is robust to spikes. Real systems often use both: median to remove spikes, then a moving average to smooth.
5. **Why `static_assert(N % 2 == 1)`?** With an even window the median is the average of two readings, a value that was never measured. Odd keeps it a real reading, and the check happens at compile time, at no run-time cost.

## Ideas for your team
- Log raw and filtered readings for a week, then report the real false-trigger count from your own robot.
- Tune the hysteresis band using the sensor's measured noise.
