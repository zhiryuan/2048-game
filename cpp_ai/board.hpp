#pragma once

#include "types.hpp"
#include <algorithm>

// ============================================================
// Board: 64-bit bitboard, 4 bits per cell, row-major
// Row 0 at bits 0-15, row 1 at 16-31, row 2 at 32-47, row 3 at 48-63
// ============================================================

// Cell position to bit offset
inline int cell_offset(int row, int col) {
    return BITS_PER_CELL * (CELLS_PER_ROW * row + col);
}
inline int cell_offset(int pos) {
    return BITS_PER_CELL * pos;
}

inline int get_cell(Board b, int pos) {
    return static_cast<int>((b >> cell_offset(pos)) & CELL_MASK);
}

inline int get_cell(Board b, int row, int col) {
    return static_cast<int>((b >> cell_offset(row, col)) & CELL_MASK);
}

inline Board set_cell(Board b, int pos, int val) {
    int shift = cell_offset(pos);
    return (b & ~(static_cast<Board>(CELL_MASK) << shift))
           | (static_cast<Board>(val & CELL_MASK) << shift);
}

inline Board set_cell(Board b, int row, int col, int val) {
    return set_cell(b, row * N_COLS + col, val);
}

inline uint16_t get_row(Board b, int r) {
    return static_cast<uint16_t>((b >> (r * ROW_BITS)) & ROW_MASK);
}

inline Board set_row(Board b, int r, uint16_t val) {
    int shift = r * ROW_BITS;
    return (b & ~(static_cast<Board>(ROW_MASK) << shift))
           | (static_cast<Board>(val) << shift);
}

inline uint16_t get_col(Board b, int c) {
    uint16_t result = 0;
    for (int i = 0; i < N_ROWS; ++i)
        result |= static_cast<uint16_t>(get_cell(b, i, c)) << (BITS_PER_CELL * i);
    return result;
}

inline Board set_col(Board b, int c, uint16_t val) {
    for (int i = 0; i < N_ROWS; ++i) {
        int nibble = (val >> (BITS_PER_CELL * i)) & CELL_MASK;
        b = set_cell(b, i, c, nibble);
    }
    return b;
}

// ============================================================
// Move LUT: precomputed row slide+merge, 65536 entries
// ============================================================

struct RowResult {
    uint16_t row;    // row after sliding left
    int score;       // merge score from this slide
    bool changed;    // whether any tile moved or merged
};

extern RowResult MOVE_LUT[LUT_SIZE];

inline void init_move_lut() {
    for (int entry = 0; entry < LUT_SIZE; ++entry) {
        // Extract 4 nibbles
        int v[4];
        v[0] = (entry >>  0) & 0xF;
        v[1] = (entry >>  4) & 0xF;
        v[2] = (entry >>  8) & 0xF;
        v[3] = (entry >> 12) & 0xF;

        // Compact: remove zeros
        int tmp[4] = {0, 0, 0, 0};
        int n = 0;
        for (int i = 0; i < 4; ++i)
            if (v[i] != 0) tmp[n++] = v[i];

        // Merge left-to-right
        int score = 0;
        int merged[4] = {0, 0, 0, 0};
        int m = 0;
        int i = 0;
        while (i < n) {
            if (i + 1 < n && tmp[i] == tmp[i + 1]) {
                int new_val = std::min(tmp[i] + 1, MAX_TILE_EXP);
                merged[m++] = new_val;
                score += (1 << (tmp[i] + 1)); // actual score = 2^(v+1)
                i += 2;
            } else {
                merged[m++] = tmp[i];
                i += 1;
            }
        }

        // Pack result
        uint16_t result = 0;
        for (int j = 0; j < m; ++j)
            result |= static_cast<uint16_t>(merged[j]) << (BITS_PER_CELL * j);
        // remaining slots stay 0

        bool changed = (entry != result);

        MOVE_LUT[entry] = {result, score, changed};
    }
}

// ============================================================
// Move execution
// ============================================================

struct MoveResult {
    Board afterstate;
    int score;
    bool valid;
};

inline MoveResult execute_move(Board b, Direction d) {
    Board result = b;
    int total_score = 0;
    bool any_change = false;

    switch (d) {
    case LEFT:
        for (int r = 0; r < N_ROWS; ++r) {
            uint16_t row = get_row(result, r);
            auto& lut = MOVE_LUT[row];
            if (lut.changed) {
                result = set_row(result, r, lut.row);
                total_score += lut.score;
                any_change = true;
            }
        }
        break;
    case RIGHT:
        for (int r = 0; r < N_ROWS; ++r) {
            uint16_t row = get_row(result, r);
            uint16_t rev = reverse_row(row);
            auto& lut = MOVE_LUT[rev];
            if (lut.changed) {
                result = set_row(result, r, reverse_row(lut.row));
                total_score += lut.score;
                any_change = true;
            }
        }
        break;
    case UP:
        for (int c = 0; c < N_COLS; ++c) {
            uint16_t col = get_col(result, c);
            auto& lut = MOVE_LUT[col];
            if (lut.changed) {
                result = set_col(result, c, lut.row);
                total_score += lut.score;
                any_change = true;
            }
        }
        break;
    case DOWN:
        for (int c = 0; c < N_COLS; ++c) {
            uint16_t col = get_col(result, c);
            uint16_t rev = reverse_row(col);
            auto& lut = MOVE_LUT[rev];
            if (lut.changed) {
                result = set_col(result, c, reverse_row(lut.row));
                total_score += lut.score;
                any_change = true;
            }
        }
        break;
    }

    return {result, total_score, any_change};
}

// ============================================================
// Game logic
// ============================================================

inline bool is_game_over(Board b) {
    for (int d = 0; d < 4; ++d) {
        auto mr = execute_move(b, static_cast<Direction>(d));
        if (mr.valid) return false;
    }
    return true;
}

inline int count_empty(Board b) {
    int count = 0;
    for (int i = 0; i < N_CELLS; ++i)
        if (get_cell(b, i) == 0) ++count;
    return count;
}

// Fill positions array with indices of empty cells, return count
inline int get_empty_positions(Board b, int* positions) {
    int count = 0;
    for (int i = 0; i < N_CELLS; ++i)
        if (get_cell(b, i) == 0) positions[count++] = i;
    return count;
}

inline int max_tile(Board b) {
    int m = 0;
    for (int i = 0; i < N_CELLS; ++i)
        m = std::max(m, get_cell(b, i));
    return m;
}

// Place a new tile on board: log2_val = 1 for tile 2, 2 for tile 4
inline Board spawn_tile(Board b, int pos, int log2_val) {
    return set_cell(b, pos, log2_val);
}

// Random spawn: pick empty cell uniformly, 90% tile 2, 10% tile 4.
// Returns board with tile placed. If no empty cells, returns unchanged.
// tile_val output: actual log2 value placed (1 or 2).
inline Board random_spawn(Board b, RNG& rng, int& out_log2_val) {
    int positions[N_CELLS];
    int n = get_empty_positions(b, positions);
    if (n == 0) { out_log2_val = 0; return b; }
    int idx = rng.rand_int(n);
    int pos = positions[idx];
    int val = rng.chance(0.9) ? 1 : 2;
    out_log2_val = val;
    return spawn_tile(b, pos, val);
}

// Initial board: 2 random tiles
inline Board init_board(RNG& rng) {
    Board b = 0;
    int dummy;
    b = random_spawn(b, rng, dummy);
    b = random_spawn(b, rng, dummy);
    return b;
}
