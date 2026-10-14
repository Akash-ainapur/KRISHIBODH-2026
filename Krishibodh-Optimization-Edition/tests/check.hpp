#pragma once
// A ~60-line test harness so the project builds with no downloads.
// TEST(name) registers a test; CHECK / CHECK_EQ / CHECK_NEAR record failures
// without stopping the test. Swap for GoogleTest later: the macros map 1:1
// (TEST -> TEST(Suite, Name), CHECK_EQ -> EXPECT_EQ, CHECK_NEAR -> EXPECT_NEAR).

#include <cmath>
#include <functional>
#include <iostream>
#include <string>
#include <vector>

namespace check {

struct Test { std::string name; std::function<void()> fn; };

inline std::vector<Test>& registry() { static std::vector<Test> r; return r; }
inline int& failures() { static int f = 0; return f; }

struct Register {
    Register(std::string name, std::function<void()> fn) { registry().push_back({std::move(name), std::move(fn)}); }
};

inline void fail(const char* file, int line, const std::string& msg) {
    ++failures();
    std::cerr << "  FAIL " << file << ":" << line << "  " << msg << "\n";
}

inline int run_all() {
    int failed_tests = 0;
    for (auto& t : registry()) {
        const int before = failures();
        try { t.fn(); }
        catch (const std::exception& e) { fail("<exception>", 0, t.name + ": " + e.what()); }
        const bool ok = failures() == before;
        if (!ok) ++failed_tests;
        std::cout << (ok ? "[ OK ] " : "[FAIL] ") << t.name << "\n";
    }
    std::cout << "\n" << registry().size() - failed_tests << "/" << registry().size() << " tests passed\n";
    return failed_tests == 0 ? 0 : 1;
}

}  // namespace check

#define CHECK_CAT2(a, b) a##b
#define CHECK_CAT(a, b) CHECK_CAT2(a, b)
#define TEST(name)                                                              \
    static void CHECK_CAT(test_fn_, name)();                                    \
    static check::Register CHECK_CAT(test_reg_, name)(#name, CHECK_CAT(test_fn_, name)); \
    static void CHECK_CAT(test_fn_, name)()

#define CHECK(cond) \
    do { if (!(cond)) check::fail(__FILE__, __LINE__, "CHECK(" #cond ")"); } while (0)
#define CHECK_EQ(a, b)                                                                                 \
    do { const auto va_ = (a); const auto vb_ = (b);                                                   \
         if (!(va_ == vb_)) check::fail(__FILE__, __LINE__, #a " == " #b "  (" + std::to_string(va_) + \
                                        " vs " + std::to_string(vb_) + ")"); } while (0)
#define CHECK_NEAR(a, b, eps)                                                                          \
    do { const double va_ = (a), vb_ = (b);                                                            \
         if (std::fabs(va_ - vb_) > (eps)) check::fail(__FILE__, __LINE__, #a " ~= " #b "  (" +       \
                                        std::to_string(va_) + " vs " + std::to_string(vb_) + ")"); } while (0)
#define CHECK_THROWS(expr) \
    do { bool threw_ = false; try { (void)(expr); } catch (...) { threw_ = true; } \
         if (!threw_) check::fail(__FILE__, __LINE__, "expected exception: " #expr); } while (0)
