#pragma once

#include "parametric_closure/model.hpp"

#include <algorithm>
#include <cstdint>
#include <queue>
#include <set>
#include <utility>
#include <vector>

namespace pcf {

inline Macroitem build_macroitem(const Instance& instance, std::vector<int> nodes) {
    std::sort(nodes.begin(), nodes.end());
    Macroitem macroitem;
    macroitem.nodes = std::move(nodes);
    for (const int v : macroitem.nodes) {
        macroitem.profit += instance.profit[v];
        macroitem.weight += instance.weight[v];
    }
    return macroitem;
}

struct WorkNode {
    bool alive = true;
    std::int64_t profit = 0;
    std::int64_t weight = 0;
    std::vector<int> original_nodes;
    std::set<int> out;
    std::set<int> in;
};

inline std::vector<std::vector<int>> outgoing(const Instance& instance) {
    std::vector<std::vector<int>> out(instance.n);
    for (const auto& arc : instance.arcs) out[arc.tail].push_back(arc.head);
    return out;
}

}  // namespace pcf
