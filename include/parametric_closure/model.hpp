#pragma once

#include "parametric_closure/rational.hpp"

#include <cstdint>
#include <vector>

namespace pcf {

struct Arc {
    int tail = -1;
    int head = -1;
};

// Parametric maximum-closure instance. Arc (u,v) means x_u <= x_v.
struct Instance {
    int n = 0;
    std::vector<std::int64_t> profit;
    std::vector<std::int64_t> weight;
    std::vector<Arc> arcs;
};

struct Macroitem {
    std::vector<int> nodes;
    std::int64_t profit = 0;
    std::int64_t weight = 0;

    Ratio ratio() const { return {profit, weight}; }
};

struct MacroitemSequence {
    std::vector<Macroitem> macroitems;
};

}  // namespace pcf
