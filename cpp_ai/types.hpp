#pragma once

#include <cstdint>

// ============================================================
// Constants
// ============================================================

constexpr int MAX_TILE_EXP = 15;        // cap at 32768 (2^15), for 65536 clip to 15
constexpr int BITS_PER_CELL = 4;
constexpr int CELL_MASK = 0xF;
constexpr int CELLS_PER_ROW = 4;
constexpr int ROW_BITS = 16;
constexpr int ROW_MASK = 0xFFFF;
constexpr int N_CELLS = 16;
constexpr int N_ROWS = 4;
constexpr int N_COLS = 4;
constexpr int LUT_SIZE = 65536;         // 16-bit rows
constexpr int NUM_SYMMETRIES = 8;       // D4 group
constexpr int NUM_4TUPLE_PATTERNS = 17; // 4 rows + 4 cols + 9 2x2 blocks
constexpr int NUM_6TUPLE_PATTERNS = 6;  // 2x3 blocks
constexpr int NUM_WINDOWS = 4;          // buckets for 6-tuple values
constexpr int WIN_BINS = 6;             // 6 buckets per window
constexpr int IDX_4TUPLE = 65536;       // 16^4
constexpr int IDX_6TUPLE = 46656;       // 6^6
constexpr int TOTAL_FEATURES =
    NUM_4TUPLE_PATTERNS * NUM_SYMMETRIES +
    NUM_6TUPLE_PATTERNS * NUM_SYMMETRIES * NUM_WINDOWS; // 17*8 + 6*8*4 = 328

// ============================================================
// Types
// ============================================================

using Board = uint64_t;

enum Direction { UP = 0, RIGHT = 1, DOWN = 2, LEFT = 3 };
constexpr Direction DIRS[4] = {UP, RIGHT, DOWN, LEFT};

// ============================================================
// xoshiro256** PRNG (fast, passes BigCrush)
// ============================================================

struct RNG {
    uint64_t s[4];

    RNG(uint64_t seed = 0) { seed_from(seed); }

    void seed_from(uint64_t seed) {
        // splitmix64 seeding
        uint64_t z = seed + 0x9e3779b97f4a7c15ULL;
        for (int i = 0; i < 4; ++i) {
            z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
            z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
            z = z ^ (z >> 31);
            s[i] = z;
        }
    }

    uint64_t next() {
        const uint64_t result = rotl(s[1] * 5, 7) * 9;
        const uint64_t t = s[1] << 17;
        s[2] ^= s[0];
        s[3] ^= s[1];
        s[1] ^= s[2];
        s[0] ^= s[3];
        s[2] ^= t;
        s[3] = rotl(s[3], 45);
        return result;
    }

    // [0, 1) double
    double uniform() {
        return (next() >> 11) * 0x1.0p-53; // 1 / 2^53
    }

    // [0, n) integer
    int rand_int(int n) {
        return static_cast<int>(next() % static_cast<uint64_t>(n));
    }

    // roll: true with probability p (0..1)
    bool chance(double p) { return uniform() < p; }

private:
    static inline uint64_t rotl(uint64_t x, int k) {
        return (x << k) | (x >> (64 - k));
    }
};

// ============================================================
// Row reverse (nibble-wise, for right/down moves)
// ============================================================

inline uint16_t reverse_row(uint16_t x) {
    // swap nibble 0<->3 and 1<->2
    x = ((x & 0xF000) >> 12) | ((x & 0x0F00) >> 4)
      | ((x & 0x00F0) << 4)  | ((x & 0x000F) << 12);
    return x;
}

// ============================================================
// Window bucketing for 6-tuple encoding
// ============================================================

struct Window {
    int lo; // lower bound (inclusive) of 5-value window
    int hi; // upper bound (inclusive)
};

constexpr Window WINDOWS[NUM_WINDOWS] = {
    { 1,  5}, // covers tiles 2..32
    { 4,  8}, // covers tiles 16..256
    { 7, 11}, // covers tiles 128..2048
    {10, 14}, // covers tiles 1024..16384
};

inline int bucket(int log2_val, const Window& w) {
    if (log2_val == 0) return 0;       // empty
    if (log2_val <= w.lo) return 1;    // below window
    if (log2_val >= w.hi) return 5;    // above window
    return log2_val - w.lo + 1;        // within window (2..4)
}
