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

// A closure layer is one increment M_r \ M_{r-1} of the nested optimal
// closure sequence -- itself the maximal closure of the residual instance
// at lambda = lambda_r (see the manuscript's Proposition on optimal ratios).
struct ClosureLayer {
    std::vector<int> nodes;
    std::int64_t profit = 0;
    std::int64_t weight = 0;

    Ratio ratio() const { return {profit, weight}; }
};

struct ClosureLayerSequence {
    std::vector<ClosureLayer> layers;
};

}  // namespace pcf
