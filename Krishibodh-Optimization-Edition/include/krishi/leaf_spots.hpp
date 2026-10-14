#pragma once
// Leaf-spot counter: how many separate diseased spots are on the plant, and how big?
//
// The Python analytics.py gives one number: the fraction of yellow/brown pixels.
// That cannot tell "one big rotten patch" from "forty small spots" (an early
// fungal infection). Counting spots needs CONNECTED COMPONENTS: group lesion
// pixels that touch each other.
//
// Two classic ways, both here so they can be checked against each other:
//   union-find (disjoint set union): one pass over pixels, union each lesion
//     pixel with its lesion neighbours. Near O(1) per operation with path
//     compression + union by size.
//   BFS flood fill: start at an unvisited lesion pixel, visit everything reachable.
//
// Images are read as binary PPM (P6), which needs no library. Convert a JPEG with:
//   python -c "from PIL import Image; Image.open('in.jpg').convert('RGB').save('in.ppm')"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace krishi {

struct Image {
    int width = 0;
    int height = 0;
    std::vector<std::uint8_t> rgb;  // width * height * 3, row-major
};

Image read_ppm(const std::string& path);
void write_ppm(const std::string& path, const Image& img);

// HSV on OpenCV's scale (H 0-179, S and V 0-255), so thresholds match analytics.py.
struct Hsv { int h, s, v; };
Hsv rgb_to_hsv(std::uint8_t r, std::uint8_t g, std::uint8_t b);

struct ColorThresholds {
    int green_h_min = 25, green_h_max = 90, green_s_min = 40, green_v_min = 40;    // healthy tissue
    int lesion_h_min = 8, lesion_h_max = 24, lesion_s_min = 50, lesion_v_min = 20;  // yellow-brown damage
};

enum class PixelClass : std::uint8_t { Background, Healthy, Lesion };

std::vector<PixelClass> classify(const Image& img, const ColorThresholds& t = {});

struct Spot {
    std::size_t area = 0;          // pixels
    int min_x, min_y, max_x, max_y;  // bounding box
};

struct SpotReport {
    std::vector<Spot> spots;       // sorted largest first
    std::size_t healthy_px = 0;
    std::size_t lesion_px = 0;
    double lesion_ratio() const {
        const std::size_t plant = healthy_px + lesion_px;
        return plant ? static_cast<double>(lesion_px) / static_cast<double>(plant) : 0.0;
    }
};

// Disjoint set union with path compression and union by size.
class DisjointSet {
public:
    explicit DisjointSet(std::size_t n);
    std::size_t find(std::size_t x);
    // Returns false if a and b were already in the same set.
    bool unite(std::size_t a, std::size_t b);
    std::size_t size_of(std::size_t x) { return size_[find(x)]; }

private:
    std::vector<std::size_t> parent_;
    std::vector<std::size_t> size_;
};

// 8-connected spots; spots smaller than min_area pixels are treated as noise.
SpotReport find_spots_union_find(const std::vector<PixelClass>& cls, int width, int height, std::size_t min_area = 4);
SpotReport find_spots_bfs(const std::vector<PixelClass>& cls, int width, int height, std::size_t min_area = 4);

}  // namespace krishi
