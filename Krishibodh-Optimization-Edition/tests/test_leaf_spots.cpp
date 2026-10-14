#include <cstdio>
#include <random>

#include "check.hpp"
#include "krishi/leaf_spots.hpp"

using namespace krishi;

namespace {
// Builds a class grid from ASCII: '.' background, 'g' healthy, 'x' lesion.
std::vector<PixelClass> grid(const std::vector<std::string>& rows) {
    std::vector<PixelClass> out;
    for (const auto& r : rows)
        for (char c : r) out.push_back(c == 'x' ? PixelClass::Lesion : c == 'g' ? PixelClass::Healthy : PixelClass::Background);
    return out;
}
}  // namespace

TEST(hsv_matches_opencv_scale) {
    const Hsv green = rgb_to_hsv(0, 255, 0);
    CHECK_EQ(green.h, 60);   // 120 degrees / 2
    CHECK_EQ(green.s, 255);
    const Hsv brown = rgb_to_hsv(150, 90, 30);
    CHECK(brown.h >= 8 && brown.h <= 24);
    const Hsv grey = rgb_to_hsv(128, 128, 128);
    CHECK_EQ(grey.s, 0);
}

TEST(diagonal_pixels_join_one_spot) {
    const auto cls = grid({"x....",
                           ".x...",
                           "..x..",
                           ".....",
                           "...xx"});
    const SpotReport r = find_spots_union_find(cls, 5, 5, 1);
    CHECK_EQ(r.spots.size(), std::size_t{2});
    CHECK_EQ(r.spots[0].area, std::size_t{3});  // the diagonal, largest first
}

TEST(min_area_drops_noise) {
    const auto cls = grid({"xx...x",
                           "xx....",
                           "......"});
    CHECK_EQ(find_spots_union_find(cls, 6, 3, 2).spots.size(), std::size_t{1});
    CHECK_EQ(find_spots_union_find(cls, 6, 3, 1).spots.size(), std::size_t{2});
}

TEST(lesion_ratio_counts_plant_pixels_only) {
    const auto cls = grid({"ggg.",
                           "gxg.",
                           "ggg."});
    const SpotReport r = find_spots_bfs(cls, 4, 3, 1);
    CHECK_EQ(r.lesion_px, std::size_t{1});
    CHECK_EQ(r.healthy_px, std::size_t{8});
    CHECK_NEAR(r.lesion_ratio(), 1.0 / 9.0, 1e-12);
}

TEST(union_find_and_bfs_agree_on_random_images) {
    std::mt19937 rng(5);
    std::bernoulli_distribution lesion(0.45);  // near the percolation threshold: big, twisted spots
    for (int trial = 0; trial < 30; ++trial) {
        const int w = 40, h = 30;
        std::vector<PixelClass> cls(static_cast<std::size_t>(w * h));
        for (auto& c : cls) c = lesion(rng) ? PixelClass::Lesion : PixelClass::Healthy;
        const SpotReport a = find_spots_union_find(cls, w, h, 1);
        const SpotReport b = find_spots_bfs(cls, w, h, 1);
        CHECK_EQ(a.spots.size(), b.spots.size());
        for (std::size_t i = 0; i < a.spots.size() && i < b.spots.size(); ++i) {
            CHECK_EQ(a.spots[i].area, b.spots[i].area);
            CHECK_EQ(a.spots[i].min_x, b.spots[i].min_x);
            CHECK_EQ(a.spots[i].max_y, b.spots[i].max_y);
        }
    }
}

TEST(ppm_round_trip_and_classify) {
    Image img{3, 1, {0, 200, 0, 150, 90, 30, 255, 255, 255}};  // green, brown, white
    write_ppm("test_tmp.ppm", img);
    const Image back = read_ppm("test_tmp.ppm");
    CHECK_EQ(back.width, 3);
    CHECK(back.rgb == img.rgb);
    const auto cls = classify(back);
    CHECK(cls[0] == PixelClass::Healthy);
    CHECK(cls[1] == PixelClass::Lesion);
    CHECK(cls[2] == PixelClass::Background);
    std::remove("test_tmp.ppm");
}

TEST(disjoint_set_basics) {
    DisjointSet d(6);
    CHECK(d.unite(0, 1));
    CHECK(d.unite(2, 3));
    CHECK(d.unite(1, 3));
    CHECK(!d.unite(0, 2));  // already connected
    CHECK_EQ(d.size_of(3), std::size_t{4});
    CHECK(d.find(4) != d.find(0));
}
