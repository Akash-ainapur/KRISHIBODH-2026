# 05. Leaf-spot counter: connected components on an image

**Files:** `include/krishi/leaf_spots.hpp`, `src/leaf_spots.cpp`, `tests/test_leaf_spots.cpp`
**DSA:** graphs on grids, BFS, union-find (disjoint set union)

## The problem
`analytics.py` gives one number: the fraction of yellow/brown pixels. It cannot tell **one large rotten patch** from **forty small spots**, and forty small spots is what an early fungal infection looks like. To count spots, group damaged pixels that touch each other. That is **connected components**, with the image as a graph where each pixel is a node connected to its 8 neighbours.

## Pipeline
1. **Read the image** as binary PPM (P6). It's a tiny, dependency-free format. Convert a robot JPEG with:
   ```bash
   python -c "from PIL import Image; Image.open('in.jpg').convert('RGB').save('in.ppm')"
   ```
2. **RGB → HSV** on OpenCV's scale (H 0–179, S and V 0–255), so the thresholds match `analytics.py`. Hue separates "what colour" from "how bright", which matters under changing daylight.
3. **Classify** each pixel: healthy (green hue), lesion (yellow-brown hue), or background. The thresholds are in `ColorThresholds` so your team can tune them.
4. **Find connected lesion regions**, drop tiny ones as noise (`min_area`), and report each spot's area and bounding box.

## Two algorithms for step 4

### BFS flood fill
Find an unvisited lesion pixel, put it in a queue, and visit every lesion neighbour reachable from it. That is one spot. Repeat.
Key detail: mark a pixel **when it is queued**, not when it is popped. Otherwise the same pixel can be queued several times by different neighbours.

### Union-find (disjoint set union)
Scan pixels row by row. For each lesion pixel, `unite` it with lesion neighbours **already scanned** (left, up-left, up, up-right). Afterwards, all pixels with the same `find()` root form one spot.

Two optimisations make each operation almost O(1):
- **Path compression:** after `find(x)`, point every node on the path straight at the root.
- **Union by size:** hang the smaller tree under the larger, so trees stay shallow.

Together they give O(α(n)) per operation, where α is the inverse Ackermann function, which is below 5 for any input that fits in the universe.

## Results (`krishi_bench`, synthetic 1280×720 mask)
| Algorithm | Time | Spots |
|---|---|---|
| BFS | 22.3 ms | 43,521 |
| Union-find | 28.3 ms | 43,521 |

**BFS won here, and that is worth understanding.** Union-find needs a second pass, plus a hash map from root to spot id. BFS touches each pixel once and its queue stays in cache. Union-find shines when the data arrives **incrementally** (new edges over time, like a network growing) or when you only need "are these two connected?". The tests run both on 30 random images and require identical results.

## Interview questions
1. **Number of islands** (LeetCode 200): this exact problem with 4-connectivity. Know both the BFS and union-find answers.
2. **4- vs 8-connectivity?** 4 counts only up/down/left/right neighbours; 8 also counts diagonals. With 4, a diagonal line of pixels becomes many separate spots. The test `diagonal_pixels_join_one_spot` checks we use 8.
3. **Why only 4 neighbours in the union-find scan, when connectivity is 8?** The other 4 neighbours have not been scanned yet. When they are, they will look back at this pixel, so every edge is still seen exactly once.
4. **What do path compression and union by rank or size each buy?** Either alone gives O(log n) per operation; together, O(α(n)).
5. **Recursive DFS vs BFS on a big image?** Recursive DFS can overflow the call stack on a large connected region (a million pixels means a million stack frames). BFS with an explicit queue cannot.
6. **Why HSV instead of RGB thresholds?** In RGB, a shadow changes all three channels. In HSV, a shadow mostly changes V (brightness) and leaves H (the colour) alone.

## Ideas for your team
- Run it on the 96 captured images in `enhanced_app/app/captured_images`, after converting them to PPM, and plot spot count over time per plant. A rising count is an early disease warning.
- Tune `ColorThresholds` against a few hand-labelled images.
