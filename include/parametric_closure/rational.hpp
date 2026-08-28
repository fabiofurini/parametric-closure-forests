#pragma once

#include <cstdint>
#include <numeric>
#include <stdexcept>

namespace pcf {

struct Ratio {
    std::int64_t num = 0;
    std::int64_t den = 1;

    Ratio() = default;
    Ratio(std::int64_t numerator, std::int64_t denominator) : num(numerator), den(denominator) {
        if (den == 0) throw std::invalid_argument("rational denominator is zero");
        if (den < 0) {
            num = -num;
            den = -den;
        }
        const auto divisor = std::gcd(num, den);
        num /= divisor;
        den /= divisor;
    }
};

inline int compare(const Ratio& lhs, const Ratio& rhs) {
    const __int128 left = static_cast<__int128>(lhs.num) * rhs.den;
    const __int128 right = static_cast<__int128>(rhs.num) * lhs.den;
    return (left > right) - (left < right);
}

inline bool operator==(const Ratio& lhs, const Ratio& rhs) {
    return lhs.num == rhs.num && lhs.den == rhs.den;
}

}  // namespace pcf
