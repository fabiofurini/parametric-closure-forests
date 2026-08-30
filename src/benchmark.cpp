#include "parametric_closure/pcf.hpp"

#ifndef PCF_GIT_COMMIT
#define PCF_GIT_COMMIT "unknown"
#endif

#include <sys/resource.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <ctime>
#include <iostream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using pcf::RaCStats;

pcf::ClosureLayerSequence run(const pcf::Instance& instance, const std::string& algorithm, RaCStats* rac_stats) {
    if (algorithm == "pac") return pcf::compute_pac(instance);
    if (algorithm == "dpac") return pcf::compute_dpac(instance);
    if (algorithm == "hpac") return pcf::compute_hpac(instance);
    if (algorithm == "hpac_eager") return pcf::compute_hpac_eager(instance);
    if (algorithm == "hpac_bounded") return pcf::compute_hpac_bounded(instance);
    if (algorithm == "hipac") return pcf::compute_hipac(instance);
    if (algorithm == "dhpac") return pcf::compute_dhpac(instance);
    if (algorithm == "hopac") return pcf::compute_hopac(instance);
    if (algorithm == "rac") return pcf::compute_rac(instance, rac_stats);
    throw std::invalid_argument("unknown algorithm: " + algorithm);
}

std::vector<std::string> split(const std::string& text) {
    std::vector<std::string> result;
    std::size_t begin = 0;
    while (begin < text.size()) {
        const std::size_t end = text.find(',', begin);
        result.push_back(text.substr(begin, end == std::string::npos ? end : end - begin));
        if (end == std::string::npos) break;
        begin = end + 1;
    }
    return result;
}

// Non-cryptographic FNV-1a hash over a canonical serialization of the
// returned sequence. It is a determinism/agreement fingerprint used to pair
// algorithm outputs during aggregation, not a cryptographic checksum: exact
// correctness is established separately by the CTest oracle and differential
// suite (see docs/RAC_AUDIT.md and docs/EXPERIMENTAL_PROTOCOL.md).
std::uint64_t sequence_fingerprint(const pcf::ClosureLayerSequence& sequence) {
    std::uint64_t hash = 1469598103934665603ull;  // FNV offset basis
    auto mix = [&hash](std::int64_t value) {
        for (int byte = 0; byte < 8; ++byte) {
            hash ^= static_cast<std::uint8_t>(value >> (byte * 8));
            hash *= 1099511628211ull;  // FNV prime
        }
    };
    for (const auto& layer : sequence.layers) {
        mix(layer.profit);
        mix(layer.weight);
        mix(static_cast<std::int64_t>(layer.nodes.size()));
        std::vector<int> nodes = layer.nodes;
        std::sort(nodes.begin(), nodes.end());
        for (const int node : nodes) mix(node);
    }
    return hash;
}

long peak_rss_kib() {
    struct rusage usage {};
    getrusage(RUSAGE_SELF, &usage);
    return usage.ru_maxrss;  // kibibytes on Linux
}

std::string timestamp_utc() {
    const auto now = std::chrono::system_clock::now();
    const std::time_t now_c = std::chrono::system_clock::to_time_t(now);
    std::tm utc{};
    gmtime_r(&now_c, &utc);
    char buffer[32];
    std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &utc);
    return buffer;
}

int count_components(const pcf::Instance& instance) {
    std::vector<int> parent(instance.n);
    std::iota(parent.begin(), parent.end(), 0);
    auto find = [&](int v) {
        while (parent[v] != v) { parent[v] = parent[parent[v]]; v = parent[v]; }
        return v;
    };
    for (const auto& arc : instance.arcs) {
        const int a = find(arc.tail);
        const int b = find(arc.head);
        if (a != b) parent[a] = b;
    }
    std::vector<char> seen(instance.n, 0);
    int components = 0;
    for (int v = 0; v < instance.n; ++v) if (!seen[find(v)]) { seen[find(v)] = 1; ++components; }
    return components;
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        std::string path;
        std::string campaign_id = "unspecified";
        std::vector<std::string> algorithms;
        int repetitions = 1;
        unsigned shuffle_seed = 0;
        bool shuffle = false;
        for (int i = 1; i < argc; ++i) {
            const std::string flag = argv[i];
            if ((flag == "--instance" || flag == "--algorithms" || flag == "--repetitions" ||
                 flag == "--shuffle-seed" || flag == "--campaign-id") && i + 1 < argc) {
                const std::string value = argv[++i];
                if (flag == "--instance") path = value;
                else if (flag == "--algorithms") algorithms = split(value);
                else if (flag == "--repetitions") repetitions = std::stoi(value);
                else if (flag == "--campaign-id") campaign_id = value;
                else { shuffle_seed = static_cast<unsigned>(std::stoul(value)); shuffle = true; }
            } else {
                throw std::invalid_argument(
                    "usage: pcf_benchmark --instance FILE --algorithms hpac,rac --repetitions N "
                    "[--shuffle-seed S] [--campaign-id ID]");
            }
        }
        if (path.empty() || algorithms.empty() || repetitions <= 0) throw std::invalid_argument("missing benchmark option");
        const auto instance = pcf::read_instance(path);
        const int n_arcs = static_cast<int>(instance.arcs.size());
        const int n_components = count_components(instance);
        std::mt19937 generator(shuffle_seed);
        std::cout << "campaign_id,instance,algorithm,repetition,order,elapsed_ns,n_layers,n_breakpoints,"
                      "sequence_hash,peak_rss_kib,git_commit,timestamp_utc,n_nodes,n_arcs,n_components,"
                      "rac_clusters,rac_joins,rac_internalizations,rac_envelope_sum_calls,rac_envelope_max_calls,"
                      "rac_hull_calls,rac_lines_scanned,rac_line_comparisons,rac_rational_comparisons,"
                      "rac_pieces_stored,rac_topdown_events,rac_topdown_scans,rac_expanded_vertices,"
                      "rac_expanded_edges,rac_rounds,rac_max_cluster_depth,rac_estimated_bytes\n";
        for (int repetition = 0; repetition < repetitions; ++repetition) {
            std::vector<int> order(algorithms.size());
            std::iota(order.begin(), order.end(), 0);
            if (shuffle) std::shuffle(order.begin(), order.end(), generator);
            for (int position = 0; position < static_cast<int>(order.size()); ++position) {
                const auto& algorithm = algorithms[order[position]];
                RaCStats rac_stats;
                const auto started = std::chrono::steady_clock::now();
                const auto result = run(instance, algorithm, &rac_stats);
                const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(
                    std::chrono::steady_clock::now() - started).count();
                const auto fingerprint = sequence_fingerprint(result);
                const auto rss = peak_rss_kib();
                std::cout << campaign_id << ',' << path << ',' << algorithm << ',' << repetition << ','
                          << position << ',' << elapsed << ',' << result.layers.size() << ','
                          << (result.layers.empty() ? 0 : result.layers.size() - 1) << ','
                          << fingerprint << ',' << rss << ',' << PCF_GIT_COMMIT << ',' << timestamp_utc() << ','
                          << instance.n << ',' << n_arcs << ',' << n_components;
                if (algorithm == "rac") {
                    std::cout << ',' << rac_stats.clusters << ',' << rac_stats.joins << ','
                              << rac_stats.internalizations << ',' << rac_stats.envelope_sum_calls << ','
                              << rac_stats.envelope_max_calls << ',' << rac_stats.hull_calls << ','
                              << rac_stats.lines_scanned << ',' << rac_stats.line_comparisons << ','
                              << rac_stats.rational_comparisons << ',' << rac_stats.pieces_stored << ','
                              << rac_stats.topdown_events << ',' << rac_stats.topdown_scans << ','
                              << rac_stats.expanded_vertices << ',' << rac_stats.expanded_edges << ','
                              << rac_stats.rounds << ',' << rac_stats.max_cluster_depth << ','
                              << rac_stats.estimated_bytes;
                } else {
                    std::cout << ",,,,,,,,,,,,,,,";
                }
                std::cout << '\n';
            }
        }
    } catch (const std::exception& error) {
        std::cerr << "pcf_benchmark: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
