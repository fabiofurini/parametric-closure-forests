#include "parametric_closure/pcf.hpp"

#include <algorithm>
#include <iostream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <vector>

namespace {

void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}

bool same_sequence(const pcf::ClosureLayerSequence& lhs, const pcf::ClosureLayerSequence& rhs) {
    if (lhs.layers.size() != rhs.layers.size()) return false;
    for (std::size_t i = 0; i < lhs.layers.size(); ++i) {
        if (lhs.layers[i].nodes != rhs.layers[i].nodes) return false;
        if (!(lhs.layers[i].ratio() == rhs.layers[i].ratio())) return false;
    }
    return true;
}

pcf::Instance mixed_tree() {
    return {4, {10, 3, 8, -2}, {2, 1, 4, 1}, {{0, 1}, {2, 1}, {3, 2}}};
}

void require_well_formed(const pcf::Instance& instance, const pcf::ClosureLayerSequence& sequence) {
    std::vector<int> rank(instance.n, -1);
    for (std::size_t r = 0; r < sequence.layers.size(); ++r) {
        const auto& layer = sequence.layers[r];
        if (layer.nodes.empty()) throw std::runtime_error("empty layer");
        if (layer.weight <= 0) throw std::runtime_error("non-positive layer weight");
        for (const int v : layer.nodes) {
            if (v < 0 || v >= instance.n || rank[v] != -1) throw std::runtime_error("layers do not partition items");
            rank[v] = static_cast<int>(r);
        }
        if (r > 0 && pcf::compare(sequence.layers[r - 1].ratio(), layer.ratio()) <= 0)
            throw std::runtime_error("layer ratios are not strictly decreasing");
    }
    for (const int r : rank) if (r < 0) throw std::runtime_error("missing item in layer sequence");
    for (const auto& arc : instance.arcs) {
        if (rank[arc.tail] < rank[arc.head]) throw std::runtime_error("prefix is not a closure");
    }
}

bool is_closed_mask(const pcf::Instance& instance, unsigned mask) {
    for (const auto& arc : instance.arcs) {
        if ((mask & (1U << arc.tail)) != 0U && (mask & (1U << arc.head)) == 0U) return false;
    }
    return true;
}

__int128 value_at(const pcf::Instance& instance, unsigned mask, const pcf::Ratio& lambda) {
    __int128 profit = 0;
    __int128 weight = 0;
    for (int v = 0; v < instance.n; ++v) {
        if ((mask & (1U << v)) == 0U) continue;
        profit += instance.profit[v];
        weight += instance.weight[v];
    }
    return profit * lambda.den - static_cast<__int128>(lambda.num) * weight;
}

void require_optimal_mask(const pcf::Instance& instance, unsigned mask, const pcf::Ratio& lambda) {
    const __int128 value = value_at(instance, mask, lambda);
    for (unsigned candidate = 0; candidate < (1U << instance.n); ++candidate) {
        if (is_closed_mask(instance, candidate) && value_at(instance, candidate, lambda) > value)
            throw std::runtime_error("layer prefix is not maximum closure at tested lambda");
    }
}

void require_matches_enumeration(const pcf::Instance& instance, const pcf::ClosureLayerSequence& sequence) {
    if (instance.n > 20) throw std::runtime_error("enumeration oracle called beyond its safe limit");
    unsigned prefix = 0U;
    for (std::size_t r = 0; r < sequence.layers.size(); ++r) {
        const auto& layer = sequence.layers[r];
        for (const int v : layer.nodes) prefix |= 1U << v;
        const pcf::Ratio breakpoint = layer.ratio();
        require_optimal_mask(instance, prefix, breakpoint);
        pcf::Ratio sample;
        if (r + 1 < sequence.layers.size()) {
            const auto next = sequence.layers[r + 1].ratio();
            sample = {breakpoint.num * next.den + next.num * breakpoint.den,
                      2 * breakpoint.den * next.den};
        } else {
            sample = {breakpoint.num - breakpoint.den, breakpoint.den};
        }
        require_optimal_mask(instance, prefix, sample);
    }
    const auto first = sequence.layers.front().ratio();
    require_optimal_mask(instance, 0U, {first.num + first.den, first.den});
}

pcf::Instance random_forest(int n, std::mt19937& generator) {
    std::uniform_int_distribution<int> profit(-12, 17);
    std::uniform_int_distribution<int> weight(1, 9);
    std::bernoulli_distribution link(0.78);
    std::bernoulli_distribution direction(0.5);
    pcf::Instance instance;
    instance.n = n;
    instance.profit.resize(n);
    instance.weight.resize(n);
    for (int v = 0; v < n; ++v) {
        instance.profit[v] = profit(generator);
        instance.weight[v] = weight(generator);
        if (v > 0 && link(generator)) {
            std::uniform_int_distribution<int> parent(0, v - 1);
            const int u = parent(generator);
            instance.arcs.push_back(direction(generator) ? pcf::Arc{u, v} : pcf::Arc{v, u});
        }
    }
    return instance;
}

pcf::Instance random_out_forest(int n, std::mt19937& generator) {
    std::uniform_int_distribution<int> profit(-12, 17);
    std::uniform_int_distribution<int> weight(1, 9);
    std::bernoulli_distribution link(0.78);
    pcf::Instance instance;
    instance.n = n;
    instance.profit.resize(n);
    instance.weight.resize(n);
    for (int v = 0; v < n; ++v) {
        instance.profit[v] = profit(generator);
        instance.weight[v] = weight(generator);
        if (v > 0 && link(generator)) {
            std::uniform_int_distribution<int> parent(0, v - 1);
            instance.arcs.push_back({parent(generator), v});
        }
    }
    return instance;
}

void test_rac_differential() {
    std::mt19937 generator(20260828);
    for (int n = 1; n <= 100; ++n) {
        for (int repetition = 0; repetition < 20; ++repetition) {
            const auto instance = random_forest(n, generator);
            pcf::validate_instance(instance);
            const auto pac = pcf::compute_pac(instance);
            const auto dpac = pcf::compute_dpac(instance);
            const auto hpac = pcf::compute_hpac(instance);
            const auto dhpac = pcf::compute_dhpac(instance);
            const auto rac = pcf::compute_rac(instance);
            require_well_formed(instance, pac);
            require_well_formed(instance, dpac);
            require_well_formed(instance, hpac);
            require_well_formed(instance, dhpac);
            require_well_formed(instance, rac);
            require(same_sequence(pac, dpac), "PaC and DPaC differ on random forest");
            require(same_sequence(pac, hpac), "PaC and HPaC differ on random forest");
            require(same_sequence(dhpac, hpac), "DHPaC and HPaC differ on random forest");
            require(same_sequence(pac, rac), "PaC and RaC differ on random forest");
        }
    }
}

void test_rac_small_random_enumeration() {
    std::mt19937 generator(11072026);
    std::uniform_int_distribution<int> size(2, 11);
    for (int repetition = 0; repetition < 10000; ++repetition) {
        const auto instance = random_forest(size(generator), generator);
        const auto pac = pcf::compute_pac(instance);
        const auto dpac = pcf::compute_dpac(instance);
        const auto hpac = pcf::compute_hpac(instance);
        const auto dhpac = pcf::compute_dhpac(instance);
        const auto rac = pcf::compute_rac(instance);
        require_well_formed(instance, pac);
        require_well_formed(instance, dpac);
        require_well_formed(instance, hpac);
        require_well_formed(instance, dhpac);
        require_well_formed(instance, rac);
        require_matches_enumeration(instance, pac);
        require_matches_enumeration(instance, dpac);
        require_matches_enumeration(instance, hpac);
        require_matches_enumeration(instance, dhpac);
        require_matches_enumeration(instance, rac);
        require(same_sequence(dhpac, hpac), "DHPaC and HPaC differ on enumerated random forest");
        require(same_sequence(dpac, hpac), "DPaC and HPaC differ on enumerated random forest");
        require(same_sequence(pac, hpac), "PaC and HPaC differ on enumerated random forest");
        require(same_sequence(pac, rac), "PaC and RaC differ on enumerated random forest");
    }
}

void test_dhpac_against_hpac() {
    std::mt19937 generator(28082026);
    std::uniform_int_distribution<int> small_size(2, 11);
    for (int repetition = 0; repetition < 6000; ++repetition) {
        const auto instance = random_out_forest(small_size(generator), generator);
        require(pcf::is_out_forest(instance), "generated instance must be an out-forest");
        const auto dpac = pcf::compute_dpac(instance);
        const auto hpac = pcf::compute_hpac(instance);
        const auto dhpac = pcf::compute_dhpac(instance);
        const auto hopac = pcf::compute_hopac(instance);
        require_well_formed(instance, dhpac);
        require_matches_enumeration(instance, dhpac);
        require(same_sequence(dpac, hpac), "DPaC and HPaC differ on enumerated out-forest");
        require(same_sequence(dhpac, hpac), "DHPaC and HPaC differ on enumerated out-forest");
        require(same_sequence(dhpac, hopac), "DHPaC and HOPaC alias differ");
    }
    for (int n = 1; n <= 500; ++n) {
        for (int repetition = 0; repetition < 4; ++repetition) {
            const auto instance = random_out_forest(n, generator);
            const auto hpac = pcf::compute_hpac(instance);
            const auto dhpac = pcf::compute_dhpac(instance);
            require_well_formed(instance, dhpac);
            require(same_sequence(dhpac, hpac), "DHPaC and HPaC differ on large out-forest");
        }
    }
}

pcf::Instance structured_tree(int n, const std::string& shape) {
    pcf::Instance instance;
    instance.n = n;
    instance.profit.resize(n);
    instance.weight.resize(n);
    for (int v = 0; v < n; ++v) {
        instance.profit[v] = ((37 * v + 11) % 31) - 15;
        instance.weight[v] = 1 + ((19 * v + 7) % 11);
    }
    for (int v = 1; v < n; ++v) {
        const int parent = shape == "star" ? 0 : (shape == "binary" ? (v - 1) / 2 : v - 1);
        instance.arcs.push_back((v % 2 == 0) ? pcf::Arc{parent, v} : pcf::Arc{v, parent});
    }
    return instance;
}

void test_structured_rac_differential() {
    for (const std::string shape : {"path", "binary", "star"}) {
        for (const int n : {1, 2, 3, 4, 7, 16, 63, 128, 257}) {
            const auto instance = structured_tree(n, shape);
            const auto pac = pcf::compute_pac(instance);
            const auto dpac = pcf::compute_dpac(instance);
            const auto hpac = pcf::compute_hpac(instance);
            const auto dhpac = pcf::compute_dhpac(instance);
            const auto rac = pcf::compute_rac(instance);
            require_well_formed(instance, pac);
            require_well_formed(instance, dpac);
            require_well_formed(instance, hpac);
            require_well_formed(instance, dhpac);
            require_well_formed(instance, rac);
            require(same_sequence(dpac, hpac), "DPaC and HPaC differ on structured tree");
            require(same_sequence(dhpac, hpac), "DHPaC and HPaC differ on structured tree");
            require(same_sequence(pac, hpac), "PaC and HPaC differ on structured tree");
            require(same_sequence(pac, rac), "PaC and RaC differ on structured tree");
        }
    }
}

void test_rac_exhaustive_small() {
    for (int n = 1; n <= 4; ++n) {
        int profit_cases = 1;
        for (int v = 0; v < n; ++v) profit_cases *= 3;
        std::vector<std::pair<int, int>> possible_edges;
        for (int u = 0; u < n; ++u) for (int v = u + 1; v < n; ++v) possible_edges.push_back({u, v});
        for (int subset = 0; subset < (1 << static_cast<int>(possible_edges.size())); ++subset) {
            std::vector<std::pair<int, int>> edges;
            for (int e = 0; e < static_cast<int>(possible_edges.size()); ++e)
                if (subset & (1 << e)) edges.push_back(possible_edges[e]);
            pcf::Instance undirected;
            undirected.n = n;
            undirected.profit.assign(n, 0);
            undirected.weight.assign(n, 1);
            for (const auto [u, v] : edges) undirected.arcs.push_back({u, v});
            if (!pcf::is_forest(undirected)) continue;
            for (int direction = 0; direction < (1 << static_cast<int>(edges.size())); ++direction) {
                for (int profit_code = 0; profit_code < profit_cases; ++profit_code) {
                    for (int weight_code = 0; weight_code < (1 << n); ++weight_code) {
                        pcf::Instance instance;
                        instance.n = n;
                        instance.profit.resize(n);
                        instance.weight.resize(n);
                        int code = profit_code;
                        for (int v = 0; v < n; ++v) {
                            instance.profit[v] = (code % 3) - 1;
                            instance.weight[v] = 1 + ((weight_code >> v) & 1);
                            code /= 3;
                        }
                        for (int e = 0; e < static_cast<int>(edges.size()); ++e) {
                            const auto [u, v] = edges[e];
                            instance.arcs.push_back((direction & (1 << e)) ? pcf::Arc{u, v} : pcf::Arc{v, u});
                        }
                        const auto pac = pcf::compute_pac(instance);
                        const auto dpac = pcf::compute_dpac(instance);
                        const auto hpac = pcf::compute_hpac(instance);
                        const auto dhpac = pcf::compute_dhpac(instance);
                        const auto rac = pcf::compute_rac(instance);
                        require_well_formed(instance, pac);
                        require_well_formed(instance, dpac);
                        require_well_formed(instance, hpac);
                        require_well_formed(instance, dhpac);
                        require_well_formed(instance, rac);
                        require_matches_enumeration(instance, pac);
                        require_matches_enumeration(instance, dpac);
                        require_matches_enumeration(instance, hpac);
                        require_matches_enumeration(instance, dhpac);
                        require_matches_enumeration(instance, rac);
                        require(same_sequence(dpac, hpac), "DPaC and HPaC differ on exhaustive small forest");
                        require(same_sequence(dhpac, hpac), "DHPaC and HPaC differ on exhaustive small forest");
                        require(same_sequence(pac, hpac), "PaC and HPaC differ on exhaustive small forest");
                        require(same_sequence(pac, rac), "PaC and RaC differ on exhaustive small forest");
                    }
                }
            }
        }
    }
}

}  // namespace

int main() {
    try {
        const auto instance = mixed_tree();
        pcf::validate_instance(instance);
        require(pcf::is_forest(instance), "fixture must be a forest");
        require(pcf::is_in_forest(instance), "fixture must be an in-forest");
        const auto pac = pcf::compute_pac(instance);
        const auto dpac = pcf::compute_dpac(instance);
        const auto hpac = pcf::compute_hpac(instance);
        const auto dhpac = pcf::compute_dhpac(instance);
        const auto hipac = pcf::compute_hipac(instance);
        const auto rac = pcf::compute_rac(instance);
        require(same_sequence(pac, hpac), "PaC and HPaC differ");
        require(same_sequence(pac, dpac), "PaC and DPaC differ");
        require(same_sequence(hpac, dhpac), "HPaC and DHPaC differ");
        require(same_sequence(pac, hipac), "PaC and HIPaC differ");
        require(same_sequence(pac, rac), "PaC and RaC differ");
        require_well_formed(instance, pac);
        require_well_formed(instance, rac);
        test_rac_exhaustive_small();
        test_rac_small_random_enumeration();
        test_dhpac_against_hpac();
        test_rac_differential();
        test_structured_rac_differential();
        std::cout << "pcf tests passed\n";
    } catch (const std::exception& error) {
        std::cerr << "pcf test failure: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
