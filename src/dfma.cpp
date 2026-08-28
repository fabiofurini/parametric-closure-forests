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
    for (const int u : topological) {
        for (const int v : graph[u].out) {
            sums.profit[v] += sums.profit[u];
            sums.weight[v] += sums.weight[u];
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

void contract_arc_dual(std::vector<WorkNode>& graph, int u, int v) {
    // For arc u->v, the dual contraction preserves u and merges v into it.
    for (int predecessor : std::vector<int>(graph[v].in.begin(), graph[v].in.end())) {
        graph[predecessor].out.erase(v);
        if (predecessor != u) {
            graph[predecessor].out.insert(u);
            graph[u].in.insert(predecessor);
        }
    }
    for (int successor : std::vector<int>(graph[v].out.begin(), graph[v].out.end())) {
        graph[successor].in.erase(v);
        if (successor != u) {
            graph[u].out.insert(successor);
            graph[successor].in.insert(u);
        }
    }
    graph[u].in.erase(v);
    graph[u].out.erase(v);
    graph[u].profit += graph[v].profit;
    graph[u].weight += graph[v].weight;
    graph[u].original_nodes.insert(graph[u].original_nodes.end(),
                                   graph[v].original_nodes.begin(), graph[v].original_nodes.end());
    graph[v].in.clear();
    graph[v].out.clear();
    graph[v].alive = false;
}

}  // namespace

MacroitemSequence compute_dfma(const Instance& instance) {
    validate_instance(instance);
    auto graph = make_work_graph(instance);
    int alive = instance.n;
    std::vector<Macroitem> increasing;

    while (alive > 0) {
        const ClosureSums sums = closure_sums(graph);
        std::optional<std::pair<std::pair<int, int>, Ratio>> best_fin;
        std::optional<Ratio> best_initial;
        for (int u = 0; u < instance.n; ++u) {
            if (!graph[u].alive) continue;
            if (graph[u].in.empty()) {
                const Ratio candidate{graph[u].profit, graph[u].weight};
                if (!best_initial || compare(candidate, *best_initial) < 0) best_initial = candidate;
            }
            for (int v : graph[u].out) {
                const Ratio candidate{sums.profit[v] - sums.profit[u], sums.weight[v] - sums.weight[u]};
                if (!best_fin || compare(candidate, best_fin->second) < 0 ||
                    (compare(candidate, best_fin->second) == 0 && std::pair{u, v} < best_fin->first)) {
                    best_fin = {{{u, v}, candidate}};
                }
            }
        }
        if (!best_initial) throw std::runtime_error("working graph has no initial node");
        if (!best_fin || compare(*best_initial, best_fin->second) < 0) {
            std::vector<int> emitted;
            for (int u = 0; u < instance.n; ++u) {
                if (!graph[u].alive || !graph[u].in.empty()) continue;
                if (compare(Ratio{graph[u].profit, graph[u].weight}, *best_initial) == 0)
                    emitted.insert(emitted.end(), graph[u].original_nodes.begin(), graph[u].original_nodes.end());
            }
            increasing.push_back(make_macroitem(instance, std::move(emitted)));
            for (int u = 0; u < instance.n; ++u) {
                if (graph[u].alive && graph[u].in.empty() &&
                    compare(Ratio{graph[u].profit, graph[u].weight}, *best_initial) == 0) {
                    erase_node(graph, u);
                    --alive;
                }
            }
        } else {
            contract_arc_dual(graph, best_fin->first.first, best_fin->first.second);
            --alive;
        }
    }
    MacroitemSequence sequence;
    sequence.macroitems.assign(increasing.rbegin(), increasing.rend());
    canonicalize(sequence);
    return sequence;
}

}  // namespace pcf

