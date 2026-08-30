#pragma once

#include "parametric_closure/model.hpp"

#include <cstdint>

namespace pcf {

struct RaCStats {
    std::uint64_t clusters = 0;
    std::uint64_t joins = 0;
    std::uint64_t internalizations = 0;
    std::uint64_t envelope_sum_calls = 0;
    std::uint64_t envelope_max_calls = 0;
    std::uint64_t hull_calls = 0;
    std::uint64_t lines_scanned = 0;
    std::uint64_t line_comparisons = 0;
    std::uint64_t rational_comparisons = 0;
    std::uint64_t pieces_stored = 0;
    std::uint64_t topdown_events = 0;
    std::uint64_t topdown_scans = 0;
    std::uint64_t expanded_vertices = 0;
    std::uint64_t expanded_edges = 0;
    std::uint64_t rounds = 0;
    std::uint64_t max_cluster_depth = 0;
    std::uint64_t estimated_bytes = 0;
};

ClosureLayerSequence compute_pac(const Instance& instance);
ClosureLayerSequence compute_dpac(const Instance& instance);
ClosureLayerSequence compute_hpac(const Instance& instance);
// HPaC variant with an eager (erase-then-insert) update-in-place priority
// structure instead of HPaC's push-only lazy-deletion heap: memory is always
// O(n), never O(number of touch operations). See src/hpac_eager.cpp.
ClosureLayerSequence compute_hpac_eager(const Instance& instance);
// HPaC variant that keeps HPaC's lazy-deletion heap but periodically rebuilds
// it once it grows past a constant factor of the live candidate count, so
// memory stays O(n) at the cost of an amortized rebuild. See
// src/hpac_bounded.cpp.
ClosureLayerSequence compute_hpac_bounded(const Instance& instance);
ClosureLayerSequence compute_hipac(const Instance& instance);
// Dual heap-based PaC for a general directed forest.
ClosureLayerSequence compute_dhpac(const Instance& instance);
// Specialized dual heap algorithm for out-forests, called HOPaC in the manuscript.
ClosureLayerSequence compute_hopac(const Instance& instance);
ClosureLayerSequence compute_rac(const Instance& instance, RaCStats* stats = nullptr);

}  // namespace pcf
