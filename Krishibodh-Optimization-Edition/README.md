# KRISHIBODH: Optimization Edition (C++17)

A C++ engine that makes the KRISHIBODH gantry robot plan smarter, schedule safely, sense reliably and talk to the PC without silent errors. Each module fixes a real weakness in the current robot and is built on a classic data structure or algorithm.

> **Status (14 Oct 2026):** for team review. 44/44 unit tests pass, zero compiler warnings. The firmware sketch (`firmware/krishi_motion/krishi_motion.ino`) has **not** been compiled for the Arduino or tested on the robot yet. Its logic is tested on the PC with a fake robot.

## What each module fixes

| # | Module | Problem in today's robot | DSA / technique | Measured result (synthetic data) |
|---|---|---|---|---|
| 1 | [Route planner](docs/01_route_planner.md) | Visits plants in list order | TSP: nearest neighbour, 2-opt, Held-Karp bitmask DP | 7.9% less gantry time at 14 plants, 13.8% at 200 |
| 2 | [Scheduler](docs/02_scheduler.md) | `time.sleep()` experiments can collide on the one gantry | Min-heap priority queue, lazy deletion | 83 jobs/day, 0 collisions |
| 3 | [Sensor filter](docs/03_sensor_filter.md) | One noisy reading decides watering | Ring buffer, median, hysteresis, two heaps, multisets | False "dry" decisions: **203 → 1** per 10,000 readings |
| 4 | [Sensor history](docs/04_sensor_history.md) | No fast "min/max/avg over a time range" | Binary search + segment tree | **238×** faster than scanning (1 year of data) |
| 5 | [Leaf spots](docs/05_leaf_spots.md) | Health is one ratio; cannot count disease spots | Connected components: union-find and BFS | 43,521 spots in a 1280×720 mask in 22 ms |
| 6 | [Firmware](docs/06_firmware_protocol_and_fsm.md) | Blocking `delay()` loops, text commands with no error check | Finite-state machine, CRC-16, COBS framing, fixed queue | Every single-bit corruption detected; answers STOP mid-move |

Start with **[docs/00_modern_cpp_primer.md](docs/00_modern_cpp_primer.md)**: it explains the modern C++ ideas used everywhere, and how they differ from the Arduino style in `sketch_nov8a.ino`.

## Folder map
```
include/krishi/           public headers (one per module)
src/                      implementations
firmware/krishi_motion/   Arduino sketch + headers shared by the Arduino AND the PC
                          (krishi_protocol.h, motion_fsm.h, sensor_filter.h: no STL, no heap)
apps/krishi_cli.cpp       command-line tool
tests/                    44 unit tests (tiny built-in harness, no downloads)
bench/                    benchmarks: new approach vs the obvious baseline
data/plants_demo.csv      plant coordinates (2 real, 10 illustrative)
docs/                     one explainer per module, with interview questions
```

## Build and run
Needs a C++17 compiler (GCC 9+, Clang 10+, or MSVC 2019+) and CMake 3.16+.

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
./build/krishi_tests                      # 44 tests
./build/krishi_bench                      # benchmark tables
./build/krishi plan data/plants_demo.csv  # best visit order + commands for the CURRENT firmware
./build/krishi day                        # simulate a day of scheduled jobs
./build/krishi frame 2000 800 10000       # text command vs binary frame
./build/krishi spots photo.ppm            # count leaf spots (see docs/05 to convert a JPEG)
```

On Windows without a modern compiler: `winget install BrechtSanders.WinLibs.POSIX.UCRT` installs GCC, CMake and Ninja together.

`krishi plan` prints commands in the **existing** text format (`SMART:x,y,z`), so the route planner works with today's firmware before anyone flashes the new one.

## Suggested review order for the team
1. `docs/00` (primer), then `docs/03` (sensor filter: smallest module, biggest practical win).
2. `docs/01` and `docs/02` (planning and scheduling: pure C++, easy to run).
3. `docs/04` and `docs/05` (data structures for the dashboard and vision).
4. `docs/06` (firmware) **last, and with the robot**: it changes how the PC and the Arduino talk.

## Review checklist
- [ ] Builds with zero warnings on your machine; `krishi_tests` reports 44/44.
- [ ] Replace the 10 illustrative plants in `data/plants_demo.csv` with measured coordinates, then re-run `krishi plan`.
- [ ] Measure real move times on the gantry and compare with `GantryModel` (`geometry.hpp`).
- [ ] Log raw moisture for a week; check the median filter and hysteresis thresholds against real noise.
- [ ] Convert a few captured photos to PPM and tune `ColorThresholds` for `krishi spots`.
- [ ] Compile `krishi_motion.ino` in the Arduino IDE (needs AccelStepper); bench-test MOVE, STOP and SMART_WATER with the gantry lifted.
- [ ] Update `arduino_service.py` to send binary frames and wait for ACK/DONE by sequence number.

## Honest limits
- All benchmark numbers come from **synthetic, seeded data** on one Windows laptop. Re-measure on the robot before quoting them.
- The route-planner saving is modest for small beds; its value grows with the number of plants.
- The firmware is untested on hardware.
