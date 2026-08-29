#include "parametric_closure/algorithms.hpp"
#include "parametric_closure/instance.hpp"

#include "internal/work_graph.hpp"

#include <algorithm>
#include <optional>
#include <queue>
#include <stdexcept>
#include <vector>

namespace pcf {

ClosureLayerSequence compute_hopac(const Instance& instance) {
    validate_instance(instance);
    if (!is_out_forest(instance)) throw std::invalid_argument("HOPaC requires an out-forest");

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
        return result != 0 ? result > 0 : lhs.node > rhs.node;
    };
    std::priority_queue<Entry, std::vector<Entry>, decltype(cmp)> heap(cmp);
    const auto push = [&](int v) { if (graph[v].alive) heap.push({{graph[v].profit, graph[v].weight}, v, version[v]}); };
    for (int v = 0; v < instance.n; ++v) push(v);

    std::vector<ClosureLayer> increasing;
    std::optional<Ratio> current;
    for (int alive = instance.n; alive > 0; --alive) {
        Entry entry{};
        do {
            if (heap.empty()) throw std::runtime_error("HOPaC heap became empty");
            entry = heap.top(); heap.pop();
        } while (!graph[entry.node].alive || entry.version != version[entry.node]);
        const int v = entry.node;
        if (graph[v].in.empty()) {
            ClosureLayer layer = make_closure_layer(instance, graph[v].original_nodes);
            if (!current || compare(layer.ratio(), *current) > 0) {
                current = layer.ratio();
                increasing.push_back(std::move(layer));
            } else {
                auto& previous = increasing.back();
                previous.nodes.insert(previous.nodes.end(), layer.nodes.begin(), layer.nodes.end());
                previous.profit += layer.profit;
                previous.weight += layer.weight;
            }
            for (int successor : std::vector<int>(graph[v].out.begin(), graph[v].out.end())) graph[successor].in.erase(v);
            graph[v].out.clear();
            graph[v].alive = false;
        } else {
            const int u = *graph[v].in.begin();
            for (int successor : std::vector<int>(graph[v].out.begin(), graph[v].out.end())) {
                graph[successor].in.erase(v);
                if (successor != u) { graph[u].out.insert(successor); graph[successor].in.insert(u); }
            }
            graph[u].out.erase(v);
            graph[u].profit += graph[v].profit;
            graph[u].weight += graph[v].weight;
            graph[u].original_nodes.insert(graph[u].original_nodes.end(), graph[v].original_nodes.begin(), graph[v].original_nodes.end());
            graph[v].in.clear(); graph[v].out.clear(); graph[v].alive = false;
            ++version[u]; push(u);
        }
    }
    ClosureLayerSequence sequence;
    sequence.layers.assign(increasing.rbegin(), increasing.rend());
    canonicalize(sequence);
    return sequence;
}

}  // namespace pcf
