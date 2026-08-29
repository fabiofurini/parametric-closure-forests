#include "parametric_closure/algorithms.hpp"
#include "parametric_closure/instance.hpp"

#include "internal/work_graph.hpp"

#include <algorithm>
#include <optional>
#include <queue>
#include <stdexcept>
#include <vector>

namespace pcf {

ClosureLayerSequence compute_hipac(const Instance& instance) {
    validate_instance(instance);
    if (!is_in_forest(instance)) throw std::invalid_argument("HIPaC requires an in-forest");

    std::vector<WorkNode> graph(instance.n);
    std::vector<int> version(instance.n, 0);
    for (int v = 0; v < instance.n; ++v) {
        graph[v].profit = instance.profit[v];
        graph[v].weight = instance.weight[v];
        graph[v].original_nodes = {v};
    }
    for (const Arc& arc : instance.arcs) {
        graph[arc.tail].out.insert(arc.head);
        graph[arc.head].in.insert(arc.tail);
    }

    struct Entry { Ratio ratio; int node; int version; };
    const auto cmp = [](const Entry& lhs, const Entry& rhs) {
        const int result = compare(lhs.ratio, rhs.ratio);
        return result != 0 ? result < 0 : lhs.node > rhs.node;
    };
    std::priority_queue<Entry, std::vector<Entry>, decltype(cmp)> heap(cmp);
    const auto push = [&](int v) { if (graph[v].alive) heap.push({{graph[v].profit, graph[v].weight}, v, version[v]}); };
    for (int v = 0; v < instance.n; ++v) push(v);

    ClosureLayerSequence sequence;
    std::optional<Ratio> current;
    for (int alive = instance.n; alive > 0; --alive) {
        Entry entry{};
        do {
            if (heap.empty()) throw std::runtime_error("HIPaC heap became empty");
            entry = heap.top(); heap.pop();
        } while (!graph[entry.node].alive || entry.version != version[entry.node]);
        const int u = entry.node;
        if (graph[u].out.empty()) {
            ClosureLayer layer = make_closure_layer(instance, graph[u].original_nodes);
            if (!current || compare(layer.ratio(), *current) < 0) {
                current = layer.ratio();
                sequence.layers.push_back(std::move(layer));
            } else {
                auto& previous = sequence.layers.back();
                previous.nodes.insert(previous.nodes.end(), layer.nodes.begin(), layer.nodes.end());
                previous.profit += layer.profit;
                previous.weight += layer.weight;
            }
            for (int predecessor : std::vector<int>(graph[u].in.begin(), graph[u].in.end())) graph[predecessor].out.erase(u);
            graph[u].in.clear();
            graph[u].alive = false;
        } else {
            const int v = *graph[u].out.begin();
            for (int predecessor : std::vector<int>(graph[u].in.begin(), graph[u].in.end())) {
                graph[predecessor].out.erase(u);
                if (predecessor != v) { graph[predecessor].out.insert(v); graph[v].in.insert(predecessor); }
            }
            graph[v].in.erase(u);
            graph[v].profit += graph[u].profit;
            graph[v].weight += graph[u].weight;
            graph[v].original_nodes.insert(graph[v].original_nodes.end(), graph[u].original_nodes.begin(), graph[u].original_nodes.end());
            graph[u].in.clear(); graph[u].out.clear(); graph[u].alive = false;
            ++version[v]; push(v);
        }
    }
    canonicalize(sequence);
    return sequence;
}

}  // namespace pcf
