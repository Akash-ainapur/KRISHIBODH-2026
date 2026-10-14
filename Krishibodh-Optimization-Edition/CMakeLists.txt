cmake_minimum_required(VERSION 3.16)
project(krishi_core VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# Warnings are errors-in-waiting: keep the build at zero warnings.
if(MSVC)
  add_compile_options(/W4 /permissive-)
else()
  add_compile_options(-Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wno-sign-conversion)
endif()

option(KRISHI_SANITIZE "Build with AddressSanitizer + UndefinedBehaviorSanitizer (Linux/macOS)" OFF)
if(KRISHI_SANITIZE AND NOT MSVC)
  add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
  add_link_options(-fsanitize=address,undefined)
endif()

# ---- library -------------------------------------------------------------
add_library(krishi_core
  src/route_planner.cpp
  src/scheduler.cpp
  src/sensor_history.cpp
  src/leaf_spots.cpp
  src/protocol.cpp
)
target_include_directories(krishi_core PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  # The wire protocol and motion state machine live with the firmware so the
  # Arduino and the PC compile the SAME source. One truth, two targets.
  ${CMAKE_CURRENT_SOURCE_DIR}/firmware/krishi_motion
)

# ---- command-line tool ---------------------------------------------------
add_executable(krishi apps/krishi_cli.cpp)
target_link_libraries(krishi PRIVATE krishi_core)

# ---- tests ---------------------------------------------------------------
enable_testing()
add_executable(krishi_tests
  tests/test_main.cpp
  tests/test_route_planner.cpp
  tests/test_scheduler.cpp
  tests/test_sensor_filter.cpp
  tests/test_sensor_history.cpp
  tests/test_leaf_spots.cpp
  tests/test_protocol.cpp
  tests/test_motion_fsm.cpp
)
target_link_libraries(krishi_tests PRIVATE krishi_core)
target_include_directories(krishi_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
add_test(NAME krishi_tests COMMAND krishi_tests)

# ---- benchmarks ----------------------------------------------------------
add_executable(krishi_bench bench/bench_main.cpp)
target_link_libraries(krishi_bench PRIVATE krishi_core)
