#pragma once
// Medians on the PC side, where memory is plentiful and streams are long.
// (The tiny fixed-window version for the Arduino is MedianFilter in sensor_filter.h.)
//
// StreamingMedian: median of EVERYTHING seen so far, using two heaps.
//   lower_ is a max-heap holding the smaller half, upper_ a min-heap with the
//   larger half. Keep sizes balanced (differ by at most 1): the median is at
//   the top of one or both. add() is O(log n), median() is O(1).
//
// SlidingMedian: median of the last k values. Heaps cannot delete an arbitrary
//   old value cheaply, so this uses two balanced trees (std::multiset), which can.
//   add() is O(log k).

#include <cstddef>
#include <functional>
#include <iterator>
#include <queue>
#include <set>
#include <stdexcept>
#include <vector>

namespace krishi {

class StreamingMedian {
public:
    void add(double v) {
        if (lower_.empty() || v <= lower_.top()) lower_.push(v);
        else upper_.push(v);
        // Rebalance so lower_ has the same size as upper_, or one more.
        if (lower_.size() > upper_.size() + 1) { upper_.push(lower_.top()); lower_.pop(); }
        else if (upper_.size() > lower_.size()) { lower_.push(upper_.top()); upper_.pop(); }
    }
    double median() const {
        if (lower_.empty()) throw std::logic_error("median of empty stream");
        if (lower_.size() > upper_.size()) return lower_.top();
        return (lower_.top() + upper_.top()) / 2.0;
    }
    std::size_t size() const { return lower_.size() + upper_.size(); }

private:
    std::priority_queue<double> lower_;                                         // max-heap
    std::priority_queue<double, std::vector<double>, std::greater<double>> upper_;  // min-heap
};

class SlidingMedian {
public:
    explicit SlidingMedian(std::size_t k) : k_(k) {
        if (k == 0) throw std::invalid_argument("window must be > 0");
    }

    void add(double v) {
        order_.push(v);
        insert(v);
        if (order_.size() > k_) { erase(order_.front()); order_.pop(); }
    }
    double median() const {
        if (lower_.empty()) throw std::logic_error("median of empty window");
        if (lower_.size() > upper_.size()) return *lower_.rbegin();
        return (*lower_.rbegin() + *upper_.begin()) / 2.0;
    }

private:
    void insert(double v) {
        if (lower_.empty() || v <= *lower_.rbegin()) lower_.insert(v);
        else upper_.insert(v);
        rebalance();
    }
    void erase(double v) {
        // Erase ONE copy (erase(value) would remove every duplicate).
        auto it = lower_.find(v);
        if (it != lower_.end()) lower_.erase(it);
        else upper_.erase(upper_.find(v));
        rebalance();
    }
    void rebalance() {
        if (lower_.size() > upper_.size() + 1) {
            auto last = std::prev(lower_.end());
            upper_.insert(*last);
            lower_.erase(last);
        } else if (upper_.size() > lower_.size()) {
            lower_.insert(*upper_.begin());
            upper_.erase(upper_.begin());
        }
    }

    std::size_t k_;
    std::queue<double> order_;      // arrival order, to know which value expires
    std::multiset<double> lower_;   // smaller half
    std::multiset<double> upper_;   // larger half
};

}  // namespace krishi
