#include "parametric_closure/instance.hpp"

#include "internal/work_graph.hpp"

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <limits>
#include <numeric>
#include <queue>
#include <set>
#include <sstream>
#include <stdexcept>

namespace pcf {

bool is_dag(const Instance& instance) {
    std::vector<int> degree(instance.n, 0);
    const auto out = outgoing(instance);
    for (const auto& arc : instance.arcs) ++degree[arc.head];
    std::queue<int> queue;
    for (int v = 0; v < instance.n; ++v) if (degree[v] == 0) queue.push(v);
    int visited = 0;
    while (!queue.empty()) {
        const int u = queue.front();
        queue.pop();
        ++visited;
        for (const int v : out[u]) if (--degree[v] == 0) queue.push(v);
    }
    return visited == instance.n;
}

bool is_forest(const Instance& instance) {
    std::vector<int> parent(instance.n);
    std::iota(parent.begin(), parent.end(), 0);
    auto find = [&](int v) {
        int root = v;
        while (parent[root] != root) root = parent[root];
        while (parent[v] != v) {
            const int next = parent[v];
            parent[v] = root;
            v = next;
        }
        return root;
    };
    for (const auto& arc : instance.arcs) {
        const int a = find(arc.tail);
        const int b = find(arc.head);
        if (a == b) return false;
        parent[a] = b;
    }
    return true;
}

bool is_in_forest(const Instance& instance) {
    if (!is_forest(instance) || !is_dag(instance)) return false;
    std::vector<int> degree(instance.n, 0);
    for (const auto& arc : instance.arcs) if (++degree[arc.tail] > 1) return false;
    return true;
}

bool is_out_forest(const Instance& instance) {
    if (!is_forest(instance) || !is_dag(instance)) return false;
    std::vector<int> degree(instance.n, 0);
    for (const auto& arc : instance.arcs) if (++degree[arc.head] > 1) return false;
    return true;
}

void validate_instance(const Instance& instance, bool require_forest) {
    if (instance.n <= 0 || static_cast<int>(instance.profit.size()) != instance.n ||
        static_cast<int>(instance.weight.size()) != instance.n) {
        throw std::invalid_argument("invalid parametric maximum-closure instance dimensions");
    }
    for (const auto weight : instance.weight) {
        if (weight <= 0) throw std::invalid_argument("all weights must be positive");
    }
    __int128 total_absolute_profit = 0;
    __int128 total_weight = 0;
    for (int v = 0; v < instance.n; ++v) {
        const auto profit = instance.profit[v];
        total_absolute_profit += profit < 0 ? -static_cast<__int128>(profit) : profit;
        total_weight += instance.weight[v];
    }
    const __int128 limit = static_cast<__int128>(std::numeric_limits<std::int64_t>::max()) / 4;
    if (total_absolute_profit > limit || total_weight > limit) {
        throw std::invalid_argument("instance coefficient totals exceed the exact arithmetic safety bound");
    }
    std::set<std::pair<int, int>> seen;
    for (const auto& arc : instance.arcs) {
        if (arc.tail < 0 || arc.tail >= instance.n || arc.head < 0 || arc.head >= instance.n || arc.tail == arc.head) {
            throw std::invalid_argument("invalid closure arc endpoint");
        }
        if (!seen.insert({arc.tail, arc.head}).second) throw std::invalid_argument("duplicate closure arc");
    }
    if (!is_dag(instance)) throw std::invalid_argument("closure graph must be acyclic");
    if (require_forest && !is_forest(instance)) throw std::invalid_argument("algorithm requires an underlying forest");
}

Macroitem make_macroitem(const Instance& instance, std::vector<int> nodes) {
    return build_macroitem(instance, std::move(nodes));
}

void canonicalize(MacroitemSequence& sequence) {
    std::vector<Macroitem> merged;
    for (auto& macroitem : sequence.macroitems) {
        std::sort(macroitem.nodes.begin(), macroitem.nodes.end());
        if (!merged.empty() && compare(merged.back().ratio(), macroitem.ratio()) == 0) {
            auto& previous = merged.back();
            previous.nodes.insert(previous.nodes.end(), macroitem.nodes.begin(), macroitem.nodes.end());
            std::sort(previous.nodes.begin(), previous.nodes.end());
            previous.profit += macroitem.profit;
            previous.weight += macroitem.weight;
        } else {
            merged.push_back(std::move(macroitem));
        }
    }
    sequence.macroitems = std::move(merged);
}

Instance read_instance(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open instance: " + path);
    std::string magic;
    int version = 0;
    if (!(input >> magic >> version) || magic != "pcf" || version != 1) {
        throw std::invalid_argument("expected 'pcf 1' header");
    }
    Instance instance;
    std::string field;
    if (!(input >> field >> instance.n) || field != "n") throw std::invalid_argument("expected n field");
    if (!(input >> field) || field != "profits") throw std::invalid_argument("expected profits field");
    instance.profit.resize(instance.n);
    for (auto& value : instance.profit) if (!(input >> value)) throw std::invalid_argument("invalid profit list");
    if (!(input >> field) || field != "weights") throw std::invalid_argument("expected weights field");
    instance.weight.resize(instance.n);
    for (auto& value : instance.weight) if (!(input >> value)) throw std::invalid_argument("invalid weight list");
    int m = 0;
    if (!(input >> field >> m) || field != "arcs" || m < 0) throw std::invalid_argument("expected arc count");
    instance.arcs.reserve(m);
    for (int e = 0; e < m; ++e) {
        int tail = 0;
        int head = 0;
        if (!(input >> tail >> head)) throw std::invalid_argument("invalid closure arc");
        instance.arcs.push_back({tail - 1, head - 1});
    }
    validate_instance(instance);
    return instance;
}

void write_sequence(std::ostream& out, const MacroitemSequence& sequence) {
    out << "macroitems " << sequence.macroitems.size() << '\n';
    for (std::size_t i = 0; i < sequence.macroitems.size(); ++i) {
        const auto& macroitem = sequence.macroitems[i];
        out << "macroitem " << (i + 1) << " ratio " << macroitem.profit << '/' << macroitem.weight << " nodes";
        for (const int v : macroitem.nodes) out << ' ' << (v + 1);
        out << '\n';
    }
}

}  // namespace pcf
