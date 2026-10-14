#include "krishi/leaf_spots.hpp"

#include <algorithm>
#include <fstream>
#include <numeric>
#include <queue>
#include <stdexcept>
#include <unordered_map>

namespace krishi {

// ---- PPM I/O ---------------------------------------------------------------

static void skip_space_and_comments(std::istream& in) {
    while (true) {
        int c = in.peek();
        if (c == '#') { std::string line; std::getline(in, line); }
        else if (c == ' ' || c == '\n' || c == '\r' || c == '\t') in.get();
        else return;
    }
}

Image read_ppm(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("cannot open " + path);
    std::string magic;
    in >> magic;
    if (magic != "P6") throw std::runtime_error(path + ": only binary PPM (P6) is supported");
    int maxval = 0;
    Image img;
    skip_space_and_comments(in); in >> img.width;
    skip_space_and_comments(in); in >> img.height;
    skip_space_and_comments(in); in >> maxval;
    in.get();  // exactly one whitespace byte before pixel data
    if (img.width <= 0 || img.height <= 0 || maxval != 255) throw std::runtime_error(path + ": unsupported PPM header");
    img.rgb.resize(static_cast<std::size_t>(img.width) * static_cast<std::size_t>(img.height) * 3);
    in.read(reinterpret_cast<char*>(img.rgb.data()), static_cast<std::streamsize>(img.rgb.size()));
    if (!in) throw std::runtime_error(path + ": truncated pixel data");
    return img;
}

void write_ppm(const std::string& path, const Image& img) {
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("cannot write " + path);
    out << "P6\n" << img.width << ' ' << img.height << "\n255\n";
    out.write(reinterpret_cast<const char*>(img.rgb.data()), static_cast<std::streamsize>(img.rgb.size()));
}

// ---- colour ----------------------------------------------------------------

Hsv rgb_to_hsv(std::uint8_t r8, std::uint8_t g8, std::uint8_t b8) {
    const int r = r8, g = g8, b = b8;
    const int mx = std::max({r, g, b});
    const int mn = std::min({r, g, b});
    const int delta = mx - mn;
    int h = 0;
    if (delta != 0) {
        double hd;  // degrees 0-360
        if (mx == r) hd = 60.0 * (g - b) / delta;
        else if (mx == g) hd = 60.0 * (b - r) / delta + 120.0;
        else hd = 60.0 * (r - g) / delta + 240.0;
        if (hd < 0) hd += 360.0;
        h = static_cast<int>(hd / 2.0 + 0.5) % 180;  // OpenCV halves hue to fit a byte
    }
    const int s = mx == 0 ? 0 : (255 * delta + mx / 2) / mx;
    return {h, s, mx};
}

std::vector<PixelClass> classify(const Image& img, const ColorThresholds& t) {
    const std::size_t n = static_cast<std::size_t>(img.width) * static_cast<std::size_t>(img.height);
    std::vector<PixelClass> out(n, PixelClass::Background);
    for (std::size_t i = 0; i < n; ++i) {
        const Hsv c = rgb_to_hsv(img.rgb[3 * i], img.rgb[3 * i + 1], img.rgb[3 * i + 2]);
        if (c.h >= t.lesion_h_min && c.h <= t.lesion_h_max && c.s >= t.lesion_s_min && c.v >= t.lesion_v_min)
            out[i] = PixelClass::Lesion;
        else if (c.h >= t.green_h_min && c.h <= t.green_h_max && c.s >= t.green_s_min && c.v >= t.green_v_min)
            out[i] = PixelClass::Healthy;
    }
    return out;
}

// ---- union-find ------------------------------------------------------------

DisjointSet::DisjointSet(std::size_t n) : parent_(n), size_(n, 1) {
    std::iota(parent_.begin(), parent_.end(), std::size_t{0});
}

std::size_t DisjointSet::find(std::size_t x) {
    std::size_t root = x;
    while (parent_[root] != root) root = parent_[root];
    while (parent_[x] != root) {  // path compression: point every node on the path at the root
        const std::size_t next = parent_[x];
        parent_[x] = root;
        x = next;
    }
    return root;
}

bool DisjointSet::unite(std::size_t a, std::size_t b) {
    a = find(a);
    b = find(b);
    if (a == b) return false;
    if (size_[a] < size_[b]) std::swap(a, b);  // union by size: hang the smaller tree under the larger
    parent_[b] = a;
    size_[a] += size_[b];
    return true;
}

// ---- spot finding ----------------------------------------------------------

namespace {

void count_pixels(const std::vector<PixelClass>& cls, SpotReport& rep) {
    for (PixelClass c : cls) {
        if (c == PixelClass::Healthy) ++rep.healthy_px;
        else if (c == PixelClass::Lesion) ++rep.lesion_px;
    }
}

void finish(SpotReport& rep, std::size_t min_area) {
    rep.spots.erase(std::remove_if(rep.spots.begin(), rep.spots.end(),
                                   [min_area](const Spot& s) { return s.area < min_area; }),
                    rep.spots.end());
    std::sort(rep.spots.begin(), rep.spots.end(), [](const Spot& a, const Spot& b) {
        if (a.area != b.area) return a.area > b.area;
        return a.min_y != b.min_y ? a.min_y < b.min_y : a.min_x < b.min_x;  // deterministic order
    });
}

void grow(Spot& s, int x, int y) {
    ++s.area;
    s.min_x = std::min(s.min_x, x); s.max_x = std::max(s.max_x, x);
    s.min_y = std::min(s.min_y, y); s.max_y = std::max(s.max_y, y);
}

}  // namespace

SpotReport find_spots_union_find(const std::vector<PixelClass>& cls, int width, int height, std::size_t min_area) {
    SpotReport rep;
    count_pixels(cls, rep);
    auto idx = [width](int x, int y) { return static_cast<std::size_t>(y) * static_cast<std::size_t>(width) + static_cast<std::size_t>(x); };
    auto lesion = [&](int x, int y) { return cls[idx(x, y)] == PixelClass::Lesion; };

    DisjointSet dsu(cls.size());
    // Raster scan: only look at neighbours already visited (left, up-left, up,
    // up-right). Every 8-connected edge is still seen once, from its later pixel.
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            if (!lesion(x, y)) continue;
            if (x > 0 && lesion(x - 1, y)) dsu.unite(idx(x, y), idx(x - 1, y));
            if (y > 0) {
                if (x > 0 && lesion(x - 1, y - 1)) dsu.unite(idx(x, y), idx(x - 1, y - 1));
                if (lesion(x, y - 1)) dsu.unite(idx(x, y), idx(x, y - 1));
                if (x + 1 < width && lesion(x + 1, y - 1)) dsu.unite(idx(x, y), idx(x + 1, y - 1));
            }
        }
    }

    std::unordered_map<std::size_t, std::size_t> spot_of_root;
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            if (!lesion(x, y)) continue;
            const std::size_t root = dsu.find(idx(x, y));
            auto [it, inserted] = spot_of_root.try_emplace(root, rep.spots.size());
            if (inserted) rep.spots.push_back(Spot{0, x, y, x, y});
            grow(rep.spots[it->second], x, y);
        }
    }
    finish(rep, min_area);
    return rep;
}

SpotReport find_spots_bfs(const std::vector<PixelClass>& cls, int width, int height, std::size_t min_area) {
    SpotReport rep;
    count_pixels(cls, rep);
    std::vector<bool> seen(cls.size(), false);
    auto idx = [width](int x, int y) { return static_cast<std::size_t>(y) * static_cast<std::size_t>(width) + static_cast<std::size_t>(x); };

    for (int y0 = 0; y0 < height; ++y0) {
        for (int x0 = 0; x0 < width; ++x0) {
            if (cls[idx(x0, y0)] != PixelClass::Lesion || seen[idx(x0, y0)]) continue;
            Spot s{0, x0, y0, x0, y0};
            std::queue<std::pair<int, int>> q;
            q.push({x0, y0});
            seen[idx(x0, y0)] = true;
            while (!q.empty()) {
                auto [x, y] = q.front();
                q.pop();
                grow(s, x, y);
                for (int dy = -1; dy <= 1; ++dy) {
                    for (int dx = -1; dx <= 1; ++dx) {
                        const int nx = x + dx, ny = y + dy;
                        if ((dx || dy) && nx >= 0 && ny >= 0 && nx < width && ny < height &&
                            !seen[idx(nx, ny)] && cls[idx(nx, ny)] == PixelClass::Lesion) {
                            seen[idx(nx, ny)] = true;  // mark when QUEUED, or a pixel can be queued twice
                            q.push({nx, ny});
                        }
                    }
                }
            }
            rep.spots.push_back(s);
        }
    }
    finish(rep, min_area);
    return rep;
}

}  // namespace krishi
