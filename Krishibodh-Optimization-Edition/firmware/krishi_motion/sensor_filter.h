#pragma once
// Sensor filtering that runs ON THE ARDUINO (and on the PC for tests).
//
// Rules for code that must fit an 8-bit microcontroller with 2 KB of RAM:
//   - no heap allocation (no new, no std::vector): sizes are template parameters
//   - no STL (avr-gcc ships without it)
//   - everything fixed-size and O(N) at worst, with N tiny (5 to 15)
//
// Today the firmware waters when ONE analogRead() is above 599. One electrical
// spike can water a wet plant. This file adds: a ring buffer of recent readings,
// a median filter that ignores spikes, and hysteresis so the decision does not
// flicker when the value sits near the threshold.

#include <stdint.h>
#include <stddef.h>

namespace krishi {

// Fixed-capacity circular buffer: push overwrites the oldest value when full.
// head_ points at the slot the NEXT value goes into; (head_ + i) % N walks it.
template <typename T, size_t N>
class RingBuffer {
    static_assert(N > 0, "RingBuffer needs capacity > 0");

public:
    void push(T v) {
        data_[head_] = v;
        head_ = (head_ + 1) % N;
        if (size_ < N) ++size_;
    }
    size_t size() const { return size_; }
    bool full() const { return size_ == N; }
    // i = 0 is the oldest value still stored.
    T operator[](size_t i) const { return data_[(head_ + N - size_ + i) % N]; }

private:
    T data_[N] = {};
    size_t head_ = 0;
    size_t size_ = 0;
};

// Median of the last N readings. A median ignores up to (N-1)/2 outliers,
// where a mean would be dragged by every spike.
// Cost: copy N values and insertion-sort them, O(N^2) with N = 5..15. That is
// FASTER than a heap on a microcontroller at this size and needs no extra memory.
template <size_t N>
class MedianFilter {
    static_assert(N % 2 == 1, "use an odd window so the median is one real reading");

public:
    // Adds a reading and returns the filtered value.
    uint16_t update(uint16_t raw) {
        window_.push(raw);
        const size_t n = window_.size();
        uint16_t tmp[N];
        for (size_t i = 0; i < n; ++i) tmp[i] = window_[i];
        for (size_t i = 1; i < n; ++i) {  // insertion sort
            uint16_t key = tmp[i];
            size_t j = i;
            while (j > 0 && tmp[j - 1] > key) { tmp[j] = tmp[j - 1]; --j; }
            tmp[j] = key;
        }
        return tmp[n / 2];
    }
    bool warmed_up() const { return window_.full(); }

private:
    RingBuffer<uint16_t, N> window_;
};

// Two thresholds instead of one (a Schmitt trigger in electronics).
// Higher analog value = DRIER soil on this sensor.
//   becomes DRY  when value rises above dry_above
//   becomes WET  when value falls below wet_below
//   in between   keeps the previous state
// With a single threshold, a reading wobbling 598, 601, 597, 602 would flip the
// decision every sample.
class Hysteresis {
public:
    Hysteresis(uint16_t dry_above, uint16_t wet_below) : dry_above_(dry_above), wet_below_(wet_below) {}

    bool update(uint16_t value) {
        if (!dry_ && value > dry_above_) dry_ = true;
        else if (dry_ && value < wet_below_) dry_ = false;
        return dry_;
    }
    bool dry() const { return dry_; }

private:
    uint16_t dry_above_;
    uint16_t wet_below_;
    bool dry_ = false;
};

}  // namespace krishi
