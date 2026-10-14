#include "krishi/scheduler.hpp"

#include <algorithm>
#include <stdexcept>
#include <utility>

namespace krishi {

JobId Scheduler::add(Job job) {
    if (job.period < 0 || job.duration < 0) throw std::invalid_argument("period and duration must be >= 0");
    job.id = next_id_++;
    const JobId id = job.id;
    heap_.push(std::move(job));
    return id;
}

void Scheduler::cancel(JobId id) { cancelled_.insert(id); }

std::vector<Execution> Scheduler::run_until(Seconds until) {
    std::vector<Execution> ran;
    while (!heap_.empty() && heap_.top().due < until) {
        Job job = heap_.top();
        heap_.pop();

        if (cancelled_.count(job.id)) continue;  // lazy deletion

        // The gantry is one physical resource: start when both the job is due
        // and the previous job has finished.
        const Seconds start = std::max(job.due, gantry_free_at_);
        const Seconds end = start + job.duration;
        gantry_free_at_ = end;
        ran.push_back({job.id, job.name, job.due, start, end});

        if (job.period > 0) {
            // Anchor the next run to the SCHEDULE (due + period), not to when it
            // finished. Anchoring to `end` would make every delay push all future
            // runs later ("drift"). If we fell more than a whole period behind,
            // skip the missed slots instead of firing a burst of catch-up runs.
            job.due += job.period;
            if (job.due < end) job.due += (end - job.due + job.period - 1) / job.period * job.period;  // ceil
            heap_.push(std::move(job));
        }
    }
    return ran;
}

const char* to_string(Action a) {
    switch (a) {
        case Action::MovePlant:     return "move";
        case Action::CheckMoisture: return "check_moisture";
        case Action::WaterSmart:    return "water_smart";
        case Action::WaterForce:    return "water_force";
        case Action::Capture:       return "capture";
        case Action::Home:          return "home";
    }
    return "?";
}

}  // namespace krishi
