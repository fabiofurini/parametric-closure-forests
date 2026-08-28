#include "parametric_closure/algorithms.hpp"
#include "parametric_closure/instance.hpp"

#include "internal/work_graph.hpp"

#include <optional>
#include <stdexcept>
#include <utility>
#include <vector>

namespace pcf {
namespace {

std::vector<WorkNode> make_work_graph(const Instance& instance) {
    std::vector<WorkNode> graph(instance.n);
    for (int v = 0; v < instance.n; ++v) {
        graph[v].profit = instance.profit[v];
        graph[v].weight = instance.weight[v];
        graph[v].original_nodes = {v};
    }
    for (const Arc& arc : instance.arcs) {
        graph[arc.tail].out.insert(arc.head);
        graph[arc.head].in.insert(arc.tail);
    }
    return graph;
}

struct ClosureSums {
    std::vector<std::int64_t> profit;
    std::vector<std::int64_t> weight;
};

ClosureSums closure_sums(const std::vector<WorkNode>& graph) {
    const int n = static_cast<int>(graph.size());
    ClosureSums sums;
    sums.profit.resize(n);
    sums.weight.resize(n);
    std::vector<int> indegree(n, 0);
    std::vector<int> queue;
    queue.reserve(n);
    for (int u = 0; u < n; ++u) {
        if (!graph[u].alive) continue;
        sums.profit[u] = graph[u].profit;
        sums.weight[u] = graph[u].weight;
        for (int v : graph[u].out) ++indegree[v];
    }
    for (int u = 0; u < n; ++u) if (graph[u].alive && indegree[u] == 0) queue.push_back(u);
    std::vector<int> topological;
    topological.reserve(queue.size());
    for (std::size_t pos = 0; pos < queue.size(); ++pos) {
        const int u = queue[pos];
        topological.push_back(u);
        for (int v : graph[u].out) if (--indegree[v] == 0) queue.push_back(v);
    }
    std::size_t alive = 0;
    for (const WorkNode& node : graph) alive += node.alive;
    if (topological.size() != alive) throw std::runtime_error("contracted graph is not acyclic");
    for (auto it = topological.rbegin(); it != topological.rend(); ++it) {
        const int u = *it;
        for (int v : graph[u].out) {
            sums.profit[u] += sums.profit[v];
            sums.weight[u] += sums.weight[v];
        }
    }
    return sums;
}

void erase_node(std::vector<WorkNode>& graph, int v) {
    for (int predecessor : std::vector<int>(graph[v].in.begin(), graph[v].in.end()))
        graph[predecessor].out.erase(v);
    for (int successor : std::vector<int>(graph[v].out.begin(), graph[v].out.end()))
        graph[successor].in.erase(v);
    graph[v].in.clear();
    graph[v].out.clear();
    graph[v].alive = false;
}

void contract_arc(std::vector<WorkNode>& graph, int u, int v) {
    for (int predecessor : std::vector<int>(graph[u].in.begin(), graph[u].in.end())) {
        graph[predecessor].out.erase(u);
        if (predecessor != v) {
            graph[predecessor].out.insert(v);
            graph[v].in.insert(predecessor);
        }
    }
    for (int successor : std::vector<int>(graph[u].out.begin(), graph[u].out.end())) {
        graph[successor].in.erase(u);
        if (successor != v) {
            graph[v].out.insert(successor);
            graph[successor].in.insert(v);
        }
    }
    graph[v].in.erase(u);
    graph[v].out.erase(u);
    graph[v].profit += graph[u].profit;
    graph[v].weight += graph[u].weight;
    graph[v].original_nodes.insert(graph[v].original_nodes.end(),
                                   graph[u].original_nodes.begin(), graph[u].original_nodes.end());
    graph[u].in.clear();
    graph[u].out.clear();
    graph[u].alive = false;
}

}  // namespace

MacroitemSequence compute_fma(const Instance& instance) {
    validate_instance(instance);
    auto graph = make_work_graph(instance);
    int alive = instance.n;
    MacroitemSequence sequence;

    while (alive > 0) {
        const ClosureSums sums = closure_sums(graph);
        std::optional<std::pair<std::pair<int, int>, Ratio>> best_wing;
        std::optional<Ratio> best_final;

        for (int u = 0; u < instance.n; ++u) {
            if (!graph[u].alive) continue;
            if (graph[u].out.empty()) {
                const Ratio candidate{graph[u].profit, graph[u].weight};
                if (!best_final || compare(candidate, *best_final) > 0) best_final = candidate;
            }
            for (int v : graph[u].out) {
                const Ratio candidate{sums.profit[u] - sums.profit[v], sums.weight[u] - sums.weight[v]};
                if (!best_wing || compare(candidate, best_wing->second) > 0 ||
                    (compare(candidate, best_wing->second) == 0 && std::pair{u, v} < best_wing->first)) {
                    best_wing = {{{u, v}, candidate}};
                }
            }
        }
        if (!best_final) throw std::runtime_error("working graph has no final node");

        if (!best_wing || compare(*best_final, best_wing->second) > 0) {
            std::vector<int> emitted;
            for (int u = 0; u < instance.n; ++u) {
                if (!graph[u].alive || !graph[u].out.empty()) continue;
                if (compare(Ratio{graph[u].profit, graph[u].weight}, *best_final) == 0) {
                    emitted.insert(emitted.end(), graph[u].original_nodes.begin(), graph[u].original_nodes.end());
                }
            }
            sequence.macroitems.push_back(make_macroitem(instance, std::move(emitted)));
            for (int u = 0; u < instance.n; ++u) {
                if (graph[u].alive && graph[u].out.empty() &&
                    compare(Ratio{graph[u].profit, graph[u].weight}, *best_final) == 0) {
                    erase_node(graph, u);
                    --alive;
                }
            }
        } else {
            contract_arc(graph, best_wing->first.first, best_wing->first.second);
            --alive;
        }
    }
    canonicalize(sequence);
    return sequence;
}

}  // namespace pcf
