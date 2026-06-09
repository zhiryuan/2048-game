#pragma once

#include "types.hpp"
#include "board.hpp"

// ============================================================
// Pattern definitions (cell positions, linear index 0-15)
// ============================================================

// 4-tuple patterns: 4 rows + 4 cols + 9 2x2 blocks = 17
constexpr int PATTERNS_4[NUM_4TUPLE_PATTERNS][4] = {
    // rows
    { 0,  1,  2,  3},
    { 4,  5,  6,  7},
    { 8,  9, 10, 11},
    {12, 13, 14, 15},
    // columns
    { 0,  4,  8, 12},
    { 1,  5,  9, 13},
    { 2,  6, 10, 14},
    { 3,  7, 11, 15},
    // 2x2 blocks
    { 0,  1,  4,  5},  // top-left
    { 1,  2,  5,  6},  // top-mid
    { 2,  3,  6,  7},  // top-right
    { 4,  5,  8,  9},  // mid-left
    { 5,  6,  9, 10},  // center
    { 6,  7, 10, 11},  // mid-right
    { 8,  9, 12, 13},  // bottom-left
    { 9, 10, 13, 14},  // bottom-mid
    {10, 11, 14, 15},  // bottom-right
};

// 6-tuple patterns: 2x3 blocks
constexpr int PATTERNS_6[NUM_6TUPLE_PATTERNS][6] = {
    { 0,  1,  2,  4,  5,  6},  // top-left 2x3
    { 1,  2,  3,  5,  6,  7},  // top-right 2x3
    { 4,  5,  6,  8,  9, 10},  // mid-left 2x3
    { 5,  6,  7,  9, 10, 11},  // mid-right 2x3
    { 8,  9, 10, 12, 13, 14},  // bottom-left 2x3
    { 9, 10, 11, 13, 14, 15},  // bottom-right 2x3
};

// ============================================================
// D4 symmetry: 8 transformations of cell positions
// ============================================================

// Apply symmetry s to cell position (row, col), return new position
inline int apply_sym(int row, int col, int sym) {
    int r, c;
    switch (sym) {
    case 0: r = row;     c = col;      break; // identity
    case 1: r = col;     c = 3 - row;  break; // rot90
    case 2: r = 3 - row; c = 3 - col;  break; // rot180
    case 3: r = 3 - col; c = row;      break; // rot270
    case 4: r = row;     c = 3 - col;  break; // reflectH
    case 5: r = 3 - row; c = col;      break; // reflectV
    case 6: r = col;     c = row;      break; // transpose
    case 7: r = 3 - col; c = 3 - row;  break; // anti-diagonal
    default: r = row; c = col; break;
    }
    return r * N_COLS + c;
}

// Precomputed: for each (pattern, symmetry, cell_index), the cell position
// indexer_4[p][s][k] = cell position on original board for pattern p,
//   symmetry s, and the k-th cell in the pattern
extern int indexer_4[NUM_4TUPLE_PATTERNS][NUM_SYMMETRIES][4];
extern int indexer_6[NUM_6TUPLE_PATTERNS][NUM_SYMMETRIES][6];

// Precomputed index multiplier tables
extern int mult_4[4];   // {4096, 256, 16, 1}
extern int mult_6[6];   // {7776, 1296, 216, 36, 6, 1}

inline void init_indexers() {
    // 4-tuple multipliers: 16^3, 16^2, 16^1, 16^0
    mult_4[0] = 4096; mult_4[1] = 256; mult_4[2] = 16; mult_4[3] = 1;

    // 6-tuple multipliers: 6^5, 6^4, 6^3, 6^2, 6^1, 6^0
    mult_6[0] = 7776; mult_6[1] = 1296; mult_6[2] = 216;
    mult_6[3] = 36;   mult_6[4] = 6;    mult_6[5] = 1;

    // Build indexers
    for (int p = 0; p < NUM_4TUPLE_PATTERNS; ++p) {
        for (int s = 0; s < NUM_SYMMETRIES; ++s) {
            for (int k = 0; k < 4; ++k) {
                int pos = PATTERNS_4[p][k];
                int row = pos / N_COLS;
                int col = pos % N_COLS;
                indexer_4[p][s][k] = apply_sym(row, col, s);
            }
        }
    }
    for (int p = 0; p < NUM_6TUPLE_PATTERNS; ++p) {
        for (int s = 0; s < NUM_SYMMETRIES; ++s) {
            for (int k = 0; k < 6; ++k) {
                int pos = PATTERNS_6[p][k];
                int row = pos / N_COLS;
                int col = pos % N_COLS;
                indexer_6[p][s][k] = apply_sym(row, col, s);
            }
        }
    }
}

// ============================================================
// N-tuple network
// ============================================================

struct NtupleNetwork {
    // 4-tuple weights: 17 patterns, 1 table each, 65536 entries
    // Shared across 8 symmetries
    float* tables_4[NUM_4TUPLE_PATTERNS];

    // 6-tuple weights: 6 patterns × 4 windows, 46656 entries each
    float* tables_6[NUM_6TUPLE_PATTERNS * NUM_WINDOWS];

    NtupleNetwork() {
        for (int i = 0; i < NUM_4TUPLE_PATTERNS; ++i) {
            tables_4[i] = new float[IDX_4TUPLE]();
        }
        for (int i = 0; i < NUM_6TUPLE_PATTERNS * NUM_WINDOWS; ++i) {
            tables_6[i] = new float[IDX_6TUPLE]();
        }
    }

    ~NtupleNetwork() {
        for (int i = 0; i < NUM_4TUPLE_PATTERNS; ++i) delete[] tables_4[i];
        for (int i = 0; i < NUM_6TUPLE_PATTERNS * NUM_WINDOWS; ++i) delete[] tables_6[i];
    }

    // No copy
    NtupleNetwork(const NtupleNetwork&) = delete;
    NtupleNetwork& operator=(const NtupleNetwork&) = delete;

    // Move
    NtupleNetwork(NtupleNetwork&& other) noexcept {
        for (int i = 0; i < NUM_4TUPLE_PATTERNS; ++i) {
            tables_4[i] = other.tables_4[i];
            other.tables_4[i] = nullptr;
        }
        for (int i = 0; i < NUM_6TUPLE_PATTERNS * NUM_WINDOWS; ++i) {
            tables_6[i] = other.tables_6[i];
            other.tables_6[i] = nullptr;
        }
    }
};

// ============================================================
// Evaluate board value
// ============================================================

inline float evaluate(const NtupleNetwork& net, Board b) {
    float total = 0.0f;

    // 4-tuples: 17 patterns × 8 symmetries = 136 lookups
    for (int p = 0; p < NUM_4TUPLE_PATTERNS; ++p) {
        float* table = net.tables_4[p];
        for (int s = 0; s < NUM_SYMMETRIES; ++s) {
            const int* idxr = indexer_4[p][s];
            int idx = (get_cell(b, idxr[0]) << 12)
                    | (get_cell(b, idxr[1]) << 8)
                    | (get_cell(b, idxr[2]) << 4)
                    |  get_cell(b, idxr[3]);
            total += table[idx];
        }
    }

    // 6-tuples: 6 patterns × 8 symmetries × 4 windows = 192 lookups
    for (int p = 0; p < NUM_6TUPLE_PATTERNS; ++p) {
        for (int s = 0; s < NUM_SYMMETRIES; ++s) {
            const int* idxr = indexer_6[p][s];
            // Extract cell values once per (p,s)
            int vals[6];
            for (int k = 0; k < 6; ++k)
                vals[k] = get_cell(b, idxr[k]);

            for (int w = 0; w < NUM_WINDOWS; ++w) {
                const Window& win = WINDOWS[w];
                float* table = net.tables_6[p * NUM_WINDOWS + w];
                int idx = bucket(vals[0], win) * mult_6[0]
                        + bucket(vals[1], win) * mult_6[1]
                        + bucket(vals[2], win) * mult_6[2]
                        + bucket(vals[3], win) * mult_6[3]
                        + bucket(vals[4], win) * mult_6[4]
                        + bucket(vals[5], win) * mult_6[5];
                total += table[idx];
            }
        }
    }

    return total;
}

// ============================================================
// Update weights (distribute TD error to all features)
// ============================================================

inline void update(NtupleNetwork& net, Board b, float delta, float alpha) {
    // alpha is the total learning rate, divide by number of features
    float per_feature = alpha * delta / static_cast<float>(TOTAL_FEATURES);

    // 4-tuples
    for (int p = 0; p < NUM_4TUPLE_PATTERNS; ++p) {
        float* table = net.tables_4[p];
        for (int s = 0; s < NUM_SYMMETRIES; ++s) {
            const int* idxr = indexer_4[p][s];
            int idx = (get_cell(b, idxr[0]) << 12)
                    | (get_cell(b, idxr[1]) << 8)
                    | (get_cell(b, idxr[2]) << 4)
                    |  get_cell(b, idxr[3]);
            table[idx] += per_feature;
        }
    }

    // 6-tuples
    for (int p = 0; p < NUM_6TUPLE_PATTERNS; ++p) {
        for (int s = 0; s < NUM_SYMMETRIES; ++s) {
            const int* idxr = indexer_6[p][s];
            int vals[6];
            for (int k = 0; k < 6; ++k)
                vals[k] = get_cell(b, idxr[k]);

            for (int w = 0; w < NUM_WINDOWS; ++w) {
                const Window& win = WINDOWS[w];
                float* table = net.tables_6[p * NUM_WINDOWS + w];
                int idx = bucket(vals[0], win) * mult_6[0]
                        + bucket(vals[1], win) * mult_6[1]
                        + bucket(vals[2], win) * mult_6[2]
                        + bucket(vals[3], win) * mult_6[3]
                        + bucket(vals[4], win) * mult_6[4]
                        + bucket(vals[5], win) * mult_6[5];
                table[idx] += per_feature;
            }
        }
    }
}

// ============================================================
// Weight save/load (simple binary format)
// ============================================================

#include <fstream>
#include <iostream>
#include <string>

inline void save_weights(const NtupleNetwork& net, const std::string& path) {
    std::ofstream f(path, std::ios::binary);
    if (!f) {
        std::cerr << "Cannot open " << path << " for writing\n";
        return;
    }
    uint32_t magic = 0x20480001;
    f.write(reinterpret_cast<const char*>(&magic), 4);

    for (int i = 0; i < NUM_4TUPLE_PATTERNS; ++i)
        f.write(reinterpret_cast<const char*>(net.tables_4[i]),
                IDX_4TUPLE * sizeof(float));

    for (int i = 0; i < NUM_6TUPLE_PATTERNS * NUM_WINDOWS; ++i)
        f.write(reinterpret_cast<const char*>(net.tables_6[i]),
                IDX_6TUPLE * sizeof(float));

    std::cout << "Weights saved to " << path << " ("
              << (IDX_4TUPLE * NUM_4TUPLE_PATTERNS
                  + IDX_6TUPLE * NUM_6TUPLE_PATTERNS * NUM_WINDOWS)
                 * sizeof(float) / 1024 / 1024 << " MB)\n";
}

inline bool load_weights(NtupleNetwork& net, const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) {
        std::cerr << "Cannot open " << path << " for reading\n";
        return false;
    }
    uint32_t magic;
    f.read(reinterpret_cast<char*>(&magic), 4);
    if (magic != 0x20480001) {
        std::cerr << "Bad magic: " << std::hex << magic << "\n";
        return false;
    }

    for (int i = 0; i < NUM_4TUPLE_PATTERNS; ++i)
        f.read(reinterpret_cast<char*>(net.tables_4[i]),
               IDX_4TUPLE * sizeof(float));

    for (int i = 0; i < NUM_6TUPLE_PATTERNS * NUM_WINDOWS; ++i)
        f.read(reinterpret_cast<char*>(net.tables_6[i]),
               IDX_6TUPLE * sizeof(float));

    std::cout << "Weights loaded from " << path << "\n";
    return true;
}
