#include "check.hpp"
#include "krishi/scheduler.hpp"

using namespace krishi;

TEST(jobs_run_in_due_order) {
    Scheduler s;
    s.add({0, "late", Action::Capture, 1, 50, 0, 5, 0});
    s.add({0, "early", Action::Capture, 2, 10, 0, 5, 0});
    const auto ran = s.run_until(100);
    CHECK_EQ(ran.size(), std::size_t{2});
    CHECK(ran[0].name == "early");
    CHECK(ran[1].name == "late");
}

TEST(priority_breaks_ties_then_insertion_order) {
    Scheduler s;
    s.add({0, "low", Action::Capture, 1, 10, 0, 1, 5});
    s.add({0, "high", Action::WaterSmart, 1, 10, 0, 1, 0});
    s.add({0, "high2", Action::WaterSmart, 1, 10, 0, 1, 0});
    const auto ran = s.run_until(100);
    CHECK(ran[0].name == "high");
    CHECK(ran[1].name == "high2");
    CHECK(ran[2].name == "low");
}

TEST(gantry_conflict_delays_second_job) {
    Scheduler s;
    s.add({0, "water", Action::WaterSmart, 1, 0, 0, 30, 0});
    s.add({0, "capture", Action::Capture, 2, 10, 0, 5, 0});  // due while gantry is busy until t=30
    const auto ran = s.run_until(100);
    CHECK_EQ(ran[1].started, Seconds{30});
    CHECK_EQ(ran[1].waited(), Seconds{20});
}

TEST(recurring_job_does_not_drift) {
    Scheduler s;
    s.add({0, "capture", Action::Capture, 1, 0, 60, 10, 0});
    s.add({0, "slow", Action::WaterSmart, 2, 55, 0, 20, 0});  // occupies the gantry 55..75
    const auto ran = s.run_until(200);
    // capture: 0, then 60 (delayed to 75 by "slow"), then 120 and 180 ON SCHEDULE.
    std::vector<Seconds> scheduled;
    for (const auto& e : ran) if (e.name == "capture") scheduled.push_back(e.scheduled);
    CHECK_EQ(scheduled.size(), std::size_t{4});
    CHECK_EQ(scheduled[1], Seconds{60});
    CHECK_EQ(scheduled[2], Seconds{120});
    CHECK_EQ(scheduled[3], Seconds{180});
}

TEST(missed_slots_are_skipped_not_burst) {
    Scheduler s;
    s.add({0, "long", Action::WaterForce, 1, 0, 0, 250, 0});  // gantry busy 0..250
    s.add({0, "tick", Action::Capture, 2, 10, 60, 1, 1});
    const auto ran = s.run_until(400);
    std::vector<Seconds> starts;
    for (const auto& e : ran) if (e.name == "tick") starts.push_back(e.started);
    // tick due 10 runs late at 250; slots 70..250 are skipped; next is 310 (10 + 5*60).
    CHECK_EQ(starts.size(), std::size_t{3});
    CHECK_EQ(starts[0], Seconds{250});
    CHECK_EQ(starts[1], Seconds{310});
    CHECK_EQ(starts[2], Seconds{370});
}

TEST(cancel_uses_lazy_deletion) {
    Scheduler s;
    const JobId a = s.add({0, "a", Action::Capture, 1, 10, 30, 1, 0});
    s.add({0, "b", Action::Capture, 2, 20, 0, 1, 0});
    s.cancel(a);
    const auto ran = s.run_until(1000);
    CHECK_EQ(ran.size(), std::size_t{1});
    CHECK(ran[0].name == "b");
}

TEST(run_until_is_resumable) {
    Scheduler s;
    s.add({0, "tick", Action::Capture, 1, 0, 10, 1, 0});
    CHECK_EQ(s.run_until(25).size(), std::size_t{3});  // 0, 10, 20
    CHECK_EQ(s.run_until(45).size(), std::size_t{2});  // 30, 40
}
