#include "parametric_closure/algorithms.hpp"
#include "parametric_closure/instance.hpp"

#include <set>
#include <stdexcept>
#include <utility>
#include <vector>

// HPaC-Eager: same algorithm and same incremental closure-sum maintenance as
// HPaC (hpac.cpp), but the two priority structures (best wing / best final)
// are kept as std::set<>-based indexed structures with an erase-then-insert
// "touch" instead of HPaC's push-only lazy-deletion heap. This guarantees the
// two sets never hold more than one entry per currently alive edge/node, so
// memory is bounded by O(n) even on inputs where a lazy heap would
// accumulate O(touches) stale entries (e.g. a star graph, where every touch
// of the hub re-pushes one entry per incident edge). See hpac.cpp for the
// detailed explanation of each step; this file only documents what differs.

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

struct WingEntry {
    Ratio ratio;
    int edge = -1;
};

struct WingCmp {
    bool operator()(const WingEntry& a, const WingEntry& b) const {
        const int cr = compare(a.ratio, b.ratio);
        if (cr != 0) return cr > 0;  // larger ratio sorts first (set::begin() == "top")
        return a.edge < b.edge;      // edge is a unique key -> total order, no collisions
    }
};

struct FinalEntry {
    Ratio ratio;
    int node = -1;
};

struct FinalCmp {
    bool operator()(const FinalEntry& a, const FinalEntry& b) const {
        const int cr = compare(a.ratio, b.ratio);
        if (cr != 0) return cr > 0;
        return a.node < b.node;
    }
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

void compute_closure_sums(
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

    for (auto it = workspace.topo.rbegin(); it != workspace.topo.rend(); ++it) {
        const int u = *it;
        for (int e = g[u].first_out; e != -1; e = edges[e].next_out) {
            const int v = edges[e].to;
            workspace.sums[u].p += workspace.sums[v].p;
            workspace.sums[u].w += workspace.sums[v].w;
        }
    }
}

void collect_reverse_reachable(
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
        for (int e = g[u].first_in; e != -1; e = edges[e].next_in) {
            const int pred = edges[e].from;
            if (seen[pred] == stamp) continue;
            seen[pred] = stamp;
            stack.push_back(pred);
        }
    }
}

}  // namespace

ClosureLayerSequence compute_hpac_eager(const Instance& instance) {
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

    ClosureLayerSequence sequence;
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
    compute_closure_sums(g, edges, active_nodes, closure);

    // --- best-final structure: at most one live entry per node -----------
    std::set<FinalEntry, FinalCmp> final_set;
    std::vector<bool> has_final(instance.n, false);
    std::vector<std::set<FinalEntry, FinalCmp>::iterator> final_it(instance.n);
    auto sync_final = [&](int u) {
        if (has_final[u]) {
            final_set.erase(final_it[u]);
            has_final[u] = false;
        }
        if (g[u].alive && g[u].first_out == -1) {
            final_it[u] = final_set.insert({{g[u].p, g[u].w}, u}).first;
            has_final[u] = true;
        }
    };
    for (int i = 0; i < instance.n; ++i) sync_final(i);

    // --- best-wing structure: at most one live entry per edge -------------
    std::set<WingEntry, WingCmp> wing_set;
    std::vector<bool> has_wing(edges.size(), false);
    std::vector<std::set<WingEntry, WingCmp>::iterator> wing_it(edges.size());
    auto current_wing_ratio = [&](int e) {
        const int u = edges[e].from;
        const int v = edges[e].to;
        return Ratio{closure.sums[u].p - closure.sums[v].p,
                     closure.sums[u].w - closure.sums[v].w};
    };
    auto sync_wing = [&](int e) {
        if (has_wing[e]) {
            wing_set.erase(wing_it[e]);
            has_wing[e] = false;
        }
        if (edges[e].alive && g[edges[e].from].alive && g[edges[e].to].alive) {
            wing_it[e] = wing_set.insert({current_wing_ratio(e), e}).first;
            has_wing[e] = true;
        }
    };
    auto sync_node_edges = [&](int u) {
        for (int e = g[u].first_out; e != -1; e = edges[e].next_out) sync_wing(e);
        for (int e = g[u].first_in; e != -1; e = edges[e].next_in) sync_wing(e);
    };
    for (int e = 0; e < static_cast<int>(edges.size()); ++e) sync_wing(e);

    std::vector<int> mark(instance.n, 0);
    std::vector<int> reverse_stack;
    std::vector<int> ancestors_a;
    std::vector<int> ancestors_b;
    std::vector<int> affected;
    int stamp = 1;

    while (!active_nodes.empty()) {
        const bool has_wing_candidate = !wing_set.empty();
        const int best_edge = has_wing_candidate ? wing_set.begin()->edge : -1;
        const Ratio best_wing = has_wing_candidate ? wing_set.begin()->ratio : Ratio{0, 1};

        if (final_set.empty()) throw std::runtime_error("working graph has no final node");
        const Ratio best_final = final_set.begin()->ratio;

        if (!has_wing_candidate || compare(best_final, best_wing) > 0) {
            // --- EMIT layer -------------------------------------------
            std::vector<int> best_finals;
            while (!final_set.empty() && compare(final_set.begin()->ratio, best_final) == 0) {
                const int node = final_set.begin()->node;
                final_set.erase(final_set.begin());
                has_final[node] = false;
                best_finals.push_back(node);
            }
            std::vector<int> macro_nodes;
            int macro_size = 0;
            for (int f : best_finals) {
                macro_size += g[f].original_count;
            }
            macro_nodes.reserve(macro_size);
            for (int f : best_finals) {
                for (int node = g[f].first_original; node != -1; node = next_original[node]) {
                    macro_nodes.push_back(node);
                }
            }
            sequence.layers.push_back(make_closure_layer(instance, macro_nodes));
            std::vector<int> final_candidates;
            affected.clear();
            for (int f : best_finals) {
                ancestors_a.clear();
                collect_reverse_reachable(f, g, edges, stamp++, mark, ancestors_a, reverse_stack);
                const auto delta = closure.sums[f];
                for (int x : ancestors_a) {
                    if (x == f) continue;
                    closure.sums[x].p -= delta.p;
                    closure.sums[x].w -= delta.w;
                    affected.push_back(x);
                }
                while (g[f].first_in != -1) {
                    const int e = g[f].first_in;
                    const int pred = edges[e].from;
                    detach_in(g, edges, e);
                    detach_out(g, edges, e);
                    edges[e].alive = false;
                    sync_wing(e);  // retire the edge (no reinsertion: it's dead)
                    final_candidates.push_back(pred);
                }
                remove_active(f);
            }
            for (int x : affected) sync_node_edges(x);
            for (int pred : final_candidates) sync_final(pred);
        } else {
            // --- CONTRACT arc u -> v ---------------------------------------
            const int u = edges[best_edge].from;
            const int v = edges[best_edge].to;
            ancestors_a.clear();
            ancestors_b.clear();
            affected.clear();
            const int stamp_v = stamp++;
            collect_reverse_reachable(v, g, edges, stamp_v, mark, ancestors_a, reverse_stack);
            const int stamp_u = stamp++;
            collect_reverse_reachable(u, g, edges, stamp_u, mark, ancestors_b, reverse_stack);
            const ClosureSum delta{closure.sums[u].p - closure.sums[v].p,
                                   closure.sums[u].w - closure.sums[v].w};
            for (int x : ancestors_a) {
                if (mark[x] == stamp_u) continue;
                closure.sums[x].p += delta.p;
                closure.sums[x].w += delta.w;
                affected.push_back(x);
            }
            while (g[u].first_in != -1) {
                const int e = g[u].first_in;
                detach_in(g, edges, e);
                attach_in(g, edges, v, e);
                sync_wing(e);
            }
            while (g[u].first_out != -1) {
                const int e = g[u].first_out;
                const int succ = edges[e].to;
                detach_out(g, edges, e);
                if (succ != v) {
                    attach_out(g, edges, v, e);
                    sync_wing(e);
                } else {
                    detach_in(g, edges, e);
                    edges[e].alive = false;
                    sync_wing(e);  // retire the self-loop edge
                }
            }
            g[v].p += g[u].p;
            g[v].w += g[u].w;
            if (g[u].first_original != -1) {
                next_original[g[u].last_original] = g[v].first_original;
                g[v].first_original = g[u].first_original;
                g[v].original_count += g[u].original_count;
            }
            sync_final(v);
            for (int x : affected) sync_node_edges(x);
            remove_active(u);
        }
    }
    return sequence;
}

}  // namespace pcf
