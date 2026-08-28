#include "parametric_closure/algorithms.hpp"
#include "parametric_closure/instance.hpp"

#include <queue>
#include <stdexcept>
#include <utility>
#include <vector>

namespace pcf {
namespace {

struct ClosureSum {
    std::int64_t p = 0;
    std::int64_t w = 0;
};

struct Node {
    bool alive = true;
    std::int64_t p = 0;
    std::int64_t w = 0;
    int first_out = -1;
    int first_in = -1;
    int first_original = -1;
    int last_original = -1;
    int original_count = 0;
};

struct Edge {
    int from = -1;
    int to = -1;
    int next_out = -1;
    int prev_out = -1;
    int next_in = -1;
    int prev_in = -1;
    bool alive = true;
};

struct Workspace {
    std::vector<int> indegree;
    std::vector<int> queue;
    std::vector<int> topo;
    std::vector<ClosureSum> sums;
};

struct FinEntry {
    Ratio ratio;
    int edge = -1;
    int version = 0;
};

void attach_out(std::vector<Node>& graph, std::vector<Edge>& edges, int node, int edge) {
    edges[edge].from = node;
    edges[edge].prev_out = -1;
    edges[edge].next_out = graph[node].first_out;
    if (graph[node].first_out != -1) edges[graph[node].first_out].prev_out = edge;
    graph[node].first_out = edge;
}

void attach_in(std::vector<Node>& graph, std::vector<Edge>& edges, int node, int edge) {
    edges[edge].to = node;
    edges[edge].prev_in = -1;
    edges[edge].next_in = graph[node].first_in;
    if (graph[node].first_in != -1) edges[graph[node].first_in].prev_in = edge;
    graph[node].first_in = edge;
}

void detach_out(std::vector<Node>& graph, std::vector<Edge>& edges, int edge) {
    const int node = edges[edge].from;
    const int previous = edges[edge].prev_out;
    const int next = edges[edge].next_out;
    if (previous != -1) edges[previous].next_out = next;
    else graph[node].first_out = next;
    if (next != -1) edges[next].prev_out = previous;
    edges[edge].prev_out = -1;
    edges[edge].next_out = -1;
}

void detach_in(std::vector<Node>& graph, std::vector<Edge>& edges, int edge) {
    const int node = edges[edge].to;
    const int previous = edges[edge].prev_in;
    const int next = edges[edge].next_in;
    if (previous != -1) edges[previous].next_in = next;
    else graph[node].first_in = next;
    if (next != -1) edges[next].prev_in = previous;
    edges[edge].prev_in = -1;
    edges[edge].next_in = -1;
}

void compute_succeeding_sums(
    const std::vector<Node>& graph,
    const std::vector<Edge>& edges,
    const std::vector<int>& active,
    Workspace& workspace) {
    for (const int u : active) {
        workspace.indegree[u] = 0;
        workspace.sums[u] = {graph[u].p, graph[u].w};
    }
    for (const int u : active)
        for (int edge = graph[u].first_out; edge != -1; edge = edges[edge].next_out)
            ++workspace.indegree[edges[edge].to];
    workspace.queue.clear();
    for (const int u : active) if (workspace.indegree[u] == 0) workspace.queue.push_back(u);
    workspace.topo.clear();
    for (std::size_t position = 0; position < workspace.queue.size(); ++position) {
        const int u = workspace.queue[position];
        workspace.topo.push_back(u);
        for (int edge = graph[u].first_out; edge != -1; edge = edges[edge].next_out) {
            const int v = edges[edge].to;
            if (--workspace.indegree[v] == 0) workspace.queue.push_back(v);
        }
    }
    if (workspace.topo.size() != active.size()) throw std::runtime_error("working graph is not acyclic");
    for (const int u : workspace.topo)
        for (int edge = graph[u].first_out; edge != -1; edge = edges[edge].next_out) {
            const int v = edges[edge].to;
            workspace.sums[v].p += workspace.sums[u].p;
            workspace.sums[v].w += workspace.sums[u].w;
        }
}

void collect_forward_reachable(
    int start,
    const std::vector<Node>& graph,
    const std::vector<Edge>& edges,
    int stamp,
    std::vector<int>& seen,
    std::vector<int>& nodes,
    std::vector<int>& stack) {
    stack.clear();
    stack.push_back(start);
    seen[start] = stamp;
    while (!stack.empty()) {
        const int u = stack.back();
        stack.pop_back();
        nodes.push_back(u);
        for (int edge = graph[u].first_out; edge != -1; edge = edges[edge].next_out) {
            const int successor = edges[edge].to;
            if (seen[successor] == stamp) continue;
            seen[successor] = stamp;
            stack.push_back(successor);
        }
    }
}

}  // namespace

MacroitemSequence compute_dhfma(const Instance& instance) {
    validate_instance(instance);
    std::vector<Node> graph(instance.n);
    std::vector<int> next_original(instance.n, -1);
    for (int v = 0; v < instance.n; ++v) {
        graph[v].p = instance.profit[v];
        graph[v].w = instance.weight[v];
        graph[v].first_original = v;
        graph[v].last_original = v;
        graph[v].original_count = 1;
    }
    std::vector<Edge> edges(instance.arcs.size());
    for (int edge = 0; edge < static_cast<int>(instance.arcs.size()); ++edge) {
        attach_out(graph, edges, instance.arcs[edge].tail, edge);
        attach_in(graph, edges, instance.arcs[edge].head, edge);
    }

    std::vector<int> active(instance.n), active_position(instance.n);
    for (int v = 0; v < instance.n; ++v) active[v] = active_position[v] = v;
    const auto remove_active = [&](int v) {
        const int position = active_position[v];
        const int last = active.back();
        active[position] = last;
        active_position[last] = position;
        active.pop_back();
        graph[v].alive = false;
    };

    Workspace closure;
    closure.indegree.resize(instance.n);
    closure.sums.resize(instance.n);
    compute_succeeding_sums(graph, edges, active, closure);

    std::vector<int> node_version(instance.n, 0);
    struct InitialEntry { Ratio ratio; int node = -1; int version = 0; };
    const auto initial_compare = [](const InitialEntry& lhs, const InitialEntry& rhs) {
        const int result = compare(lhs.ratio, rhs.ratio);
        return result != 0 ? result > 0 : lhs.node > rhs.node;
    };
    std::priority_queue<InitialEntry, std::vector<InitialEntry>, decltype(initial_compare)> initial_heap(initial_compare);
    const auto push_initial = [&](int u) {
        if (graph[u].alive && graph[u].first_in == -1)
            initial_heap.push({{graph[u].p, graph[u].w}, u, node_version[u]});
    };
    const auto discard_stale_initials = [&]() {
        while (!initial_heap.empty()) {
            const auto top = initial_heap.top();
            if (graph[top.node].alive && graph[top.node].first_in == -1 && top.version == node_version[top.node]) return;
            initial_heap.pop();
        }
    };
    for (int v = 0; v < instance.n; ++v) push_initial(v);

    std::vector<int> edge_version(edges.size(), 0);
    const auto fin_compare = [](const FinEntry& lhs, const FinEntry& rhs) {
        const int result = compare(lhs.ratio, rhs.ratio);
        return result != 0 ? result > 0 : lhs.edge > rhs.edge;
    };
    std::priority_queue<FinEntry, std::vector<FinEntry>, decltype(fin_compare)> fin_heap(fin_compare);
    const auto current_fin_ratio = [&](int edge) {
        const int u = edges[edge].from;
        const int v = edges[edge].to;
        return Ratio{closure.sums[v].p - closure.sums[u].p, closure.sums[v].w - closure.sums[u].w};
    };
    const auto push_fin = [&](int edge) {
        if (edge != -1 && edges[edge].alive && graph[edges[edge].from].alive && graph[edges[edge].to].alive)
            fin_heap.push({current_fin_ratio(edge), edge, edge_version[edge]});
    };
    const auto touch_edge = [&](int edge) {
        if (edge == -1 || !edges[edge].alive) return;
        ++edge_version[edge];
        push_fin(edge);
    };
    const auto touch_node_edges = [&](int u) {
        for (int edge = graph[u].first_out; edge != -1; edge = edges[edge].next_out) touch_edge(edge);
        for (int edge = graph[u].first_in; edge != -1; edge = edges[edge].next_in) touch_edge(edge);
    };
    const auto discard_stale_fins = [&]() {
        while (!fin_heap.empty()) {
            const auto top = fin_heap.top();
            if (edges[top.edge].alive && graph[edges[top.edge].from].alive &&
                graph[edges[top.edge].to].alive && top.version == edge_version[top.edge]) return;
            fin_heap.pop();
        }
    };
    for (int edge = 0; edge < static_cast<int>(edges.size()); ++edge) push_fin(edge);

    std::vector<int> mark(instance.n, 0), selected_initial(instance.n, 0), stack, reached_u, reached_v, affected;
    int stamp = 1;
    int selected_stamp = 1;
    std::vector<Macroitem> increasing;

    while (!active.empty()) {
        discard_stale_fins();
        const bool has_fin = !fin_heap.empty();
        const int best_edge = has_fin ? fin_heap.top().edge : -1;
        const Ratio best_fin = has_fin ? fin_heap.top().ratio : Ratio{0, 1};
        discard_stale_initials();
        if (initial_heap.empty()) throw std::runtime_error("working graph has no initial node");
        const Ratio best_initial = initial_heap.top().ratio;

        if (!has_fin || compare(best_initial, best_fin) < 0) {
            std::vector<int> best_initials;
            while (true) {
                discard_stale_initials();
                if (initial_heap.empty() || compare(initial_heap.top().ratio, best_initial) != 0) break;
                const int node = initial_heap.top().node;
                initial_heap.pop();
                if (selected_initial[node] == selected_stamp) continue;
                selected_initial[node] = selected_stamp;
                best_initials.push_back(node);
            }
            ++selected_stamp;
            std::vector<int> macro_nodes;
            int macro_size = 0;
            for (const int u : best_initials) macro_size += graph[u].original_count;
            macro_nodes.reserve(macro_size);
            for (const int u : best_initials)
                for (int v = graph[u].first_original; v != -1; v = next_original[v]) macro_nodes.push_back(v);
            increasing.push_back(make_macroitem(instance, std::move(macro_nodes)));

            std::vector<int> new_initials;
            affected.clear();
            for (const int u : best_initials) {
                reached_u.clear();
                collect_forward_reachable(u, graph, edges, stamp++, mark, reached_u, stack);
                const ClosureSum delta = closure.sums[u];
                for (const int x : reached_u) {
                    if (x == u) continue;
                    closure.sums[x].p -= delta.p;
                    closure.sums[x].w -= delta.w;
                    affected.push_back(x);
                }
                while (graph[u].first_out != -1) {
                    const int edge = graph[u].first_out;
                    const int successor = edges[edge].to;
                    detach_out(graph, edges, edge);
                    detach_in(graph, edges, edge);
                    edges[edge].alive = false;
                    ++edge_version[edge];
                    new_initials.push_back(successor);
                }
                remove_active(u);
            }
            for (const int x : affected) touch_node_edges(x);
            for (const int u : new_initials) push_initial(u);
        } else {
            const int u = edges[best_edge].from;
            const int v = edges[best_edge].to;
            reached_u.clear();
            reached_v.clear();
            affected.clear();
            const int stamp_u = stamp++;
            collect_forward_reachable(u, graph, edges, stamp_u, mark, reached_u, stack);
            const int stamp_v = stamp++;
            collect_forward_reachable(v, graph, edges, stamp_v, mark, reached_v, stack);
            const ClosureSum delta{closure.sums[v].p - closure.sums[u].p,
                                   closure.sums[v].w - closure.sums[u].w};
            for (const int x : reached_u) {
                if (mark[x] == stamp_v) continue;
                closure.sums[x].p += delta.p;
                closure.sums[x].w += delta.w;
                affected.push_back(x);
            }
            while (graph[v].first_in != -1) {
                const int edge = graph[v].first_in;
                const int predecessor = edges[edge].from;
                detach_in(graph, edges, edge);
                detach_out(graph, edges, edge);
                if (predecessor != u) {
                    attach_out(graph, edges, predecessor, edge);
                    attach_in(graph, edges, u, edge);
                    touch_edge(edge);
                } else {
                    edges[edge].alive = false;
                    ++edge_version[edge];
                }
            }
            while (graph[v].first_out != -1) {
                const int edge = graph[v].first_out;
                const int successor = edges[edge].to;
                detach_out(graph, edges, edge);
                detach_in(graph, edges, edge);
                attach_out(graph, edges, u, edge);
                attach_in(graph, edges, successor, edge);
                touch_edge(edge);
            }
            graph[u].p += graph[v].p;
            graph[u].w += graph[v].w;
            if (graph[v].first_original != -1) {
                next_original[graph[v].last_original] = graph[u].first_original;
                graph[u].first_original = graph[v].first_original;
                graph[u].original_count += graph[v].original_count;
            }
            ++node_version[u];
            push_initial(u);
            for (const int x : affected) touch_node_edges(x);
            remove_active(v);
        }
    }

    MacroitemSequence sequence;
    sequence.macroitems.assign(increasing.rbegin(), increasing.rend());
    canonicalize(sequence);
    return sequence;
}

}  // namespace pcf
