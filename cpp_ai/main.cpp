#include "board.hpp"
#include "ntuple.hpp"

#include <iostream>
#include <iomanip>
#include <sstream>
#include <string>
#include <thread>
#include <atomic>
#include <mutex>
#include <vector>
#include <chrono>
#include <algorithm>
#include <cstring>

// Socket (Mac/Linux)
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

// ============================================================
// Global LUT and indexer definitions
// ============================================================

RowResult MOVE_LUT[LUT_SIZE];
int indexer_4[NUM_4TUPLE_PATTERNS][NUM_SYMMETRIES][4];
int indexer_6[NUM_6TUPLE_PATTERNS][NUM_SYMMETRIES][6];
int mult_4[4];
int mult_6[6];

// ============================================================
// Greedy action selection (1-ply)
// ============================================================

struct GreedyResult {
    float value;        // max over actions of (score + V(afterstate))
    Direction action;
    Board afterstate;
    int score;
    bool valid;
};

inline GreedyResult greedy(const NtupleNetwork& net, Board board) {
    GreedyResult best;
    best.value = -1e30f;
    best.valid = false;

    for (int d = 0; d < 4; ++d) {
        Direction dir = DIRS[d];
        auto mr = execute_move(board, dir);
        if (!mr.valid) continue;
        float val = static_cast<float>(mr.score) + evaluate(net, mr.afterstate);
        if (val > best.value) {
            best.value = val;
            best.action = dir;
            best.afterstate = mr.afterstate;
            best.score = mr.score;
            best.valid = true;
        }
    }
    return best;
}

// ============================================================
// Game stats
// ============================================================

struct GameStats {
    int total_score = 0;
    int steps = 0;
    int max_tile = 0;
};

// ============================================================
// TD(0) afterstate training: one episode
//
// Trajectory: s0 -> (a0,r0) -> s'0 -> spawn -> s1 -> (a1,r1) -> s'1 ...
//
// TD target for V(s'_t): if not terminal:
//   target = max_a [ r(s_{t+1}, a) + V(s'(s_{t+1}, a)) ]
//          = greedy_value(s_{t+1})
// if terminal: target = 0
//
// Update: V(s'_t) += alpha * (target - V(s'_t))
// ============================================================

inline GameStats train_episode(NtupleNetwork& net, float alpha, RNG& rng) {
    GameStats stats;
    Board board = init_board(rng);
    Board prev_afterstate = 0;
    bool has_prev = false;

    while (true) {
        // Greedy action from current board state
        auto gr = greedy(net, board);
        if (!gr.valid) break; // terminal

        stats.total_score += gr.score;
        stats.steps++;

        // Track max tile (from BEFORE the move, i.e. the state)
        int tile_exp = max_tile(board);
        int tile_val = 1 << tile_exp;
        if (tile_val > stats.max_tile) stats.max_tile = tile_val;

        // TD(0) update for previous afterstate
        // target = greedy_value(s_t) = gr.value
        if (has_prev) {
            float v_old = evaluate(net, prev_afterstate);
            float td_error = gr.value - v_old;
            update(net, prev_afterstate, td_error, alpha);
        }

        prev_afterstate = gr.afterstate;
        has_prev = true;

        // Environment: spawn random tile
        int spawn_val;
        board = random_spawn(gr.afterstate, rng, spawn_val);
    }

    // Terminal update for the last afterstate: target = 0
    if (has_prev) {
        float v_old = evaluate(net, prev_afterstate);
        update(net, prev_afterstate, -v_old, alpha);
    }

    // Also track the final board's max tile
    int final_tile = 1 << max_tile(board);
    if (final_tile > stats.max_tile) stats.max_tile = final_tile;

    return stats;
}

// ============================================================
// Multi-threaded training
// ============================================================

struct TrainConfig {
    int total_episodes;
    float alpha;
    NtupleNetwork* net;

    std::atomic<long long> episodes_done{0};
    std::atomic<long long> total_score{0};
    std::atomic<long long> total_steps{0};
    std::atomic<int> best_tile{0};
    std::mutex print_mutex;
};

void train_worker(TrainConfig& cfg, int thread_id) {
    RNG rng(static_cast<uint64_t>(thread_id + 1) * 0x9e3779b97f4a7c15ULL);

    long long local_score = 0;
    int local_steps = 0;
    int local_best = 0;
    int local_episodes = 0;

    auto last_report = std::chrono::steady_clock::now();

    while (true) {
        int ep = cfg.episodes_done.fetch_add(1, std::memory_order_relaxed);
        if (ep >= cfg.total_episodes) break;

        auto stats = train_episode(*cfg.net, cfg.alpha, rng);

        local_score += stats.total_score;
        local_steps += stats.steps;
        if (stats.max_tile > local_best) local_best = stats.max_tile;
        local_episodes++;

        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
            now - last_report).count();
        if (elapsed > 2000) {
            std::lock_guard<std::mutex> lock(cfg.print_mutex);
            cfg.total_score.fetch_add(local_score, std::memory_order_relaxed);
            cfg.total_steps.fetch_add(local_steps, std::memory_order_relaxed);

            // Update best tile thread-safely
            int old_best = cfg.best_tile.load(std::memory_order_relaxed);
            while (local_best > old_best) {
                if (cfg.best_tile.compare_exchange_weak(old_best, local_best,
                                                        std::memory_order_relaxed))
                    break;
            }

            int done = cfg.episodes_done.load(std::memory_order_relaxed);
            std::cout << "\r[" << done << "/" << cfg.total_episodes
                      << "] best=" << cfg.best_tile.load(std::memory_order_relaxed)
                      << "  avg_score=" << (local_score / std::max(local_episodes, 1))
                      << "  steps=" << (local_steps / std::max(local_episodes, 1))
                      << "        " << std::flush;

            local_score = 0;
            local_steps = 0;
            local_episodes = 0;
            last_report = now;
        }
    }

    // Final update
    cfg.total_score.fetch_add(local_score, std::memory_order_relaxed);
    cfg.total_steps.fetch_add(local_steps, std::memory_order_relaxed);
    int old_best = cfg.best_tile.load(std::memory_order_relaxed);
    while (local_best > old_best) {
        if (cfg.best_tile.compare_exchange_weak(old_best, local_best,
                                                std::memory_order_relaxed))
            break;
    }
}

void train_parallel(NtupleNetwork& net, int episodes, int threads, float alpha) {
    TrainConfig cfg;
    cfg.total_episodes = episodes;
    cfg.alpha = alpha;
    cfg.net = &net;

    std::cout << "Training: " << episodes << " episodes, "
              << threads << " threads, alpha=" << alpha << "\n";

    auto t0 = std::chrono::steady_clock::now();

    std::vector<std::thread> workers;
    for (int i = 0; i < threads; ++i)
        workers.emplace_back(train_worker, std::ref(cfg), i);
    for (auto& t : workers) t.join();

    auto t1 = std::chrono::steady_clock::now();
    double sec = std::chrono::duration<double>(t1 - t0).count();

    std::cout << "\rDone! " << episodes << " episodes in "
              << std::fixed << std::setprecision(1) << sec << "s ("
              << std::setprecision(0) << (episodes / sec) << " eps/s)\n"
              << "Best tile: " << cfg.best_tile.load()
              << "  Avg score: " << (cfg.total_score.load() / episodes)
              << "  Avg steps: " << (cfg.total_steps.load() / episodes) << "\n";
}

// ============================================================
// Expectimax search
// ============================================================

struct TTEntry {
    uint64_t hash;
    float value;
    int depth;   // remaining search depth at which this was computed
    bool valid;
};

class TranspositionTable {
    std::vector<TTEntry> entries_;
    int mask_;

public:
    explicit TranspositionTable(int size_mb) {
        long long bytes = static_cast<long long>(size_mb) * 1024 * 1024;
        int count = static_cast<int>(bytes / sizeof(TTEntry));
        int pow2 = 1;
        while (pow2 < count) pow2 <<= 1;
        entries_.resize(pow2);
        mask_ = pow2 - 1;
        clear();
    }

    void clear() {
        for (auto& e : entries_) e.valid = false;
    }

    float* lookup(uint64_t hash, int depth) {
        int idx = static_cast<int>(hash & static_cast<uint64_t>(mask_));
        for (int i = 0; i < 4; ++i) {
            auto& e = entries_[(idx + i) & mask_];
            if (!e.valid) return nullptr;
            if (e.hash == hash && e.depth >= depth) return &e.value;
        }
        return nullptr;
    }

    void store(uint64_t hash, float value, int depth) {
        int idx = static_cast<int>(hash & static_cast<uint64_t>(mask_));
        for (int i = 0; i < 4; ++i) {
            auto& e = entries_[(idx + i) & mask_];
            if (!e.valid || e.hash == hash) {
                e.hash = hash; e.value = value; e.depth = depth; e.valid = true;
                return;
            }
        }
        entries_[idx] = {hash, value, depth, true};
    }
};

// Forward declarations
static float expt_max(Board board, int depth, int max_depth,
                      const NtupleNetwork& net, TranspositionTable& tt);
static float expt_chance(Board afterstate, int depth, int max_depth,
                         const NtupleNetwork& net, TranspositionTable& tt);

// Max node: player chooses best move. depth starts at 1.
static float expt_max(Board board, int depth, int max_depth,
                      const NtupleNetwork& net, TranspositionTable& tt) {
    int remaining = max_depth - depth + 1;
    float* cached = tt.lookup(board, remaining);
    if (cached) return *cached;

    if (is_game_over(board)) {
        tt.store(board, 0.0f, remaining);
        return 0.0f;
    }

    float best = -1e30f;
    for (int d = 0; d < 4; ++d) {
        auto mr = execute_move(board, DIRS[d]);
        if (!mr.valid) continue;

        float val;
        if (depth >= max_depth) {
            // Leaf: evaluate afterstate directly
            val = static_cast<float>(mr.score) + evaluate(net, mr.afterstate);
        } else {
            val = static_cast<float>(mr.score)
                + expt_chance(mr.afterstate, depth + 1, max_depth, net, tt);
        }
        if (val > best) best = val;
    }

    tt.store(board, best, remaining);
    return best;
}

// Chance node: environment places random tile (2 at 90%, 4 at 10%)
static float expt_chance(Board afterstate, int depth, int max_depth,
                         const NtupleNetwork& net, TranspositionTable& tt) {
    int positions[N_CELLS];
    int n = get_empty_positions(afterstate, positions);
    if (n == 0) return evaluate(net, afterstate);

    float total = 0.0f;
    for (int i = 0; i < n; ++i) {
        int pos = positions[i];
        total += 0.9f * expt_max(spawn_tile(afterstate, pos, 1), depth, max_depth, net, tt);
        total += 0.1f * expt_max(spawn_tile(afterstate, pos, 2), depth, max_depth, net, tt);
    }
    return total / static_cast<float>(n);
}

// ============================================================
// Evaluation mode
// ============================================================

void evaluate_model(const NtupleNetwork& net, int episodes, int depth, int tt_mb) {
    TranspositionTable tt(tt_mb);
    RNG rng(12345);

    std::cout << "Evaluating: " << episodes << " games, depth=" << depth
              << ", TT=" << tt_mb << "MB\n";

    int max_tile_count[17] = {};
    long long total_score = 0;
    auto t0 = std::chrono::steady_clock::now();

    for (int ep = 0; ep < episodes; ++ep) {
        Board board = init_board(rng);
        int score = 0;
        tt.clear();

        while (!is_game_over(board)) {
            // Use expectimax to select action
            float best_val = -1e30f;
            Board best_after = 0;
            int best_score = 0;

            for (int d = 0; d < 4; ++d) {
                auto mr = execute_move(board, DIRS[d]);
                if (!mr.valid) continue;

                float val;
                if (depth <= 1) {
                    val = static_cast<float>(mr.score) + evaluate(net, mr.afterstate);
                } else {
                    val = static_cast<float>(mr.score)
                        + expt_chance(mr.afterstate, 2, depth, net, tt);
                }

                if (val > best_val) {
                    best_val = val;
                    best_after = mr.afterstate;
                    best_score = mr.score;
                }
            }

            score += best_score;
            int dummy;
            board = random_spawn(best_after, rng, dummy);
        }

        total_score += score;
        int mt = max_tile(board);
        if (mt >= 0 && mt < 17) max_tile_count[mt]++;

        if ((ep + 1) % std::max(1, episodes / 10) == 0) {
            auto t1 = std::chrono::steady_clock::now();
            double sec = std::chrono::duration<double>(t1 - t0).count();
            std::cout << "\r  " << (ep + 1) << "/" << episodes
                      << " (" << std::fixed << std::setprecision(1)
                      << ((ep + 1) / sec) << " games/s)" << std::flush;
        }
    }

    auto t1 = std::chrono::steady_clock::now();
    double sec = std::chrono::duration<double>(t1 - t0).count();

    std::cout << "\rDone! " << episodes << " games in "
              << std::fixed << std::setprecision(1) << sec << "s ("
              << (episodes / sec) << " games/s)\n\n";

    std::cout << "Max tile distribution:\n";
    for (int i = 1; i <= 16; ++i) {
        if (max_tile_count[i] > 0) {
            std::cout << "  " << (1 << i) << ": " << max_tile_count[i]
                      << " (" << std::fixed << std::setprecision(1)
                      << (100.0 * max_tile_count[i] / episodes) << "%)\n";
        }
    }
    std::cout << "Average score: " << (total_score / episodes) << "\n";
}

// ============================================================
// Play mode: connect to Python 2048 game via Unix socket
// ============================================================

static const char* SOCK_PATH = "/tmp/2048game.sock";

// Parse board state from game message format:
//   move\n
//   n m\n
//   v00 v01 v02 v03\n
//   ...
//   \n
// Values: 1=2, 2=4, 3=8, ... ; 0=empty ; negative=special tile
static Board parse_board(const std::string& msg) {
    std::istringstream ss(msg);
    std::string line;
    std::getline(ss, line); // "move"
    int n, m;
    ss >> n >> m;
    std::getline(ss, line); // consume rest of dimensions line

    Board board = 0;
    for (int r = 0; r < n && r < 4; ++r) {
        for (int c = 0; c < m && c < 4; ++c) {
            int val;
            ss >> val;
            // Game sends actual tile value (2,4,8,...); 0=empty; negative=special
            // Convert to log2: __builtin_ctz(2)=1, ctz(4)=2, ctz(32)=5, etc.
            int log2v = 0;
            if (val > 0) {
                log2v = __builtin_ctz(val);
                if (log2v > MAX_TILE_EXP) log2v = MAX_TILE_EXP;
            }
            board = set_cell(board, r, c, log2v);
        }
        // Consume remaining values if grid is larger
        for (int c = 4; c < m; ++c) { int dummy; ss >> dummy; }
    }
    return board;
}

// Map direction to char for Python game
static char dir_to_char(Direction d) {
    switch (d) {
    case UP:    return 'w';
    case DOWN:  return 's';
    case LEFT:  return 'a';
    case RIGHT: return 'd';
    default:    return 'w';
    }
}

static int play_mode(const NtupleNetwork& net, int depth, int tt_mb) {
    // Connect to socket
    int sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock < 0) {
        std::cerr << "Failed to create socket\n";
        return 1;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCK_PATH, sizeof(addr.sun_path) - 1);

    if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        std::cerr << "Failed to connect to " << SOCK_PATH
                  << "\nMake sure the Python game is running first.\n";
        close(sock);
        return 1;
    }

    std::cout << "Connected to 2048 game at " << SOCK_PATH << "\n"
              << "AI playing with depth=" << depth << ", TT=" << tt_mb << "MB\n"
              << "Press Ctrl+C to stop.\n" << std::endl;

    TranspositionTable tt(tt_mb);
    char buf[8192];
    int move_count = 0;

    while (true) {
        // Receive board state (one recv, like cli_2048_not_ai.py)
        int n = (int)recv(sock, buf, sizeof(buf) - 1, 0);
        if (n <= 0) {
            if (n == 0) std::cout << "Game disconnected.\n";
            else perror("recv");
            break;
        }
        buf[n] = '\0';

        // Trim trailing "\n\n" (board message terminator)
        if (n >= 2 && buf[n-1] == '\n' && buf[n-2] == '\n')
            buf[n-2] = '\0';

        std::string msg(buf);

        // Check for "still" (game over or invalid state)
        if (msg.find("still") == 0) {
            std::cout << "Game over.\n";
            break;
        }

        // Parse board
        Board board = parse_board(msg + "\n");

        // Find best move using expectimax
        float best_val = -1e30f;
        Direction best_dir = UP;
        tt.clear();

        for (int d = 0; d < 4; ++d) {
            auto mr = execute_move(board, DIRS[d]);
            if (!mr.valid) continue;

            float val;
            if (depth <= 1) {
                val = static_cast<float>(mr.score) + evaluate(net, mr.afterstate);
            } else {
                val = static_cast<float>(mr.score)
                    + expt_chance(mr.afterstate, 2, depth, net, tt);
            }
            if (val > best_val) {
                best_val = val;
                best_dir = DIRS[d];
            }
        }

        // Send move
        char move_ch = dir_to_char(best_dir);
        if (send(sock, &move_ch, 1, 0) < 0) {
            perror("send");
            break;
        }

        move_count++;
        int mt = 1 << max_tile(board);
        std::cout << "\r[" << move_count << "] max_tile=" << mt
                  << "  move=" << move_ch << "      " << std::flush;
    }

    close(sock);
    std::cout << "\nTotal moves: " << move_count << "\n";
    return 0;
}

// ============================================================
// CLI
// ============================================================

static void print_usage() {
    std::cout << R"(Usage:
  2048_ai train --episodes N [--threads 8] [--alpha 0.1]
                [--load weights.bin] [--save weights.bin]
  2048_ai eval  --episodes N [--depth 3] [--tt-size 256]
                --load weights.bin
  2048_ai play  [--depth 2] [--tt-size 256]
                --load weights.bin
)";
}

static std::string get_arg(int argc, char* argv[],
                           const std::string& name, const std::string& def = "") {
    for (int i = 1; i < argc - 1; ++i)
        if (argv[i] == name) return argv[i + 1];
    return def;
}

int main(int argc, char* argv[]) {
    if (argc < 2) { print_usage(); return 1; }

    std::string mode = argv[1];

    // Initialize globals
    init_move_lut();
    init_indexers();

    NtupleNetwork net;

    if (mode == "train") {
        int episodes = std::stoi(get_arg(argc, argv, "--episodes", "100000"));
        int threads  = std::stoi(get_arg(argc, argv, "--threads", "8"));
        float alpha  = std::stof(get_arg(argc, argv, "--alpha", "0.1"));
        std::string load = get_arg(argc, argv, "--load");
        std::string save = get_arg(argc, argv, "--save", "cpp_ai_weights.bin");

        if (!load.empty()) load_weights(net, load);

        train_parallel(net, episodes, threads, alpha);

        if (!save.empty()) save_weights(net, save);

    } else if (mode == "eval") {
        int episodes = std::stoi(get_arg(argc, argv, "--episodes", "100"));
        int depth    = std::stoi(get_arg(argc, argv, "--depth", "3"));
        int tt_mb    = std::stoi(get_arg(argc, argv, "--tt-size", "256"));
        std::string load = get_arg(argc, argv, "--load");

        if (load.empty()) {
            std::cerr << "Error: --load required for eval\n";
            return 1;
        }
        if (!load_weights(net, load)) return 1;

        evaluate_model(net, episodes, depth, tt_mb);

    } else if (mode == "play") {
        int depth    = std::stoi(get_arg(argc, argv, "--depth", "2"));
        int tt_mb    = std::stoi(get_arg(argc, argv, "--tt-size", "256"));
        std::string load = get_arg(argc, argv, "--load");

        if (load.empty()) {
            std::cerr << "Error: --load required for play\n";
            return 1;
        }
        if (!load_weights(net, load)) return 1;

        return play_mode(net, depth, tt_mb);

    } else {
        std::cerr << "Unknown mode: " << mode << "\n";
        print_usage();
        return 1;
    }

    return 0;
}
