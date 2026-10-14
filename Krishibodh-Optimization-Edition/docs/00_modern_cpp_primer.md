# 00. Modern C++ in this project (read this first)

The original firmware is **Arduino C++**: global variables, `String`, `delay()`, no standard library. It works, but it is "C with objects". C++ interviews ask about **modern C++ (C++17)**, and every module here uses it on purpose. This page maps each idea to the exact line where you can see it.

## The ideas, and where they live

| Idea | One-line meaning | Where to look |
|---|---|---|
| **RAII** | An object cleans up after itself when it goes out of scope (files close, memory frees). No `delete`, no leaks. | `std::ifstream` in `leaf_spots.cpp` closes itself; every `std::vector` frees itself. |
| **STL containers** | Ready-made data structures with known complexity. | `std::vector` (everywhere), `std::priority_queue` (scheduler), `std::multiset` (sliding median), `std::unordered_map` (spot ids), `std::queue` (BFS). |
| **Move semantics** | Hand over a big object's insides instead of copying them. | `heap_.push(std::move(job))` in `scheduler.cpp`; `plants_(std::move(plants))` in the planner constructor. |
| **`const` correctness** | A method marked `const` promises not to change the object. | `route_time(...) const`, `query(...) const`. The compiler enforces it. |
| **`std::optional`** | "A value, or nothing" without magic numbers like -1. | `SensorHistory::index_range` returns `std::nullopt` when no reading is in range. |
| **Structured bindings** | Unpack a pair or struct into names. | `auto [it, inserted] = spot_of_root.try_emplace(...)` in `leaf_spots.cpp`. |
| **`constexpr`** | Computed by the compiler, not at run time. | The CRC lookup table in `protocol.cpp` is built at compile time. |
| **Templates** | Write the code once, the compiler makes a version per type or size. | `RingBuffer<T, N>`, `MedianFilter<N>`, and `MotionController<Hal>`, which runs with real motors on the Arduino and a fake robot in the tests. |
| **Lambdas** | Small unnamed functions, often passed to algorithms. | Comparators in `std::sort` and `std::lower_bound`; `idx` helpers in `leaf_spots.cpp`. |
| **Namespaces** | Avoid name clashes between libraries. | Everything is in `krishi::`, the protocol in `krishi::proto::`. |
| **`static_assert`** | Fail the BUILD, not the robot, when something is wrong. | `MedianFilter` refuses an even window size at compile time. |

## Two kinds of C++ in one repo

| | PC code (`src/`, `include/`) | Firmware code (`firmware/krishi_motion/`) |
|---|---|---|
| Memory | Heap allowed (`std::vector` grows) | **No heap.** Sizes fixed at compile time. |
| Library | Full STL | **No STL** (avr-gcc does not ship it) |
| RAM | Gigabytes | 2 KB on an Arduino Uno |
| Example | `StreamingMedian` uses two `std::priority_queue`s | `MedianFilter<5>` sorts 5 numbers in a plain array |

The firmware headers are still modern C++ (templates, `static_assert`, namespaces). Modern does not mean "uses the heap".

## Build, test, run

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
./build/krishi_tests          # 44 unit tests
./build/krishi_bench          # benchmarks
./build/krishi plan data/plants_demo.csv
```

On Linux or macOS, add `-DKRISHI_SANITIZE=ON` to run the tests under AddressSanitizer and UndefinedBehaviorSanitizer, which catch out-of-bounds reads and similar memory bugs that tests alone can miss.

## Interview questions this project prepares you for

- **What is RAII and why does C++ need it?** C++ has no garbage collector. Tying a resource's lifetime to an object's scope means the destructor always releases it, even when an exception is thrown.
- **`std::vector` vs a raw array?** A vector knows its size, grows, and frees itself. A raw array is fixed and decays to a pointer. On the Arduino we use fixed arrays on purpose, because a growing heap fragments 2 KB of RAM.
- **What does `std::move` actually do?** Nothing at run time. It is a cast that says "you may steal from this object". The move constructor then takes the internal buffer instead of copying it.
- **Why templates instead of virtual functions for the hardware layer?** Templates resolve at compile time, with no vtable and no indirect call per step, which matters inside a motor loop on an 8-bit CPU. A virtual interface would also work, at a small run-time cost.
