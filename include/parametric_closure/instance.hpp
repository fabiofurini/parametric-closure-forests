#pragma once

#include "parametric_closure/model.hpp"

#include <iosfwd>
#include <string>

namespace pcf {

bool is_dag(const Instance& instance);
bool is_forest(const Instance& instance);
bool is_in_forest(const Instance& instance);
bool is_out_forest(const Instance& instance);
void validate_instance(const Instance& instance, bool require_forest = true);

ClosureLayer make_closure_layer(const Instance& instance, std::vector<int> nodes);
void canonicalize(ClosureLayerSequence& sequence);

Instance read_instance(const std::string& path);
void write_sequence(std::ostream& out, const ClosureLayerSequence& sequence);

}  // namespace pcf
