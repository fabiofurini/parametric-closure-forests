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
                throw std::invalid_argument("usage: pcf_solve --instance FILE --algorithm pac|dpac|hpac|hpac_lazy|hpac_eager|hpac_bounded|hipac|dhpac|hopac|rac");
            }
        }
        if (instance_path.empty() || algorithm.empty()) throw std::invalid_argument("missing required option");
        const auto instance = pcf::read_instance(instance_path);
        pcf::ClosureLayerSequence result;
        if (algorithm == "pac") result = pcf::compute_pac(instance);
        else if (algorithm == "dpac") result = pcf::compute_dpac(instance);
        else if (algorithm == "hpac") result = pcf::compute_hpac(instance);
        else if (algorithm == "hpac_lazy") result = pcf::compute_hpac_lazy(instance);
        else if (algorithm == "hpac_eager") result = pcf::compute_hpac_eager(instance);
        else if (algorithm == "hpac_bounded") result = pcf::compute_hpac_bounded(instance);
        else if (algorithm == "hipac") result = pcf::compute_hipac(instance);
        else if (algorithm == "dhpac") result = pcf::compute_dhpac(instance);
        else if (algorithm == "hopac") result = pcf::compute_hopac(instance);
        else if (algorithm == "rac") result = pcf::compute_rac(instance);
        else throw std::invalid_argument("unknown closure algorithm: " + algorithm);
        pcf::write_sequence(std::cout, result);
    } catch (const std::exception& error) {
        std::cerr << "pcf_solve: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
