#pragma once
// Experiment scheduler: a min-heap of timed jobs sharing ONE gantry.
//
// Today ExperimentManager runs steps with time.sleep(), so two experiments can
// ask for the gantry at once. Here every job sits in a priority queue ordered by
// (due time, priority, id). The gantry is a single resource: a job that comes
// due while it is busy waits, and the wait is recorded.
//
// The clock is simulated (seconds since start), so a whole day runs in
// microseconds and tests are deterministic. A real driver just calls
// run_until(now()) in its loop.

#include <cstdint>
#include <functional>
#include <queue>
#include <string>
#include <unordered_set>
#include <vector>

namespace krishi {

using Seconds = std::int64_t;
using JobId = std::uint32_t;

enum class Action { MovePlant, CheckMoisture, WaterSmart, WaterForce, Capture, Home };

struct Job {
    JobId id = 0;
    std::string name;
    Action action = Action::Capture;
    int plant = 0;          // which plant the job is for
    Seconds due = 0;        // next time it should start
    Seconds period = 0;     // 0 = run once; otherwise repeat every `period` seconds
    Seconds duration = 0;   // how long it holds the gantry
    int priority = 0;       // lower runs first when two jobs are due together
};

struct Execution {
    JobId id;
    std::string name;
    Seconds scheduled;      // when it was due
    Seconds started;        // when the gantry was actually free
    Seconds finished;
    Seconds waited() const { return started - scheduled; }
};

class Scheduler {
public:
    // Adds a job and returns its id.
    JobId add(Job job);
    // O(1): marks the id cancelled; the stale heap entry is skipped when popped
    // ("lazy deletion"), because std::priority_queue cannot remove from the middle.
    void cancel(JobId id);

    // Runs every job that becomes due before `until`, in order, and returns what ran.
    std::vector<Execution> run_until(Seconds until);

    Seconds gantry_free_at() const { return gantry_free_at_; }
    std::size_t pending() const { return heap_.size(); }

private:
    struct Later {  // std::priority_queue is a max-heap; this comparator turns it into a min-heap
        bool operator()(const Job& a, const Job& b) const {
            if (a.due != b.due) return a.due > b.due;
            if (a.priority != b.priority) return a.priority > b.priority;
            return a.id > b.id;  // stable tie-break: earlier-added job first
        }
    };

    std::priority_queue<Job, std::vector<Job>, Later> heap_;
    std::unordered_set<JobId> cancelled_;
    JobId next_id_ = 1;
    Seconds gantry_free_at_ = 0;
};

const char* to_string(Action a);

}  // namespace krishi
