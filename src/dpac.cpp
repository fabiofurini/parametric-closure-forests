#include "parametric_closure/algorithms.hpp"
#include "parametric_closure/instance.hpp"

#include <stdexcept>
#include <utility>
#include <vector>

namespace pcf {

namespace {

struct ClosureSum {
    std::int64_t p = 0;
    std::int64_t w = 0;
};

struct FastNode {
    bool alive = true;
    std::int64_t p = 0;
    std::int64_t w = 0;
    int first_out = -1;
    int first_in = -1;
    int first_original = -1;
    int last_original = -1;
    int original_count = 0;
};

struct FastEdge {
    int from = -1;
    int to = -1;
    int next_out = -1;
    int prev_out = -1;
    int next_in = -1;
    int prev_in = -1;
    bool alive = true;
};

struct ClosureWorkspace {
    std::vector<int> indegree;
    std::vector<int> queue;
    std::vector<int> topo;
    std::vector<ClosureSum> sums;
};

void attach_out(std::vector<FastNode>& g, std::vector<FastEdge>& edges, int node, int edge) {
    edges[edge].from = node;
    edges[edge].prev_out = -1;
    edges[edge].next_out = g[node].first_out;
    if (g[node].first_out != -1) edges[g[node].first_out].prev_out = edge;
    g[node].first_out = edge;
}

void attach_in(std::vector<FastNode>& g, std::vector<FastEdge>& edges, int node, int edge) {
    edges[edge].to = node;
    edges[edge].prev_in = -1;
    edges[edge].next_in = g[node].first_in;
    if (g[node].first_in != -1) edges[g[node].first_in].prev_in = edge;
    g[node].first_in = edge;
}

void detach_out(std::vector<FastNode>& g, std::vector<FastEdge>& edges, int edge) {
    const int node = edges[edge].from;
    const int prev = edges[edge].prev_out;
    const int next = edges[edge].next_out;
    if (prev != -1) edges[prev].next_out = next;
    else g[node].first_out = next;
    if (next != -1) edges[next].prev_out = prev;
    edges[edge].prev_out = -1;
    edges[edge].next_out = -1;
}

void detach_in(std::vector<FastNode>& g, std::vector<FastEdge>& edges, int edge) {
    const int node = edges[edge].to;
    const int prev = edges[edge].prev_in;
    const int next = edges[edge].next_in;
    if (prev != -1) edges[prev].next_in = next;
    else g[node].first_in = next;
    if (next != -1) edges[next].prev_in = prev;
    edges[edge].prev_in = -1;
    edges[edge].next_in = -1;
}

// Forward propagation: sums[v] accumulates (p, w) of v plus every ancestor of
// v still alive in the working graph (opposite direction of pac.cpp's
// backward/descendant sums, matching DPaC's dual selection rule).
void compute_succeeding_sums(
    const std::vector<FastNode>& g,
    const std::vector<FastEdge>& edges,
    const std::vector<int>& active_nodes,
    ClosureWorkspace& workspace) {
    for (int u : active_nodes) {
        workspace.indegree[u] = 0;
        workspace.sums[u].p = g[u].p;
        workspace.sums[u].w = g[u].w;
    }
    for (int u : active_nodes) {
        for (int e = g[u].first_out; e != -1; e = edges[e].next_out) {
            const int v = edges[e].to;
            ++workspace.indegree[v];
        }
    }

    workspace.queue.clear();
    workspace.queue.reserve(active_nodes.size());
    for (int u : active_nodes) {
        if (workspace.indegree[u] == 0) workspace.queue.push_back(u);
    }

    workspace.topo.clear();
    workspace.topo.reserve(active_nodes.size());
    int head = 0;
    while (head < static_cast<int>(workspace.queue.size())) {
        const int u = workspace.queue[head++];
        workspace.topo.push_back(u);
        for (int e = g[u].first_out; e != -1; e = edges[e].next_out) {
            const int v = edges[e].to;
            if (--workspace.indegree[v] == 0) workspace.queue.push_back(v);
        }
    }
    if (workspace.topo.size() != active_nodes.size())
        throw std::runtime_error("working graph is not acyclic");

    for (int u : workspace.topo) {
        for (int e = g[u].first_out; e != -1; e = edges[e].next_out) {
            const int v = edges[e].to;
            workspace.sums[v].p += workspace.sums[u].p;
            workspace.sums[v].w += workspace.sums[u].w;
        }
    }
}

void collect_forward_reachable(
    int start,
    const std::vector<FastNode>& g,
    const std::vector<FastEdge>& edges,
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
        for (int e = g[u].first_out; e != -1; e = edges[e].next_out) {
            const int succ = edges[e].to;
            if (seen[succ] == stamp) continue;
            seen[succ] = stamp;
            stack.push_back(succ);
        }
    }
}

}  // namespace

// DPaC (dual Peel-and-Contract): the no-heap baseline for the dual selection
// rule on a general directed forest. Mirrors compute_pac's incremental
// closure-sum maintenance (one-time init + bounded delta patch per step)
// rather than recomputing the sums from scratch every iteration.
ClosureLayerSequence compute_dpac(const Instance& instance) {
    validate_instance(instance);

    std::vector<FastNode> g(instance.n);
    std::vector<int> next_original(instance.n, -1);
    for (int i = 0; i < instance.n; ++i) {
        g[i].p = instance.profit[i];
        g[i].w = instance.weight[i];
        g[i].first_original = i;
        g[i].last_original = i;
        g[i].original_count = 1;
    }
    std::vector<FastEdge> edges(instance.arcs.size());
    for (int e = 0; e < static_cast<int>(instance.arcs.size()); ++e) {
        const auto& a = instance.arcs[e];
        edges[e].alive = true;
        attach_out(g, edges, a.tail, e);
        attach_in(g, edges, a.head, e);
    }

    std::vector<int> active_nodes(instance.n);
    std::vector<int> active_pos(instance.n);
    for (int i = 0; i < instance.n; ++i) {
        active_nodes[i] = i;
        active_pos[i] = i;
    }
    auto remove_active = [&](int u) {
        const int pos = active_pos[u];
        const int last = active_nodes.back();
        active_nodes[pos] = last;
        active_pos[last] = pos;
        active_nodes.pop_back();
        g[u].alive = false;
    };

    ClosureWorkspace closure;
    closure.indegree.assign(instance.n, 0);
    closure.sums.resize(instance.n);
    compute_succeeding_sums(g, edges, active_nodes, closure);

    // See pac.cpp for why this bypasses Ratio's GCD-normalising constructor:
    // find_best_fin/find_best_initial scan every live edge/node on every
    // iteration, and weights (hence weight-sum differences) are always
    // strictly positive, so a raw cross-multiply comparison is safe here.
    auto compare_raw = [](std::int64_t p1, std::int64_t w1, std::int64_t p2, std::int64_t w2) {
        const __int128 left = static_cast<__int128>(p1) * w2;
        const __int128 right = static_cast<__int128>(p2) * w1;
        return (left > right) - (left < right);
    };

    auto find_best_fin = [&]() {
        int best_edge = -1;
        std::int64_t best_p = 0, best_w = 1;
        for (int e = 0; e < static_cast<int>(edges.size()); ++e) {
            if (!edges[e].alive) continue;
            const int u = edges[e].from;
            const int v = edges[e].to;
            if (!g[u].alive || !g[v].alive) continue;
            const std::int64_t p = closure.sums[v].p - closure.sums[u].p;
            const std::int64_t w = closure.sums[v].w - closure.sums[u].w;
            const int cr = best_edge == -1 ? -1 : compare_raw(p, w, best_p, best_w);
            if (cr < 0 || (cr == 0 && e < best_edge)) {
                best_edge = e;
                best_p = p;
                best_w = w;
            }
        }
        return std::pair<int, Ratio>{best_edge, best_edge == -1 ? Ratio{0, 1} : Ratio{best_p, best_w}};
    };

    auto find_best_initial = [&]() {
        int best_node = -1;
        std::int64_t best_p = 0, best_w = 1;
        for (int u : active_nodes) {
            if (!g[u].alive || g[u].first_in != -1) continue;
            const int cr = best_node == -1 ? -1 : compare_raw(g[u].p, g[u].w, best_p, best_w);
            if (cr < 0 || (cr == 0 && u < best_node)) {
                best_node = u;
                best_p = g[u].p;
                best_w = g[u].w;
            }
        }
        return std::pair<int, Ratio>{best_node, best_node == -1 ? Ratio{0, 1} : Ratio{best_p, best_w}};
    };

    std::vector<int> mark(instance.n, 0);
    std::vector<int> reverse_stack;
    std::vector<int> reached_u;
    std::vector<int> reached_v;
    int stamp = 1;
    std::vector<ClosureLayer> increasing;

    while (!active_nodes.empty()) {
        const auto [best_edge, best_fin] = find_best_fin();
        const bool has_fin = best_edge != -1;
        const auto [best_initial_node, best_initial] = find_best_initial();
        if (best_initial_node == -1) throw std::runtime_error("working graph has no initial node");

        if (!has_fin || compare(best_initial, best_fin) < 0) {
            std::vector<int> best_initials;
            for (int u : active_nodes) {
                if (!g[u].alive || g[u].first_in != -1) continue;
                if (compare_raw(g[u].p, g[u].w, best_initial.num, best_initial.den) == 0) best_initials.push_back(u);
            }

            std::vector<int> macro_nodes;
            int macro_size = 0;
            for (int u : best_initials) macro_size += g[u].original_count;
            macro_nodes.reserve(macro_size);
            for (int u : best_initials) {
                for (int node = g[u].first_original; node != -1; node = next_original[node]) {
                    macro_nodes.push_back(node);
                }
            }
            increasing.push_back(make_closure_layer(instance, std::move(macro_nodes)));

            for (int u : best_initials) {
                reached_u.clear();
                collect_forward_reachable(u, g, edges, stamp++, mark, reached_u, reverse_stack);
                const auto delta = closure.sums[u];
                for (int x : reached_u) {
                    if (x == u) continue;
                    closure.sums[x].p -= delta.p;
                    closure.sums[x].w -= delta.w;
                }
                while (g[u].first_out != -1) {
                    const int e = g[u].first_out;
                    detach_out(g, edges, e);
                    detach_in(g, edges, e);
                    edges[e].alive = false;
                }
                remove_active(u);
            }
        } else {
            const int u = edges[best_edge].from;
            const int v = edges[best_edge].to;

            reached_u.clear();
            reached_v.clear();
            const int stamp_u = stamp++;
            collect_forward_reachable(u, g, edges, stamp_u, mark, reached_u, reverse_stack);
            const int stamp_v = stamp++;
            collect_forward_reachable(v, g, edges, stamp_v, mark, reached_v, reverse_stack);
            const ClosureSum delta{closure.sums[v].p - closure.sums[u].p,
                                   closure.sums[v].w - closure.sums[u].w};
            for (int x : reached_u) {
                if (mark[x] == stamp_v) continue;
                closure.sums[x].p += delta.p;
                closure.sums[x].w += delta.w;
            }

            while (g[v].first_in != -1) {
                const int e = g[v].first_in;
                const int pred = edges[e].from;
                detach_in(g, edges, e);
                detach_out(g, edges, e);
                if (pred != u) {
                    attach_out(g, edges, pred, e);
                    attach_in(g, edges, u, e);
                } else {
                    edges[e].alive = false;
                }
            }
            while (g[v].first_out != -1) {
                const int e = g[v].first_out;
                const int succ = edges[e].to;
                detach_out(g, edges, e);
                detach_in(g, edges, e);
                attach_out(g, edges, u, e);
                attach_in(g, edges, succ, e);
            }

            g[u].p += g[v].p;
            g[u].w += g[v].w;
            if (g[v].first_original != -1) {
                next_original[g[v].last_original] = g[u].first_original;
                g[u].first_original = g[v].first_original;
                g[u].original_count += g[v].original_count;
            }
            remove_active(v);
        }
    }

    ClosureLayerSequence sequence;
    sequence.layers.assign(increasing.rbegin(), increasing.rend());
    canonicalize(sequence);
    return sequence;
}

}  // namespace pcf
