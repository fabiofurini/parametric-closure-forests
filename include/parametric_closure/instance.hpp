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

Macroitem make_macroitem(const Instance& instance, std::vector<int> nodes);
void canonicalize(MacroitemSequence& sequence);

Instance read_instance(const std::string& path);
void write_sequence(std::ostream& out, const MacroitemSequence& sequence);

}  // namespace pcf
