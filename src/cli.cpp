#include "parametric_closure/pcf.hpp"

#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char* argv[]) {
    try {
        std::string instance_path;
        std::string algorithm;
        for (int i = 1; i < argc; ++i) {
            const std::string flag = argv[i];
            if ((flag == "--instance" || flag == "--algorithm") && i + 1 < argc) {
                const std::string value = argv[++i];
                if (flag == "--instance") instance_path = value;
                else algorithm = value;
            } else {
                throw std::invalid_argument("usage: pcf_solve --instance FILE --algorithm fma|dfma|hfma|hima|dhfma|homa|rac");
            }
        }
        if (instance_path.empty() || algorithm.empty()) throw std::invalid_argument("missing required option");
        const auto instance = pcf::read_instance(instance_path);
        pcf::MacroitemSequence result;
        if (algorithm == "fma") result = pcf::compute_fma(instance);
        else if (algorithm == "dfma") result = pcf::compute_dfma(instance);
        else if (algorithm == "hfma") result = pcf::compute_hfma(instance);
        else if (algorithm == "hima") result = pcf::compute_hima(instance);
        else if (algorithm == "dhfma") result = pcf::compute_dhfma(instance);
        else if (algorithm == "homa") result = pcf::compute_homa(instance);
        else if (algorithm == "rac") result = pcf::compute_rac(instance);
        else throw std::invalid_argument("unknown closure algorithm: " + algorithm);
        pcf::write_sequence(std::cout, result);
    } catch (const std::exception& error) {
        std::cerr << "pcf_solve: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
