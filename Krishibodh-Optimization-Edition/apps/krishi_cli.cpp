// krishi: command-line front end for the optimization edition.
//
//   krishi plan  <plants.csv>    compare visit orders, print commands for the robot
//   krishi day                   simulate a day of scheduled experiments
//   krishi spots <image.ppm>     count leaf spots in a plant photo
//   krishi frame <x> <y> <z>     show the binary frame for a SMART_WATER command

#include <cstdio>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

#include "krishi/leaf_spots.hpp"
#include "krishi/protocol.hpp"
#include "krishi/route_planner.hpp"
#include "krishi/scheduler.hpp"

using namespace krishi;

namespace {

std::vector<Plant> load_plants(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open " + path);
    std::vector<Plant> plants;
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty() || line[0] == '#' || line.rfind("name", 0) == 0) continue;  // comments, header
        std::stringstream ss(line);
        Plant p;
        std::string x, y, z;
        std::getline(ss, p.name, ',');
        std::getline(ss, x, ',');
        std::getline(ss, y, ',');
        std::getline(ss, z, ',');
        p.pos = {std::stoll(x), std::stoll(y), std::stoll(z)};
        plants.push_back(p);
    }
    return plants;
}

int cmd_plan(const std::string& path) {
    RoutePlanner rp({0, 0, 0}, load_plants(path));
    const std::size_t n = rp.plants().size();
    std::cout << n << " plants, times include Z retract/lower, X+Y move together\n\n";

    const Route fixed = rp.fixed_order();
    const Route nn = rp.nearest_neighbour();
    const Route opt2 = rp.two_opt(nn);
    std::cout << std::left << std::setw(28) << "strategy" << std::right << std::setw(10) << "seconds"
              << std::setw(12) << "vs fixed" << "\n";
    auto row = [&](const char* name, const Route& r) {
        std::cout << std::left << std::setw(28) << name << std::right << std::fixed << std::setprecision(1)
                  << std::setw(10) << r.seconds << std::setw(11) << (100.0 * (fixed.seconds - r.seconds) / fixed.seconds)
                  << "%\n";
    };
    row("fixed order (today)", fixed);
    row("nearest neighbour", nn);
    row("nearest neighbour + 2-opt", opt2);
    Route best = opt2;
    if (n <= RoutePlanner::kMaxExact) {
        best = rp.held_karp();
        row("held-karp (exact optimum)", best);
    }

    std::cout << "\nCommands for the CURRENT firmware (text protocol), best order:\n";
    for (std::size_t i : best.order) {
        const Point& p = rp.plants()[i].pos;
        std::cout << "SMART:" << p.x << ',' << p.y << ',' << p.z << "    # " << rp.plants()[i].name << "\n";
    }
    std::cout << "0,0,0    # home\n";
    return 0;
}

int cmd_day() {
    // Two experiments sharing one gantry, as in the dashboard's demo protocols.
    Scheduler s;
    s.add({0, "capture P1 (every 30 min)", Action::Capture, 1, 0, 1800, 120, 1});
    s.add({0, "smart water P1 (9am, 5pm)", Action::WaterSmart, 1, 9 * 3600, 8 * 3600, 300, 0});
    s.add({0, "capture P2 (every 45 min)", Action::Capture, 2, 600, 2700, 120, 1});
    s.add({0, "force water P2 (noon)", Action::WaterForce, 2, 12 * 3600, 0, 600, 0});
    const auto ran = s.run_until(24 * 3600);

    Seconds total_wait = 0;
    int delayed = 0;
    for (const auto& e : ran) {
        if (e.waited() > 0) {
            ++delayed;
            std::printf("%02lld:%02lld  %-28s waited %llds for the gantry\n",
                        static_cast<long long>(e.started / 3600), static_cast<long long>(e.started % 3600 / 60),
                        e.name.c_str(), static_cast<long long>(e.waited()));
        }
        total_wait += e.waited();
    }
    std::cout << "\n" << ran.size() << " jobs ran in 24 h; " << delayed << " had to wait (total "
              << total_wait << " s), none collided.\n";
    return 0;
}

int cmd_spots(const std::string& path) {
    const Image img = read_ppm(path);
    const auto cls = classify(img);
    const SpotReport r = find_spots_union_find(cls, img.width, img.height, 20);
    std::cout << path << ": " << img.width << "x" << img.height << "\n"
              << "plant pixels  " << r.healthy_px + r.lesion_px << "\n"
              << "lesion ratio  " << std::fixed << std::setprecision(1) << 100.0 * r.lesion_ratio() << "%\n"
              << "spots (>=20px) " << r.spots.size() << "\n";
    for (std::size_t i = 0; i < r.spots.size() && i < 10; ++i) {
        const Spot& s = r.spots[i];
        std::cout << "  #" << i + 1 << "  " << s.area << " px  box (" << s.min_x << "," << s.min_y << ")-("
                  << s.max_x << "," << s.max_y << ")\n";
    }
    return 0;
}

int cmd_frame(long long x, long long y, long long z) {
    const auto bytes = encode(make_move(1, proto::SMART_WATER, {x, y, z}));
    const std::string text = "SMART:" + std::to_string(x) + "," + std::to_string(y) + "," + std::to_string(z) + "\n";
    std::cout << "text command  (" << text.size() << " bytes, no error check): " << text;
    std::cout << "binary frame  (" << bytes.size() << " bytes, CRC-16 + COBS):     ";
    for (auto b : bytes) std::printf("%02X ", b);
    std::cout << "\n";
    return 0;
}

int usage() {
    std::cerr << "usage:\n  krishi plan <plants.csv>\n  krishi day\n  krishi spots <image.ppm>\n  krishi frame <x> <y> <z>\n";
    return 2;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const std::string cmd = argc > 1 ? argv[1] : "";
        if (cmd == "plan" && argc == 3) return cmd_plan(argv[2]);
        if (cmd == "day") return cmd_day();
        if (cmd == "spots" && argc == 3) return cmd_spots(argv[2]);
        if (cmd == "frame" && argc == 5) return cmd_frame(std::stoll(argv[2]), std::stoll(argv[3]), std::stoll(argv[4]));
        return usage();
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
}
